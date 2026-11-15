import secrets
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.security import hash_secret, verify_secret, utcnow, create_access_token
from app.models.models import OTPChallenge, User, UserRole, UserStatus
from app.schemas.auth import UserSummary, TokenResponse
from app.services.sms import get_sms_provider, SmsDeliveryError

def request_otp(db: Session, phone: str) -> tuple[str, str | None]:
    now = utcnow()
    recent = db.scalars(select(OTPChallenge).where(
        OTPChallenge.phone_e164 == phone,
        OTPChallenge.created_at >= now - timedelta(minutes=10)
    )).all()
    if len(recent) >= 3:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Try again later.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    dev_code = code if settings.app_env == "development" and settings.otp_dev_return_code else None
    if dev_code is None:
        try:
            provider = get_sms_provider()
        except SmsDeliveryError:
            raise HTTPException(status_code=503, detail="OTP delivery is not configured. Contact the platform administrator.")
        try:
            provider.send(
                phone,
                f"Your EUROGRIP PITSTOP OS verification code is {code}. It expires in {settings.otp_ttl_minutes} minutes.",
            )
        except SmsDeliveryError:
            raise HTTPException(status_code=502, detail="OTP delivery failed. Please try again later.")
    challenge = OTPChallenge(
        phone_e164=phone,
        code_hash=hash_secret(code),
        expires_at=now + timedelta(minutes=settings.otp_ttl_minutes)
    )
    db.add(challenge)
    db.commit()
    return challenge.id, dev_code

def verify_otp(db: Session, phone: str, code: str) -> TokenResponse:
    now = utcnow()
    challenge = db.scalar(select(OTPChallenge).where(
        OTPChallenge.phone_e164 == phone,
        OTPChallenge.consumed.is_(False)
    ).order_by(OTPChallenge.created_at.desc()))
    expiry = challenge.expires_at if challenge and challenge.expires_at.tzinfo else (challenge.expires_at.replace(tzinfo=now.tzinfo) if challenge else now)
    if not challenge or expiry < now or challenge.attempts >= 5:
        raise HTTPException(status_code=401, detail="OTP is invalid or expired.")
    challenge.attempts += 1
    if not verify_secret(code, challenge.code_hash):
        db.commit()
        raise HTTPException(status_code=401, detail="OTP is invalid or expired.")
    challenge.consumed = True
    user = db.scalar(select(User).where(User.phone_e164 == phone))
    if not user:
        db.commit()
        raise HTTPException(status_code=403, detail="No account found. Complete mechanic registration first.")
    if user.status != UserStatus.active:
        db.commit()
        raise HTTPException(status_code=403, detail="Account is not active.")
    roles = [r.role_code for r in user.roles]
    db.commit()
    token = create_access_token(user.id, roles)
    summary = UserSummary(id=user.id, phone_e164=user.phone_e164, display_name=user.display_name, status=user.status.value, roles=roles)
    return TokenResponse(access_token=token, expires_in=settings.jwt_ttl_minutes * 60, user=summary)
