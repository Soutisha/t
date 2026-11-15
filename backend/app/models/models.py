import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.security import utcnow

def new_id() -> str:
    return str(uuid.uuid4())

class UserStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"

class VerificationStatus(str, enum.Enum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    phone_e164: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    roles: Mapped[list["UserRole"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    mechanic: Mapped["Mechanic | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_code", "scope_type", "scope_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_code: Mapped[str] = mapped_column(String(40))
    scope_type: Mapped[str] = mapped_column(String(30), default="global")
    scope_id: Mapped[str] = mapped_column(String(80), default="*")
    user: Mapped[User] = relationship(back_populates="roles")

class Mechanic(Base):
    __tablename__ = "mechanics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    mechanic_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    shop_type: Mapped[str] = mapped_column(String(50))
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    languages: Mapped[str] = mapped_column(String(250), default="English")
    service_categories: Mapped[str] = mapped_column(String(500), default="")
    participation_type: Mapped[str] = mapped_column(String(30), default="interested")
    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus), default=VerificationStatus.unverified)
    user: Mapped[User] = relationship(back_populates="mechanic")
    shops: Mapped[list["Shop"]] = relationship(back_populates="owner")

class Shop(Base):
    __tablename__ = "shops"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    shop_type: Mapped[str] = mapped_column(String(50))
    address_text: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    location_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    owner: Mapped[Mechanic] = relationship(back_populates="shops")

class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(80))
    policy_version: Mapped[str] = mapped_column(String(30))
    granted: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class OTPChallenge(Base):
    __tablename__ = "otp_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    phone_e164: Mapped[str] = mapped_column(String(16), index=True)
    code_hash: Mapped[str] = mapped_column(String(300))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
