# Phase 29 — Real Staging Integration

## Purpose

Phase 29 adds an operator-driven integration verifier for a deployed staging environment. It deliberately separates read-only checks from provider operations that can write data or incur charges.

## Run a safe verification

From the repository root:

```bash
python3 scripts/staging-integration.py \
  --web https://staging.example.org \
  --api https://staging.example.org \
  --env-file .env.staging \
  --report pilot/reports/staging-integration.json
```

The default run checks the gateway `/healthz`, API `/health/live` plus security headers, API `/health/ready` including database/Redis/object-storage status, and static environment configuration. It does not authenticate to Twilio, send SMS, write to object storage, or change application data.

The environment file is parsed as plain key/value text and is never sourced or executed. Reports omit configuration values and apply redaction to provider identifiers, credentials and phone-number-like strings. Protect report files as operational records even though they are sanitized.

## Explicit provider checks

Twilio account validation is read-only and must be explicitly enabled:

```bash
set -a
. ./.env.staging
set +a
python3 scripts/staging-integration.py \
  --web https://staging.example.org \
  --check-twilio
```

This makes an authenticated account API request. It does not send an SMS. For an actual SMS delivery test, continue to use the separate `scripts/twilio-verify.py` flow, which requires `--send-test-sms --to ... --confirm-send`.

An S3/MinIO round-trip writes, reads and deletes one disposable object. It requires both an explicit opt-in and a dedicated unique prefix:

```bash
set -a
. ./.env.staging
set +a
python3 scripts/staging-integration.py \
  --web https://staging.example.org \
  --storage-roundtrip \
  --confirm-storage-write \
  --storage-test-prefix staging-verification/operator-unique-run-20261115
```

Use only a prefix reserved for staging verification. The configured S3 credentials must be the application identity, not MinIO root credentials. The verifier attempts cleanup in a `finally` block; if cleanup fails, inspect the reported prefix and remove the probe object through an approved operator procedure.

## Report semantics

Each check is `passed`, `failed`, or `skipped`. A skipped provider test is not a pass. Overall status is failed if any executed check fails. The JSON report contains a timestamp, aggregate counts, sanitized check details and an explicit side-effect summary.

## Operational limitations

- `/health/ready` proves the API can reach its configured database, Redis and object storage. It does not prove that the database schema is at the latest Alembic revision.
- The environment-file check validates required keys and placeholder/length/origin rules; it does not prove credentials are valid.
- Twilio verification checks account authentication and active status only. It does not prove sender registration, destination reachability or real OTP delivery.
- S3 round-trip proves the supplied identity can perform the tested bucket/object operations for one key. It does not independently prove the complete policy is least-privilege.
- The verifier does not perform load, penetration, backup restoration, participant-consent or full product acceptance testing.
- The current execution environment has no Docker Engine and no supplied staging hostname or production credentials. Therefore Phase 29 implementation is locally tested; no live PostgreSQL, Redis, MinIO, Twilio or HTTPS staging integration is claimed.

## Recommended CI database integration

The repository's current CI job runs the complete backend suite against SQLite. For a production deployment, add a PostgreSQL service-container job that applies Alembic migrations to an empty database and runs the backend suite against that service. This phase does not claim that such a PostgreSQL CI job has been executed in this environment.
