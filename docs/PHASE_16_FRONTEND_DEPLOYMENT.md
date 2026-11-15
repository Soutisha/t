# Phase 16 — Frontend Integration and Deployment Foundation

## Delivered

### Authenticated frontend

- React sign-in screen uses the existing OTP request and verification APIs.
- Access token and basic user session are stored in `sessionStorage`, not persistent local storage.
- The frontend loads the user's server-issued roles; the old role-switcher is removed from the signed-in header.
- A 401 response clears the session and returns the user to sign-in.
- Sign-out clears the local session.
- The browser API client attaches the bearer token to protected requests.

### Live analytics integration

The Reports & ROI workspace now calls:
- `/api/v1/admin/analytics/executive`
- `/api/v1/admin/analytics/advocacy-funnel`
- `/api/v1/admin/analytics/operations`
- `/api/v1/admin/analytics/report.csv`

It renders real database aggregates, date filters, CSV export, and the explicit ROI `not_configured` state. It no longer displays synthetic KPI values in this workspace. The rest of the pre-existing UI still contains clearly labelled demo data/placeholders.

### OTP delivery

- Development mode may return a mock OTP only when `OTP_DEV_RETURN_CODE=true`.
- Twilio SMS delivery is supported when configured.
- If neither development mock nor provider credentials are available, OTP requests fail closed with HTTP 503 instead of silently creating an unusable challenge.
- Production configuration validation now requires Twilio credentials and disabled development OTP echo.

### Deployment

- Added a multi-stage frontend Dockerfile.
- Added Nginx configuration to serve the React build, proxy `/api/` to FastAPI, and proxy health checks.
- Docker Compose now includes a `web` service exposed on port 8080.
- Added an operator-run admin bootstrap script. It only promotes an existing active account and never creates credentials or bypasses OTP.

## Local development

1. Start the backend using the instructions in the root README.
2. In another terminal, run `cd frontend && npm install && npm run dev`.
3. The Vite development server proxies `/api` and `/health` to `http://localhost:8000`.
4. Sign in using an existing account. The local development OTP is returned by the API only in development mode when the flag is enabled.
5. Admin users must have the `administrator` or `eurogrip_admin` role assigned server-side.

## Staging deployment preparation

1. Copy `.env.cloud.example` to `.env` and replace every placeholder with strong, unique secrets.
2. Configure Twilio credentials and a verified sender number. Confirm the sender is permitted to send to the target countries.
3. Configure `CORS_ORIGINS` to the actual approved origin(s); do not use `*`.
4. Review Docker Compose ports, TLS termination, backups, volume encryption, and firewall rules.
5. Build and start with `docker compose up --build -d`.
6. Validate `/healthz`, `/health/live`, `/health/ready`, OTP delivery, login, and an authorised admin analytics request.
7. Use `python -m scripts.bootstrap_admin +91XXXXXXXXXX "Platform Admin"` from the backend environment only after an authorised account has been created and verified.

The supplied Compose file is a staging foundation, not a complete public-internet production topology. It does not configure TLS certificates, external secrets management, centralised logs, backup scheduling, alerting, or a managed database.

## Known gaps

- Full mechanic self-registration is not yet presented as a frontend workflow; the backend onboarding endpoint exists.
- The other transactional frontend modules still contain demo content and are not yet wired to their APIs.
- Admin bootstrap requires an existing active user; initial account creation and role assignment remain an operator-controlled process.
- Browser E2E, npm production build, Docker image build, Twilio delivery and live deployment could not be executed in this runtime because frontend dependencies/provider credentials/Docker runtime are not available.
