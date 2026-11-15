# EUROGRIP PITSTOP OS

Greenfield implementation of a national mechanic advocacy platform for Eurogrip.

## Current status
- Phase 0: Greenfield repository audit completed.
- Phase 1: Architecture and technical contract baseline documented.
- Phase 2: UI/UX source created; local build/test still required.
- Phase 3: Authentication/onboarding API source created; runtime verification required.
- Phase 4: Mechanic Passport API/models created; runtime verification required.
- Phase 5: Tool Bank and rewards API/models created; runtime verification required.
- Phase 6: Advocacy and verified fitment API/models created; included in the passing backend test suite.
- Phase 7: TrustVision evidence intake, QR/OCR processing, duplicate detection and human fraud review APIs created.
- Phase 8: RAG Copilot document ingestion, approval-gated retrieval, citations and abstention implemented.
- Phase 9: Supervisor and specialist agent workflows, run audit traces and human-approval boundary implemented.
- Phase 10: Consent-based geospatial registration, nearby discovery and territory lookup implemented.
- Phase 11: Training Academy course lifecycle, lesson progress, quiz grading and certificate verification implemented; 28 backend tests pass.
- Phase 12: JWT validation, OTP-gated onboarding, API throttling, request audit events, security headers and versioned consent controls implemented; 32 backend tests pass.
- Phase 13: Docker/Compose infrastructure, PostgreSQL/Redis/MinIO configuration, Alembic baseline, S3 storage adapter and enterprise integration/outbox framework implemented; 37 backend tests pass.
- No live cloud account or ERP provider is connected; integration framework and local infrastructure definitions are provided.

## Development principles
- Modular monolith first.
- API-first backend.
- Database-backed workflows.
- Role-based access control.
- Synthetic demo data clearly labelled.
- Human approval for financial, reward, access and irreversible actions.
- Tests and evidence required for every completed phase.

See `docs/PROJECT_AUDIT.md`, `docs/IMPLEMENTATION_ROADMAP.md`, `docs/PHASE_4_MECHANIC_PASSPORT.md`, `docs/PHASE_5_TOOL_BANK_REWARDS.md`, `docs/PHASE_6_ADVOCACY_FITMENT.md`, and `docs/PHASE_7_TRUSTVISION.md`, and `docs/PHASE_8_RAG_COPILOT.md`, and `docs/PHASE_9_LANGGRAPH_AGENTS.md`, and `docs/PHASE_10_GEOSPATIAL_INTELLIGENCE.md`, and `docs/PHASE_11_TRAINING_ACADEMY_AR.md`, and `docs/PHASE_12_SECURITY_PRIVACY.md`, and `docs/PHASE_13_CLOUD_INTEGRATIONS.md`.


## Phase 14 — Business Intelligence

Admin-only executive, advocacy, operational analytics and CSV export are available under `/api/v1/admin/analytics`. See `docs/PHASE_14_BUSINESS_INTELLIGENCE_ROI.md` for KPI definitions and known gaps. ROI remains explicitly `not_configured` until approved monetary inputs are supplied.


## Phase 15 — End-to-End Validation

The backend integration suite now includes application health/readiness, OpenAPI route registration, administrator analytics access, RBAC rejection, date-range validation, and CSV export checks. See `docs/PHASE_15_END_TO_END_VALIDATION.md`. The full backend test suite currently passes with 41 tests in the local SQLite test configuration. The frontend remains a demo UI pending authenticated API integration.


## Phase 16 — Frontend Integration and Deployment Foundation

The React client now has OTP sign-in, OTP-verified mechanic onboarding, server-derived roles, session expiry handling, sign-out, and live Reports & ROI analytics with CSV export. A Twilio SMS adapter is available for production OTP delivery and fails closed when delivery is not configured. A frontend Docker image and Nginx reverse proxy are included in Docker Compose. See `docs/PHASE_16_FRONTEND_DEPLOYMENT.md`.

The backend test suite passes 45 tests in the local SQLite test configuration. Frontend npm build, Docker image build, live Twilio delivery and deployment remain unverified in this environment. The remaining transactional frontend pages still include demo data and require API integration.


## Phase 17 — Complete Frontend Integration

Primary authenticated workspaces are connected to the backend: Passport, Tool Bank, Rewards, Advocacy, Product Catalogue, Academy, Territory, TrustVision, Copilot, personal dashboard and the administrator analytics overview. The mechanic directory now reads live records and administrators can verify pending profiles. See `docs/PHASE_17_FRONTEND_INTEGRATION.md`.

Validation: 48 backend tests pass; all 8 frontend TS/TSX files pass syntax transpilation. Full frontend typecheck/build, browser E2E and Docker deployment remain unverified. Several advanced workflows still need dedicated polished screens.


## Phase 18 — End-to-End Workflow Hardening

Completed deeper workflows for Academy course authoring, enrolment, lesson completion, quizzes and certificates; TrustVision evidence detail and OCR corrections; advocacy campaigns; Tool Bank product stock and fulfilment; and reward redemption review. Added API route contract coverage and a complete Academy journey regression test.

Validation: 50 backend tests pass; 8 frontend TS/TSX files pass syntax transpilation; stub-assisted TypeScript check passes. Full npm build, browser E2E and Docker runtime remain unverified. See `docs/PHASE_18_END_TO_END_WORKFLOWS.md`.

## Phase 19 — Production Readiness Foundation

- API container runs as non-root UID 10001; TrustVision evidence storage uses a persistent writable volume.
- API readiness checks PostgreSQL and, in production, Redis. Compose waits for API health before starting the web container.
- API, PostgreSQL, Redis and MinIO are no longer published directly on host ports; the web gateway is the public entry point. MinIO console access should use a secure administrative tunnel.
- Added `.env.example`, `scripts/production-preflight.sh`, `scripts/backup.sh`, `scripts/restore.sh` and `scripts/smoke-test.py`.
- Added GitHub Actions CI for backend tests, frontend build and Compose configuration validation.

Before deployment: copy `.env.example` to `.env`, replace all placeholders with unique random values, use HTTPS at the public ingress, and run `bash scripts/production-preflight.sh`. Use URL-safe hexadecimal secrets for database/Redis/MinIO passwords because the Compose connection strings interpolate them directly. Backups must be copied off-host and encrypted by the operator.

Phase 19 does not claim a live deployment. The current TrustVision evidence route still stores files on its persistent local volume; the MinIO bucket is provisioned but is not yet the TrustVision storage adapter. SMS credentials, TLS ingress, provider verification, restore drills and Docker image execution require environment-specific validation.

### Phase 19 validation snapshot

Backend tests: 51 passed. Python compilation, eight-file frontend syntax transpilation, stub-assisted TypeScript checking, Compose YAML parsing, CI workflow YAML parsing and shell-script syntax checks passed. The production-preflight script was tested with both valid and invalid fixtures. Docker Engine is unavailable and frontend dependency installation did not complete here, so Docker builds, actual Compose validation, strict `npm run build`, live smoke tests and restore drills have not been run.


## Phase 20 — Staging Deployment and Integration Validation
Phase 20 adds a staging Compose override and deployment/status/stop scripts, CI container image builds, and completes the TrustVision object-storage integration. Evidence uploads and admin evidence-file retrieval now use the configured local or S3-compatible adapter; staging selects the private MinIO bucket. Object keys are stored logically so the configured prefix is applied exactly once. Storage round-trip, traversal and S3 contract tests are included.

See `docs/PHASE_20_STAGING_INTEGRATION.md` for staging setup. A live deployment, public TLS validation, real Twilio delivery, backup/restore drill and security/load testing still require an appropriately configured staging host.


## Phase 21 — Observability, Security Audit and Disaster Recovery
Phase 21 adds structured JSON request logs, a bearer-protected Prometheus metrics endpoint, optional Prometheus monitoring and alert rules, Docker log rotation, CodeQL and Dependabot configuration, and age-encrypted PostgreSQL plus MinIO backup/restore scripts. See `docs/PHASE_21_OBSERVABILITY_SECURITY_RECOVERY.md`. A real restore rehearsal, alert notification test, CodeQL hosted scan and security/load assessment remain operator tasks.


## Phase 22 — Real Provider Integrations and Production Pilot Foundation
Phase 22 extracts Twilio SMS delivery into a provider adapter, adds a no-send credential check and an explicitly confirmed chargeable test-SMS command, provisions a bucket-scoped MinIO application identity, removes MinIO root credentials from the API, and adds S3 readiness validation. See `docs/PHASE_22_PROVIDER_INTEGRATIONS_PILOT.md`. Live provider verification and the pilot go/no-go checklist must be completed in the target staging environment.


## Phase 23 — Staging Pilot Verification Gate
Adds a fail-closed staging verifier for gateway health, API security headers and PostgreSQL/Redis/object-storage readiness; integrates it into the staging deploy script; and adds an explicitly confirmed OTP/login check for an existing pilot account. See `docs/PHASE_23_STAGING_PILOT_VERIFICATION.md`. Live staging and provider checks remain operator-run.


## Phase 24 — Controlled Pilot Operations and Acceptance
Adds a read-only role-aware acceptance runner for mechanic/admin API surfaces, an explicit mechanic-to-admin authorization probe, pilot operations protocol, daily aggregate operations log and incident report template. See `docs/PHASE_24_CONTROLLED_PILOT_OPERATIONS.md` and `pilot/CONTROLLED_PILOT_PROTOCOL.md`. No live pilot was executed.


## Phase 25 — Privacy lifecycle and account deletion
Adds a user-requested, admin-reviewed and separately confirmed account deactivation/redaction workflow; explicit opt-in retention controls for OTP, security audit and user activity data; a dry-run-first maintenance script; and a Privacy & data workspace. Retention remains disabled by default until the data owner approves exact windows. Retention windows default to disabled pending approval by the data owner. See `docs/PHASE_25_PRIVACY_DATA_LIFECYCLE.md`.

## Phase 26 — Staging release and pilot launch gate
Deployment now requires `bash scripts/staging-deploy.sh --deploy`, checks Docker and production secrets before changing services, waits for readiness, and verifies database/Redis/object storage and security headers. The smoke test covers the same infrastructure gate. See `docs/PHASE_26_STAGING_RELEASE_AND_PILOT_LAUNCH.md` for deployment, rollback and pilot go/no-go procedures. No live staging deployment or participant pilot is claimed.

## Phase 27 — Controlled pilot launch controller
Added `scripts/pilot-launch-gate.py` to combine HTTPS staging/dependency checks, read-only mechanic/admin API acceptance and recorded human/provider evidence into a fail-closed GO/NO_GO report. Added `pilot/templates/launch-approval.example.json` and the runbook in `docs/PHASE_27_PILOT_LAUNCH_CONTROL.md`. The controller is read-only; no live staging deployment or real participant pilot is claimed.

## Phase 28 — Pilot workflow rehearsal
Added a synthetic mechanic/admin/dealer end-to-end Tool Bank, Rewards and Advocacy workflow test, including human approval boundaries and ledger/stock invariants. Added `scripts/pilot-workflow-rehearsal.py` to run the full backend regression suite against a disposable SQLite database and emit a sanitized JUnit-derived JSON report. Provider calls are mocked; no live pilot or real SMS is claimed. See `docs/PHASE_28_LIVE_PILOT_WORKFLOW_REHEARSAL.md`.


## Phase 29 — Real staging integration verifier

Phase 29 adds `scripts/staging-integration.py` for fail-closed staging checks. Its default mode is read-only and verifies gateway health, API liveness/security headers, database/Redis/object-storage readiness, and optionally the presence/strength of required staging environment settings. Optional Twilio account verification is read-only and never sends an SMS. An S3/MinIO disposable-object round-trip requires both `--storage-roundtrip` and `--confirm-storage-write` plus a dedicated unique `staging-verification/` prefix. Reports are sanitized JSON.

See `docs/PHASE_29_REAL_STAGING_INTEGRATION.md`. No live staging environment or provider credentials were available during this phase; no live provider integration is claimed.


## Phase 30 — Production deployment and controlled pilot readiness

Added `scripts/production-readiness.py`, a static fail-closed preflight for production secrets/configuration, HTTPS CORS, Twilio sender formats, MinIO identity separation, compose invariants, storage policy, migrations and backup/restore assets. It never deploys or contacts providers. CI now includes a PostgreSQL 16 migration-and-backend-test job alongside the SQLite suite. See `docs/PHASE_30_PRODUCTION_DEPLOYMENT_AND_PILOT_READINESS.md`. A static `READY_FOR_OPERATOR_REVIEW` is not a pilot GO decision.
