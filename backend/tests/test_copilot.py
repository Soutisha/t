import json
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.models import User, UserRole, UserStatus
from app.models.copilot import KnowledgeDocument, KnowledgeChunk
from app.core.security import create_access_token
from app.services.copilot import (
    normalise_text, chunk_pages, embed_text, cosine_similarity,
    extract_document, sha256_hex
)

def test_chunking_preserves_page_and_overlaps_content():
    text = " ".join(f"tyre specification item {i}" for i in range(160))
    chunks = chunk_pages([{"page_number": 4, "text": text}], chunk_chars=240, overlap=40)
    assert len(chunks) > 1
    assert all(x["page_number"] == 4 for x in chunks)
    assert chunks[0]["content"][-30:] in chunks[1]["content"]

def test_hash_embeddings_are_normalised_and_repeatable(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "rag_embedding_provider", "hashing")
    a = embed_text("approved tyre safety instructions")
    b = embed_text("approved tyre safety instructions")
    assert a == b
    assert abs(cosine_similarity(a, a) - 1.0) < 1e-6

def test_plain_text_ingestion_is_utf8_and_hashable():
    raw = b"# Approved tyre guide\nTyre pressure guidance is specified in this manual."
    pages, count = extract_document(raw, "guide.md", "text/markdown")
    assert count == 1
    assert "Tyre pressure guidance" in pages[0]["text"]
    assert sha256_hex(raw)

def test_copilot_api_requires_approved_sources_and_returns_citations():
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
    try:
        with TestingSession() as db:
            admin = User(phone_e164="+917000000021", display_name="Knowledge Admin", status=UserStatus.active)
            mechanic = User(phone_e164="+917000000022", display_name="Knowledge Mechanic", status=UserStatus.active)
            db.add_all([admin, mechanic]); db.flush()
            db.add(UserRole(user_id=admin.id, role_code="administrator", scope_type="global", scope_id="*"))
            db.add(UserRole(user_id=mechanic.id, role_code="mechanic", scope_type="global", scope_id="*"))
            db.commit()
            admin_token = create_access_token(admin.id, ["administrator"])
            mechanic_token = create_access_token(mechanic.id, ["mechanic"])

        with TestClient(app) as client:
            raw = b"Approved tyre safety guide. The tyre pressure must be checked using the vehicle manufacturer recommendation. Follow the specified cold tyre pressure for the vehicle."
            upload = client.post("/api/v1/admin/copilot/documents",
                headers={"Authorization": f"Bearer {admin_token}"},
                data={"title": "Tyre Safety Guide", "category": "safety", "language": "en"},
                files={"file": ("tyre-guide.txt", raw, "text/plain")})
            assert upload.status_code == 201, upload.text
            document_id = upload.json()["data"]["document_id"]

            pending_answer = client.post("/api/v1/copilot/ask",
                headers={"Authorization": f"Bearer {mechanic_token}"},
                json={"question": "What does the guide say about tyre pressure?"})
            assert pending_answer.status_code == 200
            assert pending_answer.json()["data"]["abstained"] is True

            approved = client.patch(f"/api/v1/admin/copilot/documents/{document_id}/approval",
                headers={"Authorization": f"Bearer {admin_token}"},
                data={"approved": "true"})
            assert approved.status_code == 200, approved.text

            answer = client.post("/api/v1/copilot/ask",
                headers={"Authorization": f"Bearer {mechanic_token}"},
                json={"question": "What does the guide say about tyre pressure?"})
            assert answer.status_code == 200, answer.text
            data = answer.json()["data"]
            assert data["abstained"] is False
            assert data["citations"]
            assert data["citations"][0]["title"] == "Tyre Safety Guide"
            assert "[S1]" in data["answer"]
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
