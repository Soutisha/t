from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import OTPChallenge
from app.models.security import SecurityAuditEvent
from app.models.copilot import CopilotQueryLog
from app.models.agents import AgentRun


def retention_candidates(db: Session, *, now: datetime | None = None) -> dict:
    current = now or datetime.now(timezone.utc)
    result = {"otp_challenges": 0, "security_audit_events": 0,
              "user_activity_records": 0, "disabled_policies": []}
    if settings.otp_retention_hours > 0:
        cutoff = current - timedelta(hours=settings.otp_retention_hours)
        result["otp_challenges"] = db.scalar(select(func.count()).select_from(OTPChallenge).where(
            OTPChallenge.created_at < cutoff,
            OTPChallenge.expires_at < current,
        )) or 0
    else:
        result["disabled_policies"].append("otp_challenges")
    if settings.security_audit_retention_days > 0:
        cutoff = current - timedelta(days=settings.security_audit_retention_days)
        result["security_audit_events"] = db.scalar(select(func.count()).select_from(SecurityAuditEvent).where(
            SecurityAuditEvent.created_at < cutoff,
        )) or 0
    else:
        result["disabled_policies"].append("security_audit_events")
    if settings.user_activity_retention_days > 0:
        cutoff = current - timedelta(days=settings.user_activity_retention_days)
        result["user_activity_records"] = (
            (db.scalar(select(func.count()).select_from(CopilotQueryLog).where(CopilotQueryLog.created_at < cutoff)) or 0)
            + (db.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.created_at < cutoff)) or 0)
        )
    else:
        result["disabled_policies"].append("user_activity_records")
    return result


def execute_retention(db: Session, *, now: datetime | None = None) -> dict:
    current = now or datetime.now(timezone.utc)
    candidates = retention_candidates(db, now=current)
    deleted = {"otp_challenges": 0, "security_audit_events": 0, "user_activity_records": 0}
    if settings.otp_retention_hours > 0:
        cutoff = current - timedelta(hours=settings.otp_retention_hours)
        result = db.execute(delete(OTPChallenge).where(
            OTPChallenge.created_at < cutoff,
            OTPChallenge.expires_at < current,
        ))
        deleted["otp_challenges"] = result.rowcount or 0
    if settings.security_audit_retention_days > 0:
        cutoff = current - timedelta(days=settings.security_audit_retention_days)
        result = db.execute(delete(SecurityAuditEvent).where(
            SecurityAuditEvent.created_at < cutoff,
        ))
        deleted["security_audit_events"] = result.rowcount or 0
    if settings.user_activity_retention_days > 0:
        cutoff = current - timedelta(days=settings.user_activity_retention_days)
        activity_result = db.execute(delete(CopilotQueryLog).where(CopilotQueryLog.created_at < cutoff))
        agent_result = db.execute(delete(AgentRun).where(AgentRun.created_at < cutoff))
        deleted["user_activity_records"] = (activity_result.rowcount or 0) + (agent_result.rowcount or 0)
    db.commit()
    return {"candidates": candidates, "deleted": deleted}
