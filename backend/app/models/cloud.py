import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.core.security import utcnow

def _id(): return str(uuid.uuid4())

class IntegrationConnection(Base):
    __tablename__ = "integration_connections"
    __table_args__ = (UniqueConstraint("provider", "connection_name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    connection_name: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(20), default="sandbox")
    base_url: Mapped[str] = mapped_column(String(500), default="")
    credential_env_key: Mapped[str] = mapped_column(String(100), default="")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="configured")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class IntegrationSyncRun(Base):
    __tablename__ = "integration_sync_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    connection_id: Mapped[str] = mapped_column(ForeignKey("integration_connections.id"), index=True)
    operation: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    records_read: Mapped[int] = mapped_column(Integer, default=0)
    records_written: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str] = mapped_column(String(80), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class IntegrationOutbox(Base):
    __tablename__ = "integration_outbox"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(60), default="")
    aggregate_id: Mapped[str] = mapped_column(String(36), default="")
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    last_error_code: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
