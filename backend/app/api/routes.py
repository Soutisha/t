import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.models import Consent, Mechanic, Shop, User, UserRole, UserStatus, VerificationStatus, OTPChallenge
from app.core.security import utcnow
from datetime import timedelta
from app.schemas.auth import OTPRequest, OTPVerify, MechanicRegistration
from app.services.auth import request_otp, verify_otp
from app.schemas.privacy import ConsentUpdate
from app.models.geospatial import GeoLocation

router = APIRouter()

@router.post("/auth/otp/request")
def otp_request(payload: OTPRequest, db: Session = Depends(get_db)):
    challenge_id, dev_code = request_otp(db, payload.phone_e164)
    result = {"challenge_id": challenge_id, "expires_in": settings.otp_ttl_minutes * 60, "delivery": "development_mock" if dev_code else settings.sms_provider}
    if dev_code:
        result["development_otp"] = dev_code
    return {"data": result}

@router.post("/auth/otp/verify")
def otp_verify(payload: OTPVerify, db: Session = Depends(get_db)):
    result = verify_otp(db, payload.phone_e164, payload.code)
    return {"data": result.model_dump()}

@router.post("/onboarding/mechanics", status_code=201)
def register_mechanic(payload: MechanicRegistration, db: Session = Depends(get_db)):
    verified = db.scalar(select(OTPChallenge).where(
        OTPChallenge.phone_e164 == payload.phone_e164,
        OTPChallenge.consumed.is_(True),
        OTPChallenge.created_at >= utcnow() - timedelta(minutes=15)
    ).order_by(OTPChallenge.created_at.desc()))
    if not verified:
        raise HTTPException(status_code=401, detail="Verify the mobile number with a valid OTP before registration.")
    if db.scalar(select(User).where(User.phone_e164 == payload.phone_e164)):
        raise HTTPException(status_code=409, detail="An account with this mobile number already exists.")
    user = User(phone_e164=payload.phone_e164, display_name=payload.display_name.strip(), status=UserStatus.active)
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_code="mechanic", scope_type="global", scope_id="*"))
    mechanic_code = "EGM-" + uuid.uuid4().hex[:10].upper()
    mechanic = Mechanic(
        user_id=user.id, mechanic_code=mechanic_code, shop_type=payload.shop_type,
        experience_years=payload.experience_years, languages=", ".join(payload.languages),
        service_categories=", ".join(payload.service_categories),
        participation_type=payload.participation_type,
        verification_status=VerificationStatus.pending
    )
    db.add(mechanic)
    db.flush()
    db.add(Shop(
        owner_mechanic_id=mechanic.id, name=payload.shop_name.strip(), shop_type=payload.shop_type,
        address_text=payload.address_text, city=payload.city, state=payload.state,
        location_consent=payload.location_consent
    ))
    db.add(Consent(user_id=user.id, purpose="platform_account", policy_version=payload.consent_policy_version, granted=True))
    if payload.location_consent:
        db.add(Consent(user_id=user.id, purpose="shop_location", policy_version=payload.consent_policy_version, granted=True))
    db.commit()
    db.refresh(user)
    return {"data": {
        "user_id": user.id, "mechanic_id": mechanic.id, "mechanic_code": mechanic_code,
        "display_name": user.display_name, "participation_type": mechanic.participation_type,
        "verification_status": mechanic.verification_status.value,
        "message": "Registration completed. Profile verification is pending."
    }}

@router.get("/me")
def get_me(user: User = Depends(current_user)):
    return {"data": {
        "id": user.id, "phone_e164": user.phone_e164, "display_name": user.display_name,
        "status": user.status.value, "roles": [r.role_code for r in user.roles],
        "mechanic": ({
            "id": user.mechanic.id, "mechanic_code": user.mechanic.mechanic_code,
            "participation_type": user.mechanic.participation_type,
            "verification_status": user.mechanic.verification_status.value,
            "experience_years": user.mechanic.experience_years
        } if user.mechanic else None)
    }}

@router.patch("/me/profile")
def update_profile(payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    allowed = {"display_name"}
    if set(payload) - allowed:
        raise HTTPException(status_code=422, detail="Only display_name can be updated through this endpoint.")
    name = payload.get("display_name")
    if not isinstance(name, str) or len(name.strip()) < 2 or len(name) > 120:
        raise HTTPException(status_code=422, detail="display_name must contain 2 to 120 characters.")
    user.display_name = name.strip()
    db.commit()
    return {"data": {"id": user.id, "display_name": user.display_name}}

@router.get("/admin/onboarding/pending")
def pending_profiles(db: Session = Depends(get_db), user: User = Depends(require_roles("administrator"))):
    rows = db.scalars(select(Mechanic).where(Mechanic.verification_status == VerificationStatus.pending)).all()
    return {"data": [{"mechanic_id": m.id, "mechanic_code": m.mechanic_code, "display_name": m.user.display_name if m.user else None} for m in rows]}


@router.get("/me/privacy/consents")
def list_my_consents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Consent).where(Consent.user_id == user.id).order_by(Consent.created_at.desc())).all()
    return {"data": [{"purpose": x.purpose, "policy_version": x.policy_version,
        "granted": x.granted, "recorded_at": x.created_at} for x in rows]}

@router.post("/me/privacy/consents/{purpose}")
def update_my_consent(purpose: str, payload: ConsentUpdate,
                      user: User = Depends(current_user), db: Session = Depends(get_db)):
    if purpose not in ("shop_location", "geolocation_discovery", "product_advocacy", "training_analytics"):
        raise HTTPException(status_code=422, detail="Unsupported consent purpose.")
    db.add(Consent(user_id=user.id, purpose=purpose,
        policy_version=payload.policy_version, granted=payload.granted))
    if purpose == "shop_location":
        mechanic = db.scalar(select(Mechanic).where(Mechanic.user_id == user.id))
        if mechanic:
            shops = db.scalars(select(Shop).where(Shop.owner_mechanic_id == mechanic.id)).all()
            for shop in shops:
                shop.location_consent = payload.granted
    if purpose == "geolocation_discovery":
        locations = db.scalars(select(GeoLocation).where(GeoLocation.owner_user_id == user.id)).all()
        for location in locations:
            location.location_consent = payload.granted
            if not payload.granted:
                location.discoverable = False
    db.commit()
    return {"data": {"purpose": purpose, "granted": payload.granted,
        "policy_version": payload.policy_version,
        "message": "Consent preference recorded. Withdrawal disables the associated discovery flag where applicable."}}


@router.get("/admin/mechanics")
def admin_mechanic_directory(
    q: str = Query(default="", max_length=120),
    verification_status: str | None = Query(default=None, pattern="^(pending|verified|rejected|unverified)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("administrator", "eurogrip_admin", "field_rep", "field_representative")),
):
    statement = select(Mechanic, User, Shop).join(User, User.id == Mechanic.user_id).outerjoin(
        Shop, Shop.owner_mechanic_id == Mechanic.id
    )
    if verification_status:
        statement = statement.where(Mechanic.verification_status == VerificationStatus(verification_status))
    if q.strip():
        term = f"%{q.strip()}%"
        statement = statement.where(
            User.display_name.ilike(term) | Mechanic.mechanic_code.ilike(term) |
            Shop.name.ilike(term) | Shop.city.ilike(term)
        )
    rows = db.execute(statement.order_by(User.display_name).offset(offset).limit(limit)).all()
    unique = {}
    for mechanic, account, shop in rows:
        item = unique.setdefault(mechanic.id, {
            "mechanic_id": mechanic.id,
            "mechanic_code": mechanic.mechanic_code,
            "display_name": account.display_name,
            "account_status": account.status.value,
            "verification_status": mechanic.verification_status.value,
            "shop_type": mechanic.shop_type,
            "experience_years": mechanic.experience_years,
            "participation_type": mechanic.participation_type,
            "shop_name": None, "city": None, "state": None,
        })
        if shop and item["shop_name"] is None:
            item.update({"shop_name": shop.name, "city": shop.city, "state": shop.state})
    return {"data": list(unique.values()), "meta": {"limit": limit, "offset": offset, "returned": len(unique)}}


@router.patch("/admin/onboarding/mechanics/{mechanic_id}/verification")
def verify_mechanic_profile(
    mechanic_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("administrator", "eurogrip_admin")),
):
    mechanic = db.get(Mechanic, mechanic_id)
    if not mechanic:
        raise HTTPException(status_code=404, detail="Mechanic profile not found.")
    approved = payload.get("approved")
    if not isinstance(approved, bool):
        raise HTTPException(status_code=422, detail="approved must be a boolean.")
    if mechanic.verification_status != VerificationStatus.pending:
        raise HTTPException(status_code=409, detail="Only pending mechanic profiles can be reviewed.")
    mechanic.verification_status = VerificationStatus.verified if approved else VerificationStatus.rejected
    db.commit()
    return {"data": {"mechanic_id": mechanic.id, "verification_status": mechanic.verification_status.value}}
