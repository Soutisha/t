# Phase 30 — Production Deployment Validation and Controlled Pilot Readiness

## Objective

Phase 30 adds a static deployment preflight and a PostgreSQL-backed CI job. It strengthens the path from a code-complete pilot foundation to an operator-reviewed deployment. It does not deploy infrastructure or authorize a participant pilot.

## 1. Prepare production configuration

1. Copy `.env.example` to a secret-managed `.env` on the deployment host. Do not commit it.
2. Generate independent random secrets for PostgreSQL, Redis, MinIO root, MinIO app, JWT, client fingerprint and metrics access.
3. Keep MinIO root credentials limited to bootstrap/administration. The API must use the dedicated `MINIO_APP_USER` and `MINIO_APP_PASSWORD`.
4. Configure explicit HTTPS `CORS_ORIGINS`, Twilio Account SID/token and a registered E.164 sender.
5. Keep `OTP_DEV_RETURN_CODE=false` in production. Do not enable development OTP for a pilot.
6. Confirm DNS, TLS termination, firewall rules, private database/Redis/MinIO ports, off-host encrypted backup destination and monitoring alert receivers.

## 2. Run static preflight

```bash
python3 scripts/production-readiness.py \
  --env-file .env \
  --report /secure/operator-records/production-preflight.json \
  --check-compose
```

The command checks required configuration, secret lengths, HTTPS CORS, Twilio identifier formats, distinct MinIO identities, compose security invariants, scoped MinIO policy presence, migration assets and backup/restore procedures. It never prints secret values.

A `READY_FOR_OPERATOR_REVIEW` decision means these static checks passed. It is not a deployment authorization, live connectivity check, security certification or pilot GO decision.

## 3. Deploy using reviewed operations

Use the approved deployment change window and a known release artifact. Review the compose configuration before applying it. Back up the current database and evidence bucket using `scripts/backup.sh`, verify the encrypted artifact with `scripts/backup-verify.sh`, and store it off-host. Apply Alembic migrations as a controlled release step before routing traffic to the new API version. Do not use development `create_all` in production.

After deployment, run:
- `scripts/staging-integration.py` for gateway/API/dependency checks.
- `scripts/pilot-acceptance.py` with short-lived mechanic and administrator test tokens.
- `scripts/pilot-launch-gate.py` with the fully reviewed, restricted approval record.

Each runner has a different scope. Do not treat one passing runner as a substitute for the others.

## 4. Rollback and recovery

Before a release, record the deployed image digests, current Alembic revision, release identifier and operator decision. Define a rollback owner and stop authority. If a release causes data corruption or an unacceptable security/privacy issue:
1. Stop pilot onboarding and new workflow execution; preserve evidence and logs.
2. Remove public traffic or scale down API/web using the deployment operator's approved procedure.
3. Assess whether the release is code-only and compatible with the current schema. Roll back images only when schema compatibility is confirmed.
4. For a database restore, use the encrypted backup and `scripts/restore.sh`. This operation overwrites the database and evidence bucket and requires the interactive `RESTORE` confirmation.
5. Re-run readiness, mechanic/admin acceptance, evidence retrieval and critical workflow smoke tests before reopening traffic.
6. Record incident timeline, data-loss window, recovery actions and accountable approval.

Do not assume Alembic downgrades are safe for every release. Prefer a forward fix unless a tested rollback procedure explicitly covers the schema change.

## 5. PostgreSQL CI

The CI workflow now retains the fast SQLite job and adds a PostgreSQL 16 service job. The PostgreSQL job installs backend dependencies, applies Alembic migrations to a fresh database, reports the current revision and runs the backend test suite against PostgreSQL.

The PostgreSQL job is configured in GitHub Actions but was not executed in this local environment. A successful local SQLite migration does not prove the hosted PostgreSQL job has passed.

## 6. Final pilot launch conditions

The business pilot owner must still confirm geography, cohort, dates, feature scope, participant consent, privacy notice, retention/deletion procedure, escalation contacts, field support, real OTP delivery, backup restore evidence, monitoring alert delivery and a rehearsed stop/rollback. The existing Phase 27 approval template remains the formal evidence checklist.

## Phase 30 safety boundary

- No deployment, DNS/TLS changes, database writes, SMS, participant contact or provider mutation is performed by the static preflight.
- `READY_FOR_OPERATOR_REVIEW` is deliberately not named `GO`.
- Real staging integration and the Phase 27 GO/NO_GO gate remain required.
- PostgreSQL CI is added as configuration; it must run in GitHub Actions before its result can be claimed.
- Docker Engine and production credentials were not supplied in this environment.
