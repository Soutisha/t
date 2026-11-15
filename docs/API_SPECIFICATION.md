# API Specification — Contract Baseline

Base path: `/api/v1`. JSON requests and responses. OpenAPI is generated from FastAPI schemas. Use consistent error envelopes and request correlation IDs.

## Standard success envelope
```json
{
  "data": {},
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-01-01T00:00:00Z"
  }
}
```

## Standard error envelope
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": []
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

## Initial route groups
- `GET /health/live` — process liveness.
- `GET /health/ready` — dependency readiness.
- `POST /auth/otp/request` — request OTP through configured provider or development mock.
- `POST /auth/otp/verify` — verify OTP and establish session.
- `GET /me` — current user and effective roles/scopes.
- `POST /mechanics` — create mechanic profile.
- `GET /mechanics/{mechanic_id}` — authorised mechanic profile.
- `PATCH /mechanics/{mechanic_id}` — update permitted profile fields.
- `POST /recommendations` — submit a recommendation.
- `POST /recommendations/{id}/evidence` — attach evidence.
- `POST /tool-requests` — submit equipment request.
- `GET /tool-requests/{id}` — view own or authorised request.
- `POST /admin/tool-requests/{id}/decision` — authorised approval/rejection with audit.
- `POST /evidence` — upload evidence metadata/file.
- `POST /training/courses/{id}/attempts` — submit assessment attempt.
- `GET /admin/analytics/overview` — database-derived aggregate metrics.

## Contract rules
- All write endpoints validate role, object scope and business state.
- Mutating requests accept an idempotency key where duplicate submission is harmful.
- Pagination uses `limit` and opaque `cursor`.
- Dates are ISO 8601 UTC.
- Never return private phone numbers, customer identifiers or precise locations without a defined permission and purpose.
- AI endpoints must return provenance and review status; they must not silently mutate business records.
- External provider adapters return explicit `not_configured` or `sandbox` status rather than pretending to be live.

## Versioning
Breaking contract changes require a versioned API path or an explicit migration window. OpenAPI snapshots are checked in CI once the backend is implemented.
