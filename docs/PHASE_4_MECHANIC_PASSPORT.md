# Phase 4 — Mechanic Passport

## Delivered source
- Persistent passport profile with private-by-default public visibility and a consent version/timestamp.
- Unique mechanic code from onboarding is reused as the professional identity.
- Skill claims with pending/verified/rejected states and an administrator verification queue.
- Verified certifications, achievements and advocacy milestones data models for later phases to populate.
- Evidence-based progression: Registered Mechanic → Skilled Mechanic → Certified Mechanic → Eurogrip Champion → Master Mentor.
- QR identity endpoint emits a PNG QR code containing an opaque HMAC-signed verification URL. It does not encode phone number, address or other personal data.
- Public profile endpoint is only available after explicit opt-in; it returns name, mechanic code, verified skills/certifications/achievements and tier, not phone/address/shop location.
- Passport audit events record visibility changes and skill submissions/verifications.

## Progression rules
- Skilled Mechanic: at least 3 verified skills.
- Certified Mechanic: Skilled plus at least 1 verified certification.
- Eurogrip Champion: Certified plus at least 3 verified advocacy milestones.
- Master Mentor: Champion plus at least 2 verified `mentor_verified` milestones.
- Self-reported or pending items do not count. These are initial configurable rules, not official Eurogrip policy; confirm thresholds with the business owner before production.

## API
- `GET /api/v1/passport/me`
- `PATCH /api/v1/passport/me/visibility`
- `POST /api/v1/passport/me/skills`
- `GET /api/v1/passport/me/qr`
- `GET /api/v1/passport/verify/{token}`
- `GET /api/v1/passport/public/{slug}`
- `GET /api/v1/admin/passport/skills/pending`
- `PATCH /api/v1/admin/passport/skills/{skill_id}/verification`

## Verification and limitations
- Python syntax compilation is run for the backend source.
- Automated rule/token tests are included but have not been executed in this environment because dependency installation/runtime DB verification is not available.
- QR generation requires the added `qrcode[pil]` dependency to be installed.
- The existing Phase 3 local development bootstrap uses `create_all`; it creates new passport tables but does not migrate an already-existing database schema. Production requires Alembic migrations.
- Certification and advocacy data are modeled but no Phase 5/6/11 event integrations exist yet; no fabricated activity is inserted.
- The public URL base is configurable with `PASSPORT_PUBLIC_BASE_URL`. Set it to a reachable HTTPS host before generating QR codes outside local development.
