import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.security import utcnow

def _id(): return str(uuid.uuid4())

class AdvocacyProduct(Base):
    __tablename__ = "advocacy_products"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    sku: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    tyre_type: Mapped[str] = mapped_column(String(80), default="")
    specifications_json: Mapped[str] = mapped_column(Text, default="{}")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AdvocacyRecommendation(Base):
    __tablename__ = "advocacy_recommendations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("advocacy_products.id"), index=True)
    referral_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_reference_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    referral_source: Mapped[str] = mapped_column(String(40), default="mechanic")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="submitted")
    reward_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    product: Mapped[AdvocacyProduct] = relationship()

class FitmentRecord(Base):
    __tablename__ = "fitment_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("advocacy_products.id"), index=True)
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("advocacy_recommendations.id"), nullable=True, index=True)
    vehicle_reference: Mapped[str] = mapped_column(String(100), default="")
    fitment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    evidence_confidence: Mapped[str] = mapped_column(String(20), default="low")
    verification_status: Mapped[str] = mapped_column(String(24), default="pending")
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_note: Mapped[str] = mapped_column(Text, default="")
    reward_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    product: Mapped[AdvocacyProduct] = relationship()

class AdvocacyEvidence(Base):
    __tablename__ = "advocacy_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    fitment_id: Mapped[str | None] = mapped_column(ForeignKey("fitment_records.id", ondelete="CASCADE"), nullable=True, index=True)
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("advocacy_recommendations.id", ondelete="CASCADE"), nullable=True, index=True)
    evidence_type: Mapped[str] = mapped_column(String(40))
    storage_reference: Mapped[str] = mapped_column(String(500))
    confidence: Mapped[str] = mapped_column(String(20), default="low")
    submitted_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class DealerReferral(Base):
    __tablename__ = "dealer_referrals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("advocacy_recommendations.id"), nullable=True)
    dealer_reference: Mapped[str] = mapped_column(String(100))
    dealer_name: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(24), default="submitted")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class StockistRegistration(Base):
    __tablename__ = "stockist_registrations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    shop_reference: Mapped[str] = mapped_column(String(100), default="")
    dealer_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class DealerSalesRecord(Base):
    __tablename__ = "dealer_sales_records"
    __table_args__ = (UniqueConstraint("dealer_user_id", "invoice_reference", name="uq_dealer_invoice_reference"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    dealer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    dealer_reference: Mapped[str] = mapped_column(String(100))
    invoice_reference: Mapped[str] = mapped_column(String(100))
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("advocacy_recommendations.id"), nullable=True, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("advocacy_products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    sale_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(24), default="dealer_submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class DealerStockingRecord(Base):
    __tablename__ = "dealer_stocking_records"
    __table_args__ = (UniqueConstraint("dealer_user_id", "stocking_reference", name="uq_dealer_stocking_reference"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    dealer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    dealer_reference: Mapped[str] = mapped_column(String(100))
    stocking_reference: Mapped[str] = mapped_column(String(100))
    mechanic_id: Mapped[str | None] = mapped_column(ForeignKey("mechanics.id"), nullable=True, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("advocacy_products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    stock_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(24), default="dealer_submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class CustomerFeedback(Base):
    __tablename__ = "customer_feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("advocacy_recommendations.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)
    feedback_text: Mapped[str] = mapped_column(Text, default="")
    verification_status: Mapped[str] = mapped_column(String(24), default="unverified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AdvocacyCampaign(Base):
    __tablename__ = "advocacy_campaigns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    campaign_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=False)

class CampaignParticipation(Base):
    __tablename__ = "campaign_participations"
    __table_args__ = (UniqueConstraint("campaign_id", "mechanic_id", name="uq_campaign_mechanic"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("advocacy_campaigns.id", ondelete="CASCADE"), index=True)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="registered")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AdvocacyEventLedger(Base):
    __tablename__ = "advocacy_event_ledger"
    __table_args__ = (UniqueConstraint("event_type", "source_id", name="uq_advocacy_event_source"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mechanic_id: Mapped[str] = mapped_column(ForeignKey("mechanics.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("advocacy_products.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(30))  # recommendation / fitment / stocking / sale
    source_id: Mapped[str] = mapped_column(String(80))
    referral_source: Mapped[str] = mapped_column(String(40), default="")
    dealer_reference: Mapped[str] = mapped_column(String(100), default="")
    location_reference: Mapped[str] = mapped_column(String(140), default="")
    verification_status: Mapped[str] = mapped_column(String(24), default="submitted")
    confidence: Mapped[str] = mapped_column(String(20), default="low")
    reward_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
