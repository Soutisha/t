import hashlib
import hmac
import json
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import Mechanic, User
from app.models.passport import (
    MechanicPassportProfile, MechanicSkill, MechanicCertification,
    MechanicAchievement, MechanicAdvocacyMilestone
)

LEVELS = [
    ("registered_mechanic", "Registered Mechanic"),
    ("skilled_mechanic", "Skilled Mechanic"),
    ("certified_mechanic", "Certified Mechanic"),
    ("eurogrip_champion", "Eurogrip Champion"),
    ("master_mentor", "Master Mentor"),
]

def get_or_create_profile(db: Session, mechanic: Mechanic) -> MechanicPassportProfile:
    profile = db.scalar(select(MechanicPassportProfile).where(MechanicPassportProfile.mechanic_id == mechanic.id))
    if not profile:
        profile = MechanicPassportProfile(mechanic_id=mechanic.id)
        db.add(profile)
        db.flush()
    return profile

def progression(db: Session, mechanic: Mechanic) -> dict:
    skills = db.scalar(select(func.count()).select_from(MechanicSkill).where(
        MechanicSkill.mechanic_id == mechanic.id, MechanicSkill.verification_status == "verified")) or 0
    certs = db.scalar(select(func.count()).select_from(MechanicCertification).where(
        MechanicCertification.mechanic_id == mechanic.id, MechanicCertification.verification_status == "verified")) or 0
    advocacy = db.scalar(select(func.count()).select_from(MechanicAdvocacyMilestone).where(
        MechanicAdvocacyMilestone.mechanic_id == mechanic.id, MechanicAdvocacyMilestone.verified.is_(True))) or 0
    mentoring = db.scalar(select(func.count()).select_from(MechanicAdvocacyMilestone).where(
        MechanicAdvocacyMilestone.mechanic_id == mechanic.id,
        MechanicAdvocacyMilestone.verified.is_(True),
        MechanicAdvocacyMilestone.milestone_code == "mentor_verified")) or 0

    # Levels require evidence-backed milestones; unverified/self-reported data never advances a tier.
    index = 0
    reasons = ["Passport created"]
    if skills >= 3:
        index = 1; reasons.append("At least 3 verified skills")
    if index >= 1 and certs >= 1:
        index = 2; reasons.append("At least 1 verified certification")
    if index >= 2 and advocacy >= 3:
        index = 3; reasons.append("At least 3 verified advocacy milestones")
    if index >= 3 and mentoring >= 2:
        index = 4; reasons.append("At least 2 verified mentoring milestones")
    return {"code": LEVELS[index][0], "name": LEVELS[index][1], "verified_skills": skills,
            "verified_certifications": certs, "verified_advocacy_milestones": advocacy,
            "verified_mentoring_milestones": mentoring, "qualification_reasons": reasons}

def passport_payload(db: Session, mechanic: Mechanic, user: User, include_private: bool = True) -> dict:
    profile = get_or_create_profile(db, mechanic)
    skills = db.scalars(select(MechanicSkill).where(MechanicSkill.mechanic_id == mechanic.id).order_by(MechanicSkill.created_at.desc())).all()
    certs = db.scalars(select(MechanicCertification).where(MechanicCertification.mechanic_id == mechanic.id).order_by(MechanicCertification.awarded_at.desc())).all()
    achievements = db.scalars(select(MechanicAchievement).where(
        MechanicAchievement.mechanic_id == mechanic.id, MechanicAchievement.verified.is_(True)
    ).order_by(MechanicAchievement.created_at.desc())).all()
    result = {
        "mechanic_code": mechanic.mechanic_code,
        "display_name": user.display_name,
        "level": progression(db, mechanic),
        "skills": [{"name": x.skill_name, "years_experience": x.years_experience,
                    "verification_status": x.verification_status} for x in skills],
        "certifications": [{"name": x.certificate_name, "issuer": x.issuer,
                            "verification_status": x.verification_status} for x in certs],
        "achievements": [{"title": x.title, "description": x.description, "badge_code": x.badge_code}
                         for x in achievements],
        "public_profile_enabled": profile.public_enabled,
    }
    if include_private:
        result["profile_visibility"] = "public" if profile.public_enabled else "private"
        result["public_slug"] = profile.public_slug if profile.public_enabled else None
    return result

def make_qr_token(mechanic_id: str) -> str:
    # Opaque signed identity token; no phone number, address or profile data is embedded.
    digest = hmac.new(settings.jwt_secret.encode(), mechanic_id.encode(), hashlib.sha256).hexdigest()
    return f"{mechanic_id}.{digest}"

def verify_qr_token(token: str) -> str | None:
    try:
        mechanic_id, supplied = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(settings.jwt_secret.encode(), mechanic_id.encode(), hashlib.sha256).hexdigest()
    return mechanic_id if hmac.compare_digest(supplied, expected) else None
