from datetime import datetime, timezone
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.models import Mechanic, User
from app.models.passport import MechanicPassportProfile, MechanicSkill, PassportAuditEvent
from app.schemas.passport import SkillCreate, VisibilityUpdate, VerificationUpdate
from app.services.passport import get_or_create_profile, passport_payload, make_qr_token, verify_qr_token

router = APIRouter()

def owned_mechanic(user: User, db: Session) -> Mechanic:
    mechanic = db.scalar(select(Mechanic).where(Mechanic.user_id == user.id))
    if not mechanic:
        raise HTTPException(status_code=404, detail="Mechanic profile not found.")
    return mechanic

@router.get("/passport/me")
def my_passport(user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = owned_mechanic(user, db)
    data = passport_payload(db, mechanic, user)
    db.commit()
    return {"data": data}

@router.patch("/passport/me/visibility")
def update_visibility(payload: VisibilityUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = owned_mechanic(user, db)
    profile = get_or_create_profile(db, mechanic)
    profile.public_enabled = payload.enabled
    profile.consent_version = payload.consent_version if payload.enabled else None
    profile.consented_at = datetime.now(timezone.utc) if payload.enabled else None
    db.add(PassportAuditEvent(mechanic_id=mechanic.id, actor_user_id=user.id,
        event_type="visibility_changed", subject_type="passport_profile", subject_id=profile.id,
        details='{"enabled": ' + str(payload.enabled).lower() + '}'))
    db.commit()
    return {"data": {"public_profile_enabled": profile.public_enabled}}

@router.post("/passport/me/skills", status_code=201)
def add_skill(payload: SkillCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = owned_mechanic(user, db)
    name = payload.skill_name.strip()
    if db.scalar(select(MechanicSkill).where(
        MechanicSkill.mechanic_id == mechanic.id, MechanicSkill.skill_name == name
    )):
        raise HTTPException(status_code=409, detail="This skill is already listed.")
    skill = MechanicSkill(mechanic_id=mechanic.id, skill_name=name,
                          years_experience=payload.years_experience, verification_status="pending")
    db.add(skill); db.flush()
    db.add(PassportAuditEvent(mechanic_id=mechanic.id, actor_user_id=user.id,
        event_type="skill_submitted", subject_type="skill", subject_id=skill.id))
    db.commit()
    return {"data": {"skill_id": skill.id, "skill_name": name, "verification_status": "pending",
                     "message": "Skill submitted. It will count toward progression only after verification."}}

@router.get("/passport/me/qr")
def passport_qr(user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = owned_mechanic(user, db)
    profile = get_or_create_profile(db, mechanic)
    db.commit()
    token = make_qr_token(mechanic.id)
    verify_url = f"{settings.passport_public_base_url.rstrip('/')}/api/v1/passport/verify/{token}"
    try:
        import qrcode
        image = qrcode.make(verify_url)
        output = BytesIO()
        image.save(output, format="PNG")
        return Response(content=output.getvalue(), media_type="image/png",
                        headers={"Cache-Control": "no-store"})
    except ImportError:
        raise HTTPException(status_code=503, detail="QR image dependency is unavailable. Install backend requirements.")

@router.get("/passport/verify/{token}")
def verify_passport_qr(token: str, db: Session = Depends(get_db)):
    mechanic_id = verify_qr_token(token)
    if not mechanic_id:
        raise HTTPException(status_code=404, detail="Invalid passport QR.")
    mechanic = db.get(Mechanic, mechanic_id)
    if not mechanic:
        raise HTTPException(status_code=404, detail="Passport not found.")
    profile = db.scalar(select(MechanicPassportProfile).where(
        MechanicPassportProfile.mechanic_id == mechanic.id))
    if not profile or not profile.public_enabled:
        return {"data": {"valid": True, "profile_visible": False,
                         "message": "Identity token is valid, but the mechanic has not enabled public profile sharing."}}
    return {"data": {"valid": True, "profile_visible": True,
                     "public_profile_url": f"{settings.passport_public_base_url.rstrip('/')}/api/v1/passport/public/{profile.public_slug}"}}

@router.get("/passport/public/{slug}")
def public_passport(slug: str, db: Session = Depends(get_db)):
    profile = db.scalar(select(MechanicPassportProfile).where(
        MechanicPassportProfile.public_slug == slug, MechanicPassportProfile.public_enabled.is_(True)))
    if not profile:
        raise HTTPException(status_code=404, detail="Public passport not found.")
    mechanic = db.get(Mechanic, profile.mechanic_id)
    return {"data": passport_payload(db, mechanic, mechanic.user, include_private=False)}

@router.get("/admin/passport/skills/pending")
def pending_skills(user: User = Depends(require_roles("administrator", "eurogrip_admin")), db: Session = Depends(get_db)):
    rows = db.scalars(select(MechanicSkill).where(MechanicSkill.verification_status == "pending")).all()
    return {"data": [{"skill_id": x.id, "mechanic_id": x.mechanic_id, "mechanic_code": (db.get(Mechanic, x.mechanic_id).mechanic_code if db.get(Mechanic, x.mechanic_id) else None),
                      "skill_name": x.skill_name, "years_experience": x.years_experience} for x in rows]}

@router.patch("/admin/passport/skills/{skill_id}/verification")
def verify_skill(skill_id: str, payload: VerificationUpdate,
                 user: User = Depends(require_roles("administrator", "eurogrip_admin")), db: Session = Depends(get_db)):
    skill = db.get(MechanicSkill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found.")
    skill.verification_status = "verified" if payload.approved else "rejected"
    skill.verified_by = user.id if payload.approved else None
    skill.verified_at = datetime.now(timezone.utc) if payload.approved else None
    db.add(PassportAuditEvent(mechanic_id=skill.mechanic_id, actor_user_id=user.id,
        event_type="skill_verified" if payload.approved else "skill_rejected",
        subject_type="skill", subject_id=skill.id))
    db.commit()
    return {"data": {"skill_id": skill.id, "verification_status": skill.verification_status}}
