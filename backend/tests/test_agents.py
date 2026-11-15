import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.models import User, UserRole, UserStatus
from app.models.agents import AgentRun
from app.core.security import create_access_token
from app.services.agents import classify_intent, run_agent_workflow

def test_supervisor_routes_to_expected_specialist():
    assert classify_intent("Can you check tyre compatibility for this bike?") == "fitment"
    assert classify_intent("What is my reward points balance?") == "rewards"
    assert classify_intent("Show available tools in tool bank") == "toolbank"
    assert classify_intent("Explain warranty from the manual") == "knowledge"
    assert classify_intent("What is my mechanic passport status?") == "mechanic_support"
    assert classify_intent("Hello there") == "general"
    assert classify_intent("Please reserve this tool for me") == "action_planning"

def test_mutating_request_is_blocked_and_flags_human_approval():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    try:
        with Session() as db:
            user = User(phone_e164="+917000000034", display_name="Approval Test", status=UserStatus.active)
            db.add(user); db.commit()
            result = run_agent_workflow("Please redeem 500 reward points", user.id, db)
            assert result["intent"] == "action_planning"
            assert result["requires_human_approval"] is True
            assert "not executed" in result["response"]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()

def test_general_agent_is_read_only_and_explains_scope():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    try:
        with Session() as db:
            user = User(phone_e164="+917000000031", display_name="Agent Test", status=UserStatus.active)
            db.add(user); db.commit()
            result = run_agent_workflow("Hello there", user.id, db)
            assert result["intent"] == "general"
            assert "approved Eurogrip knowledge" in result["response"]
            assert result["trace"][0]["agent"] == "supervisor_router"
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()

def test_agent_api_logs_run_and_enforces_private_run_access():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    def override_db():
        db = Session()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override_db
    try:
        with Session() as db:
            user = User(phone_e164="+917000000032", display_name="Agent API", status=UserStatus.active)
            other = User(phone_e164="+917000000033", display_name="Other User", status=UserStatus.active)
            db.add_all([user, other]); db.commit()
            token = create_access_token(user.id, ["mechanic"])
            other_token = create_access_token(other.id, ["mechanic"])
        with TestClient(app) as client:
            response = client.post("/api/v1/agents/run",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "Hello, what can you do?"})
            assert response.status_code == 201, response.text
            data = response.json()["data"]
            assert data["side_effects_performed"] is False
            assert data["agent_trace"]
            own = client.get(f"/api/v1/agents/runs/{data['run_id']}",
                headers={"Authorization": f"Bearer {token}"})
            assert own.status_code == 200
            private = client.get(f"/api/v1/agents/runs/{data['run_id']}",
                headers={"Authorization": f"Bearer {other_token}"})
            assert private.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
