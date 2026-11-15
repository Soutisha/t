import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.core.security import utcnow

def _id(): return str(uuid.uuid4())

class TrustVisionEvidence(Base):
    __tablename__ = "trustvision_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    submitted_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    mechanic_id: Mapped[str | None] = mapped_column(ForeignKey("mechanics.id"), nullable=True, index=True)
    evidence_kind: Mapped[str] = mapped_column(String(30), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    perceptual_hash: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="")
    source_id: Mapped[str] = mapped_column(String(80), default="")
    duplicate_of_id: Mapped[str | None] = mapped_column(ForeignKey("trustvision_evidence.id"), nullable=True)
    quality_status: Mapped[str] = mapped_column(String(24), default="not_checked")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class TrustVisionOCRResult(Base):
    __tablename__ = "trustvision_ocr_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("trustvision_evidence.id", ondelete="CASCADE"), unique=True, index=True)
    engine: Mapped[str] = mapped_column(String(50), default="pytesseract")
    status: Mapped[str] = mapped_column(String(24), default="pending")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    invoice_number: Mapped[str] = mapped_column(String(120), default="")
    dealer_name: Mapped[str] = mapped_column(String(160), default="")
    invoice_date: Mapped[str] = mapped_column(String(40), default="")
    product_name: Mapped[str] = mapped_column(String(160), default="")
    sku: Mapped[str] = mapped_column(String(80), default="")
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_amount: Mapped[str] = mapped_column(String(60), default="")
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    manual_correction_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class TrustVisionFraudCase(Base):
    __tablename__ = "trustvision_fraud_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("trustvision_evidence.id"), nullable=True, index=True)
    mechanic_id: Mapped[str | None] = mapped_column(ForeignKey("mechanics.id"), nullable=True, index=True)
    case_type: Mapped[str] = mapped_column(String(40), index=True)
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(16))
    reason_codes_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(24), default="pending_review")
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class TrustVisionQRScan(Base):
    __tablename__ = "trustvision_qr_scans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("advocacy_products.id"), nullable=True, index=True)
    scanned_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("trustvision_evidence.id"), nullable=True)
    scan_status: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
