# Phase 6 — Advocacy and Verified Fitment Engine

## Business rule carried through the implementation
Mechanic influence and mechanic stocking are distinct. A mechanic can recommend Eurogrip and submit fitment evidence without being a stockist. The system stores recommendations, fitments, dealer sales and stocking as different records and different event types. A recommendation is not treated as a sale; a fitment is not treated as a stocking record.

## Delivered source
- Admin-managed product catalogue with SKU, product name, tyre type and authorised specification payload.
- Signed product QR token generation and public product identification endpoint; optional PNG QR endpoint for printing.
- Mechanic product recommendation registration with referral code and optional hashed customer reference.
- Evidence metadata submission for recommendations and fitments. This stores references only; binary upload/storage is not implemented yet.
- Fitment submission linked to an optional recommendation, with evidence confidence levels `low`, `medium`, `high` and human verification.
- Dealer referral workflow.
- Optional stockist registration workflow; status remains pending until an administrator verifies it.
- Customer feedback capture.
- Admin-managed advocacy campaigns and mechanic participation.
- Dealer-only sales and stocking record submission endpoints. Dealer sales require invoice reference; stocking requires a stocking reference. Both have uniqueness protection per dealer.
- Administrator review queue and verification endpoints for recommendations, fitments, stockist registrations, dealer sales and dealer stocking.
- Advocacy event ledger with unique event-type/source identity, referral source, dealer reference, optional coarse location label, event date, verification status, evidence confidence and reward eligibility.
- Approved recommendations, fitments and stockist registrations create verified Mechanic Passport advocacy milestones.

## API
- `GET /api/v1/advocacy/products`
- `POST /api/v1/admin/advocacy/products`
- `GET /api/v1/admin/advocacy/products/{product_id}/qr`
- `GET /api/v1/admin/advocacy/products/{product_id}/qr.png`
- `GET /api/v1/advocacy/products/identify/{token}`
- `POST /api/v1/advocacy/recommendations`
- `POST /api/v1/advocacy/recommendations/{recommendation_id}/evidence`
- `GET /api/v1/advocacy/me/events`
- `POST /api/v1/advocacy/fitments`
- `POST /api/v1/advocacy/dealer-referrals`
- `POST /api/v1/advocacy/stockist-registrations`
- `POST /api/v1/advocacy/customer-feedback`
- `GET /api/v1/advocacy/campaigns`
- `POST /api/v1/admin/advocacy/campaigns`
- `POST /api/v1/advocacy/campaigns/{campaign_id}/participation`
- `GET /api/v1/admin/advocacy/review-queue`
- `PATCH /api/v1/admin/advocacy/recommendations/{item_id}/verification`
- `PATCH /api/v1/admin/advocacy/fitments/{item_id}/verification`
- `PATCH /api/v1/admin/advocacy/stockist-registrations/{item_id}/verification`
- `POST /api/v1/dealer/advocacy/sales-records`
- `POST /api/v1/dealer/advocacy/stocking-records`
- `PATCH /api/v1/admin/advocacy/dealer-sales/{item_id}/verification`
- `PATCH /api/v1/admin/advocacy/dealer-stocking/{item_id}/verification`

## Attribution and integrity controls
- Separate ledger event types are used for `recommendation`, `fitment`, `sale`, `stocking`, `stockist_registration` and `campaign_participation`.
- A dealer sale is linked to a mechanic recommendation only when the dealer explicitly supplies that recommendation ID. It does not automatically change the recommendation status or imply every referral converted.
- Stocking can be attributed to a mechanic only when the authorised dealer supplies a mechanic code; otherwise it remains an unattributed dealer record.
- Dealer invoice and stocking references are unique per dealer user.
- Product QR tokens are HMAC-signed and tamper-evident. QR authenticity is not a guarantee that a physical tyre is genuine; replay detection and broader TrustVision fraud analysis are Phase 7.
- No rewards are issued automatically. Verified fitments carry a reward-eligibility flag for later controlled reward processing.
- No actual Eurogrip products, SKU data, compatibility claims, dealer identities, sales, stocking, prices or campaign details are fabricated.

## Verification and limitations
- Backend Python syntax compilation passed for all backend files. The full backend unit-test suite passed: 9 tests. The FastAPI application imported successfully with 55 registered routes and 29 SQLAlchemy tables. Full HTTP workflow/integration tests against a production-like PostgreSQL database remain outstanding.
- The PNG QR endpoint depends on the Phase 4 `qrcode[pil]` dependency.
- Evidence endpoints accept storage references, not raw files. Secure upload, object storage, malware scanning and image/invoice analysis are planned for later phases.
- Dealer roles must be assigned through an authorised identity administration process; this phase does not expose public dealer self-approval.
- Frontend API integration is not complete; the existing advocacy screen remains demo-only.
- Production requires PostgreSQL migrations, API integration tests, audit logging and transaction/concurrency review.
