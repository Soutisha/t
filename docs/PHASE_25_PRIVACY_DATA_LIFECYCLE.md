# Phase 25 — Privacy Lifecycle, Retention Controls and Account Deletion

## Delivered

### Consent and account deletion lifecycle
- Added persistent `account_deletion_requests` records with pending, approved, rejected and completed states.
- Authenticated users can submit a deletion request using the exact confirmation phrase `DELETE MY ACCOUNT` and inspect their request history.
- Administrators can review and approve/reject requests.
- Execution is a separate administrator action requiring `EXECUTE ACCOUNT ERASURE`.
- Every lifecycle action writes a privacy-specific security audit event.
- The account is suspended after execution, its direct profile identifiers are replaced, roles and OTP challenges are removed, saved locations are deleted, shop location fields are redacted, and all consent purposes are withdrawn.
- User-submitted TrustVision evidence objects and their OCR/review/scan rows are removed through the configured object-storage adapter. If storage deletion fails, the database transaction is not committed.
- Advocacy evidence storage references are redacted; Copilot query/answer text and agent request/response/trace text are redacted; optional reviewer/approver actor references are cleared. The account row remains as a pseudonymous FK anchor so historical records and referential integrity are not silently broken.

### Retention controls
- Added `OTP_RETENTION_HOURS`, `SECURITY_AUDIT_RETENTION_DAYS` and `USER_ACTIVITY_RETENTION_DAYS`.
- All three default to `0`, which disables automated cleanup. No retention period is assumed or silently imposed.
- Added `scripts/retention-maintenance.py`, which is dry-run by default.
- Destructive execution requires all of:
  - A data-owner-approved non-zero policy in the environment.
  - `--execute`.
  - `--confirm-retention-policy`.
  - `RETENTION_EXECUTION_APPROVED=1`.
- The maintenance job only targets expired OTP challenges, security audit events, and Copilot/agent activity logs older than their configured windows. Account deletion requests are retained as proof of handling and are not auto-purged. The script is an operator-run maintenance task; no scheduler is installed.

### Frontend
- Added a Privacy & data workspace for authenticated roles.
- Users can inspect consent/deletion request records and submit a deletion request.
- Administrators can approve/reject and separately execute an approved request with a typed confirmation.

### Database migration
- Added Alembic revision `phase25_privacy` after the initial schema migration.
- Production deployments must apply Alembic migrations before starting the Phase 25 API.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/me/privacy/deletion-requests` | Submit user request |
| GET | `/api/v1/me/privacy/deletion-requests` | View own requests |
| GET | `/api/v1/admin/privacy/deletion-requests` | Admin review queue |
| PATCH | `/api/v1/admin/privacy/deletion-requests/{id}/decision` | Approve/reject |
| POST | `/api/v1/admin/privacy/deletion-requests/{id}/execute` | Execute approved redaction/deactivation |

Existing consent endpoints remain:
- `GET /api/v1/me/privacy/consents`
- `POST /api/v1/me/privacy/consents/{purpose}`

## Operator configuration

Retention windows are intentionally disabled until the organization's privacy/data owner approves them. After approval, set the exact values in the protected deployment environment; do not copy example values without review.

```bash
# Dry run — reports candidate counts only
python3 scripts/retention-maintenance.py

# Destructive run — only after documented approval
RETENTION_EXECUTION_APPROVED=1 python3 scripts/retention-maintenance.py \
  --execute --confirm-retention-policy
```

Apply the schema migration:

```bash
cd backend
alembic upgrade head
```

## Important scope boundaries

This is a staged account deactivation and direct-identifier redaction workflow, not a universal erasure guarantee. The account row remains as a pseudonymous foreign-key anchor. Historical rewards, learning/certificate, financial/dealer, advocacy, business and security audit records may remain linked to that anchor where approved retention, fraud prevention, safety, financial integrity or legal obligations require them. The organization must document those purposes and any applicable legal holds before approving a request.

The application cannot decide legal retention periods. The data owner must define and approve retention schedules, privacy notice language, data-subject response timelines, exceptions and incident-notification obligations. The current automated retention task handles expired OTP challenges, old security audit rows and old Copilot/agent activity logs; it does not purge all business datasets.

Evidence object deletion is performed before the database commit to avoid committing an erased DB record while leaving a known object in storage. A provider failure can cause partial object deletion before the operation aborts; the request remains approved and can be retried after the storage issue is resolved. Verify object-storage deletion semantics and backups in staging.

No real account was deleted, no live object storage was contacted, and no production migration was applied during this workspace run.
