import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import create_access_token
from app.models.models import User, UserRole, UserStatus, Mechanic, VerificationStatus
from app.models.toolbank import ToolInventory


def test_synthetic_mechanic_dealer_admin_workflow_rehearsal():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        suffix = uuid.uuid4().hex[:10]
        with Session() as db:
            admin = User(phone_e164=f"+9170{suffix[:8]}", display_name="Synthetic Admin", status=UserStatus.active)
            mechanic_user = User(phone_e164=f"+9171{suffix[:8]}", display_name="Synthetic Mechanic", status=UserStatus.active)
            dealer = User(phone_e164=f"+9172{suffix[:8]}", display_name="Synthetic Dealer", status=UserStatus.active)
            db.add_all([admin, mechanic_user, dealer])
            db.flush()
            mechanic = Mechanic(
                user_id=mechanic_user.id,
                mechanic_code="EGM-" + suffix.upper(),
                shop_type="tyre_shop",
                experience_years=6,
                languages="Bengali, English",
                service_categories="tyres",
                participation_type="non_stockist_advocate",
                verification_status=VerificationStatus.verified,
            )
            db.add(mechanic)
            db.add_all([
                UserRole(user_id=admin.id, role_code="administrator", scope_type="global", scope_id="*"),
                UserRole(user_id=mechanic_user.id, role_code="mechanic", scope_type="global", scope_id="*"),
                UserRole(user_id=dealer.id, role_code="dealer", scope_type="global", scope_id="*"),
            ])
            db.commit()
            admin_token = create_access_token(admin.id, ["administrator"])
            mechanic_token = create_access_token(mechanic_user.id, ["mechanic"])
            dealer_token = create_access_token(dealer.id, ["dealer"])
            mechanic_code = mechanic.mechanic_code

        admin_h = {"Authorization": f"Bearer {admin_token}"}
        mechanic_h = {"Authorization": f"Bearer {mechanic_token}"}
        dealer_h = {"Authorization": f"Bearer {dealer_token}"}

        with TestClient(app) as client:
            # Tool Bank: catalogue -> request -> approval -> fulfilment.
            created_tool = client.post("/api/v1/admin/toolbank/products", headers=admin_h, json={
                "sku": "SYN-" + suffix, "name": "Synthetic torque wrench",
                "description": "Non-production rehearsal item", "category": "tools",
                "points_cost": 0, "initial_quantity": 4,
            })
            assert created_tool.status_code == 201, created_tool.text
            tool_id = created_tool.json()["data"]["product_id"]
            catalog = client.get("/api/v1/toolbank/catalog", headers=mechanic_h)
            assert catalog.status_code == 200
            assert any(x["product_id"] == tool_id and x["available_quantity"] == 4 for x in catalog.json()["data"])

            requested = client.post("/api/v1/toolbank/requests", headers=mechanic_h, json={
                "product_id": tool_id, "quantity": 2, "reason": "Need tools for workshop service",
            })
            assert requested.status_code == 201, requested.text
            request_id = requested.json()["data"]["request_id"]
            # Stock must not be reserved before a human decision.
            with Session() as db:
                stock = db.scalar(select(ToolInventory).where(ToolInventory.product_id == tool_id))
                assert stock.available_quantity == 4 and stock.reserved_quantity == 0

            pending = client.get("/api/v1/admin/toolbank/requests/pending", headers=admin_h)
            assert pending.status_code == 200
            assert any(x["request_id"] == request_id for x in pending.json()["data"])
            approved = client.patch(f"/api/v1/admin/toolbank/requests/{request_id}", headers=admin_h,
                                    json={"approved": True, "note": "Approved in synthetic rehearsal"})
            assert approved.status_code == 200 and approved.json()["data"]["status"] == "approved"
            fulfilled = client.patch(f"/api/v1/admin/toolbank/requests/{request_id}/fulfil", headers=admin_h)
            assert fulfilled.status_code == 200 and fulfilled.json()["data"]["status"] == "fulfilled"
            mine = client.get("/api/v1/toolbank/requests/me", headers=mechanic_h)
            assert mine.status_code == 200 and mine.json()["data"][0]["status"] == "fulfilled"

            # Rewards: credit ledger -> redemption request -> approval -> debit ledger.
            credit = client.post("/api/v1/admin/rewards/credits", headers=admin_h, json={
                "mechanic_code": mechanic_code, "points": 250,
                "source_type": "synthetic_rehearsal", "source_id": "credit-" + suffix,
                "description": "Synthetic workflow rehearsal points",
            })
            assert credit.status_code == 201, credit.text
            assert credit.json()["data"]["balance"] == 250
            redemption = client.post("/api/v1/rewards/redemptions", headers=mechanic_h, json={
                "reward_name": "Synthetic workshop voucher", "points_cost": 100,
            })
            assert redemption.status_code == 201, redemption.text
            redemption_id = redemption.json()["data"]["redemption_id"]
            # Requested redemption is not deducted before approval.
            assert client.get("/api/v1/rewards/me", headers=mechanic_h).json()["data"]["balance"] == 250
            reward_decision = client.patch(f"/api/v1/admin/rewards/redemptions/{redemption_id}",
                headers=admin_h, json={"approved": True, "note": "Approved in synthetic rehearsal"})
            assert reward_decision.status_code == 200
            reward_balance = client.get("/api/v1/rewards/me", headers=mechanic_h)
            assert reward_balance.status_code == 200
            assert reward_balance.json()["data"]["balance"] == 150

            # Advocacy: recommendation and fitment are separate, reviewable records.
            product = client.post("/api/v1/admin/advocacy/products", headers=admin_h, json={
                "sku": "ADV-" + suffix, "product_name": "Synthetic touring tyre",
                "description": "Non-production rehearsal product", "tyre_type": "touring",
                "specifications_json": "{\"width\": 100}",
            })
            assert product.status_code == 201, product.text
            product_id = product.json()["data"]["product_id"]
            recommendation = client.post("/api/v1/advocacy/recommendations", headers=mechanic_h, json={
                "product_id": product_id, "referral_source": "workshop",
                "notes": "Synthetic recommendation", "location_label": "Test workshop",
            })
            assert recommendation.status_code == 201, recommendation.text
            recommendation_id = recommendation.json()["data"]["recommendation_id"]
            rec_review = client.patch(f"/api/v1/admin/advocacy/recommendations/{recommendation_id}/verification",
                headers=admin_h, json={"approved": True, "note": "Synthetic recommendation reviewed"})
            assert rec_review.status_code == 200
            fitment = client.post("/api/v1/advocacy/fitments", headers=mechanic_h, json={
                "product_id": product_id, "recommendation_id": recommendation_id,
                "vehicle_reference": "SYNTHETIC-VEHICLE",
                "location_label": "Test workshop",
                "evidence": [{"evidence_type": "photo_reference",
                              "storage_reference": "synthetic://phase28/evidence-1",
                              "confidence": "high"}],
            })
            assert fitment.status_code == 201, fitment.text
            fitment_id = fitment.json()["data"]["fitment_id"]
            fitment_review = client.patch(f"/api/v1/admin/advocacy/fitments/{fitment_id}/verification",
                headers=admin_h, json={"approved": True, "note": "Synthetic fitment reviewed"})
            assert fitment_review.status_code == 200
            events = client.get("/api/v1/advocacy/me/events", headers=mechanic_h)
            assert events.status_code == 200
            event_types = {item["event_type"] for item in events.json()["data"]}
            assert {"recommendation", "fitment"}.issubset(event_types)

            # Role boundary: mechanic cannot read administrator review queues.
            denied = client.get("/api/v1/admin/toolbank/requests/pending", headers=mechanic_h)
            assert denied.status_code == 403

    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
