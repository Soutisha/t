from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.models import User, UserRole, UserStatus
from app.core.security import create_access_token

def test_academy_course_learning_quiz_and_certificate_lifecycle():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine,autoflush=False,autocommit=False)
    def override_db():
        db=Session()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db]=override_db
    try:
        with Session() as db:
            admin=User(phone_e164="+917000000051",display_name="Academy Admin",status=UserStatus.active)
            learner=User(phone_e164="+917000000052",display_name="Mechanic Learner",status=UserStatus.active)
            db.add_all([admin,learner]); db.flush()
            db.add(UserRole(user_id=admin.id,role_code="administrator",scope_type="global",scope_id="*"))
            db.commit()
            admin_token=create_access_token(admin.id,["administrator"])
            learner_token=create_access_token(learner.id,["mechanic"])
        with TestClient(app) as client:
            course=client.post("/api/v1/admin/academy/courses",
                headers={"Authorization":f"Bearer {admin_token}"},
                json={"course_code":"TYRE-SAFE-01","title":"Tyre Safety Basics",
                      "description":"Intro course","category":"safety","difficulty":"beginner",
                      "estimated_minutes":15,"pass_percentage":70,
                      "lessons":[{"title":"Inspection basics","content":"Inspect tread and sidewall for visible damage.",
                                  "sequence":1,"asset_type":"interactive_3d","asset_reference":"demo:tyre-inspection"}],
                      "questions":[
                        {"prompt":"What should be checked?","options":["Tread and sidewall","Paint colour"],"correct_option":0,"sequence":1},
                        {"prompt":"When unsure about safety?","options":["Guess","Escalate for qualified inspection"],"correct_option":1,"sequence":2}
                      ]})
            assert course.status_code==201,course.text
            cid=course.json()["data"]["course_id"]
            publish=client.patch(f"/api/v1/admin/academy/courses/{cid}/publish",
                headers={"Authorization":f"Bearer {admin_token}"})
            assert publish.status_code==200,publish.text
            detail=client.get(f"/api/v1/academy/courses/{cid}",
                headers={"Authorization":f"Bearer {learner_token}"})
            assert detail.status_code==200
            lesson=detail.json()["data"]["lessons"][0]["lesson_id"]
            enroll=client.post(f"/api/v1/academy/courses/{cid}/enroll",
                headers={"Authorization":f"Bearer {learner_token}"})
            assert enroll.status_code==201,enroll.text
            eid=enroll.json()["data"]["enrollment_id"]
            premature=client.post(f"/api/v1/academy/enrollments/{eid}/quiz/submit",
                headers={"Authorization":f"Bearer {learner_token}"},
                json={"answers":{"not-yet-valid":0}})
            assert premature.status_code==409
            complete=client.post(f"/api/v1/academy/enrollments/{eid}/lessons/{lesson}/complete",
                headers={"Authorization":f"Bearer {learner_token}"})
            assert complete.status_code==200
            questions=detail.json()["data"]
            # question IDs are intentionally not exposed by course detail, so get them from DB test fixture.
            from app.models.academy import AcademyQuestion
            with Session() as db:
                qs=db.query(AcademyQuestion).filter_by(course_id=cid).order_by(AcademyQuestion.sequence).all()
                answers={qs[0].id:0,qs[1].id:1}
            submitted=client.post(f"/api/v1/academy/enrollments/{eid}/quiz/submit",
                headers={"Authorization":f"Bearer {learner_token}"},
                json={"answers":answers})
            assert submitted.status_code==200,submitted.text
            result=submitted.json()["data"]
            assert result["passed"] is True
            assert result["certificate"]["certificate_code"].startswith("EURO-")
            code=result["certificate"]["certificate_code"]
            verify=client.get(f"/api/v1/academy/certificates/verify/{code}")
            assert verify.status_code==200 and verify.json()["data"]["valid"] is True
            mine=client.get("/api/v1/academy/certificates/me",
                headers={"Authorization":f"Bearer {learner_token}"})
            assert len(mine.json()["data"])==1
    finally:
        app.dependency_overrides.pop(get_db,None)
        Base.metadata.drop_all(engine)
        engine.dispose()

def test_academy_certificate_not_issued_for_failed_quiz():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine,autoflush=False,autocommit=False)
    def override_db():
        db=Session()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db]=override_db
    try:
        with Session() as db:
            admin=User(phone_e164="+917000000053",display_name="Academy Admin2",status=UserStatus.active)
            learner=User(phone_e164="+917000000054",display_name="Learner2",status=UserStatus.active)
            db.add_all([admin,learner]); db.flush()
            db.add(UserRole(user_id=admin.id,role_code="administrator",scope_type="global",scope_id="*"))
            db.commit()
            at=create_access_token(admin.id,["administrator"]); lt=create_access_token(learner.id,["mechanic"])
        with TestClient(app) as client:
            cr=client.post("/api/v1/admin/academy/courses",headers={"Authorization":f"Bearer {at}"},
                json={"course_code":"FAIL-01","title":"Quiz Fail Course","pass_percentage":80,
                      "lessons":[{"title":"Lesson one","sequence":1}],
                      "questions":[{"prompt":"Q one?","options":["right","wrong"],"correct_option":0,"sequence":1}]})
            cid=cr.json()["data"]["course_id"]
            client.patch(f"/api/v1/admin/academy/courses/{cid}/publish",headers={"Authorization":f"Bearer {at}"})
            er=client.post(f"/api/v1/academy/courses/{cid}/enroll",headers={"Authorization":f"Bearer {lt}"})
            eid=er.json()["data"]["enrollment_id"]
            detail=client.get(f"/api/v1/academy/courses/{cid}",headers={"Authorization":f"Bearer {lt}"})
            lid=detail.json()["data"]["lessons"][0]["lesson_id"]
            client.post(f"/api/v1/academy/enrollments/{eid}/lessons/{lid}/complete",headers={"Authorization":f"Bearer {lt}"})
            from app.models.academy import AcademyQuestion
            with Session() as db: qid=db.query(AcademyQuestion).filter_by(course_id=cid).first().id
            answer=client.post(f"/api/v1/academy/enrollments/{eid}/quiz/submit",
                headers={"Authorization":f"Bearer {lt}"},json={"answers":{qid:1}})
            assert answer.status_code==200 and answer.json()["data"]["passed"] is False
            assert answer.json()["data"]["certificate"] is None
    finally:
        app.dependency_overrides.pop(get_db,None)
        Base.metadata.drop_all(engine)
        engine.dispose()
