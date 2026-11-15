# Phase 10 — Geospatial Intelligence

## Objective
Add privacy-aware location registration, nearby discovery, distance calculation and territory-zone lookup using real coordinates entered by authorised platform users. No dealer, mechanic, distributor or stock location is fabricated.

## Implemented capabilities

### Location registration and consent
- Authenticated users can register their own mechanic-shop or service-centre location.
- Dealer/distributor location registration requires a dealer/distributor or administrator role.
- Coordinates are validated for legal latitude/longitude ranges.
- Location consent and public discoverability are separate fields. A location is discoverable only when both are true.
- Owners can update their location, withdraw consent, disable discovery or deactivate a location.
- Nearby search excludes the signed-in user's own location.
- Location owners can inspect their own exact coordinates through the private `me` endpoint.

### Nearby discovery
- Search accepts a user-supplied search centre, radius (0.1–100 km), optional location type and result limit.
- A bounding-box filter reduces database candidates; Haversine distance is then calculated precisely in application code.
- Results are sorted by distance and include the calculated distance.
- Mechanic-shop public coordinates are rounded to three decimal places and their street address is not disclosed. Other discoverable location types are rounded to four decimal places.
- Discovery returns only active records with explicit consent and discoverability enabled.

### Territory zones
- Administrators can create named territory polygons using GeoJSON-compatible longitude/latitude coordinates.
- Polygon validation checks coordinate bounds, closure and minimum distinct vertices.
- Authenticated users can look up which active territory polygons contain a supplied point.
- Point-in-polygon lookup is implemented without an external GIS dependency.

## API endpoints
- `POST /api/v1/geo/locations` — register an owned location.
- `GET /api/v1/geo/locations/me` — list own locations with exact coordinates and consent settings.
- `PATCH /api/v1/geo/locations/{location_id}` — update own location and consent.
- `DELETE /api/v1/geo/locations/{location_id}` — withdraw consent and deactivate.
- `GET /api/v1/geo/nearby` — find consented discoverable locations near supplied coordinates.
- `GET /api/v1/admin/geo/locations` — administrator location inventory.
- `POST /api/v1/admin/geo/territories` — create a territory polygon.
- `GET /api/v1/geo/territories/lookup` — find active territories containing a point.

## Data and privacy safeguards
- Location data is not collected from device GPS automatically; users or trusted integrations must provide coordinates.
- No background tracking or continuous location collection is implemented.
- Consent withdrawal immediately excludes a location from discovery and deactivates it.
- Mechanic shop street addresses are withheld from public nearby results and coordinates are coarsened.
- Exact coordinates are available only to the owner and administrators.
- Production deployment should add encryption at rest, retention policy, audit events for privileged location access, and a formal consent notice/version.

## Limitations
- This phase uses portable Haversine and point-in-polygon calculations, not PostGIS. Large datasets will need PostgreSQL/PostGIS spatial indexes.
- Territory polygons are stored as GeoJSON text. Complex multipolygons, holes, topology validation and territory overlap resolution are not included.
- There is no external geocoder, routing engine, road-network travel-time calculation, live traffic, dealer ERP inventory or map-tile provider.
- Nearby search uses coordinates supplied in the request; no GPS/device permission workflow exists.
- No actual Eurogrip dealer or mechanic locations are seeded. The database begins empty.
- Frontend map and location-management screens are not yet connected to these APIs.

## Verification
- 55 backend Python files pass syntax compilation.
- Full backend test suite passes 26 tests.
- Tests cover distance calculation, polygon containment, authenticated location registration, consent-gated discovery, public coordinate precision, consent withdrawal, territory creation and territory lookup.
- FastAPI app import and route/table registration are checked separately.
