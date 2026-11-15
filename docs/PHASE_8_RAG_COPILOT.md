# Phase 8 — Eurogrip AI Copilot (RAG)

## Purpose
Provide a source-grounded assistant over an administrator-curated Eurogrip knowledge base. The Copilot retrieves approved source passages, cites the supporting document and page, and abstains when evidence is insufficient. It must not invent product specifications, vehicle compatibility, warranty terms, prices or safety guidance.

## Implemented capabilities

### Knowledge ingestion and governance
- Authenticated administrator upload for PDF, DOCX, TXT, Markdown and raster images.
- PDF text extraction, DOCX paragraph/table extraction, UTF-8 text ingestion and Tesseract OCR for image uploads.
- SHA-256 duplicate document detection.
- Configurable text chunking with overlap and page metadata.
- Document metadata includes title, category, language, filename, source reference, uploader, approval identity and status.
- New documents enter `pending_review`; only an administrator can approve or reject them.
- Retrieval is restricted to documents in `approved` status. Pending and rejected documents are excluded.

### Retrieval and citations
- Persisted chunk vectors and cosine similarity ranking.
- Deterministic signed feature hashing is the dependency-light default embedding backend.
- Optional `sentence-transformers` backend can be enabled with `RAG_EMBEDDING_PROVIDER=sentence_transformers`; the configured model is loaded locally on first use. Install `sentence-transformers` separately and provision/cache the model in deployment.
- Top-K retrieval, configurable minimum similarity threshold, chunk overlap and citation metadata.
- Each returned source includes document ID, title, category, page number, chunk index, source reference and similarity score.

### Answer generation
- Optional OpenAI-compatible chat-completions endpoint configured through `RAG_LLM_BASE_URL`, `RAG_LLM_API_KEY` and `RAG_LLM_MODEL`.
- The generation prompt requires answers to use only supplied approved passages, treats retrieved documents as untrusted reference data, requires source citations, and instructs the model to abstain on unsupported product/fitment/safety facts.
- If no LLM endpoint is configured or the call fails, the service uses an extractive sentence-selection fallback and still cites the supporting source.
- If no retrieved passage meets the configured threshold, the service abstains rather than guessing.
- Query history records answer mode, abstention, retrieval count and citations. Users can submit feedback.

## API endpoints
- `POST /api/v1/admin/copilot/documents` — upload and index a document in pending review.
- `GET /api/v1/admin/copilot/documents` — administrator document catalogue.
- `PATCH /api/v1/admin/copilot/documents/{document_id}/approval` — approve or reject a pending document.
- `POST /api/v1/copilot/ask` — authenticated source-grounded question answering.
- `POST /api/v1/copilot/queries/{query_id}/feedback` — submit feedback on the user's own query.

## Configuration
- `RAG_EMBEDDING_PROVIDER=hashing` uses deterministic lexical feature hashing with 384 dimensions and no external model download.
- For semantic retrieval, install `sentence-transformers` and set `RAG_EMBEDDING_PROVIDER=sentence_transformers`. Model weights must be provisioned and reviewed for the target environment.
- `RAG_CHUNK_CHARS`, `RAG_CHUNK_OVERLAP`, `RAG_TOP_K` and `RAG_MIN_SIMILARITY` tune retrieval.
- Leave LLM settings empty to use extractive fallback. Configure only an approved enterprise endpoint and secret manager-backed API key for generated answers.
- PDF ingestion requires `pypdf`; DOCX ingestion requires `python-docx`; image OCR requires Tesseract binary and language packs.

## Important limitations
- No real Eurogrip manuals, product catalogue, vehicle-fitment tables, warranty policies or dealer documents have been supplied. The knowledge base starts empty; no product fact or compatibility claim has been fabricated.
- The default hashing vectorizer is lexical retrieval, not a transformer semantic embedding. Similarity threshold must be calibrated against a representative approved document/query set.
- Sentence-transformers is an optional backend and is not included in the base requirements to avoid silently downloading model weights.
- No translation model is connected. Language metadata and multilingual query strings are accepted, but translation/quality across Indian languages is not validated.
- Scanned PDF OCR is not implemented in this phase. Image file OCR is supported when Tesseract is available.
- The default store keeps vectors as JSON in the relational database and computes similarity in application memory. This is suitable for a small pilot, not a national-scale corpus. PostgreSQL pgvector/indexed retrieval is a later scaling task.
- The optional LLM endpoint has not been connected to a real provider. The tested path is extractive fallback.
- Frontend chat and document-review screens remain to be wired to these APIs.
- Automated tests cover chunking, embeddings, parsing, approval gating, citations and the authenticated question-answering API. Load testing, adversarial prompt-injection evaluation, retrieval benchmarking and human quality evaluation remain outstanding.

## Verification
- All backend Python files pass syntax compilation.
- Full backend test suite passes 19 tests.
- FastAPI app import and route registration are verified. This is not a production deployment certification.
