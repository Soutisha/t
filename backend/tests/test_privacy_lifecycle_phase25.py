import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import SessionLocal
from app.main import app
from app.models.models import User, UserRole, UserStatus, Mechanic, Shop, Consent, OTPChallenge
from app.models.privacy import AccountDeletionRequest
from app.models.trustvision import TrustVisionEvidence
from app.models.security import SecurityAuditEvent
from app.models.copilot import CopilotQueryLog
from app.models.agents import AgentRun


class FakeStorage:
    def __init__(self):
        self.deleted = []
    def delete(self, key):
        self.deleted.append(key)


def _identity(role: str):
    db = SessionLocal()
    try:
        user = User(phone_e164=f"+9188{uuid.uuid4().int % 10**8:08d}",
                    display_name="Privacy Lifecycle Test", status=UserStatus.active)
        db.add(user); db.flush()
        db.add(UserRole(user_id=user.id, role_code=role, scope_type="global", scope_id="*"))
        db.commit()
        return user.id, create_access_token(user.id, [role])
    finally:
        db.close()


def test_account_deletion_requires_user_confirmation_and_admin_approval(monkeypatch):
    user_id, mechanic_token = _identity("mechanic")
    admin_id, admin_token = _identity("administrator")
    fake_storage = FakeStorage()
    monkeypatch.setattr("app.api.privacy_routes.get_object_storage", lambda: fake_storage)

    db = SessionLocal()
    try:
        account = db.get(User, user_id)
        mechanic = Mechanic(
            user_id=user_id, mechanic_code="EGM-" + uuid.uuid4().hex[:10].upper(),
            shop_type="tyre_shop", experience_years=3, languages="Bengali",
            service_categories="tyres", participation_type="interested",
        )
        db.add(mechanic); db.flush()
        db.add(Shop(owner_mechanic_id=mechanic.id, name="Privacy Test Shop",
                    shop_type="tyre_shop", address_text="Sensitive street",
                    city="Kolkata", state="West Bengal", location_consent=True))
        db.add(Consent(user_id=user_id, purpose="shop_location", policy_version="1.0", granted=True))
        db.add(OTPChallenge(phone_e164=account.phone_e164, code_hash="hash",
                            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)))
        evidence = TrustVisionEvidence(
            submitted_by=user_id, mechanic_id=mechanic.id, evidence_kind="fitment",
            original_filename="private-photo.png", storage_key="evidence/private-photo.png",
            mime_type="image/png", byte_size=123, sha256="a" * 64,
            perceptual_hash=None, source_type="", source_id="", quality_status="ok",
        )
        db.add(evidence)
        db.add(CopilotQueryLog(user_id=user_id, question="contains sensitive query",
                               answer="contains sensitive answer", answer_mode="extractive",
                               abstained=False, retrieval_count=0, citations_json="[]"))
        db.add(AgentRun(user_id=user_id, request_text="sensitive agent prompt",
                        intent="general", status="completed", response_text="sensitive agent response",
                        trace_json="[]", requires_human_approval=False))
        db.commit()
        evidence_id = evidence.id
    finally:
        db.close()

    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {mechanic_token}"}
        bad = client.post("/api/v1/me/privacy/deletion-requests",
                          headers=headers, json={"confirmation": "yes"})
        assert bad.status_code == 422
        created = client.post("/api/v1/me/privacy/deletion-requests", headers=headers,
                              json={"confirmation": "DELETE MY ACCOUNT", "reason": "No longer participating"})
        assert created.status_code == 201
        request_id = created.json()["data"]["request_id"]

        duplicate = client.post("/api/v1/me/privacy/deletion-requests", headers=headers,
                                json={"confirmation": "DELETE MY ACCOUNT"})
        assert duplicate.status_code == 409

        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        pending = client.get("/api/v1/admin/privacy/deletion-requests", headers=admin_headers)
        assert pending.status_code == 200
        assert any(row["request_id"] == request_id for row in pending.json()["data"])

        premature = client.post(f"/api/v1/admin/privacy/deletion-requests/{request_id}/execute",
                                 headers=admin_headers, json={"confirmation": "EXECUTE ACCOUNT ERASURE"})
        assert premature.status_code == 409

        decision = client.patch(f"/api/v1/admin/privacy/deletion-requests/{request_id}/decision",
                                headers=admin_headers, json={"approved": True, "note": "Approved test request"})
        assert decision.status_code == 200
        assert decision.json()["data"]["status"] == "approved"

        wrong_confirm = client.post(f"/api/v1/admin/privacy/deletion-requests/{request_id}/execute",
                                    headers=admin_headers, json={"confirmation": "execute"})
        assert wrong_confirm.status_code == 422

        executed = client.post(f"/api/v1/admin/privacy/deletion-requests/{request_id}/execute",
                               headers=admin_headers, json={"confirmation": "EXECUTE ACCOUNT ERASURE"})
        assert executed.status_code == 200, executed.text
        assert executed.json()["data"]["status"] == "completed"
        assert executed.json()["data"]["evidence_objects_removed"] == 1
        assert fake_storage.deleted == ["evidence/private-photo.png"]

        # Terminally suspended account cannot authenticate; database identity is pseudonymized.
        blocked = client.get("/api/v1/me", headers=headers)
        assert blocked.status_code == 401

    db = SessionLocal()
    try:
        account = db.get(User, user_id)
        assert account.status == UserStatus.suspended
        assert account.display_name == "Deleted account"
        assert account.phone_e164 != "+918800000000"
        assert db.scalars(select(UserRole).where(UserRole.user_id == user_id)).all() == []
        consent = db.scalar(select(Consent).where(Consent.user_id == user_id))
        assert consent.granted is False
        assert db.get(TrustVisionEvidence, evidence_id) is None
        request_row = db.get(AccountDeletionRequest, request_id)
        assert request_row.status == "completed"
        query_log = db.scalar(select(CopilotQueryLog).where(CopilotQueryLog.user_id == user_id))
        agent_run = db.scalar(select(AgentRun).where(AgentRun.user_id == user_id))
        assert query_log.question == "[redacted by account deletion]"
        assert query_log.answer == "[redacted by account deletion]"
        assert agent_run.request_text == "[redacted by account deletion]"
        assert agent_run.response_text == "[redacted by account deletion]"
        events = db.scalars(select(SecurityAuditEvent).where(
            SecurityAuditEvent.event_type.like("privacy_deletion_%")
        )).all()
        assert len(events) >= 3
    finally:
        db.close()


def test_retention_is_disabled_by_default_and_dry_run_does_not_delete(monkeypatch):
    from app.services import retention
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(retention.settings, "otp_retention_hours", 0)
    monkeypatch.setattr(retention.settings, "security_audit_retention_days", 0)
    monkeypatch.setattr(retention.settings, "user_activity_retention_days", 0)
    try:
        with TestingSession() as db:
            report = retention.retention_candidates(db)
            assert report["otp_challenges"] == 0
            assert report["security_audit_events"] == 0
            assert set(report["disabled_policies"]) == {"otp_challenges", "security_audit_events", "user_activity_records"}
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_retention_executes_only_after_explicitly_configured_windows(monkeypatch):
    from app.services import retention
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(retention.settings, "otp_retention_hours", 24)
    monkeypatch.setattr(retention.settings, "security_audit_retention_days", 30)
    monkeypatch.setattr(retention.settings, "user_activity_retention_days", 30)
    try:
        with TestingSession() as db:
            old = OTPChallenge(phone_e164="+918800000001", code_hash="hash",
                               expires_at=now - timedelta(days=3),
                               created_at=now - timedelta(days=3))
            recent = OTPChallenge(phone_e164="+918800000002", code_hash="hash",
                                  expires_at=now + timedelta(minutes=5),
                                  created_at=now)
            old_user = User(phone_e164="+918800000003", display_name="Old activity", status=UserStatus.active)
            recent_user = User(phone_e164="+918800000004", display_name="Recent activity", status=UserStatus.active)
            db.add_all([old_user, recent_user])
            db.flush()
            old_activity = CopilotQueryLog(
                user_id=old_user.id, question="old", answer="old", created_at=now - timedelta(days=60),
            )
            recent_activity = CopilotQueryLog(
                user_id=recent_user.id, question="recent", answer="recent", created_at=now,
            )
            db.add_all([old, recent, old_activity, recent_activity])
            db.commit()
            candidates = retention.retention_candidates(db, now=now)
            assert candidates["otp_challenges"] == 1
            assert candidates["user_activity_records"] == 1
            result = retention.execute_retention(db, now=now)
            assert result["deleted"]["otp_challenges"] == 1
            assert result["deleted"]["user_activity_records"] == 1
            remaining = db.scalars(select(OTPChallenge)).all()
            assert len(remaining) == 1
            assert remaining[0].phone_e164 == "+918800000002"
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_storage_failure_prevents_account_erasure_commit(monkeypatch):
    from app.services.object_storage import StorageError

    user_id, mechanic_token = _identity("mechanic")
    admin_id, admin_token = _identity("administrator")
    db = SessionLocal()
    try:
        mechanic = Mechanic(
            user_id=user_id, mechanic_code="EGM-" + uuid.uuid4().hex[:10].upper(),
            shop_type="tyre_shop", experience_years=1, languages="English",
            service_categories="tyres", participation_type="interested",
        )
        db.add(mechanic); db.flush()
        evidence = TrustVisionEvidence(
            submitted_by=user_id, mechanic_id=mechanic.id, evidence_kind="fitment",
            original_filename="private.png", storage_key="private/fail.png",
            mime_type="image/png", byte_size=100, sha256="b" * 64,
            perceptual_hash=None, source_type="", source_id="", quality_status="ok",
        )
        db.add(evidence); db.commit()
        evidence_id = evidence.id
    finally:
        db.close()

    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {mechanic_token}"}
        created = client.post("/api/v1/me/privacy/deletion-requests", headers=headers,
                              json={"confirmation": "DELETE MY ACCOUNT"})
        request_id = created.json()["data"]["request_id"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        client.patch(f"/api/v1/admin/privacy/deletion-requests/{request_id}/decision",
                     headers=admin_headers, json={"approved": True})

        class BrokenStorage:
            def delete(self, key):
                raise StorageError("private provider details")
        monkeypatch.setattr("app.api.privacy_routes.get_object_storage", lambda: BrokenStorage())
        response = client.post(f"/api/v1/admin/privacy/deletion-requests/{request_id}/execute",
                               headers=admin_headers,
                               json={"confirmation": "EXECUTE ACCOUNT ERASURE"})
        assert response.status_code == 503
        assert "private provider details" not in response.text

    db = SessionLocal()
    try:
        assert db.get(User, user_id).status == UserStatus.active
        assert db.get(TrustVisionEvidence, evidence_id) is not None
        assert db.get(AccountDeletionRequest, request_id).status == "approved"
    finally:
        db.close()
