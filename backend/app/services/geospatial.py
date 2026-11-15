import json
import math

EARTH_RADIUS_KM = 6371.0088

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlon/2)**2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))

def public_coordinates(location) -> tuple[float, float]:
    # Mechanic-owned premises are rounded to roughly 100m to reduce address-level exposure.
    precision = 3 if location.location_type == "mechanic_shop" else 4
    return round(location.latitude, precision), round(location.longitude, precision)

def point_in_polygon(longitude: float, latitude: float, polygon: list[list[float]]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = ((yi > latitude) != (yj > latitude)) and (
            longitude < (xj-xi) * (latitude-yi) / ((yj-yi) or 1e-15) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside

def parse_polygon(value: str) -> list[list[float]]:
    raw = json.loads(value)
    if not isinstance(raw, list):
        raise ValueError("Stored territory polygon is invalid.")
    return raw
