# Phase 21 — Observability, Security Audit and Disaster Recovery

## Delivered

### Application observability
- Structured JSON request logs are emitted to stdout with UTC timestamp, level, request ID, method, normalized route, status and duration.
- Unhandled exceptions are logged with request ID and stack trace; client responses remain generic.
- `/internal/metrics` exposes Prometheus request counters and cumulative latency histograms.
- Production metrics access requires a bearer token of at least 32 characters. The endpoint is not proxied by the public Nginx configuration.
- Added bounded Docker local log rotation for core services.

### Monitoring and alert rules
- Added optional Prometheus service under the `monitoring` Compose profile.
- Added alerts for API target unavailability, 5xx ratio above 5%, and p95 latency above 1.5 seconds.
- Create the Prometheus scrape secret using `scripts/monitoring-setup.sh`, then start with `docker compose --profile monitoring up -d`.
- Prometheus is not published to the host by default. Use a private tunnel or internal network access to inspect it.
- Configure Alertmanager or your external monitoring provider for notification delivery; the included Prometheus rules evaluate conditions but do not send notifications on their own.

### Security and supply-chain checks
- Added scheduled GitHub CodeQL analysis for Python and JavaScript/TypeScript.
- Added weekly Dependabot updates for pip, npm and GitHub Actions.
- Production preflight now requires a long random metrics bearer token.
- Metrics credentials are mounted read-only into Prometheus and ignored by Git.

### Encrypted backup and recovery
- `scripts/backup.sh` now exports the PostgreSQL database and private MinIO evidence bucket, bundles them, encrypts the archive with age, and writes a SHA-256 checksum.
- `scripts/backup-verify.sh` decrypts and checks bundle members, object archive readability and PostgreSQL dump readability when `pg_restore` is installed.
- `scripts/restore.sh` decrypts the archive, requires the operator to type `RESTORE`, restores PostgreSQL and replaces the private evidence bucket.
- `scripts/monitoring-setup.sh` provisions the Prometheus bearer-token file from `.env`.

## Operator setup

### Monitoring
1. Set `METRICS_TOKEN` in `.env` to a unique random value of at least 32 characters.
2. Run `./scripts/monitoring-setup.sh`.
3. Start optional monitoring: `docker compose --profile monitoring up -d`.
4. Configure Alertmanager or an external alert receiver, retention and dashboarding.
5. Scrape `/internal/metrics` only from the private Compose network.

### Encrypted backups
1. Install `age` on the host.
2. Generate an age identity and recipient with `age-keygen`; store the private identity outside the application host.
3. Set `AGE_RECIPIENT` to the public recipient in the backup job environment.
4. Run `./scripts/backup.sh /secure/backup-directory`.
5. Verify using `AGE_IDENTITY_FILE=/secure/age-identity.txt ./scripts/backup-verify.sh /secure/backup-directory/backup.tar.gz.age`.
6. Copy encrypted backups and checksums to off-host/object-lock storage with access controls and retention.
7. For recovery, run `AGE_IDENTITY_FILE=/secure/age-identity.txt ./scripts/restore.sh /secure/backup-directory/backup.tar.gz.age` and type `RESTORE` only after confirming the target environment.

## Important limitations and operational controls
- Request metrics are in-memory and process-local. For multiple API workers/replicas, use a Prometheus multiprocess strategy or an external metrics backend before scaling horizontally.
- Prometheus rules need Alertmanager or another receiver to generate notifications.
- CodeQL analysis is configured but its hosted scan has not been executed from this workspace.
- Encrypted backups require an operator-managed age recipient/identity and off-host retention destination.
- The backup script depends on Docker Compose, PostgreSQL client tools in the Postgres service, and the `mc` utility image. The restore is destructive and must be rehearsed against an isolated recovery stack.
- No real restore drill, penetration test, external vulnerability scan, alert delivery test or production load test has been run here.
- S3 server-side encryption is configurable. Do not set `S3_SERVER_SIDE_ENCRYPTION=AES256` for MinIO unless its KMS/SSE configuration supports it; configure bucket/volume encryption independently.


## Phase 22 readiness extension
Production `/health/ready` now also checks access to the configured S3 bucket using the application identity. A healthy database and Redis are not sufficient for readiness when evidence storage is unavailable.
