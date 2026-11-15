# Phase 24 — Controlled Pilot Operations and Acceptance Toolkit

## Objective
Provide a repeatable, read-only operational acceptance pass for a deployed pilot using separate mechanic and administrator credentials, plus an operator protocol for running a small, controlled field pilot.

## Delivered

### 1. Role-aware acceptance runner
`scripts/pilot-acceptance.py` checks the existing read-only API surfaces for:
- Mechanic identity and consent records.
- Tool Bank catalog and mechanic request history.
- Rewards balance.
- Academy course catalogue, learning history and certificates.
- TrustVision mechanic evidence list.
- Advocacy products, events and campaigns.
- Administrator onboarding, TrustVision review, Tool Bank requests, rewards redemptions, Academy courses, advocacy review and operational analytics.
- A negative authorization test: the mechanic token must receive HTTP 403 from an administrator-only analytics route.

The runner does not create, update, approve, redeem, upload or delete business records. It requires HTTPS except for explicitly enabled localhost testing. Tokens are read from environment variables and are never included in console output or the JSON report.

### 2. Pilot operations records
- `pilot/templates/daily-operations-log.csv` provides a minimal daily count/issue log without requiring participant names or phone numbers.
- `pilot/templates/incident-report.md` provides a structured incident record and escalation checklist.
- `pilot/CONTROLLED_PILOT_PROTOCOL.md` defines entry gates, roles, daily checks, stop conditions, exit criteria and evidence to retain.

### 3. Safe rollback guidance
The protocol uses the existing staging down script and backup/restore procedures. Rollback is an operator-approved action; the acceptance script does not stop services, restore databases or mutate infrastructure.

## Runbook

### 1. Set pilot tokens in the operator shell
Do not paste tokens into chat, tickets or source control.

```bash
export PILOT_MECHANIC_TOKEN='...'
export PILOT_ADMIN_TOKEN='...'
```

### 2. Run the read-only acceptance suite

```bash
python3 scripts/pilot-acceptance.py \
  --base-url https://staging.your-domain.example \
  --report ./private-pilot-evidence/acceptance.json
```

For a localhost-only environment:

```bash
python3 scripts/pilot-acceptance.py \
  --base-url http://127.0.0.1:8080 \
  --allow-http-localhost
```

A passing result means the selected endpoints responded and the mechanic/admin boundary probe behaved as expected. It does not prove every workflow's business correctness or that records are populated.

### 3. Use separate accounts
- Use a dedicated pilot mechanic account and a dedicated administrator account.
- Do not share administrator credentials with mechanics, dealers or field representatives.
- Use test data unless the pilot owner has approved real participant data and the required consent/privacy notice.
- Remove access when a participant or operator leaves the pilot, following the organization's approved access procedure.

## Explicit pilot gates
A field pilot should not begin until the operational owner has recorded:
- Named business owner, technical owner, support contact and incident decision-maker.
- Approved pilot geography, participating shops, scope, start/end dates and participant count.
- Approved privacy notice, consent language, purpose limitation, data access rules and retention/deletion schedule.
- Twilio account and sender verification; MinIO application identity and bucket access verification.
- HTTPS, DNS, firewall, CORS, backups, restore rehearsal, alert routing and monitoring.
- Mechanic/admin acceptance suite passing on the deployed staging hostname.
- Manual verification of OTP, profile review, evidence upload/review, Academy, Tool Bank and rewards workflows.
- A tested stop/rollback decision path and a named person authorized to invoke it.

## Stop conditions
Pause onboarding and new pilot activity if any of the following occurs:
- Suspected unauthorized access, cross-role data exposure or credential leakage.
- Evidence is visible to an unauthorized account or stored outside the approved bucket.
- OTP delivery or verification repeatedly fails for legitimate pilot users.
- Readiness reports a critical dependency unavailable.
- Data loss, backup failure, unexplained record corruption or a security alert requiring investigation.
- Consent, privacy notice or participant expectations are unclear.
- The named pilot owner cannot be reached for a material operational decision.

Preserve relevant request IDs and sanitized timestamps. Do not copy OTPs, bearer tokens, raw personal data or evidence images into incident tickets. Follow the organization's approved incident response and notification requirements.

## Limitations and open production gates
- No live staging environment, real credentials or pilot participants were provided; no production pilot was executed.
- Automated checks are read-only HTTP checks and mocked unit tests. They do not simulate a complete UI/browser session.
- The application currently exposes evidence upload and retrieval/review flows; this phase does not add a complete account erasure or evidence deletion workflow.
- No data-retention durations are invented here. The business/privacy owner must define and approve retention periods and deletion procedures before real personal data is collected.
- Passing this suite is an operational smoke/authorization gate, not a security certification, legal approval, penetration test or load test.
