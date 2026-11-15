import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models.models import User
from app.models.geospatial import GeoLocation, TerritoryZone
from app.schemas.geospatial import GeoLocationCreate, GeoLocationUpdate, TerritoryCreate
from app.services.geospatial import haversine_km, public_coordinates, point_in_polygon, parse_polygon

router = APIRouter()
ADMIN = ("administrator", "eurogrip_admin")
DEALER_ROLES = {"dealer", "distributor", "administrator", "eurogrip_admin"}

def _location_data(location, distance=None):
    lat, lon = public_coordinates(location)
    return {
        "location_id": location.id, "location_type": location.location_type,
        "display_name": location.display_name, "address_text": ("" if location.location_type == "mechanic_shop" else location.address_text),
        "city": location.city, "state": location.state, "country": location.country,
        "latitude": lat, "longitude": lon,
        "distance_km": round(distance, 2) if distance is not None else None,
        "accuracy_meters": location.accuracy_meters,
    }

@router.post("/geo/locations", status_code=201)
def create_location(payload: GeoLocationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    roles = {r.role_code for r in user.roles}
    if payload.location_type in ("dealer", "distributor") and not roles.intersection(DEALER_ROLES):
        raise HTTPException(status_code=403, detail="Dealer/distributor locations require an authorised dealer account.")
    if payload.discoverable and not payload.location_consent:
        raise HTTPException(status_code=422, detail="Location discovery requires explicit consent.")
    location = GeoLocation(
        owner_user_id=user.id, location_type=payload.location_type,
        display_name=payload.display_name.strip(), entity_reference=payload.entity_reference,
        address_text=payload.address_text, city=payload.city, state=payload.state,
        country=payload.country, latitude=payload.latitude, longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters, location_consent=payload.location_consent,
        discoverable=payload.discoverable and payload.location_consent, active=True
    )
    db.add(location); db.commit()
    return {"data": _location_data(location), "message": "Location saved. Discovery is available only when consent and discoverable are both enabled."}

@router.get("/geo/locations/me")
def my_locations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(GeoLocation).where(
        GeoLocation.owner_user_id == user.id, GeoLocation.active.is_(True)
    ).order_by(GeoLocation.created_at.desc())).all()
    return {"data": [{
        "location_id": x.id, "location_type": x.location_type, "display_name": x.display_name,
        "address_text": x.address_text, "city": x.city, "state": x.state,
        "country": x.country, "latitude": x.latitude, "longitude": x.longitude,
        "location_consent": x.location_consent, "discoverable": x.discoverable,
        "accuracy_meters": x.accuracy_meters
    } for x in rows]}

@router.patch("/geo/locations/{location_id}")
def update_location(location_id: str, payload: GeoLocationUpdate,
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    location = db.get(GeoLocation, location_id)
    if not location or location.owner_user_id != user.id or not location.active:
        raise HTTPException(status_code=404, detail="Location not found.")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("location_consent") is False:
        changes["discoverable"] = False
    if changes.get("discoverable") is True and changes.get("location_consent", location.location_consent) is not True:
        raise HTTPException(status_code=422, detail="Explicit location consent is required.")
    for key, value in changes.items():
        setattr(location, key, value)
    db.commit()
    return {"data": {"location_id": location.id, "location_consent": location.location_consent,
        "discoverable": location.discoverable, "updated": True}}

@router.delete("/geo/locations/{location_id}")
def withdraw_location(location_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    location = db.get(GeoLocation, location_id)
    if not location or location.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Location not found.")
    location.location_consent = False
    location.discoverable = False
    location.active = False
    db.commit()
    return {"data": {"location_id": location.id, "active": False, "consent_withdrawn": True}}

@router.get("/geo/nearby")
def nearby_locations(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius_km: float = Query(default=10, ge=0.1, le=100),
    location_type: str | None = Query(default=None, pattern="^(mechanic_shop|dealer|distributor|service_centre)$"),
    limit: int = Query(default=25, ge=1, le=100),
    user: User = Depends(current_user), db: Session = Depends(get_db)
):
    query = select(GeoLocation).where(
        GeoLocation.active.is_(True), GeoLocation.location_consent.is_(True),
        GeoLocation.discoverable.is_(True), GeoLocation.owner_user_id != user.id
    )
    if location_type:
        query = query.where(GeoLocation.location_type == location_type)
    # Cheap bounding box before precise Haversine calculation.
    lat_delta = radius_km / 110.574
    lon_scale = max(0.01, 111.320 * abs(__import__("math").cos(__import__("math").radians(latitude))))
    lon_delta = min(180, radius_km / lon_scale)
    query = query.where(
        GeoLocation.latitude.between(max(-90, latitude-lat_delta), min(90, latitude+lat_delta)),
        GeoLocation.longitude.between(max(-180, longitude-lon_delta), min(180, longitude+lon_delta))
    )
    candidates = db.scalars(query).all()
    found = []
    for item in candidates:
        distance = haversine_km(latitude, longitude, item.latitude, item.longitude)
        if distance <= radius_km:
            found.append((item, distance))
    found.sort(key=lambda pair: pair[1])
    return {"data": [_location_data(item, distance) for item, distance in found[:limit]],
        "search": {"radius_km": radius_km, "returned": min(limit, len(found)),
                   "location_types": [location_type] if location_type else "all_discoverable"}}

@router.get("/admin/geo/locations")
def admin_locations(user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    rows = db.scalars(select(GeoLocation).order_by(GeoLocation.created_at.desc()).limit(500)).all()
    return {"data": [{"location_id": x.id, "owner_user_id": x.owner_user_id,
        "location_type": x.location_type, "display_name": x.display_name,
        "city": x.city, "state": x.state, "latitude": x.latitude, "longitude": x.longitude,
        "consent": x.location_consent, "discoverable": x.discoverable, "active": x.active} for x in rows]}

@router.post("/admin/geo/territories", status_code=201)
def create_territory(payload: TerritoryCreate, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    if db.scalar(select(TerritoryZone).where(TerritoryZone.zone_code == payload.zone_code)):
        raise HTTPException(status_code=409, detail="Territory zone code already exists.")
    zone = TerritoryZone(zone_code=payload.zone_code, name=payload.name,
        region=payload.region, polygon_geojson=json.dumps(
            {"type": "Polygon", "coordinates": [payload.polygon]}, separators=(",", ":")),
        created_by=user.id, active=True)
    db.add(zone); db.commit()
    return {"data": {"territory_id": zone.id, "zone_code": zone.zone_code, "name": zone.name}}

@router.get("/geo/territories/lookup")
def territory_lookup(latitude: float = Query(ge=-90, le=90),
                     longitude: float = Query(ge=-180, le=180),
                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(TerritoryZone).where(TerritoryZone.active.is_(True))).all()
    matches = []
    for zone in rows:
        try:
            geojson = json.loads(zone.polygon_geojson)
            polygon = geojson["coordinates"][0]
            if point_in_polygon(longitude, latitude, polygon):
                matches.append({"territory_id": zone.id, "zone_code": zone.zone_code,
                                "name": zone.name, "region": zone.region})
        except (ValueError, KeyError, TypeError, IndexError):
            continue
    return {"data": matches, "matched": bool(matches)}
