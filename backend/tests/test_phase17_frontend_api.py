import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.core.security import create_access_token
from app.models.models import User, UserRole, UserStatus, Mechanic, Shop, VerificationStatus


def _admin():
    db=SessionLocal()
    try:
        user=User(phone_e164=f"+9177{uuid.uuid4().int % 10**8:08d}",display_name="Phase 17 Admin",status=UserStatus.active)
        db.add(user);db.flush()
        db.add(UserRole(user_id=user.id,role_code="administrator",scope_type="global",scope_id="*"))
        db.commit()
        return create_access_token(user.id,["administrator"])
    finally: db.close()


def _mechanic():
    db=SessionLocal()
    try:
        user=User(phone_e164=f"+9176{uuid.uuid4().int % 10**8:08d}",display_name="Phase 17 Mechanic",status=UserStatus.active)
        db.add(user);db.flush()
        mechanic=Mechanic(user_id=user.id,mechanic_code="EGM-"+uuid.uuid4().hex[:10].upper(),shop_type="tyre_shop",
            experience_years=7,languages="Bengali, English",service_categories="tyres",
            participation_type="interested",verification_status=VerificationStatus.pending)
        db.add(mechanic);db.flush()
        db.add(Shop(owner_mechanic_id=mechanic.id,name="Live Workshop",shop_type="tyre_shop",
            address_text="Test Road",city="Kolkata",state="West Bengal",location_consent=False))
        db.commit()
        return mechanic.id,mechanic.mechanic_code
    finally: db.close()


def test_admin_mechanic_directory_and_profile_verification():
    token=_admin()
    mechanic_id,code=_mechanic()
    headers={"Authorization":f"Bearer {token}"}
    with TestClient(app) as client:
        listing=client.get("/api/v1/admin/mechanics?q=Live%20Workshop",headers=headers)
        assert listing.status_code==200
        record=next(x for x in listing.json()["data"] if x["mechanic_code"]==code)
        assert record["city"]=="Kolkata"
        assert record["verification_status"]=="pending"
        decision=client.patch(f"/api/v1/admin/onboarding/mechanics/{mechanic_id}/verification",
            headers=headers,json={"approved":True})
        assert decision.status_code==200
        assert decision.json()["data"]["verification_status"]=="verified"
        repeated=client.patch(f"/api/v1/admin/onboarding/mechanics/{mechanic_id}/verification",
            headers=headers,json={"approved":False})
        assert repeated.status_code==409


def test_mechanic_directory_is_admin_only():
    with TestClient(app) as client:
        denied=client.get("/api/v1/admin/mechanics")
        assert denied.status_code==401
        token=create_access_token("nonexistent-user",["mechanic"])
        # A syntactically valid token with a non-existent subject is rejected by auth dependency.
        denied=client.get("/api/v1/admin/mechanics",headers={"Authorization":f"Bearer {token}"})
        assert denied.status_code in (401,403)



def test_field_rep_can_read_directory_but_cannot_verify_profiles():
    db=SessionLocal()
    try:
        user=User(phone_e164=f"+9175{uuid.uuid4().int % 10**8:08d}",display_name="Phase 17 Field Rep",status=UserStatus.active)
        db.add(user);db.flush()
        db.add(UserRole(user_id=user.id,role_code="field_rep",scope_type="global",scope_id="*"))
        db.commit()
        token=create_access_token(user.id,["field_rep"])
    finally: db.close()
    mechanic_id,_=_mechanic()
    with TestClient(app) as client:
        headers={"Authorization":f"Bearer {token}"}
        listing=client.get("/api/v1/admin/mechanics",headers=headers)
        assert listing.status_code==200
        denied=client.patch(f"/api/v1/admin/onboarding/mechanics/{mechanic_id}/verification",
            headers=headers,json={"approved":True})
        assert denied.status_code==403



def test_academy_course_publish_enrol_lesson_quiz_certificate_journey():
    admin_token = _admin()
    mechanic_id, _ = _mechanic()
    db = SessionLocal()
    try:
        mechanic = db.get(Mechanic, mechanic_id)
        mechanic_user_id = mechanic.user_id
        mechanic_token = create_access_token(mechanic_user_id, ["mechanic"])
    finally:
        db.close()

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    mechanic_headers = {"Authorization": f"Bearer {mechanic_token}"}
    with TestClient(app) as client:
        created = client.post("/api/v1/admin/academy/courses", headers=admin_headers, json={
            "course_code": "P17-E2E-" + uuid.uuid4().hex[:8],
            "title": "Tyre Safety Fundamentals",
            "description": "Test course for the full learning journey.",
            "category": "technical",
            "difficulty": "beginner",
            "language": "en",
            "estimated_minutes": 10,
            "pass_percentage": 70,
            "lessons": [{
                "title": "Inspect the tyre",
                "content": "Check tread, pressure and visible damage.",
                "sequence": 1,
                "estimated_minutes": 5,
                "asset_type": "article",
                "required": True
            }],
            "questions": [{
                "prompt": "What should be checked during a tyre inspection?",
                "options": ["Tread and pressure", "Paint colour"],
                "correct_option": 0,
                "sequence": 1
            }]
        })
        assert created.status_code == 201, created.text
        course_id = created.json()["data"]["course_id"]

        unpublished = client.get(f"/api/v1/academy/courses/{course_id}", headers=mechanic_headers)
        assert unpublished.status_code == 404

        published = client.patch(f"/api/v1/admin/academy/courses/{course_id}/publish", headers=admin_headers)
        assert published.status_code == 200
        detail = client.get(f"/api/v1/academy/courses/{course_id}", headers=mechanic_headers)
        assert detail.status_code == 200
        course = detail.json()["data"]
        assert len(course["lessons"]) == 1
        assert len(course["quiz_questions"]) == 1

        enrolled = client.post(f"/api/v1/academy/courses/{course_id}/enroll", headers=mechanic_headers)
        assert enrolled.status_code == 201
        enrollment_id = enrolled.json()["data"]["enrollment_id"]
        lesson_id = course["lessons"][0]["lesson_id"]

        blocked_quiz = client.post(
            f"/api/v1/academy/enrollments/{enrollment_id}/quiz/submit",
            headers=mechanic_headers,
            json={"answers": {course["quiz_questions"][0]["question_id"]: 0}}
        )
        assert blocked_quiz.status_code == 409

        completed = client.post(
            f"/api/v1/academy/enrollments/{enrollment_id}/lessons/{lesson_id}/complete",
            headers=mechanic_headers
        )
        assert completed.status_code == 200
        assert completed.json()["data"]["progress_percentage"] == 100

        quiz = client.post(
            f"/api/v1/academy/enrollments/{enrollment_id}/quiz/submit",
            headers=mechanic_headers,
            json={"answers": {course["quiz_questions"][0]["question_id"]: 0}}
        )
        assert quiz.status_code == 200
        assert quiz.json()["data"]["passed"] is True
        assert quiz.json()["data"]["certificate"]["certificate_code"].startswith("EURO-")

        certificates = client.get("/api/v1/academy/certificates/me", headers=mechanic_headers)
        assert certificates.status_code == 200
        assert len(certificates.json()["data"]) == 1


def test_frontend_workspace_api_contracts_are_registered():
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/passport/me": {"get"},
        "/api/v1/passport/me/visibility": {"patch"},
        "/api/v1/passport/me/skills": {"post"},
        "/api/v1/toolbank/catalog": {"get"},
        "/api/v1/toolbank/requests": {"post"},
        "/api/v1/rewards/me": {"get"},
        "/api/v1/rewards/redemptions": {"post"},
        "/api/v1/advocacy/products": {"get"},
        "/api/v1/advocacy/recommendations": {"post"},
        "/api/v1/advocacy/fitments": {"post"},
        "/api/v1/academy/courses": {"get"},
        "/api/v1/academy/courses/{course_id}/enroll": {"post"},
        "/api/v1/academy/enrollments/{enrollment_id}/quiz/submit": {"post"},
        "/api/v1/geo/locations": {"post"},
        "/api/v1/geo/nearby": {"get"},
        "/api/v1/trustvision/evidence": {"post"},
        "/api/v1/copilot/ask": {"post"},
        "/api/v1/agents/run": {"post"},
        "/api/v1/admin/mechanics": {"get"},
        "/api/v1/admin/analytics/executive": {"get"},
    }
    for path, methods in expected.items():
        assert path in paths, f"Missing API path: {path}"
        assert methods.issubset(set(paths[path])), f"Missing methods for {path}"



def test_health_readiness_reports_dependencies_in_development():
    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["checks"]["database"] == "connected"
