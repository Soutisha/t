import hashlib
import hmac
import secrets
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import utcnow
from app.models.advocacy import AdvocacyEventLedger

def new_referral_code() -> str:
    return "EGR-" + secrets.token_hex(6).upper()

def product_qr_token(product_id: str) -> str:
    signature = hmac.new(settings.jwt_secret.encode(), f"product:{product_id}".encode(), hashlib.sha256).hexdigest()
    return f"{product_id}.{signature}"

def verify_product_qr_token(token: str) -> str | None:
    try:
        product_id, signature = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(settings.jwt_secret.encode(), f"product:{product_id}".encode(), hashlib.sha256).hexdigest()
    return product_id if hmac.compare_digest(signature, expected) else None

def record_event(db: Session, *, mechanic_id: str, product_id: str | None,
                 event_type: str, source_id: str, referral_source: str = "",
                 dealer_reference: str = "", location_reference: str = "", event_date=None,
                 verification_status: str = "submitted", confidence: str = "low",
                 reward_eligible: bool = False):
    event = AdvocacyEventLedger(
        mechanic_id=mechanic_id, product_id=product_id, event_type=event_type,
        source_id=source_id, referral_source=referral_source,
        dealer_reference=dealer_reference, location_reference=location_reference,
        event_date=event_date or utcnow(),
        verification_status=verification_status, confidence=confidence, reward_eligible=reward_eligible)
    db.add(event)
    return event
