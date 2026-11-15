from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.models import User, UserRole, UserStatus
from app.core.security import create_access_token
from app.services.geospatial import haversine_km, point_in_polygon

def test_haversine_distance_and_polygon_containment():
    # Approximate Kolkata to Howrah distance is around 5 km.
    distance = haversine_km(22.5726, 88.3639, 22.5958, 88.2636)
    assert 5 < distance < 12
    square = [[88.0,22.0],[89.0,22.0],[89.0,23.0],[88.0,23.0],[88.0,22.0]]
    assert point_in_polygon(88.5,22.5,square)
    assert not point_in_polygon(90.0,22.5,square)

def test_location_consent_nearby_search_and_withdrawal():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    def override_db():
        db=Session()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db]=override_db
    try:
        with Session() as db:
            owner=User(phone_e164="+917000000041",display_name="Shop Owner",status=UserStatus.active)
            visitor=User(phone_e164="+917000000042",display_name="Visitor",status=UserStatus.active)
            db.add_all([owner,visitor]); db.commit()
            owner_token=create_access_token(owner.id,["mechanic"])
            visitor_token=create_access_token(visitor.id,["mechanic"])
        with TestClient(app) as client:
            created=client.post("/api/v1/geo/locations",
                headers={"Authorization":f"Bearer {owner_token}"},
                json={"location_type":"mechanic_shop","display_name":"Test Workshop",
                      "city":"Kolkata","state":"West Bengal","latitude":22.5726,
                      "longitude":88.3639,"location_consent":True,"discoverable":True})
            assert created.status_code==201,created.text
            location_id=created.json()["data"]["location_id"]
            found=client.get("/api/v1/geo/nearby?latitude=22.573&longitude=88.364&radius_km=5",
                headers={"Authorization":f"Bearer {visitor_token}"})
            assert found.status_code==200
            assert len(found.json()["data"])==1
            # Public coordinate is rounded to reduce precision leakage.
            assert found.json()["data"][0]["latitude"]==22.573
            assert found.json()["data"][0]["address_text"]==""
            withdrawn=client.patch(f"/api/v1/geo/locations/{location_id}",
                headers={"Authorization":f"Bearer {owner_token}"},
                json={"location_consent":False})
            assert withdrawn.status_code==200
            found_again=client.get("/api/v1/geo/nearby?latitude=22.573&longitude=88.364&radius_km=5",
                headers={"Authorization":f"Bearer {visitor_token}"})
            assert found_again.json()["data"]==[]
    finally:
        app.dependency_overrides.pop(get_db,None)
        Base.metadata.drop_all(engine)
        engine.dispose()

def test_territory_create_and_lookup():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine,autoflush=False,autocommit=False)
    def override_db():
        db=Session()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db]=override_db
    try:
        with Session() as db:
            admin=User(phone_e164="+917000000043",display_name="Geo Admin",status=UserStatus.active)
            db.add(admin); db.flush()
            db.add(UserRole(user_id=admin.id,role_code="administrator",scope_type="global",scope_id="*"))
            visitor=User(phone_e164="+917000000044",display_name="Geo Visitor",status=UserStatus.active)
            db.add(visitor); db.commit()
            admin_token=create_access_token(admin.id,["administrator"])
            visitor_token=create_access_token(visitor.id,["mechanic"])
        with TestClient(app) as client:
            created=client.post("/api/v1/admin/geo/territories",
                headers={"Authorization":f"Bearer {admin_token}"},
                json={"zone_code":"KOL-CENTRAL","name":"Kolkata Central","region":"West Bengal",
                      "polygon":[[88.2,22.4],[88.5,22.4],[88.5,22.7],[88.2,22.7],[88.2,22.4]]})
            assert created.status_code==201,created.text
            found=client.get("/api/v1/geo/territories/lookup?latitude=22.57&longitude=88.36",
                headers={"Authorization":f"Bearer {visitor_token}"})
            assert found.status_code==200
            assert found.json()["matched"] is True
            assert found.json()["data"][0]["zone_code"]=="KOL-CENTRAL"
    finally:
        app.dependency_overrides.pop(get_db,None)
        Base.metadata.drop_all(engine)
        engine.dispose()
