from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.models import User, UserRole, Mechanic, UserStatus
from app.core.security import create_access_token
from app.core.config import settings

def test_authenticated_evidence_upload_persists_reviewable_evidence(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(settings, "trustvision_storage_dir", str(tmp_path / "private"))
    try:
        with TestingSession() as db:
            user = User(phone_e164="+917000000001", display_name="Upload Test", status=UserStatus.active)
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_code="mechanic", scope_type="global", scope_id="*"))
            db.add(UserRole(user_id=user.id, role_code="administrator", scope_type="global", scope_id="*"))
            db.add(Mechanic(user_id=user.id, mechanic_code="EGM-UPLOADTEST01",
                shop_type="independent", experience_years=2, languages="English",
                service_categories="tyres", participation_type="non_stockist_advocate"))
            db.commit()
            token = create_access_token(user.id, ["mechanic", "administrator"])

        image = Image.new("RGB", (640, 480), (80, 100, 120))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        with TestClient(app) as client:
            response = client.post("/api/v1/trustvision/evidence",
                headers={"Authorization": f"Bearer {token}"},
                data={"evidence_kind": "fitment"},
                files={"file": ("fitment.png", buffer.getvalue(), "image/png")})
            assert response.status_code == 201, response.text
            body = response.json()["data"]
            assert body["evidence_id"]
            assert body["evidence_kind"] == "fitment"
            stored = client.get(
                f"/api/v1/admin/trustvision/evidence/{body['evidence_id']}/file",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert stored.status_code == 200, stored.text
            assert stored.content == buffer.getvalue()
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
