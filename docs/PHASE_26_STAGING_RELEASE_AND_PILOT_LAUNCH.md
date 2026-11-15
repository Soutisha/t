# Phase 26 — Staging Release, Live Integration and Pilot Launch Gate

## Objective

Turn the existing staging foundation into a controlled, repeatable release process. This phase strengthens deployment safety and makes the difference between automated infrastructure checks and real-world pilot acceptance explicit.

## Implemented

- `scripts/staging-deploy.sh` now requires the explicit `--deploy` confirmation before it can build or start services.
- Deployment refuses to proceed when the environment file is absent, Docker Engine is unavailable, or the production preflight fails.
- The deployment waits up to five minutes for gateway/API health and dependency readiness, then runs the HTTPS/security-header/DB/Redis/object-storage verifier.
- `scripts/smoke-test.py` now validates gateway health, API liveness, request/security headers, and full dependency readiness rather than only checking HTTP status.
- Existing `scripts/pilot-acceptance.py` remains the authenticated, read-only role-aware acceptance runner. It exercises mechanic and administrator read paths and verifies that a mechanic receives HTTP 403 from an administrator-only endpoint.
- Existing `scripts/pilot-auth-check.py` remains a separate, explicitly confirmed real-SMS OTP journey. It requires `--send-otp --confirm-send`, prompts for the code without echoing it, and never prints or saves the access token.
- CI continues to run backend tests, frontend production build, Compose configuration validation and Docker image builds.

## Staging deployment

1. Provision an isolated staging host with Docker Engine and Docker Compose v2.
2. Copy `.env.staging.example` to `.env.staging`; use unique random URL-safe credentials and an explicit HTTPS `CORS_ORIGINS` value.
3. Keep `.env.staging` outside source control and restrict its file permissions (`chmod 600 .env.staging`).
4. Verify DNS/TLS at the external ingress. The built-in gateway port is not, by itself, a public TLS termination solution.
5. Run `bash scripts/production-preflight.sh .env.staging`.
6. Review the rendered Compose configuration and backup policy, then explicitly deploy with `ENV_FILE=.env.staging bash scripts/staging-deploy.sh --deploy`.
7. Run `python3 scripts/staging-verify.py --web https://staging.example.org`.
8. Run the authenticated acceptance suite with short-lived pilot tokens supplied only through environment variables:
   `PILOT_MECHANIC_TOKEN=... PILOT_ADMIN_TOKEN=... python3 scripts/pilot-acceptance.py --base-url https://staging.example.org --report pilot/reports/acceptance.json`.
9. Complete the OTP journey only with a designated test handset and explicit approval:
   `python3 scripts/pilot-auth-check.py --base-url https://staging.example.org --phone +E164_NUMBER --send-otp --confirm-send`.
10. Complete the human go/no-go checklist below before enrolling participants.

The API container runs Alembic migrations as part of its startup command. Confirm the API logs report successful migration completion and that `/health/ready` returns `ready` before opening the pilot.

## Rollback procedure

- Stop participant onboarding and record the incident/change ticket.
- Preserve logs and the latest encrypted database/object-store backups.
- Identify the last known-good immutable image tags from the release record. Do not rely on mutable `latest` tags.
- Update the deployment's image references to those exact prior tags, then run `docker compose ... up -d --no-build`.
- Verify `/health/live`, `/health/ready`, the role-aware acceptance suite and critical user journeys.
- Do not automatically downgrade the database. Alembic downgrades are not assumed safe for production data; restore a verified pre-release backup only under the approved recovery procedure.
- Record the rollback decision, data-loss window, verification evidence and follow-up actions.

## Pilot go/no-go checklist

### Infrastructure and security
- [ ] HTTPS certificate, DNS, ingress and security headers verified externally.
- [ ] `production-preflight.sh` passes against the actual staging secret file.
- [ ] API, PostgreSQL, Redis and MinIO report healthy; MinIO app identity is bucket/prefix scoped.
- [ ] Alembic current revision equals repository head.
- [ ] Metrics endpoint is protected and monitoring alerts have a tested receiver.
- [ ] Encrypted backup completed and isolated restore drill passed.
- [ ] Retention windows have written data-owner approval; defaults remain disabled otherwise.
- [ ] Privacy notice, consent wording, deletion limitations and incident contact approved.
- [ ] No secrets, real participant PII or production data in logs, reports, fixtures or demo seed data.

### Product and role acceptance
- [ ] Mechanic authentication/onboarding works with a real designated test handset.
- [ ] Mechanic can read their own Passport, Tool Bank, Rewards, Academy, Advocacy and TrustVision surfaces.
- [ ] Administrator review queues and analytics are available only to authorized roles.
- [ ] Mechanic-to-admin denial probe returns HTTP 403.
- [ ] Tool request/approval, reward review, course completion/certificate and TrustVision review are exercised with synthetic pilot records.
- [ ] Account deletion request, approval, execution safeguards and retention dry-run are reviewed by the data owner.
- [ ] Accessibility, mobile usability and participant support contact verified.

### Operational sign-off
- [ ] Named pilot owner, administrator, support contact and incident commander assigned.
- [ ] Participant consent and recruitment approved.
- [ ] Daily operations log and incident report process rehearsed.
- [ ] Pilot cohort size, dates, success metrics and stop conditions approved.
- [ ] Written go/no-go approval recorded by product, security, operations and data owners.

## Live provider and test boundaries

The automated suite intentionally does not send real SMS, create real participant accounts, redeem real rewards, issue financial transactions or delete real pilot data. These require separate operator approval and test accounts. The role-aware acceptance runner is read-only.

## Phase 26 validation record

Validation is recorded in the release handoff accompanying the cumulative ZIP. A successful local test suite or static check does not constitute a live staging deployment. No live staging host, Twilio credentials, MinIO service, pilot participants or production database are bundled with this repository.

## Local validation results

- Backend suite: **77 passed** using a fresh disposable SQLite database.
- Python compilation: passed for application, tests and migrations.
- Alembic: fresh SQLite database upgraded successfully through repository head (`phase25_privacy`).
- Shell syntax: deployment, verification, preflight, stop and status scripts passed `bash -n`.
- YAML parsing: base/staging Compose and CI/CodeQL workflow files parsed successfully.
- Deployment safety tests: no-argument deploy invocation exits before any Docker command; help is read-only; verifier rejects public HTTP and relative URLs.
- Docker Engine is not installed in this execution environment, so Docker Compose rendering, image builds, container health, PostgreSQL/Redis/MinIO integration and live deployment were not run.
- Frontend dependencies are not installed and no package install was completed; the strict Vite production build and browser tests were not run.
- No real Twilio SMS, participant login, production data mutation, account erasure or pilot participant activity was performed.
