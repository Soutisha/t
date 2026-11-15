# Phase 27 — Controlled Pilot Launch Controller

## Objective

Provide one repeatable, read-only go/no-go command that combines the existing staging infrastructure verifier, role-aware API acceptance checks and the human/provider evidence required by the controlled pilot protocol.

This phase does not claim that a live staging environment or real pilot has been executed. No staging hostname, credentials, provider account, named owners or participant cohort were supplied.

## Delivered

- `scripts/pilot-launch-gate.py`: fail-closed launch controller.
- `pilot/templates/launch-approval.example.json`: structured template for the approved pilot scope, accountable roles and required evidence.
- `backend/tests/test_phase27_pilot_launch_gate.py`: validation of complete/incomplete evidence, owner assignments, cohort bounds, HTTPS and token requirements.
- This runbook and an updated cumulative release.

## Required evidence

The controller requires all five accountable role assignments:
- Business owner
- Technical owner
- Privacy/data owner
- Support contact
- Pilot coordinator

It also requires recorded evidence for:
- Business scope approval
- Privacy notice and consent approval
- Retention and deletion policy approval
- External TLS/DNS verification
- Real Twilio OTP journey
- MinIO scoped application identity
- Encrypted backup and isolated restore drill
- Monitoring alert delivery
- Manual critical workflow sign-off
- Rollback/stop rehearsal
- Participant recruitment and consent approval

Each evidence record must include `status: approved`, an evidence reference, an approving role and an approval timestamp. These fields are operator attestations; the tool does not independently authenticate approvers or evidence files.

Pilot scope requires geography, start/end dates, cohort size from 1 to 100, and a non-empty approved feature list. This is a validation ceiling for a controlled pilot, not a recommendation to recruit 100 participants.

## Running the launch gate

1. Copy `pilot/templates/launch-approval.example.json` to a restricted operator-controlled path outside source control.
2. Complete the scope, owners and evidence references only after the responsible people have actually completed each activity.
3. Confirm the deployed HTTPS staging endpoint with the infrastructure verifier.
4. Obtain separate short-lived mechanic and administrator access tokens for designated test accounts.
5. Run:

   `PILOT_MECHANIC_TOKEN='...' PILOT_ADMIN_TOKEN='...' python3 scripts/pilot-launch-gate.py --base-url https://staging.example.org --approval-file /secure/path/pilot-approval.json --report /secure/path/pilot-launch-report.json`

6. A `NO_GO` result lists missing gates. Resolve them and rerun.
7. A `GO` result means the technical checks passed and the required approval fields were recorded. The accountable business pilot owner still makes the final launch decision.

The report excludes access tokens and approver names. Store the approval source and generated report in access-controlled storage; do not commit them to Git.

## Safety boundaries

- The command is read-only: it does not deploy, send SMS, create users, mutate workflows, issue rewards or erase data.
- Real SMS remains a separately chargeable action and must be executed with the explicit opt-in procedure in `scripts/pilot-auth-check.py`.
- The controller verifies gateway/API health and dependency readiness, then runs read-only mechanic/admin API checks and a mechanic-to-admin denial probe.
- The evidence checklist is not a substitute for independent security review, legal/privacy review, actual backup restoration, alert receiver testing or manual end-to-end workflow execution.
- Never put live access tokens, phone numbers, participant lists, names, private URLs or approval records in the source repository.

## Phase 27 local validation

The automated tests validate the approval schema and fail-closed behavior. No real staging URL, provider credentials, pilot tokens or approval evidence were supplied, so live checks are intentionally not reported as passed.

## Local validation record

- Full backend suite: **82 passed** on a fresh disposable SQLite database.
- Python compilation: passed for application, tests, migrations and launch scripts.
- CLI help: passed; HTTP launch URL is rejected before any network request.
- Approval template: valid JSON; all 11 evidence entries correctly remain pending.
- Compose and CI YAML parsing: passed.
- No live staging host, mechanic/admin tokens, approval record, Twilio account, MinIO service or pilot cohort was available. Consequently, no external runtime gate was marked passed and no GO decision was issued.
