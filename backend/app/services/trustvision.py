import hashlib
import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image, ImageStat
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.trustvision import TrustVisionEvidence, TrustVisionFraudCase, TrustVisionOCRResult, TrustVisionQRScan
from app.models.advocacy import AdvocacyProduct
from app.services.advocacy import verify_product_qr_token

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_TEXT_CHARS = 30000

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def perceptual_hash(data: bytes) -> str:
    image = Image.open(io.BytesIO(data)).convert("L").resize((8, 8))
    pixels = list(image.tobytes())
    average = sum(pixels) / len(pixels)
    bits = "".join("1" if value >= average else "0" for value in pixels)
    return f"{int(bits, 2):016x}"

def hamming_distance(first: str, second: str) -> int:
    return (int(first, 16) ^ int(second, 16)).bit_count()

def image_quality(data: bytes) -> tuple[str, list[str]]:
    image = Image.open(io.BytesIO(data)).convert("L")
    width, height = image.size
    reasons = []
    if min(width, height) < 300:
        reasons.append("LOW_RESOLUTION")
    variance = ImageStat.Stat(image).var[0]
    if variance < 30:
        reasons.append("LOW_CONTRAST_OR_BLUR")
    if width * height < 100_000:
        reasons.append("SMALL_IMAGE_AREA")
    return ("needs_review" if reasons else "acceptable", reasons)

def extract_invoice_fields(text: str) -> dict:
    compact = " ".join(text.split())
    invoice = re.search(r"(?i)(?:invoice\s*(?:no|number|#)?|bill\s*(?:no|number|#)?)\s*[:.-]?\s*([A-Z0-9/-]{3,})", compact)
    date = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", compact)
    amount = re.search(r"(?i)(?:grand\s*total|total\s*amount|net\s*amount|total)\s*[:₹Rs. ]*([0-9,]+(?:\.\d{1,2})?)", compact)
    quantity = re.search(r"(?i)(?:qty|quantity)\s*[:.-]?\s*(\d{1,6})", compact)
    sku = re.search(r"(?i)(?:sku|item\s*code|product\s*code)\s*[:.-]?\s*([A-Z0-9_-]{3,})", compact)
    dealer = re.search(r"(?i)(?:dealer|seller|supplier)\s*[:.-]?\s*(.{3,80}?)(?=\s+(?:SKU|Qty|Quantity|Invoice|Date|Total)\b|$)", compact)
    product = re.search(r"(?i)(?:product|item\s*name)\s*[:.-]?\s*(.{3,100}?)(?=\s+(?:SKU|Qty|Quantity|Invoice|Date|Total)\b|$)", compact)
    return {
        "invoice_number": invoice.group(1) if invoice else "",
        "dealer_name": dealer.group(1).strip() if dealer else "",
        "invoice_date": date.group(1) if date else "",
        "product_name": product.group(1).strip() if product else "",
        "sku": sku.group(1) if sku else "",
        "quantity": int(quantity.group(1)) if quantity else None,
        "total_amount": amount.group(1) if amount else "",
    }

def run_ocr(data: bytes) -> dict:
    if not settings.trustvision_ocr_enabled:
        return {"status": "disabled", "text": "", "confidence": 0, **extract_invoice_fields("")}
    try:
        import pytesseract
        image = Image.open(io.BytesIO(data)).convert("RGB")
        words = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        valid_conf = [int(float(v)) for v in words.get("conf", []) if str(v).strip() not in ("", "-1") and float(v) >= 0]
        text = pytesseract.image_to_string(image)[:MAX_TEXT_CHARS]
        confidence = round(sum(valid_conf) / len(valid_conf)) if valid_conf else 0
        fields = extract_invoice_fields(text)
        return {"status": "completed" if text.strip() else "low_confidence",
                "text": text, "confidence": confidence, **fields}
    except Exception as exc:
        # Missing Tesseract binary/model must never be represented as successful OCR.
        return {"status": "unavailable", "text": "", "confidence": 0,
                "error_code": type(exc).__name__, **extract_invoice_fields("")}

def decode_qr(data: bytes) -> str:
    import cv2
    import numpy as np
    image = Image.open(io.BytesIO(data)).convert("RGB")
    array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    value, points, _ = detector.detectAndDecode(array)
    return value.strip() if value else ""

def score_risk(*, exact_duplicate: bool = False, near_duplicate: bool = False,
               low_ocr: bool = False, missing_invoice: bool = False,
               duplicate_invoice: bool = False, qr_replay: bool = False,
               suspicious_image_quality: bool = False) -> dict:
    score = 0
    reasons = []
    rules = [
        (exact_duplicate, 75, "EXACT_IMAGE_DUPLICATE"),
        (duplicate_invoice, 65, "DUPLICATE_INVOICE_REFERENCE"),
        (qr_replay, 35, "UNUSUAL_QR_SCAN_FREQUENCY"),
        (near_duplicate, 35, "POSSIBLE_REUSED_IMAGE"),
        (missing_invoice, 20, "INVOICE_NUMBER_NOT_DETECTED"),
        (low_ocr, 15, "LOW_OCR_CONFIDENCE"),
        (suspicious_image_quality, 10, "IMAGE_QUALITY_WARNING"),
    ]
    for active, points, code in rules:
        if active:
            score += points
            reasons.append(code)
    score = min(100, score)
    level = "high" if score >= 70 else "medium" if score >= 35 else "low"
    return {"risk_score": score, "risk_level": level, "reason_codes": reasons}

def create_case(db: Session, *, evidence_id: str | None, mechanic_id: str | None,
                case_type: str, risk: dict, evidence_refs: list[str] | None = None):
    if risk["risk_score"] <= 0:
        return None
    case = TrustVisionFraudCase(evidence_id=evidence_id, mechanic_id=mechanic_id,
        case_type=case_type, risk_score=risk["risk_score"], risk_level=risk["risk_level"],
        reason_codes_json=json.dumps(risk["reason_codes"]),
        evidence_refs_json=json.dumps(evidence_refs or []), status="pending_review")
    db.add(case)
    return case

def find_duplicate(db: Session, digest: str, phash: str) -> tuple[TrustVisionEvidence | None, bool]:
    exact = db.scalar(select(TrustVisionEvidence).where(TrustVisionEvidence.sha256 == digest).limit(1))
    if exact:
        return exact, True
    candidates = db.scalars(select(TrustVisionEvidence).where(
        TrustVisionEvidence.perceptual_hash.is_not(None)).order_by(TrustVisionEvidence.created_at.desc()).limit(250)).all()
    for candidate in candidates:
        if hamming_distance(candidate.perceptual_hash, phash) <= 4:
            return candidate, False
    return None, False

def qr_replay_count(db: Session, token_hash: str, scanned_by: str) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    rows = db.scalars(select(TrustVisionQRScan).where(
        TrustVisionQRScan.token_hash == token_hash,
        TrustVisionQRScan.scanned_by == scanned_by,
        TrustVisionQRScan.created_at >= cutoff)).all()
    return len(rows) + 1
