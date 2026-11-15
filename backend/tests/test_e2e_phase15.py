import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.models import User, UserRole, UserStatus
from app.core.security import create_access_token


def _create_identity(role_code: str):
    db = SessionLocal()
    try:
        user = User(
            phone_e164=f"+9199{uuid.uuid4().int % 10**8:08d}",
            display_name="Phase 15 Integration Test",
            status=UserStatus.active,
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_code=role_code, scope_type="global", scope_id="*"))
        db.commit()
        return user.id, create_access_token(user.id, [role_code])
    finally:
        db.close()


def test_end_to_end_health_openapi_and_analytics_admin_workflow():
    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
        schema = client.get("/openapi.json")
        assert live.status_code == 200 and live.json()["status"] == "ok"
        assert ready.status_code == 200 and ready.json()["status"] == "ready"
        assert schema.status_code == 200
        paths = schema.json()["paths"]
        assert "/api/v1/admin/analytics/executive" in paths
        assert "/api/v1/admin/analytics/advocacy-funnel" in paths
        assert "/api/v1/admin/analytics/operations" in paths
        assert "/api/v1/admin/analytics/report.csv" in paths

        _, admin_token = _create_identity("administrator")
        headers = {"Authorization": f"Bearer {admin_token}"}
        executive = client.get("/api/v1/admin/analytics/executive", headers=headers)
        funnel = client.get("/api/v1/admin/analytics/advocacy-funnel", headers=headers)
        operations = client.get("/api/v1/admin/analytics/operations", headers=headers)
        report = client.get("/api/v1/admin/analytics/report.csv", headers=headers)

        assert executive.status_code == 200
        assert executive.json()["roi"]["status"] == "not_configured"
        assert "mechanics_registered" in executive.json()["data"]
        assert funnel.status_code == 200
        assert "verified_recommendations" in funnel.json()["data"]
        assert operations.status_code == 200
        assert "trustvision" in operations.json()["data"]
        assert report.status_code == 200
        assert report.headers["content-type"].startswith("text/csv")
        assert "verified_units_sold" in report.text


def test_end_to_end_analytics_enforces_authentication_and_role_scope():
    with TestClient(app) as client:
        unauthenticated = client.get("/api/v1/admin/analytics/executive")
        assert unauthenticated.status_code == 401

        _, mechanic_token = _create_identity("mechanic")
        forbidden = client.get(
            "/api/v1/admin/analytics/executive",
            headers={"Authorization": f"Bearer {mechanic_token}"},
        )
        assert forbidden.status_code == 403


def test_end_to_end_analytics_rejects_invalid_date_ranges():
    with TestClient(app) as client:
        _, token = _create_identity("eurogrip_admin")
        headers = {"Authorization": f"Bearer {token}"}
        invalid_order = client.get(
            "/api/v1/admin/analytics/executive?start=2026-02-01T00:00:00Z&end=2026-01-01T00:00:00Z",
            headers=headers,
        )
        excessive = client.get(
            "/api/v1/admin/analytics/executive?start=2024-01-01T00:00:00Z&end=2026-01-01T00:00:00Z",
            headers=headers,
        )
        assert invalid_order.status_code == 422
        assert excessive.status_code == 422



def test_end_to_end_mechanic_otp_onboarding_and_login():
    phone = f"+9188{uuid.uuid4().int % 10**8:08d}"
    with TestClient(app) as client:
        request = client.post("/api/v1/auth/otp/request", json={"phone_e164": phone})
        assert request.status_code == 200
        otp = request.json()["data"]["development_otp"]

        first_verify = client.post("/api/v1/auth/otp/verify", json={"phone_e164": phone, "code": otp})
        assert first_verify.status_code == 403
        assert "No account found" in first_verify.json()["detail"]

        registration = client.post("/api/v1/onboarding/mechanics", json={
            "phone_e164": phone,
            "display_name": "Phase Sixteen Mechanic",
            "shop_name": "Integration Workshop",
            "shop_type": "tyre_shop",
            "address_text": "12 Integration Road, Test Locality",
            "city": "Kolkata",
            "state": "West Bengal",
            "experience_years": 5,
            "languages": ["English", "Bengali"],
            "service_categories": ["tyres"],
            "participation_type": "interested",
            "location_consent": False,
            "consent_policy_version": "1.0",
        })
        assert registration.status_code == 201
        assert registration.json()["data"]["verification_status"] == "pending"

        second_request = client.post("/api/v1/auth/otp/request", json={"phone_e164": phone})
        assert second_request.status_code == 200
        second_otp = second_request.json()["data"]["development_otp"]
        login = client.post("/api/v1/auth/otp/verify", json={"phone_e164": phone, "code": second_otp})
        assert login.status_code == 200
        token = login.json()["data"]["access_token"]
        me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["data"]["phone_e164"] == phone
        assert "mechanic" in me.json()["data"]["roles"]
