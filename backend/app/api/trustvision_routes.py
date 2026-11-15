import hashlib
import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from PIL import Image, UnidentifiedImageError
from app.api.deps import current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.models import User, Mechanic
from app.models.advocacy import AdvocacyProduct, AdvocacyEvidence, FitmentRecord, AdvocacyRecommendation, DealerSalesRecord
from app.models.trustvision import TrustVisionEvidence, TrustVisionOCRResult, TrustVisionFraudCase, TrustVisionQRScan
from app.schemas.trustvision import FraudCaseDecision, OCRCorrection
from app.services.advocacy import verify_product_qr_token
from app.services.object_storage import get_object_storage, StorageError
from app.services.trustvision import (
    ALLOWED_MIME, sha256_hex, perceptual_hash, image_quality, run_ocr,
    decode_qr, score_risk, create_case, find_duplicate, qr_replay_count
)

router = APIRouter()
ADMIN = ("administrator", "eurogrip_admin")

def _mechanic(user: User, db: Session):
    return db.scalar(select(Mechanic).where(Mechanic.user_id == user.id))

def _safe_storage_root() -> Path:
    root = Path(settings.trustvision_storage_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    return root

def _validate_source(user: User, db: Session, source_type: str, source_id: str):
    if not source_type and not source_id:
        return
    if source_type not in ("fitment", "recommendation") or not source_id:
        raise HTTPException(status_code=422, detail="Source must be a fitment or recommendation reference.")
    mechanic = _mechanic(user, db)
    if not mechanic:
        raise HTTPException(status_code=403, detail="Only a mechanic can attach evidence to a mechanic activity.")
    if source_type == "fitment":
        item = db.get(FitmentRecord, source_id)
    else:
        item = db.get(AdvocacyRecommendation, source_id)
    if not item or item.mechanic_id != mechanic.id:
        raise HTTPException(status_code=404, detail="Source activity not found.")

@router.post("/trustvision/evidence", status_code=201)
async def upload_evidence(
    evidence_kind: str = Form(...),
    source_type: str = Form(default=""),
    source_id: str = Form(default=""),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if evidence_kind not in ("invoice", "fitment", "product_image", "product_qr"):
        raise HTTPException(status_code=422, detail="Unsupported evidence kind.")
    _validate_source(user, db, source_type, source_id)
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG and WebP images are accepted.")
    data = await file.read(settings.trustvision_max_upload_bytes + 1)
    if not data or len(data) > settings.trustvision_max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image is empty or exceeds the upload size limit.")
    try:
        image = Image.open(__import__("io").BytesIO(data))
        if image.width * image.height > 40000000:
            raise HTTPException(status_code=413, detail="Image dimensions exceed the safety limit.")
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=415, detail="Uploaded file is not a valid supported image.")
    actual_format = Image.open(__import__("io").BytesIO(data)).format
    format_mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    if format_mime.get(actual_format) != file.content_type:
        raise HTTPException(status_code=415, detail="File content does not match its declared image type.")

    digest = sha256_hex(data)
    phash = perceptual_hash(data)
    duplicate, exact_duplicate = find_duplicate(db, digest, phash)
    quality_status, quality_reasons = image_quality(data)
    evidence_id = str(uuid.uuid4())
    safe_name = Path(file.filename or "evidence-image").name[:180]
    suffix = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[actual_format]
    storage_key = f"{evidence_id}{suffix}"
    try:
        stored_key = get_object_storage().put(storage_key, data, format_mime[actual_format])
    except StorageError as exc:
        raise HTTPException(status_code=503, detail="Evidence storage is temporarily unavailable.") from exc
    storage_key = stored_key

    mechanic = _mechanic(user, db)
    evidence = TrustVisionEvidence(
        id=evidence_id, submitted_by=user.id, mechanic_id=mechanic.id if mechanic else None,
        evidence_kind=evidence_kind, original_filename=safe_name, storage_key=storage_key,
        mime_type=format_mime[actual_format], byte_size=len(data), sha256=digest,
        perceptual_hash=phash, source_type=source_type, source_id=source_id,
        duplicate_of_id=duplicate.id if duplicate else None,
        quality_status=quality_status)
    db.add(evidence)
    db.flush()

    ocr_payload = None
    if evidence_kind == "invoice":
        ocr_payload = run_ocr(data)
        ocr = TrustVisionOCRResult(
            evidence_id=evidence.id, status=ocr_payload["status"],
            extracted_text=ocr_payload.get("text", ""),
            invoice_number=ocr_payload.get("invoice_number", ""),
            dealer_name=ocr_payload.get("dealer_name", ""),
            invoice_date=ocr_payload.get("invoice_date", ""),
            product_name=ocr_payload.get("product_name", ""),
            sku=ocr_payload.get("sku", ""),
            quantity=ocr_payload.get("quantity"),
            total_amount=ocr_payload.get("total_amount", ""),
            confidence=ocr_payload.get("confidence", 0))
        db.add(ocr)

    duplicate_invoice = False
    duplicate_invoice_evidence = None
    if ocr_payload and ocr_payload.get("invoice_number") and ocr_payload.get("dealer_name"):
        prior = db.scalar(select(TrustVisionOCRResult).where(
            TrustVisionOCRResult.invoice_number == ocr_payload["invoice_number"],
            func.lower(TrustVisionOCRResult.dealer_name) == ocr_payload["dealer_name"].strip().lower()
        ).limit(1))
        if prior:
            duplicate_invoice = True
            duplicate_invoice_evidence = prior.evidence_id
    risk = score_risk(
        exact_duplicate=bool(duplicate and exact_duplicate),
        near_duplicate=bool(duplicate and not exact_duplicate),
        duplicate_invoice=duplicate_invoice,
        low_ocr=bool(ocr_payload and ocr_payload.get("confidence", 0) < 45 and ocr_payload.get("status") == "completed"),
        missing_invoice=bool(ocr_payload and not ocr_payload.get("invoice_number")),
        suspicious_image_quality=bool(quality_reasons))
    case = create_case(db, evidence_id=evidence.id, mechanic_id=evidence.mechanic_id,
        case_type="duplicate_evidence" if duplicate else "invoice_review" if evidence_kind == "invoice" else "evidence_quality",
        risk=risk, evidence_refs=[x for x in [duplicate.id if duplicate else None,
            duplicate_invoice_evidence] if x])
    linked_evidence = None
    if source_type == "fitment":
        linked_evidence = AdvocacyEvidence(fitment_id=source_id, evidence_type=evidence_kind,
            storage_reference=f"trustvision:{evidence.id}", confidence="high" if not quality_reasons else "medium",
            submitted_by=user.id)
    elif source_type == "recommendation":
        linked_evidence = AdvocacyEvidence(recommendation_id=source_id, evidence_type=evidence_kind,
            storage_reference=f"trustvision:{evidence.id}", confidence="high" if not quality_reasons else "medium",
            submitted_by=user.id)
    if linked_evidence:
        db.add(linked_evidence)
    db.commit()

    result = {"evidence_id": evidence.id, "evidence_kind": evidence_kind,
        "byte_size": evidence.byte_size, "quality_status": quality_status,
        "quality_reasons": quality_reasons, "duplicate_detected": bool(duplicate),
        "duplicate_type": "exact" if duplicate and exact_duplicate else "perceptual" if duplicate else None,
        "fraud_review_case_id": case.id if case else None,
        "risk_score": risk["risk_score"], "risk_level": risk["risk_level"],
        "reason_codes": risk["reason_codes"]}
    if ocr_payload:
        result["ocr"] = {k: ocr_payload.get(k) for k in (
            "status", "confidence", "invoice_number", "dealer_name", "invoice_date",
            "product_name", "sku", "quantity", "total_amount")}
    if evidence_kind == "product_qr":
        try:
            decoded = decode_qr(data)
        except Exception:
            decoded = ""
        token = decoded.rsplit("/api/v1/advocacy/products/identify/", 1)[-1] if "/api/v1/advocacy/products/identify/" in decoded else decoded
        product_id = verify_product_qr_token(token) if token else None
        token_hash = hashlib.sha256(token.encode()).hexdigest() if token else hashlib.sha256(b"empty-qr").hexdigest()
        scans = qr_replay_count(db, token_hash, user.id) if product_id else 1
        scan = TrustVisionQRScan(token_hash=token_hash, product_id=product_id, scanned_by=user.id,
            evidence_id=evidence.id, scan_status="valid" if product_id else "invalid")
        db.add(scan)
        if product_id:
            product = db.get(AdvocacyProduct, product_id)
            result["qr"] = {"valid": bool(product and product.active),
                "product_id": product_id, "sku": product.sku if product else None,
                "product_name": product.product_name if product else None}
            if scans >= 8:
                qr_risk = score_risk(qr_replay=True)
                qr_case = create_case(db, evidence_id=evidence.id, mechanic_id=evidence.mechanic_id,
                    case_type="qr_scan_pattern", risk=qr_risk, evidence_refs=[])
                result["qr"]["unusual_scan_pattern"] = True
                result["qr"]["fraud_review_case_id"] = qr_case.id if qr_case else None
        else:
            invalid_risk = {"risk_score": 80, "risk_level": "high", "reason_codes": ["INVALID_OR_UNREADABLE_PRODUCT_QR"]}
            qr_case = create_case(db, evidence_id=evidence.id, mechanic_id=evidence.mechanic_id,
                case_type="invalid_product_qr", risk=invalid_risk)
            result["qr"] = {"valid": False, "message": "QR could not be authenticated."}
            result["qr"]["fraud_review_case_id"] = qr_case.id if qr_case else None
    db.commit()
    return {"data": result, "message": "Evidence stored. Risk indicators are review signals, not automatic fraud findings."}

@router.get("/trustvision/me/evidence")
def my_evidence(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(TrustVisionEvidence).where(TrustVisionEvidence.submitted_by == user.id)
        .order_by(TrustVisionEvidence.created_at.desc())).all()
    return {"data": [{"evidence_id": x.id, "kind": x.evidence_kind,
        "filename": x.original_filename, "quality_status": x.quality_status,
        "duplicate_detected": bool(x.duplicate_of_id), "created_at": x.created_at} for x in rows]}

@router.get("/admin/trustvision/review-queue")
def review_queue(user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    rows = db.scalars(select(TrustVisionFraudCase).where(TrustVisionFraudCase.status == "pending_review")
        .order_by(TrustVisionFraudCase.risk_score.desc(), TrustVisionFraudCase.created_at)).all()
    return {"data": [{"case_id": c.id, "evidence_id": c.evidence_id,
        "mechanic_id": c.mechanic_id, "case_type": c.case_type,
        "risk_score": c.risk_score, "risk_level": c.risk_level,
        "reason_codes": json.loads(c.reason_codes_json),
        "evidence_refs": json.loads(c.evidence_refs_json), "status": c.status,
        "created_at": c.created_at} for c in rows]}

@router.get("/admin/trustvision/evidence/{evidence_id}")
def evidence_detail(evidence_id: str, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    evidence = db.get(TrustVisionEvidence, evidence_id)
    if not evidence: raise HTTPException(status_code=404, detail="Evidence not found.")
    ocr = db.scalar(select(TrustVisionOCRResult).where(TrustVisionOCRResult.evidence_id == evidence.id))
    cases = db.scalars(select(TrustVisionFraudCase).where(TrustVisionFraudCase.evidence_id == evidence.id)).all()
    return {"data": {"evidence_id": evidence.id, "submitted_by": evidence.submitted_by,
        "mechanic_id": evidence.mechanic_id, "kind": evidence.evidence_kind,
        "filename": evidence.original_filename, "mime_type": evidence.mime_type,
        "byte_size": evidence.byte_size, "sha256": evidence.sha256,
        "quality_status": evidence.quality_status, "source_type": evidence.source_type,
        "source_id": evidence.source_id,
        "ocr": ({"status": ocr.status, "text": ocr.extracted_text, "confidence": ocr.confidence,
            "invoice_number": ocr.invoice_number, "dealer_name": ocr.dealer_name,
            "invoice_date": ocr.invoice_date, "product_name": ocr.product_name,
            "sku": ocr.sku, "quantity": ocr.quantity, "total_amount": ocr.total_amount} if ocr else None),
        "cases": [{"case_id": c.id, "risk_score": c.risk_score, "risk_level": c.risk_level,
            "reason_codes": json.loads(c.reason_codes_json), "status": c.status} for c in cases]}}

@router.get("/admin/trustvision/evidence/{evidence_id}/file")
def evidence_file(evidence_id: str, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    evidence = db.get(TrustVisionEvidence, evidence_id)
    if not evidence: raise HTTPException(status_code=404, detail="Evidence not found.")
    try:
        content = get_object_storage().get(evidence.storage_key)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail="Evidence file is unavailable.") from exc
    return Response(content=content, media_type=evidence.mime_type,
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        })

@router.patch("/admin/trustvision/cases/{case_id}/decision")
def decide_case(case_id: str, payload: FraudCaseDecision,
                user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    case = db.get(TrustVisionFraudCase, case_id)
    if not case: raise HTTPException(status_code=404, detail="Fraud review case not found.")
    if case.status != "pending_review": raise HTTPException(status_code=409, detail="Case has already been reviewed.")
    case.status = payload.decision
    case.reviewer_id = user.id
    case.reviewer_note = payload.reviewer_note.strip()
    case.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return {"data": {"case_id": case.id, "status": case.status,
        "reviewer_id": case.reviewer_id, "reviewed_at": case.reviewed_at}}

@router.patch("/admin/trustvision/evidence/{evidence_id}/ocr-correction")
def correct_ocr(evidence_id: str, payload: OCRCorrection,
                user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    ocr = db.scalar(select(TrustVisionOCRResult).where(TrustVisionOCRResult.evidence_id == evidence_id))
    if not ocr: raise HTTPException(status_code=404, detail="OCR result not found.")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(ocr, key, value)
    ocr.manual_correction_json = json.dumps(changes, separators=(",", ":"))
    db.commit()
    return {"data": {"evidence_id": evidence_id, "corrected_fields": list(changes),
        "manual_reviewed": True}}
