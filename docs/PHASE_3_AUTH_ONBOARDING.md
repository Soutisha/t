# Phase 3 — Authentication and Mechanic Onboarding

## Delivered source
- FastAPI application with `/api/v1` routes.
- SQLAlchemy persistence models for users, roles, mechanic profiles, shops, consent and OTP challenges.
- E.164 phone validation.
- Development-only OTP mock; OTP is never returned outside `APP_ENV=development` with `OTP_DEV_RETURN_CODE=true`.
- OTP expiry, attempt limit and request throttling.
- Signed HMAC JWT access tokens and PBKDF2-HMAC OTP hashing.
- Mechanic onboarding for stockist, non-stockist advocate, interested and training participant pathways.
- Profile retrieval and restricted display-name update.
- Role-protected pending-verification list.
- Consent records and optional location consent.
- Basic security and schema tests.

## API routes
- `POST /api/v1/auth/otp/request`
- `POST /api/v1/auth/otp/verify`
- `POST /api/v1/onboarding/mechanics`
- `GET /api/v1/me`
- `PATCH /api/v1/me/profile`
- `GET /api/v1/admin/onboarding/pending`
- `GET /health/live`
- `GET /health/ready`

## Limitations / production gates
- The OTP sender is a development mock; no SMS provider is connected.
- JWT implementation is a minimal first-party HS256 implementation. Before production, perform a security review and preferably use a maintained OIDC provider/library and key rotation.
- Registration is open in this development phase; production needs abuse prevention, invitation/verification policy and CAPTCHA or equivalent controls.
- Admin role provisioning is intentionally not exposed publicly.
- No document upload, password recovery or full admin verification decision endpoint yet.
- SQLite is the local default; PostgreSQL deployment and Alembic migrations remain to be implemented.
- Rate limiting is database-window based and should move to Redis for distributed deployment.
- Automated execution of tests was not performed in this environment; test files are supplied for local verification.

## Verification status
Python source was compiled with `py_compile` successfully. Runtime dependency installation, API integration tests and security testing remain outstanding.
