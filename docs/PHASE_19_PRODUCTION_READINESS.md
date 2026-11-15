# Phase 19 — Production Readiness Foundation

## Delivered

### Runtime and container hardening
- API container runs as UID/GID 10001 rather than root.
- TrustVision evidence directory is created with correct ownership and mounted as a persistent volume.
- API and MinIO console are not directly published on host ports in the production Compose file. The web gateway is the public service.
- Compose waits for API health before starting the web gateway.
- API health check verifies database connectivity and Redis connectivity in production.
- API server trusts forwarded headers because it is only exposed on the Compose network behind the Nginx gateway.

### Operations
- `.env.example` documents all mandatory production variables.
- `scripts/production-preflight.sh` rejects placeholders, weak secrets, wildcard/non-HTTPS CORS origins and non-Twilio production SMS configuration.
- `scripts/backup.sh` exports a PostgreSQL custom-format dump and TrustVision evidence archive with SHA-256 checksums.
- `scripts/restore.sh` requires an explicit `RESTORE` confirmation before overwriting data.
- `scripts/smoke-test.py` checks web, API liveness and API readiness endpoints.

### CI
- GitHub Actions workflow runs backend compilation and pytest.
- CI installs frontend dependencies and runs the real strict Vite/TypeScript production build.
- CI validates the Docker Compose configuration.

## Validation performed in this workspace
- Backend compile and test suite are run as part of this phase.
- Frontend source syntax and stub-assisted typing are checked locally.
- Compose YAML is parsed locally.
- Docker Engine, npm dependency installation and live service providers are not available/verified here; CI is configured to run the actual frontend build on GitHub-hosted runners.

## Deployment procedure
1. Copy `.env.example` to `.env` and replace every placeholder.
2. Generate unique URL-safe secrets. Example: `openssl rand -hex 32`.
3. Run `bash scripts/production-preflight.sh`.
4. Put the web service behind a TLS-enabled reverse proxy/load balancer. Do not expose API, PostgreSQL, Redis or MinIO directly.
5. Run `docker compose config --quiet` and inspect the rendered configuration for secret leakage.
6. Run `docker compose up -d --build`.
7. Run `python scripts/smoke-test.py --web https://your-domain --api https://your-domain` (both endpoints may share the web gateway; `/health/live` and `/health/ready` are proxied by Nginx).
8. Test a real OTP send/verify using an approved test number, then test mechanic onboarding and one administrator review flow.
9. Run a backup and a restore drill in a separate staging environment before accepting production data.

## Explicit limitations / release gates
- This is a production-readiness foundation, not a claim of production deployment or certification.
- The TrustVision API currently writes evidence to its local persistent volume. MinIO is provisioned but not yet wired as the TrustVision storage adapter.
- Twilio credentials and sender registration must be verified live.
- HTTPS/TLS is expected at the external ingress and is not terminated by the included Nginx container.
- Backups are not encrypted by these scripts. Operators must encrypt and copy them off-host, define retention, and test restores.
- Restore commands should be rehearsed on a disposable staging stack; they intentionally overwrite existing data.
- No external penetration test, vulnerability assessment, load test or disaster-recovery sign-off has been performed.
- Compose's use of URL-safe secret strings is required because the current connection URLs interpolate credentials directly.
