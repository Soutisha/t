# Phase 28 — Pilot Workflow Rehearsal and Live-Execution Evidence Pack

## Objective

Exercise complete synthetic mechanic, administrator and dealer workflows against the actual FastAPI application using an isolated test database. Add a repeatable command that emits a machine-readable test report without touching production or sending real messages.

A live participant pilot cannot be executed from this workspace because no staging URL, cloud/provider credentials, designated pilot accounts, participant consent records or accountable launch approvals were supplied. This phase therefore delivers the local rehearsal and a precise handoff for the remaining live steps; it does not claim a live deployment.

## Implemented

### Synthetic Tool Bank journey
A mechanic browses the catalogue and submits a request. The administrator reviews and approves it. The test confirms stock is not reserved before approval, then fulfils the request and checks the mechanic sees the fulfilled state.

### Synthetic Rewards journey
An administrator credits a mechanic's ledger. The mechanic requests redemption. The test confirms points are not deducted while pending, then the administrator approves and the ledger-derived balance decreases by the approved amount.

### Synthetic Advocacy journey
The administrator creates a product. A mechanic submits a recommendation, which the administrator verifies. The mechanic submits a separate fitment with evidence metadata; the administrator verifies the fitment. The test confirms recommendation and fitment remain distinct event types.

### Authorization boundary
The synthetic mechanic attempts to access an administrator-only Tool Bank queue and must receive HTTP 403.

### Existing regression journeys included in the rehearsal
The new runner executes the full backend suite, including:
- OTP request/onboarding/login in development test mode.
- Mocked Twilio delivery and provider error handling.
- Mechanic Passport and role-boundary checks.
- Tool Bank and rewards ledger/approval behavior.
- Advocacy attribution and verification.
- TrustVision evidence upload/retrieval using test-local storage.
- Academy course publication, enrolment, lesson completion, quiz and certificate verification.
- Privacy deletion request/approval safeguards and retention controls.
- Staging launch gate, pilot acceptance and security checks.

## Run the rehearsal

From the repository root:

`python3 scripts/pilot-workflow-rehearsal.py --report pilot/reports/synthetic-rehearsal.json`

The runner creates a temporary SQLite database, invokes the backend pytest suite, parses JUnit results and writes a sanitized report. The temporary database is deleted after the run. The report contains test names/status/durations only; it does not contain tokens or user phone numbers.

## Live staging execution remains separate

After Phase 27 launch approvals are completed:
1. Deploy to the approved staging host using the explicit Phase 26 deployment command.
2. Verify HTTPS, DNS, API headers and database/Redis/object-storage readiness.
3. Execute the designated real OTP journey using `pilot-auth-check.py`; this sends an SMS and must be separately approved.
4. Execute the read-only role-aware API acceptance suite with separate mechanic and administrator test tokens.
5. Verify the MinIO scoped identity and perform an isolated encrypted backup restore drill.
6. Manually exercise critical workflows with synthetic pilot records and designated test accounts.
7. Record evidence in the restricted Phase 27 approval file and rerun `pilot-launch-gate.py`.
8. Obtain written business/privacy/security/operations go/no-go approval before inviting participants.

## Safety boundaries

- The rehearsal uses a disposable SQLite database and does not deploy services.
- Twilio calls are mocked; no SMS is sent.
- No real participant data, production database, rewards or physical tool fulfilment is used.
- TrustVision test data is local test data; live MinIO is not contacted.
- The test confirms application workflow behavior, not actual provider, network, device, usability, accessibility or operational readiness.
- The report must be stored in a controlled location if it is combined with external launch evidence. Do not commit actual pilot approval records or access tokens.

## Phase 28 validation record

The new synthetic Tool Bank/Rewards/Advocacy journey passes. The complete backend regression suite is executed in a fresh disposable SQLite environment. Docker, frontend build and all live external provider checks remain outside the scope of this workspace because the required services and credentials were not supplied.

## Local validation results

- Complete backend synthetic workflow/regression rehearsal: **83 passed, 0 failed, 0 errors, 0 skipped**.
- New Tool Bank/Rewards/Advocacy scenario: passed, including stock reservation timing, ledger balance, separate recommendation/fitment records and role denial.
- Runner used a temporary SQLite database and emitted a sanitized report to a temporary path; the database and report were not added to the repository.
- Python compilation and script CLI validation are checked separately in the release handoff.
- Docker Engine and frontend dependencies remain unavailable; live PostgreSQL/Redis/MinIO, browser build, real Twilio delivery and external staging were not tested.
