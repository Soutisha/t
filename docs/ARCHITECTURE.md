# Phase 1 — System Architecture

## 1. Architecture decision
Use a **modular monolith** with a single deployable FastAPI backend initially. Modules have explicit boundaries and communicate through application services and domain events. Extract a service only when independent scaling, security isolation or release cadence justifies it.

## 2. Proposed stack
- Web: Next.js, React, TypeScript.
- Mobile: defer a separate React Native app until the responsive/PWA workflow is validated.
- API: Python, FastAPI, Pydantic.
- Persistence: PostgreSQL; PostGIS extension for spatial queries.
- ORM/migrations: SQLAlchemy 2 and Alembic.
- Cache/jobs: Redis plus a background worker (Celery or RQ; choose one during implementation).
- File storage: S3-compatible object storage; local MinIO for development.
- AI: isolated Python modules; scikit-learn/OpenCV/OCR first, model serving only when justified.
- RAG: pgvector initially to reduce operational complexity; Qdrant can be evaluated if retrieval scale requires it.
- Agent workflows: LangGraph, introduced only in Phase 9.
- Auth: OIDC-compatible identity provider in production; local development auth adapter for early phases.
- Deployment: Docker Compose for development; AWS deployment design in Phase 13.
- Observability: structured logs, metrics and tracing; Prometheus/Grafana when deployed.

## 3. Logical modules
1. Identity & Access
2. Mechanic CRM
3. Mechanic Passport
4. Product Catalogue & Fitment
5. Advocacy Ledger
6. Tool Bank & Rewards
7. Evidence & TrustVision
8. Knowledge Base & Copilot
9. Agent Workflows
10. Training & Certification
11. Geospatial Intelligence
12. Notifications & Integrations
13. Fraud Review
14. Analytics & Reporting
15. Administration & Audit

Each module owns its domain services, schemas and repository interfaces. Cross-module writes must go through application services rather than direct table mutation.

## 4. Roles and access
- Mechanic: own profile, own requests, advocacy submissions, training.
- Shop owner: shop profile and explicitly delegated shop operations.
- Field representative: assigned territory and permitted mechanic records.
- Dealer/distributor: own catalogue/stock submissions and referred requests.
- Administrator: scoped administrative functions; privileged actions require audit records and, where configured, a second approval.

RBAC is supplemented by object-level checks (ownership, territory assignment, dealer ownership). A role alone must not grant access to every record.

## 5. Runtime topology
Browser/PWA -> Next.js frontend -> FastAPI API -> domain modules -> PostgreSQL/PostGIS.
The API writes files to object storage and metadata to PostgreSQL. Background jobs process OCR, notifications, imports and analytics refreshes. Redis is used for caching, rate limits and job coordination, not as the system of record.

## 6. Event model
Domain events are persisted through an outbox table in the same transaction as the business change. A worker publishes/handles events idempotently. Initial events include:
- MechanicRegistered
- MechanicProfileVerified
- RecommendationSubmitted
- FitmentEvidenceSubmitted
- FitmentVerified
- StockingRecordConfirmed
- ToolRequestSubmitted
- ToolRequestApproved
- RewardLedgerEntryCreated
- TrainingCompleted
- FraudReviewOpened

Events are not proof by themselves; source records and verification evidence remain authoritative.

## 7. Offline strategy
The web client may cache approved read-only reference data and queue eligible submissions locally. Every queued command receives a client-generated UUID idempotency key and client timestamp. Server timestamps remain authoritative. Conflicts are surfaced for review; rewards, approvals and stock confirmations are never finalised offline.

## 8. AI boundaries
AI components are advisory and evidence-linked. They cannot directly issue rewards, approve equipment, change access, confirm stock or permanently reject a mechanic. Outputs include model/version, confidence where meaningful, evidence references and review state. RAG answers cite approved source chunks.

## 9. Deployment environments
- Local: Docker Compose, seeded synthetic data, mock integrations.
- Test/staging: isolated database, sandbox providers, test accounts.
- Production: managed secrets, encrypted storage, backups, monitoring, least-privilege IAM and approved integrations.

## 10. Architecture decision records
- ADR-001: Modular monolith first.
- ADR-002: PostgreSQL is the system of record.
- ADR-003: pgvector first for RAG to minimise infrastructure.
- ADR-004: Offline queue only for safe, idempotent submissions.
- ADR-005: Human approval for high-impact operations.
