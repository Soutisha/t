import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.core.security import utcnow
from app.db.session import get_db
from app.models.models import Consent, Mechanic, OTPChallenge, Shop, User, UserRole, UserStatus, VerificationStatus
from app.models.geospatial import GeoLocation
from app.models.advocacy import AdvocacyEvidence, FitmentRecord, StockistRegistration
from app.models.copilot import CopilotQueryLog, KnowledgeDocument
from app.models.agents import AgentRun
from app.models.passport import MechanicSkill, MechanicCertification, PassportAuditEvent
from app.models.toolbank import ToolRequest, RewardLedgerEntry, RewardRedemption
from app.models.privacy import AccountDeletionRequest
from app.models.security import SecurityAuditEvent
from app.models.trustvision import TrustVisionEvidence, TrustVisionFraudCase, TrustVisionOCRResult, TrustVisionQRScan
from app.schemas.privacy import AccountDeletionCreate, AccountDeletionDecision, AccountDeletionExecute
from app.services.object_storage import StorageError, get_object_storage

router = APIRouter()
ADMIN = ("administrator", "eurogrip_admin")
REQUEST_CONFIRMATION = "DELETE MY ACCOUNT"
EXECUTE_CONFIRMATION = "EXECUTE ACCOUNT ERASURE"


def _audit(db: Session, request: Request, actor_id: str, event_type: str, path: str):
    db.add(SecurityAuditEvent(
        request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
        actor_user_id=actor_id,
        method=request.method,
        path=path[:300],
        status_code=200,
        client_fingerprint="",
        user_agent="",
        duration_ms=0,
        event_type=event_type,
    ))


@router.post("/me/privacy/deletion-requests", status_code=201)
def request_account_deletion(
    payload: AccountDeletionCreate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if payload.confirmation != REQUEST_CONFIRMATION:
        raise HTTPException(status_code=422, detail=f"Type {REQUEST_CONFIRMATION} exactly to request account deletion.")
    existing = db.scalar(select(AccountDeletionRequest).where(
        AccountDeletionRequest.user_id == user.id,
        AccountDeletionRequest.status.in_(("pending", "approved")),
    ).order_by(AccountDeletionRequest.requested_at.desc()))
    if existing:
        raise HTTPException(status_code=409, detail="An account deletion request is already active.")
    record = AccountDeletionRequest(user_id=user.id, status="pending", reason=payload.reason.strip())
    db.add(record)
    _audit(db, request, user.id, "privacy_deletion_requested", "/api/v1/me/privacy/deletion-requests")
    db.commit()
    db.refresh(record)
    return {"data": {
        "request_id": record.id,
        "status": record.status,
        "requested_at": record.requested_at,
        "message": "Request submitted for administrator review. Your account remains active until approved erasure is executed.",
    }}


@router.get("/me/privacy/deletion-requests")
def my_deletion_requests(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AccountDeletionRequest).where(
        AccountDeletionRequest.user_id == user.id
    ).order_by(AccountDeletionRequest.requested_at.desc())).all()
    return {"data": [{
        "request_id": row.id, "status": row.status, "reason": row.reason,
        "requested_at": row.requested_at, "reviewed_at": row.reviewed_at,
        "completed_at": row.completed_at, "outcome_summary": row.outcome_summary,
    } for row in rows]}


@router.get("/admin/privacy/deletion-requests")
def deletion_queue(user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    rows = db.scalars(select(AccountDeletionRequest).where(
        AccountDeletionRequest.status.in_(("pending", "approved"))
    ).order_by(AccountDeletionRequest.requested_at)).all()
    return {"data": [{
        "request_id": row.id, "user_id": row.user_id, "status": row.status,
        "reason": row.reason, "requested_at": row.requested_at,
    } for row in rows]}


@router.patch("/admin/privacy/deletion-requests/{request_id}/decision")
def decide_deletion_request(
    request_id: str,
    payload: AccountDeletionDecision,
    request: Request,
    user: User = Depends(require_roles(*ADMIN)),
    db: Session = Depends(get_db),
):
    record = db.get(AccountDeletionRequest, request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Deletion request not found.")
    if record.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending deletion requests can be reviewed.")
    record.status = "approved" if payload.approved else "rejected"
    record.reviewed_at = utcnow()
    record.reviewed_by = user.id
    record.outcome_summary = payload.note.strip()
    _audit(db, request, user.id, "privacy_deletion_approved" if payload.approved else "privacy_deletion_rejected",
           f"/api/v1/admin/privacy/deletion-requests/{request_id}/decision")
    db.commit()
    return {"data": {"request_id": record.id, "status": record.status,
                     "message": "Approved requests require a separate, explicitly confirmed execution step."}}


@router.post("/admin/privacy/deletion-requests/{request_id}/execute")
def execute_account_erasure(
    request_id: str,
    payload: AccountDeletionExecute,
    request: Request,
    user: User = Depends(require_roles(*ADMIN)),
    db: Session = Depends(get_db),
):
    if payload.confirmation != EXECUTE_CONFIRMATION:
        raise HTTPException(status_code=422, detail=f"Type {EXECUTE_CONFIRMATION} exactly to execute erasure.")
    record = db.get(AccountDeletionRequest, request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Deletion request not found.")
    if record.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved deletion requests can be executed.")
    account = db.get(User, record.user_id)
    if not account or account.status == UserStatus.suspended:
        raise HTTPException(status_code=409, detail="Account is already unavailable or has been deleted.")

    old_phone = account.phone_e164
    mechanic = db.scalar(select(Mechanic).where(Mechanic.user_id == account.id))
    evidence = db.scalars(select(TrustVisionEvidence).where(
        TrustVisionEvidence.submitted_by == account.id
    )).all()
    evidence_ids = [item.id for item in evidence]
    storage = get_object_storage()

    # Delete user-submitted evidence objects first. If storage fails, preserve DB records and stop.
    try:
        for item in evidence:
            storage.delete(item.storage_key)
    except StorageError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Evidence storage deletion failed; account erasure was not committed.") from exc

    db.execute(
        TrustVisionFraudCase.__table__.update()
        .where(TrustVisionFraudCase.reviewer_id == account.id)
        .values(reviewer_id=None)
    )
    db.execute(
        AdvocacyEvidence.__table__.update()
        .where(AdvocacyEvidence.submitted_by == account.id)
        .values(storage_reference="")
    )
    db.execute(
        CopilotQueryLog.__table__.update()
        .where(CopilotQueryLog.user_id == account.id)
        .values(question="[redacted by account deletion]", answer="[redacted by account deletion]",
                citations_json="[]", feedback="")
    )
    db.execute(
        AgentRun.__table__.update()
        .where(AgentRun.user_id == account.id)
        .values(request_text="[redacted by account deletion]", response_text="[redacted by account deletion]",
                trace_json="[]")
    )
    # Historical business records remain linked to the pseudonymous account anchor,
    # while optional reviewer/approver identity fields are cleared.
    for model, field in (
        (KnowledgeDocument, KnowledgeDocument.approved_by),
        (ToolRequest, ToolRequest.decided_by),
        (RewardLedgerEntry, RewardLedgerEntry.created_by),
        (RewardRedemption, RewardRedemption.decided_by),
        (MechanicSkill, MechanicSkill.verified_by),
        (MechanicCertification, MechanicCertification.verified_by),
        (PassportAuditEvent, PassportAuditEvent.actor_user_id),
        (FitmentRecord, FitmentRecord.reviewer_id),
        (StockistRegistration, StockistRegistration.verified_by),
    ):
        db.execute(model.__table__.update().where(field == account.id).values({field.key: None}))
    if evidence_ids:
        db.execute(delete(TrustVisionOCRResult).where(TrustVisionOCRResult.evidence_id.in_(evidence_ids)))
        db.execute(delete(TrustVisionFraudCase).where(
            (TrustVisionFraudCase.evidence_id.in_(evidence_ids)) |
            (TrustVisionFraudCase.mechanic_id == (mechanic.id if mechanic else "__none__"))
        ))
        db.execute(delete(TrustVisionQRScan).where(
            (TrustVisionQRScan.evidence_id.in_(evidence_ids)) |
            (TrustVisionQRScan.scanned_by == account.id)
        ))
        db.execute(
            TrustVisionEvidence.__table__.update()
            .where(TrustVisionEvidence.duplicate_of_id.in_(evidence_ids))
            .values(duplicate_of_id=None)
        )
        db.execute(delete(TrustVisionEvidence).where(TrustVisionEvidence.id.in_(evidence_ids)))
    else:
        db.execute(delete(TrustVisionQRScan).where(TrustVisionQRScan.scanned_by == account.id))
        db.execute(delete(TrustVisionFraudCase).where(
            TrustVisionFraudCase.mechanic_id == (mechanic.id if mechanic else "__none__")
        ))

    db.execute(delete(OTPChallenge).where(OTPChallenge.phone_e164 == old_phone))
    db.execute(delete(GeoLocation).where(GeoLocation.owner_user_id == account.id))
    db.execute(delete(UserRole).where(UserRole.user_id == account.id))

    consents = db.scalars(select(Consent).where(Consent.user_id == account.id)).all()
    for consent in consents:
        consent.granted = False

    if mechanic:
        mechanic.mechanic_code = "DEL-" + uuid.uuid4().hex[:12].upper()
        mechanic.languages = ""
        mechanic.service_categories = ""
        mechanic.verification_status = VerificationStatus.unverified
        shops = db.scalars(select(Shop).where(Shop.owner_mechanic_id == mechanic.id)).all()
        for shop in shops:
            shop.name = "Deleted shop"
            shop.address_text = ""
            shop.city = ""
            shop.state = ""
            shop.location_consent = False

    account.phone_e164 = "+999" + uuid.uuid4().hex[:12]
    account.display_name = "Deleted account"
    account.status = UserStatus.suspended

    record.status = "completed"
    record.completed_at = datetime.now(timezone.utc)
    record.reviewed_by = record.reviewed_by or user.id
    record.outcome_summary = (
        "Account disabled and direct profile identifiers redacted; user-submitted TrustVision evidence objects and records removed; "
        "location records and OTP challenges removed; consent withdrawn. Historical business, reward, learning, security and audit records "
        "may remain pseudonymized where required for integrity, fraud prevention or approved retention."
    )
    _audit(db, request, user.id, "privacy_deletion_completed",
           f"/api/v1/admin/privacy/deletion-requests/{request_id}/execute")
    db.commit()
    return {"data": {
        "request_id": record.id,
        "status": record.status,
        "completed_at": record.completed_at,
        "evidence_objects_removed": len(evidence_ids),
        "message": "Account deactivated and direct profile identifiers redacted. See outcome_summary for records retained under policy.",
    }}
