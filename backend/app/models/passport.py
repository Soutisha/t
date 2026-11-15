import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.security import utcnow

def _id() -> str:
    return str(uuid.uuid4())

class MechanicPassportProfile(Base):
    __tablename__ = "mechanic_passport_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), unique=True, index=True)
    public_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    public_slug: Mapped[str] = mapped_column(String(48), unique=True, index=True, default=lambda: uuid.uuid4().hex)
    consent_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class MechanicSkill(Base):
    __tablename__ = "mechanic_skills"
    __table_args__ = (UniqueConstraint("mechanic_id", "skill_name", name="uq_mechanic_skill_name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    skill_name: Mapped[str] = mapped_column(String(100))
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    verification_status: Mapped[str] = mapped_column(String(20), default="pending")
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class MechanicCertification(Base):
    __tablename__ = "mechanic_certifications"
    __table_args__ = (UniqueConstraint("mechanic_id", "issuer", "certificate_name", name="uq_mechanic_cert"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    certificate_name: Mapped[str] = mapped_column(String(140))
    issuer: Mapped[str] = mapped_column(String(140))
    evidence_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="pending")
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class MechanicAchievement(Base):
    __tablename__ = "mechanic_achievements"
    __table_args__ = (UniqueConstraint("mechanic_id", "source_type", "source_id", name="uq_mechanic_achievement_source"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text, default="")
    badge_code: Mapped[str] = mapped_column(String(50))
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(80))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class MechanicAdvocacyMilestone(Base):
    __tablename__ = "mechanic_advocacy_milestones"
    __table_args__ = (UniqueConstraint("mechanic_id", "milestone_code", "source_id", name="uq_advocacy_milestone_source"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    milestone_code: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class PassportAuditEvent(Base):
    __tablename__ = "passport_audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50))
    subject_type: Mapped[str] = mapped_column(String(50))
    subject_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
