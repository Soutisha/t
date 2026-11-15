from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.models import User, Mechanic, VerificationStatus
from app.models.passport import MechanicSkill, MechanicCertification, MechanicAdvocacyMilestone
from app.services.passport import progression, make_qr_token, verify_qr_token

def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)

def test_progression_uses_only_verified_evidence():
    db = setup_db()
    user = User(phone_e164="+919999999999", display_name="Test Mechanic")
    db.add(user); db.flush()
    mechanic = Mechanic(user_id=user.id, mechanic_code="EGM-TEST000001",
        shop_type="independent", experience_years=5, languages="English",
        service_categories="tyres", participation_type="interested",
        verification_status=VerificationStatus.pending)
    db.add(mechanic); db.flush()
    for name in ["Tyre fitting", "Wheel balancing", "Puncture repair"]:
        db.add(MechanicSkill(mechanic_id=mechanic.id, skill_name=name, verification_status="pending"))
    db.flush()
    assert progression(db, mechanic)["name"] == "Registered Mechanic"
    for skill in db.query(MechanicSkill).all():
        skill.verification_status = "verified"
    db.flush()
    assert progression(db, mechanic)["name"] == "Skilled Mechanic"
    db.add(MechanicCertification(mechanic_id=mechanic.id, certificate_name="Safety",
        issuer="Training Provider", verification_status="verified"))
    db.flush()
    assert progression(db, mechanic)["name"] == "Certified Mechanic"

def test_qr_token_is_signed_and_tamper_evident():
    token = make_qr_token("mechanic-123")
    assert verify_qr_token(token) == "mechanic-123"
    assert verify_qr_token(token + "x") is None
