from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.toolbank import RewardLedgerEntry

def reward_balance(db: Session, mechanic_id: str) -> int:
    credit = db.scalar(select(func.coalesce(func.sum(RewardLedgerEntry.points), 0)).where(
        RewardLedgerEntry.mechanic_id == mechanic_id,
        RewardLedgerEntry.entry_type.in_(["credit", "reversal"]))) or 0
    debit = db.scalar(select(func.coalesce(func.sum(RewardLedgerEntry.points), 0)).where(
        RewardLedgerEntry.mechanic_id == mechanic_id,
        RewardLedgerEntry.entry_type == "debit")) or 0
    return int(credit - debit)
