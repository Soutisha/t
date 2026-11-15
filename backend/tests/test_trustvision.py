from PIL import Image
from io import BytesIO
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.models import User, Mechanic
from app.models.trustvision import TrustVisionEvidence, TrustVisionFraudCase
from app.services.trustvision import (
    sha256_hex, perceptual_hash, hamming_distance, score_risk,
    extract_invoice_fields, create_case, find_duplicate
)

def image_bytes(color=(120, 120, 120), size=(640, 480)):
    image = Image.new("RGB", size, color)
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()

def test_image_hashes_are_deterministic():
    first = image_bytes()
    second = image_bytes()
    assert sha256_hex(first) == sha256_hex(second)
    assert perceptual_hash(first) == perceptual_hash(second)
    assert hamming_distance(perceptual_hash(first), perceptual_hash(second)) == 0

def test_risk_scoring_explains_signals_without_deciding_guilt():
    result = score_risk(exact_duplicate=True, duplicate_invoice=True, low_ocr=True)
    assert result["risk_score"] == 100
    assert result["risk_level"] == "high"
    assert "EXACT_IMAGE_DUPLICATE" in result["reason_codes"]
    assert "DUPLICATE_INVOICE_REFERENCE" in result["reason_codes"]

def test_invoice_field_parser_extracts_obvious_fields():
    fields = extract_invoice_fields(
        "Invoice No: EG-2026-1001 Date: 15/11/2026 "
        "Dealer: Kolkata Tyre House SKU: TYR-001 Qty: 4 Total: 12,500.00"
    )
    assert fields["invoice_number"] == "EG-2026-1001"
    assert fields["invoice_date"] == "15/11/2026"
    assert fields["sku"] == "TYR-001"
    assert fields["quantity"] == 4

def test_duplicate_detection_finds_exact_image():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(phone_e164="+918888888888", display_name="TrustVision Test")
        db.add(user); db.flush()
        mechanic = Mechanic(user_id=user.id, mechanic_code="EGM-TRUST0001",
            shop_type="independent", experience_years=2, languages="English",
            service_categories="tyres", participation_type="interested")
        db.add(mechanic); db.flush()
        data = image_bytes()
        item = TrustVisionEvidence(submitted_by=user.id, mechanic_id=mechanic.id,
            evidence_kind="invoice", original_filename="invoice.png", storage_key="a.png",
            mime_type="image/png", byte_size=len(data), sha256=sha256_hex(data),
            perceptual_hash=perceptual_hash(data))
        db.add(item); db.flush()
        duplicate, exact = find_duplicate(db, sha256_hex(data), perceptual_hash(data))
        assert duplicate.id == item.id
        assert exact is True

def test_fraud_case_is_pending_human_review():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(phone_e164="+919999999999", display_name="Review Test")
        db.add(user); db.flush()
        risk = score_risk(exact_duplicate=True)
        case = create_case(db, evidence_id=None, mechanic_id=None,
            case_type="duplicate_evidence", risk=risk)
        db.flush()
        assert case.status == "pending_review"
        assert case.risk_level == "high"
        assert db.scalar(select(TrustVisionFraudCase)).status == "pending_review"
