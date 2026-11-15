import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.models import User
from app.models.copilot import KnowledgeDocument, KnowledgeChunk, CopilotQueryLog
from app.schemas.copilot import CopilotQuestion, CopilotFeedback
from app.services.copilot import (
    sha256_hex, extract_document, chunk_pages, embed_text,
    retrieve_chunks, _llm_answer, extractive_answer
)

router = APIRouter()
ADMIN = ("administrator", "eurogrip_admin")
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024

@router.post("/admin/copilot/documents", status_code=201)
async def ingest_document(
    title: str = Form(...),
    category: str = Form(default="general"),
    language: str = Form(default="en"),
    source_reference: str = Form(default=""),
    file: UploadFile = File(...),
    user: User = Depends(require_roles(*ADMIN)),
    db: Session = Depends(get_db)
):
    title = title.strip()
    category = category.strip().lower()
    if not title or len(title) > 240:
        raise HTTPException(status_code=422, detail="Document title is required and must be under 240 characters.")
    if category not in ("product", "fitment", "warranty", "training", "safety", "policy", "general"):
        raise HTTPException(status_code=422, detail="Unsupported knowledge category.")
    if language not in ("en", "hi", "bn", "ta", "te", "kn", "ml", "mr"):
        raise HTTPException(status_code=422, detail="Unsupported document language code.")
    data = await file.read(MAX_DOCUMENT_BYTES + 1)
    if not data or len(data) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Document is empty or exceeds 25 MB.")
    digest = sha256_hex(data)
    existing = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.source_sha256 == digest))
    if existing:
        raise HTTPException(status_code=409, detail=f"Identical document already exists: {existing.id}")
    filename = (file.filename or "knowledge-document")[:255]
    try:
        pages, page_count = extract_document(data, filename, file.content_type or "application/octet-stream")
        chunks = chunk_pages(pages)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not chunks:
        raise HTTPException(status_code=422, detail="No extractable text found. Scanned PDF OCR is not supported in this ingestion path; provide a text PDF or OCR text file.")
    if len(chunks) > 10000:
        raise HTTPException(status_code=413, detail="Document produces too many chunks.")
    doc = KnowledgeDocument(
        id=str(uuid.uuid4()), title=title, category=category, source_filename=filename,
        source_sha256=digest, mime_type=file.content_type or "application/octet-stream",
        source_reference=source_reference[:500], status="pending_review", language=language,
        page_count=page_count, chunk_count=len(chunks), uploaded_by=user.id
    )
    db.add(doc)
    db.flush()
    for item in chunks:
        vector = embed_text(item["content"])
        db.add(KnowledgeChunk(
            document_id=doc.id, chunk_index=item["chunk_index"],
            page_number=item["page_number"], content=item["content"],
            embedding_json=json.dumps(vector, separators=(",", ":")),
            token_count=item["token_count"]
        ))
    db.commit()
    return {"data": {"document_id": doc.id, "title": doc.title,
        "status": doc.status, "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "message": "Document indexed in pending review. It is excluded from Copilot answers until approved."}}

@router.get("/admin/copilot/documents")
def list_documents(user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    rows = db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())).all()
    return {"data": [{"document_id": d.id, "title": d.title, "category": d.category,
        "filename": d.source_filename, "status": d.status, "page_count": d.page_count,
        "chunk_count": d.chunk_count, "language": d.language,
        "uploaded_by": d.uploaded_by, "approved_at": d.approved_at} for d in rows]}

@router.patch("/admin/copilot/documents/{document_id}/approval")
def approve_document(document_id: str, approved: bool = Form(...),
                     user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    if doc.status != "pending_review":
        raise HTTPException(status_code=409, detail="Document has already been reviewed.")
    doc.status = "approved" if approved else "rejected"
    doc.approved_by = user.id
    doc.approved_at = datetime.now(timezone.utc)
    db.commit()
    return {"data": {"document_id": doc.id, "status": doc.status,
        "message": "Only approved documents are searchable by Copilot."}}

@router.post("/copilot/ask")
def ask_copilot(payload: CopilotQuestion, user: User = Depends(current_user), db: Session = Depends(get_db)):
    question = payload.question.strip()
    approved_ids = select(KnowledgeDocument.id).where(KnowledgeDocument.status == "approved")
    chunks = db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id.in_(approved_ids))).all()
    matches = retrieve_chunks(question, chunks)
    selected = [x for x in matches if x["score"] >= settings.rag_min_similarity]
    contexts = []
    for index, item in enumerate(selected, start=1):
        chunk = item["chunk"]
        doc = db.get(KnowledgeDocument, chunk.document_id)
        if not doc or doc.status != "approved":
            continue
        contexts.append({
            "citation_id": f"S{index}", "document_id": doc.id, "title": doc.title,
            "category": doc.category, "source_reference": doc.source_reference,
            "page_number": chunk.page_number, "chunk_index": chunk.chunk_index,
            "content": chunk.content, "similarity": round(item["score"], 4)
        })
    abstained = not contexts
    mode = "abstain"
    if abstained:
        answer = "I could not find enough supporting information in the approved Eurogrip knowledge base to answer reliably. I will not guess product specifications, tyre compatibility, warranty terms or safety instructions. Please contact an authorised Eurogrip representative."
    else:
        answer = _llm_answer(question, contexts)
        if answer:
            mode = "grounded_llm"
        else:
            answer = extractive_answer(question, contexts)
            mode = "extractive"
    citations = [{"citation_id": c["citation_id"], "document_id": c["document_id"],
        "title": c["title"], "category": c["category"],
        "source_reference": c["source_reference"], "page_number": c["page_number"],
        "chunk_index": c["chunk_index"], "similarity": c["similarity"]} for c in contexts]
    log = CopilotQueryLog(user_id=user.id, question=question, answer=answer,
        answer_mode=mode, abstained=abstained, retrieval_count=len(contexts),
        citations_json=json.dumps(citations, separators=(",", ":")))
    db.add(log)
    db.commit()
    return {"data": {"query_id": log.id, "answer": answer, "answer_mode": mode,
        "abstained": abstained, "citations": citations,
        "disclaimer": "Use approved product and fitment documentation. Do not treat an unsupported answer as a compatibility approval."}}

@router.post("/copilot/queries/{query_id}/feedback")
def copilot_feedback(query_id: str, payload: CopilotFeedback,
                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    log = db.get(CopilotQueryLog, query_id)
    if not log or log.user_id != user.id:
        raise HTTPException(status_code=404, detail="Copilot query not found.")
    log.feedback = payload.feedback
    db.commit()
    return {"data": {"query_id": log.id, "feedback": log.feedback}}
