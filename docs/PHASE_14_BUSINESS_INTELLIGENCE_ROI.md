# Phase 14 — Business Intelligence, Analytics and ROI

## Delivered

Admin-only analytics endpoints use existing platform records and support optional ISO-8601 `start` and `end` filters. The end timestamp is exclusive. Date ranges are limited to 366 days.

- `GET /api/v1/admin/analytics/executive` — executive KPIs and ROI configuration status.
- `GET /api/v1/admin/analytics/advocacy-funnel` — verified recommendations, fitments, sales records, and sold units.
- `GET /api/v1/admin/analytics/operations` — Tool Bank requests, reward ledger points, training, certificates, TrustVision evidence and case statuses.
- `GET /api/v1/admin/analytics/report.csv` — CSV management report.

## Measurement rules

Only records explicitly marked verified are included in verified recommendation, fitment, and sales measures. Sales volume is a sum of verified record quantities, not revenue. The advocacy endpoint reports stages independently; it is not a cohort conversion calculation. A fitment or sale is considered linked only when its explicit recommendation foreign key is populated. This prevents inferred attribution.

Active users means accounts with active status, not monthly active users. The platform currently has no reliable event stream for general engagement or retention, so monthly active mechanics and retention rates are not fabricated. Territory performance is not presented because the existing records do not provide a trustworthy, universal territory attribution for every business event.

ROI deliberately returns `not_configured`. No approved unit economics, programme costs, or verified monetary sale amounts exist. Reward points are not treated as cash costs. No monetary ROI is invented.

## Access and privacy

All endpoints require `administrator` or `eurogrip_admin`. Responses contain aggregates only; no phone numbers, names, precise location data, evidence files, or free-text user content are exposed.

## Limitations / next integration

- No engagement/retention cohort analytics until a governed activity event definition is implemented.
- No territory leaderboard until event-to-territory attribution is reliable and consent-safe.
- No financial ROI until finance-approved cost and benefit inputs are configured.
- CSV export is currently the only export format.
- Analytics are calculated live from operational tables; no warehouse, snapshots, or scheduled aggregation jobs are included.
