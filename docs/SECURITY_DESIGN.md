# Security Design — Baseline

## Identity and sessions
Use OIDC for production identity. Enforce secure, HttpOnly, SameSite cookies for browser sessions where applicable. OTP codes are short-lived, one-time, hashed at rest, rate-limited and never logged. Development mock OTP must be disabled outside local/test environments.

## Authorisation
Use RBAC plus object-level and scope-level checks. Deny by default. Validate permissions in backend services, not only in the UI. Privileged actions are audited.

## Data protection
- TLS in transit.
- Encryption at rest for database backups and object storage.
- Secrets supplied through environment/secret manager, never committed.
- Minimise personal data and restrict retention.
- Purpose-specific consent for location and public profile visibility.
- Separate public profile fields from private account fields.

## Application security
- Pydantic validation and parameterised database access.
- CSRF protection for cookie-authenticated mutations.
- Output encoding and content security policy in frontend.
- Rate limits on OTP, login, uploads and AI endpoints.
- File type/size validation, malware scanning where available, random object keys and private buckets.
- Audit sensitive reads and all privileged writes.

## AI and evidence security
- Treat uploaded files and retrieved text as untrusted data.
- Prevent prompt instructions inside documents from overriding system policy.
- Restrict agent tools to explicit allowlists.
- Human approval for rewards, equipment, access changes and irreversible actions.
- Record model/version, evidence references and reviewer decisions.
- Do not use risk scores as automatic grounds for permanent rejection.

## Operational security
- Separate local, staging and production credentials.
- Dependency scanning and container image scanning in CI.
- Encrypted backups with restore tests.
- Incident response and access revocation procedures.
- Security review before production launch.

This document is a design baseline, not a claim of completed security controls or legal compliance.
