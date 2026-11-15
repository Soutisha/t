# Phase 5 — Smart Tool Bank and Rewards

## Delivered source
- Tool catalogue with SKU, description, category, points cost and active/inactive state.
- Inventory record with available and reserved quantities.
- Mechanic tool request submission and personal request history.
- Administrator request queue and explicit approve/reject decision.
- Stock is reserved only when a request is approved; fulfilment consumes the reservation.
- Insufficient stock and duplicate decisions are rejected by the API.
- Append-only reward ledger with credit, debit and reversal entry types.
- Mechanic reward balance is calculated from ledger entries rather than stored as a mutable balance.
- Reward redemption requests require human approval; points are deducted only on approval.
- Admin reward credits require a mechanic code, positive points, source type, source ID and description. A unique source constraint prevents duplicate credits for the same source and entry type.

## API
- `GET /api/v1/toolbank/catalog`
- `POST /api/v1/admin/toolbank/products`
- `POST /api/v1/toolbank/requests`
- `GET /api/v1/toolbank/requests/me`
- `GET /api/v1/admin/toolbank/requests/pending`
- `PATCH /api/v1/admin/toolbank/requests/{request_id}`
- `PATCH /api/v1/admin/toolbank/requests/{request_id}/fulfil`
- `GET /api/v1/rewards/me`
- `POST /api/v1/rewards/redemptions`
- `GET /api/v1/admin/rewards/redemptions/pending`
- `PATCH /api/v1/admin/rewards/redemptions/{redemption_id}`
- `POST /api/v1/admin/rewards/credits`

## Safety and business rules
- A mechanic can submit a request but cannot approve it or allocate inventory.
- Approval is a separate administrator action. Fulfilment is a second explicit action.
- A redemption request does not immediately deduct points. Approval rechecks the available balance and creates a debit ledger entry.
- Tool requests are not automatically approved based on a points balance.
- No real tool catalogue, eligibility rules, reward conversion values, vendors, delivery providers or inventory feeds were supplied. Catalogue content must be configured by authorised administrators; none is fabricated.
- `with_for_update` is used for critical approval rows. Production should use PostgreSQL and appropriate transaction isolation; SQLite does not provide equivalent row-level locking. Add concurrency/integration tests before production.

## Verification and limitations
- Backend Python syntax compilation is checked.
- Unit tests for ledger balance are included but were not executed here because the runtime dependencies/database test environment are not installed.
- Frontend API integration and live authentication are not yet wired; current frontend tool-bank figures remain clearly illustrative demo data.
- Alembic migrations, audit-event integration, notifications, vendor procurement, shipping, returns, and automated reward triggers remain future work.
