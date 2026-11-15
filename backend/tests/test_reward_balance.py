from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.models import User, Mechanic
from app.models.toolbank import RewardLedgerEntry
from app.services.rewards import reward_balance

def test_reward_balance_is_ledger_derived():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(phone_e164="+918888888888", display_name="Ledger Tester")
        db.add(user); db.flush()
        mechanic = Mechanic(user_id=user.id, mechanic_code="EGM-LEDGER0001",
            shop_type="independent", experience_years=1, languages="English",
            service_categories="tyres", participation_type="interested")
        db.add(mechanic); db.flush()
        db.add_all([
            RewardLedgerEntry(mechanic_id=mechanic.id, entry_type="credit", points=100,
                source_type="verified_activity", source_id="activity-1", description="Verified activity"),
            RewardLedgerEntry(mechanic_id=mechanic.id, entry_type="debit", points=30,
                source_type="redemption", source_id="redemption-1", description="Approved reward"),
        ])
        db.flush()
        assert reward_balance(db, mechanic.id) == 70
