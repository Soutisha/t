# Phase 23 — Staging Pilot Verification Gate

## Objective
Turn the Phase 22 staging checklist into repeatable, fail-closed checks. This phase prepares the pilot operator to validate the deployed gateway, API security headers, dependency readiness and an existing pilot account's real OTP login.

## Delivered

### 1. Staging infrastructure verifier
- Added `scripts/staging-verify.py` and `scripts/staging-verify.sh`.
- Checks web gateway `/healthz`.
- Checks API `/health/live`, JSON status, request ID and required security headers.
- Checks `/health/ready` and requires PostgreSQL, Redis and object storage to report `connected`.
- Requires HTTPS for non-local hostnames. HTTP is allowed only for localhost or when an operator explicitly passes `--allow-http` on an isolated network.
- Optional `--api` permits a private API address when it is not routed through the web gateway.
- No credentials, records or business data are modified.

### 2. Deployment gate integration
- `scripts/staging-deploy.sh` now invokes the stronger verifier after Compose reports healthy services.
- A deployment is not reported as passing when object storage is unavailable or the API security headers are missing.
- External HTTPS must still be checked separately using the public staging hostname.

### 3. Real pilot OTP/login check
- Added `scripts/pilot-auth-check.py` for an already-provisioned pilot account.
- Requires `--send-otp` and `--confirm-send` before requesting an OTP because SMS may incur charges.
- Prompts for the received OTP with hidden input.
- Verifies OTP, obtains a short-lived access token in process memory, and confirms `/api/v1/me` returns the same pilot phone number.
- Does not print or save the token, and does not create a user or register a mechanic.

### 4. Automated coverage
- Added mocked tests for successful staging readiness, unavailable object storage, HTTPS enforcement and localhost HTTP testing.
- Existing OTP onboarding, Academy, TrustVision upload and admin role tests remain part of the backend suite.
- Version bumped to `0.23.0`.

## Operator runbook

### A. Deploy
```bash
cp .env.staging.example .env.staging
# Edit .env.staging and supply real, unique secrets and provider credentials.
ENV_FILE=.env.staging ./scripts/staging-deploy.sh
```

### B. Verify the public staging gateway
```bash
./scripts/staging-verify.sh --web https://staging.your-domain.example
```

If the API is only reachable on a private network, run the verifier from an operator host that can reach both:
```bash
./scripts/staging-verify.sh \
  --web https://staging.your-domain.example \
  --api http://10.0.0.10:8000
```
The private API URL should only be used from a trusted operator network. Do not publish the API, database, Redis or MinIO ports to the internet.

### C. Verify a pre-provisioned pilot account
```bash
./scripts/pilot-auth-check.py \
  --base-url https://staging.your-domain.example \
  --phone +91XXXXXXXXXX \
  --send-otp \
  --confirm-send
```
Have the pilot device owner available to read the SMS. This sends one real OTP request. Use a dedicated test account and an approved test phone; do not use a customer or mechanic's personal account without consent.

### D. Complete manual acceptance
After the infrastructure and OTP checks pass, the pilot operator must still verify:
- Mechanic profile and shop details are correct.
- Admin profile review and approval work, and a mechanic cannot access admin-only routes.
- TrustVision evidence can be uploaded, reviewed by an authorized role and retrieved.
- Academy lesson completion, quiz and certificate work for a pilot mechanic.
- Consent settings and privacy notice match the pilot's approved data use.
- Backup is encrypted, stored off-host and restored in an isolated environment.
- External TLS, DNS, firewall, alerts, logging retention and incident response are verified.

## Validation boundaries
- Automated tests use mocked HTTP and local test databases. They do not contact Twilio, MinIO or a real staging deployment.
- No live staging hostname, provider credentials or pilot account were supplied to this workspace.
- A passing infrastructure verifier is not a penetration test, accessibility audit, load test, disaster recovery certification or business acceptance sign-off.
- Do not start a customer-facing pilot until the manual acceptance items are signed by the named operational owner.
