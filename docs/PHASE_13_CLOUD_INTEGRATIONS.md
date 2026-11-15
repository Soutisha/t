# Phase 13 — Cloud Infrastructure and Enterprise Integration Foundation

## Delivered

### Container deployment
- Added a backend Dockerfile with Python 3.12, OCR system dependency, pinned Python dependencies and an Alembic migration step before Uvicorn starts.
- Added Docker Compose services for PostgreSQL 16, Redis 7, MinIO object storage and the API.
- Added persistent volumes for PostgreSQL, Redis, MinIO and the existing TrustVision local evidence directory.
- Added `.dockerignore` and `.env.cloud.example`; deployment secrets are injected through environment variables and are not committed.

### Database migrations
- Added Alembic configuration, migration environment and a generated initial schema migration covering the current SQLAlchemy metadata.
- Verified `alembic upgrade head` against a clean local SQLite database.
- Production API startup no longer relies on `Base.metadata.create_all`; the container command applies migrations before starting the server.
- Future schema changes must be made as reviewed incremental migrations. Do not regenerate or edit the initial migration for an already deployed database.

### Distributed rate limiting
- Added optional Redis-backed fixed-window request counters in the API middleware.
- Production configuration requires a Redis URL; production fails closed if Redis is unavailable or not configured.
- Local development retains the process-local fallback when Redis is not configured.
- The current Redis counters use atomic INCR and expiry operations.

### Object storage abstraction
- Added a private local object-storage adapter with path traversal protection and restrictive filesystem permissions.
- Added an S3-compatible adapter with server-side AES256 encryption, private bucket access by default and configurable region, prefix and endpoint.
- Added optional cloud dependencies in `backend/requirements-cloud.txt`.
- The current TrustVision evidence upload route still uses its pre-existing local file implementation; migrating existing evidence to S3 and wiring the route through this abstraction remain follow-up work.

### Enterprise integration framework
- Added integration connection records for ERPNext, SAP, Dynamics 365, webhooks and S3.
- Credentials are referenced by environment-variable name only. Raw secrets are not accepted or stored in the connection JSON.
- Added sync run records and an event outbox with retry support.
- Added a provider adapter interface and registry so reviewed connector implementations can be added without coupling provider logic to API routes.
- Added administrator APIs to configure/list connections, queue sync requests, inspect sync runs and inspect/retry outbox events.

## New APIs
- `POST /api/v1/admin/integrations/connections`
- `GET /api/v1/admin/integrations/connections`
- `POST /api/v1/admin/integrations/connections/{connection_id}/sync`
- `GET /api/v1/admin/integrations/sync-runs`
- `POST /api/v1/admin/integrations/outbox`
- `GET /api/v1/admin/integrations/outbox`
- `POST /api/v1/admin/integrations/outbox/{event_id}/retry`

## Deployment quick start
1. Copy `.env.cloud.example` to `.env` at the repository root.
2. Replace every example password and secret with unique cryptographically random values.
3. Set `CORS_ORIGINS` to the exact trusted frontend origin.
4. Run `docker compose up --build`.
5. API container runs `alembic upgrade head` before Uvicorn.
6. Check `/health/live` and `/health/ready`.

The Compose file is a local infrastructure reference using MinIO as an S3-compatible service. For AWS, replace MinIO with an S3 bucket, use IAM roles instead of static access keys, and configure managed PostgreSQL and Redis services.

## Verification
- 72 backend Python files pass syntax compilation.
- Full backend suite: 37 tests passed.
- Initial Alembic migration was generated and successfully upgraded on a clean SQLite database.
- API route/model import check: 99 routes and 50 tables.

## Explicitly not delivered
- No AWS account, VPC, ECS/EKS, RDS, ElastiCache, S3 bucket or cloud DNS has been provisioned.
- No real ERPNext, SAP or Dynamics 365 tenant is connected. No provider adapter is registered yet.
- Sync requests are persisted as queued records; a provider-specific worker is not included and will not falsely mark them complete.
- Outbox events are persisted and retryable, but a production dispatcher, delivery receipts, dead-letter queue and webhook signing/allowlist policy are not yet implemented.
- Redis is used for distributed API throttling; it is not yet used for background job execution or caching.
- S3 object storage is implemented as an adapter but is not yet wired into TrustVision evidence intake.
- MinIO root credentials in Compose are for local development only. Production requires least-privilege IAM/service accounts, TLS, bucket policies, lifecycle rules, KMS policy review and secrets management.
- Docker Compose was authored and statically reviewed; Docker is not available in the execution environment, so images and multi-container startup were not run here.
- A cloud security review, disaster-recovery exercise and live ERP integration test remain outstanding.

Phase 13 therefore provides deployable infrastructure definitions and integration contracts, not a claim that a live enterprise cloud deployment or ERP synchronization is already operational.
