# Phase 12 — Cybersecurity and Privacy Hardening

## Implemented

### Authentication and token validation
- JWT access tokens now include issuer, audience, issue time, expiry and a random token identifier.
- Decoder enforces `HS256`, JWT type, signature, expiry, reasonable issue time, issuer, audience and non-empty subject.
- User status is checked against the database for every authenticated request.
- Authorization continues to use database-assigned roles rather than trusting role claims supplied in the token.
- New mechanic onboarding requires a recently consumed, successfully verified OTP challenge for the same phone number.
- OTP verification already enforces a short expiry and a maximum of five attempts; OTP request service limits three requests per phone in ten minutes.

### API perimeter
- Added request correlation IDs and response security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `Permissions-Policy`.
- HSTS is enabled when `APP_ENV` is production.
- Added per-client request throttling and a stricter authentication/onboarding throttle.
- CORS remains allow-list based and supports the required HTTP methods, including DELETE.
- Production settings reject weak placeholder JWT/fingerprint secrets, development OTP echo, and wildcard CORS.

### Audit trail
- Added `security_audit_events` with request ID, actor ID where authenticated, method, path, response status, HMAC client fingerprint, user-agent, duration and event type.
- Audit capture excludes request bodies, OTP values, authorization headers and raw client IP addresses.
- Administrator endpoint: `GET /api/v1/admin/security/audit-events?limit=100` (limit is bounded to 500).

### Privacy controls
- Added `GET /api/v1/me/privacy/consents`.
- Added `POST /api/v1/me/privacy/consents/{purpose}` for versioned consent changes.
- Supported purposes: `shop_location`, `geolocation_discovery`, `product_advocacy`, `training_analytics`.
- Withdrawing `shop_location` updates the user's shop location consent; withdrawing `geolocation_discovery` also disables discoverability for the user's registered geolocations.

## Configuration
Set production environment variables before deployment:
- `APP_ENV=production`
- `JWT_SECRET` — independently generated secret, at least 32 characters
- `CLIENT_FINGERPRINT_SECRET` — independent secret, at least 32 characters
- `OTP_DEV_RETURN_CODE=false`
- `CORS_ORIGINS` — explicit trusted frontend origins, never `*`
- `AUDIT_LOG_ENABLED=true`

See `backend/.env.example` for all names. Never commit real credentials to source control.

## Verification
- 63 backend Python files pass syntax compilation.
- Full backend suite: 32 tests passed.
- Tests include JWT tampering rejection, issuer/audience claims, security headers, OTP prerequisite for onboarding, production secret validation and all earlier module tests.

## Important production limitations
- Rate limiting is currently process-local. Multi-worker or multi-instance deployments must move counters to Redis or an equivalent shared atomic store.
- Audit events are stored in the application database; they are not immutable or tamper-evident. Production should forward them to a restricted append-only log/SIEM with retention and alerting.
- HMAC client fingerprinting reduces direct IP retention but remains pseudonymous data and still needs a documented retention period.
- No external penetration test, SAST/DAST, dependency CVE scan, WAF, SIEM connector, KMS-backed field encryption, database encryption-at-rest validation, backup restore drill or formal privacy impact assessment was performed.
- Production migrations must be applied before deploying new audit tables; development `create_all` is not a migration strategy.
- This phase is security hardening, not a certification of OWASP compliance or legal compliance.
