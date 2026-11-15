from pydantic import BaseModel, Field, field_validator

class GeoLocationCreate(BaseModel):
    location_type: str = Field(pattern="^(mechanic_shop|dealer|distributor|service_centre)$")
    display_name: str = Field(min_length=2, max_length=160)
    entity_reference: str = Field(default="", max_length=100)
    address_text: str = Field(default="", max_length=1000)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=100)
    country: str = Field(default="India", max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: int | None = Field(default=None, ge=1, le=100000)
    location_consent: bool
    discoverable: bool = False

    @field_validator("discoverable")
    @classmethod
    def discoverable_requires_consent(cls, value, info):
        if value and info.data.get("location_consent") is not True:
            raise ValueError("Explicit location consent is required before enabling discovery.")
        return value

class GeoLocationUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    address_text: str | None = Field(default=None, max_length=1000)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_consent: bool | None = None
    discoverable: bool | None = None

class TerritoryCreate(BaseModel):
    zone_code: str = Field(min_length=2, max_length=50, pattern="^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    region: str = Field(default="", max_length=100)
    polygon: list[list[float]] = Field(min_length=4, max_length=500)

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value):
        for point in value:
            if len(point) != 2 or not (-180 <= point[0] <= 180) or not (-90 <= point[1] <= 90):
                raise ValueError("Polygon coordinates must be [longitude, latitude] within valid ranges.")
        if value[0] != value[-1]:
            raise ValueError("Polygon must be closed: first and last coordinate must match.")
        if len(set(tuple(x) for x in value[:-1])) < 3:
            raise ValueError("Polygon must contain at least three distinct vertices.")
        return value
