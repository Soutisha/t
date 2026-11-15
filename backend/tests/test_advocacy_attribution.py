from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.models import User, Mechanic
from app.models.advocacy import AdvocacyProduct, AdvocacyEventLedger
from app.services.advocacy import product_qr_token, verify_product_qr_token, record_event

def test_product_qr_is_signed_and_tamper_evident():
    token = product_qr_token("product-abc")
    assert verify_product_qr_token(token) == "product-abc"
    assert verify_product_qr_token(token + "tamper") is None

def test_recommendation_fitment_and_sale_are_separate_events():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(phone_e164="+917777777777", display_name="Advocacy Tester")
        db.add(user); db.flush()
        mechanic = Mechanic(user_id=user.id, mechanic_code="EGM-ADVOCACY01",
            shop_type="independent", experience_years=3, languages="English",
            service_categories="tyres", participation_type="non_stockist_advocate")
        product = AdvocacyProduct(sku="DEMO-001", product_name="Synthetic tyre")
        db.add_all([mechanic, product]); db.flush()
        record_event(db, mechanic_id=mechanic.id, product_id=product.id,
            event_type="recommendation", source_id="rec-1", verification_status="verified")
        record_event(db, mechanic_id=mechanic.id, product_id=product.id,
            event_type="fitment", source_id="fit-1", verification_status="verified")
        record_event(db, mechanic_id=mechanic.id, product_id=product.id,
            event_type="sale", source_id="sale-1", verification_status="verified")
        db.flush()
        types = set(db.scalars(select(AdvocacyEventLedger.event_type)).all())
        assert types == {"recommendation", "fitment", "sale"}
