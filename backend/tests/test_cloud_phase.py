import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models.models import User, UserStatus
from app.schemas.cloud import IntegrationCreate
from app.services.cloud import create_connection, enqueue_event, outbox_summary, retry_outbox_event
from app.services.object_storage import LocalObjectStorage, StorageError

def _db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine,sessionmaker(bind=engine,autoflush=False,autocommit=False)

def test_integration_never_persists_raw_credentials():
    engine,Session=_db()
    try:
        with Session() as db:
            user=User(phone_e164="+917000000101",display_name="Cloud Admin",status=UserStatus.active)
            db.add(user);db.commit()
            payload=IntegrationCreate(provider="erpnext",connection_name="ERP sandbox",
                credential_env_key="ERP_API_TOKEN",base_url="https://erp.example.test",
                config={"company":"Demo"})
            row=create_connection(db,user.id,payload)
            assert row.status=="awaiting_secret"
            assert "token-value" not in row.config_json
            assert row.credential_env_key=="ERP_API_TOKEN"
    finally:
        Base.metadata.drop_all(engine);engine.dispose()

def test_outbox_enqueue_summary_and_retry():
    engine,Session=_db()
    try:
        with Session() as db:
            event=enqueue_event(db,"mechanic.profile.updated","mechanic","m-1",{"change":"profile"})
            assert outbox_summary(db)=={"pending":1}
            event.status="failed";event.attempts=3;db.commit()
            retry_outbox_event(db,event)
            assert event.status=="pending" and event.attempts==0
    finally:
        Base.metadata.drop_all(engine);engine.dispose()

def test_local_object_storage_rejects_path_traversal(tmp_path):
    store=LocalObjectStorage(str(tmp_path/"private"))
    key=store.put("evidence/a.bin",b"test","application/octet-stream")
    assert store.get(key)==b"test"
    try:
        store.put("../escape.bin",b"bad","text/plain")
        assert False
    except StorageError:
        pass

def test_adapter_registry_does_not_claim_unconfigured_providers():
    from app.services.integration_adapters import registry
    assert registry.get("erpnext") is None


def test_admin_integration_api_creates_connection_and_queues_sync():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db
    from app.models.models import UserRole
    from app.core.security import create_access_token
    engine,Session=_db()
    def override_db():
        db=Session()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db]=override_db
    try:
        with Session() as db:
            user=User(phone_e164="+917000000102",display_name="Admin API",status=UserStatus.active)
            db.add(user);db.flush()
            db.add(UserRole(user_id=user.id,role_code="administrator",scope_type="global",scope_id="*"))
            db.commit()
            token=create_access_token(user.id,["administrator"])
        with TestClient(app) as client:
            headers={"Authorization":f"Bearer {token}"}
            created=client.post("/api/v1/admin/integrations/connections",headers=headers,json={
                "provider":"erpnext","connection_name":"ERP sandbox","environment":"sandbox",
                "base_url":"https://erp.example.test","credential_env_key":"ERP_API_TOKEN",
                "config":{"company":"Example"}
            })
            assert created.status_code==201,created.text
            assert created.json()["data"]["status"]=="awaiting_secret"
            cid=created.json()["data"]["id"]
            queued=client.post(f"/api/v1/admin/integrations/connections/{cid}/sync",
                headers=headers,json={"operation":"health_check"})
            assert queued.status_code==409
            with Session() as db:
                connection=db.get(__import__("app.models.cloud",fromlist=["IntegrationConnection"]).IntegrationConnection,cid)
                connection.status="configured";db.commit()
            queued=client.post(f"/api/v1/admin/integrations/connections/{cid}/sync",
                headers=headers,json={"operation":"health_check"})
            assert queued.status_code==202
            assert queued.json()["data"]["status"]=="queued"
    finally:
        app.dependency_overrides.pop(get_db,None)
        Base.metadata.drop_all(engine);engine.dispose()
