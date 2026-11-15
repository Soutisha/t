import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.security import utcnow

def _id(): return str(uuid.uuid4())

class ToolProduct(Base):
    __tablename__ = "tool_products"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="general")
    points_cost: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ToolInventory(Base):
    __tablename__ = "tool_inventory"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("tool_products.id", ondelete="CASCADE"), unique=True, index=True)
    available_quantity: Mapped[int] = mapped_column(Integer, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    product: Mapped[ToolProduct] = relationship()

class ToolRequest(Base):
    __tablename__ = "tool_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("tool_products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    decision_note: Mapped[str] = mapped_column(Text, default="")
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    product: Mapped[ToolProduct] = relationship()

class RewardLedgerEntry(Base):
    __tablename__ = "reward_ledger_entries"
    __table_args__ = (UniqueConstraint("source_type", "source_id", "entry_type", name="uq_reward_source_entry"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    entry_type: Mapped[str] = mapped_column(String(20))  # credit / debit / reversal
    points: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class RewardRedemption(Base):
    __tablename__ = "reward_redemptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    reward_name: Mapped[str] = mapped_column(String(140))
    points_cost: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    decision_note: Mapped[str] = mapped_column(Text, default="")
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
