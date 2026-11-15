# Implementation Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Greenfield repository and requirements audit | Completed |
| 1 | System architecture and technical contracts | Completed |
| 2 | UI/UX and design system | Implemented — frontend source exists; npm build not verified in this runtime |
| 3 | Authentication and onboarding | Implemented — API and automated tests pass; production SMS provider remains unconfigured |
| 4 | Mechanic Passport | Implemented — API, models and automated tests pass; QR/public-profile production validation remains |
| 5 | Smart Tool Bank and rewards | Implemented — API, models and automated tests pass; inventory/payment operations require real data/providers |
| 6 | Advocacy and Verified Fitment Engine | Implemented — API, models and automated tests pass; real catalogue and dealer data remain external dependencies |
| 7 | TrustVision computer vision and fraud review | Implemented — upload, QR/OCR adapters, duplicate checks, risk cases and review APIs; production malware scanning and security validation remain |
| 8 | RAG AI Copilot | Implemented — governed ingestion, approval-gated retrieval, citations, abstention and optional LLM adapter; quality benchmarking remains |
| 9 | LangGraph specialised agents | Implemented — specialist routing, grounded read-only tools, action approval gates and audit traces; LangGraph runtime/provider validation remains |
| 10 | Geospatial intelligence | Implemented — consent-based location registration, nearby search, privacy-rounded discovery and territory polygon lookup; PostGIS/routing integration remains |
| 11 | Training Academy and optional AR | Implemented — course authoring, enrolment, lesson progress, graded quizzes and certificates; production training content and device-tested WebXR remain |
| 12 | Cybersecurity and privacy hardening | Implemented — JWT hardening, OTP verification gates, consent APIs, audit events and security middleware; independent penetration testing remains |
| 13 | Cloud and enterprise integrations | Implemented — Docker Compose, Alembic baseline, Redis rate limiting, object-storage adapter and integration/outbox framework; live cloud/ERP providers remain unconnected |
| 14 | Business intelligence and ROI | Implemented — admin analytics, date filters, advocacy metrics, operations metrics and CSV export; financial ROI remains not configured |
| 15 | End-to-end testing and demonstration | Implemented — backend integration tests and role workflows validated; browser E2E and external-provider tests remain |
| 16 | Frontend integration and deployment foundation | Implemented — OTP frontend, mechanic registration, live analytics, Twilio adapter, frontend container and Nginx reverse proxy; npm/Docker/provider runtime validation remains |
| 17 | Complete frontend integration | Implemented foundation — primary authenticated workspaces now call live APIs; 48 backend tests pass and frontend syntax transpiles. Dedicated advanced forms, full typecheck/build and browser E2E remain |
| 18 | End-to-end workflow hardening | Implemented — Academy learning/quiz/certificate journey, TrustVision evidence/OCR review, campaign participation, Tool Bank stock/fulfilment and reward approvals; 50 backend tests pass. Full npm build/browser E2E remain |
| 19 | Production readiness foundation | Implemented foundation — non-root API container, dependency-aware readiness, private internal services, environment preflight, backup/restore scripts, deployment smoke test and CI workflow. Live Docker deployment, provider checks and restore drill remain |

## Execution gate

Each phase must produce implementation artifacts, tests, documentation and a phase report. A phase is not complete merely because code was generated. Do not advance past a failed critical gate.

## Current release gate

The backend test suite currently passes in the local SQLite test configuration (51 tests after Phase 19). This is not equivalent to production readiness. Before a real deployment, complete the strict frontend build, staging deployment, provider credentials and contract tests, backup/restore drills, load tests, security scanning, penetration testing, monitoring/alerting, and operational sign-off.


## Phase 20 completed — Staging deployment and integration validation
Staging Compose override, deployment scripts, CI container builds, and TrustVision S3-compatible evidence storage integration are implemented. Local/fake-S3 contract tests cover storage behavior. A live staging deployment and external provider verification remain environment-dependent.


## Phase 21 completed — Observability, security audit and disaster recovery
Structured JSON logs, protected Prometheus metrics, optional monitoring and alert rules, CodeQL/Dependabot configuration, log rotation, and age-encrypted PostgreSQL/MinIO backup verification and restore workflows are implemented. Live monitoring, notifications and a real isolated restore drill remain unverified.


## Phase 22 completed — Real provider integrations and production pilot foundation
Twilio provider adapter and credential verification CLI, bucket-scoped MinIO service identity, non-root API storage credentials, S3 readiness check, and pilot go/no-go checklist implemented. Live SMS/cloud verification remains environment-dependent.


## Phase 23 completed — Staging pilot verification gate
Added staging gateway/API/dependency verification, HTTPS enforcement for public staging hostnames, deployment gate integration and an opt-in real OTP/login check for an existing pilot account. Automated tests are mocked; no live staging environment was supplied.


## Phase 24 completed — Controlled pilot operations and acceptance
Added a read-only mechanic/admin acceptance runner, role-boundary probe, controlled pilot protocol, daily aggregate operations log and incident report template. Live deployment, participant testing, privacy approval and operational sign-off remain external gates.


## Phase 25 completed — Privacy lifecycle and account deletion
Added user deletion requests, administrator approval/execution, direct-profile redaction, saved-location and user-submitted TrustVision evidence removal, consent withdrawal, configurable dry-run-first retention controls for OTP, security audit and user activity logs, Alembic migration and frontend Privacy & data workspace. Universal erasure is not claimed; retained historical records and legal holds require policy review.

## Phase 26 completed — staging release and pilot launch gate
Hardened the staging deploy command with an explicit `--deploy` confirmation, Docker daemon and production-preflight checks, bounded health/readiness waits, and a full post-deploy verifier. Expanded the smoke test to validate security headers and database/Redis/object-storage readiness. Added a staging runbook, rollback guidance and human pilot go/no-go checklist. No live host/provider/participant environment was supplied, so deployment and real-world pilot sign-off remain external gates.

## Phase 27 completed — controlled pilot launch controller
Added a read-only launch gate combining staging infrastructure verification, mechanic/admin API acceptance and recorded human/provider approval evidence. Added a structured approval template and runbook. The tool fails closed when evidence, role assignments, scope, HTTPS or test tokens are missing. Local validation: 82 backend tests pass, Python compilation and YAML parsing pass, CLI rejects HTTP and the example approval remains fail-closed. Live staging and participant execution remain external because no host, credentials or approved cohort were supplied.

## Phase 28 completed — synthetic pilot workflow rehearsal
Added a complete synthetic Tool Bank request/approval/fulfilment, rewards credit/redemption approval and advocacy recommendation/fitment review journey with role-boundary and inventory/ledger invariants. Added a repeatable isolated-SQLite rehearsal runner that produces sanitized JSON evidence. Real SMS, live cloud storage, staging host and participant execution remain external gates.


## Phase 29 — Real Staging Integration

- [x] Add read-only staging gateway/API/dependency integration verifier.
- [x] Add environment configuration validation without executing env files.
- [x] Add opt-in read-only Twilio account check; no SMS send.
- [x] Add explicit-confirmation S3/MinIO disposable-prefix round-trip.
- [x] Add sanitized machine-readable report and fail-closed tests.
- [ ] Execute against a real HTTPS staging deployment and real provider credentials.


## Phase 30 — Production Deployment Validation and Controlled Pilot Readiness

- [x] Add static production configuration/security preflight with sanitized JSON report.
- [x] Validate explicit HTTPS CORS, secret strength, Twilio formats and MinIO identity separation.
- [x] Validate compose deployment invariants, scoped policy, migrations and backup/restore assets.
- [x] Add PostgreSQL 16 migration and backend suite CI job alongside SQLite.
- [x] Document deployment, rollback, recovery and final pilot launch conditions.
- [ ] Execute hosted PostgreSQL CI job and real staging/pilot launch gate.
