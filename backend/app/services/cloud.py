import json
import os
import uuid
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import utcnow
from app.models.cloud import IntegrationConnection, IntegrationOutbox, IntegrationSyncRun

ALLOWED_CONFIG_KEYS = {
    "erpnext": {"company", "site_name", "api_version"},
    "sap": {"tenant", "company_code", "api_version"},
    "dynamics365": {"tenant_id", "environment_id", "api_version"},
    "webhook": {"event_allowlist"},
    "s3": {"bucket", "region", "prefix", "endpoint_url"}
}

def create_connection(db: Session, actor_id: str, data):
    if set(data.config) - ALLOWED_CONFIG_KEYS[data.provider]:
        raise ValueError("Unsupported provider configuration key.")
    if data.credential_env_key and data.credential_env_key not in os.environ:
        # Store only a reference. The deployment must inject the secret at runtime.
        status = "awaiting_secret"
    else:
        status = "configured"
    row = IntegrationConnection(
        provider=data.provider, connection_name=data.connection_name,
        environment=data.environment, base_url=str(data.base_url or ""),
        credential_env_key=data.credential_env_key,
        config_json=json.dumps(data.config, separators=(",", ":"), sort_keys=True),
        status=status, created_by=actor_id
    )
    db.add(row); db.commit(); db.refresh(row)
    return row

def enqueue_event(db: Session, event_type: str, aggregate_type: str, aggregate_id: str, payload: dict):
    row = IntegrationOutbox(event_type=event_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, payload_json=json.dumps(payload, separators=(",", ":")),
        status="pending", available_at=utcnow())
    db.add(row); db.commit(); db.refresh(row)
    return row

def queue_sync(db: Session, connection: IntegrationConnection, operation: str):
    row = IntegrationSyncRun(connection_id=connection.id, operation=operation,
        status="queued", created_at=utcnow())
    db.add(row); db.commit(); db.refresh(row)
    return row

def retry_outbox_event(db: Session, event: IntegrationOutbox):
    if event.status not in ("failed", "pending"):
        raise ValueError("Only failed or pending events can be retried.")
    event.status = "pending"
    event.attempts = 0
    event.last_error_code = ""
    event.available_at = utcnow()
    event.processed_at = None
    db.commit(); db.refresh(event)
    return event

def outbox_summary(db: Session):
    rows = db.execute(select(IntegrationOutbox.status, __import__("sqlalchemy").func.count()).group_by(IntegrationOutbox.status)).all()
    return {status: count for status, count in rows}
