from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models.models import Mechanic, User
from app.models.toolbank import ToolProduct, ToolInventory, ToolRequest, RewardLedgerEntry, RewardRedemption
from app.schemas.toolbank import ToolProductCreate, ToolRequestCreate, DecisionInput, RewardCreditInput, RedemptionCreate
from app.services.rewards import reward_balance

router = APIRouter()
ADMIN = ("administrator", "eurogrip_admin")

def mechanic_for(user: User, db: Session) -> Mechanic:
    item = db.scalar(select(Mechanic).where(Mechanic.user_id == user.id))
    if not item: raise HTTPException(status_code=404, detail="Mechanic profile not found.")
    return item

@router.get("/toolbank/catalog")
def catalog(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(ToolProduct).where(ToolProduct.active.is_(True)).order_by(ToolProduct.name)).all()
    result = []
    for item in rows:
        stock = db.scalar(select(ToolInventory).where(ToolInventory.product_id == item.id))
        result.append({"product_id": item.id, "sku": item.sku, "name": item.name,
            "description": item.description, "category": item.category, "points_cost": item.points_cost,
            "available_quantity": stock.available_quantity if stock else 0})
    return {"data": result}

@router.post("/admin/toolbank/products", status_code=201)
def create_product(payload: ToolProductCreate, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    if db.scalar(select(ToolProduct).where(ToolProduct.sku == payload.sku)):
        raise HTTPException(status_code=409, detail="SKU already exists.")
    product = ToolProduct(sku=payload.sku, name=payload.name, description=payload.description,
                          category=payload.category, points_cost=payload.points_cost)
    db.add(product); db.flush()
    db.add(ToolInventory(product_id=product.id, available_quantity=payload.initial_quantity))
    db.commit()
    return {"data": {"product_id": product.id, "sku": product.sku, "name": product.name}}

@router.post("/toolbank/requests", status_code=201)
def request_tool(payload: ToolRequestCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    product = db.get(ToolProduct, payload.product_id)
    if not product or not product.active: raise HTTPException(status_code=404, detail="Tool not found.")
    stock = db.scalar(select(ToolInventory).where(ToolInventory.product_id == product.id))
    if not stock or stock.available_quantity < 1:
        raise HTTPException(status_code=409, detail="This tool is currently out of stock.")
    req = ToolRequest(mechanic_id=mechanic.id, product_id=product.id,
                      quantity=payload.quantity, reason=payload.reason.strip())
    db.add(req); db.commit()
    return {"data": {"request_id": req.id, "status": req.status,
                     "message": "Request submitted for human approval. Stock is not reserved until approval."}}

@router.get("/toolbank/requests/me")
def my_tool_requests(user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    rows = db.scalars(select(ToolRequest).where(ToolRequest.mechanic_id == mechanic.id)
                      .order_by(ToolRequest.created_at.desc())).all()
    return {"data": [{"request_id": x.id, "tool": x.product.name, "quantity": x.quantity,
        "status": x.status, "reason": x.reason, "decision_note": x.decision_note,
        "created_at": x.created_at} for x in rows]}

@router.get("/admin/toolbank/requests/pending")
def pending_tool_requests(user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    rows = db.scalars(select(ToolRequest).where(ToolRequest.status == "pending")
                      .order_by(ToolRequest.created_at)).all()
    return {"data": [{"request_id": x.id, "mechanic_id": x.mechanic_id,
        "mechanic_code": db.get(Mechanic, x.mechanic_id).mechanic_code,
        "tool": x.product.name, "sku": x.product.sku, "quantity": x.quantity, "reason": x.reason} for x in rows]}

@router.patch("/admin/toolbank/requests/{request_id}")
def decide_tool_request(request_id: str, payload: DecisionInput,
                        user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    req = db.scalar(select(ToolRequest).where(ToolRequest.id == request_id).with_for_update())
    if not req: raise HTTPException(status_code=404, detail="Tool request not found.")
    if req.status != "pending": raise HTTPException(status_code=409, detail="Request has already been decided.")
    if payload.approved:
        stock = db.scalar(select(ToolInventory).where(ToolInventory.product_id == req.product_id).with_for_update())
        if not stock or stock.available_quantity < req.quantity:
            raise HTTPException(status_code=409, detail="Insufficient stock to approve this request.")
        stock.available_quantity -= req.quantity
        stock.reserved_quantity += req.quantity
        req.status = "approved"
    else:
        req.status = "rejected"
    req.decision_note = payload.note.strip()
    req.decided_by = user.id
    req.decided_at = datetime.now(timezone.utc)
    db.commit()
    return {"data": {"request_id": req.id, "status": req.status}}

@router.patch("/admin/toolbank/requests/{request_id}/fulfil")
def fulfil_tool_request(request_id: str, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    req = db.scalar(select(ToolRequest).where(ToolRequest.id == request_id).with_for_update())
    if not req: raise HTTPException(status_code=404, detail="Tool request not found.")
    if req.status != "approved": raise HTTPException(status_code=409, detail="Only approved requests can be fulfilled.")
    stock = db.scalar(select(ToolInventory).where(ToolInventory.product_id == req.product_id).with_for_update())
    if not stock or stock.reserved_quantity < req.quantity:
        raise HTTPException(status_code=409, detail="Reserved stock is inconsistent; investigate before fulfilment.")
    stock.reserved_quantity -= req.quantity
    req.status = "fulfilled"
    req.decided_by = user.id
    req.decided_at = datetime.now(timezone.utc)
    db.commit()
    return {"data": {"request_id": req.id, "status": req.status}}

@router.get("/rewards/me")
def my_rewards(user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    rows = db.scalars(select(RewardLedgerEntry).where(RewardLedgerEntry.mechanic_id == mechanic.id)
                      .order_by(RewardLedgerEntry.created_at.desc())).all()
    redemptions = db.scalars(select(RewardRedemption).where(RewardRedemption.mechanic_id == mechanic.id)
                      .order_by(RewardRedemption.created_at.desc())).all()
    return {"data": {"balance": reward_balance(db, mechanic.id),
        "ledger": [{"entry_id": x.id, "type": x.entry_type, "points": x.points,
                    "description": x.description, "created_at": x.created_at} for x in rows],
        "redemptions": [{"redemption_id": x.id, "reward_name": x.reward_name, "points_cost": x.points_cost,
                         "status": x.status, "decision_note": x.decision_note} for x in redemptions]}}

@router.post("/rewards/redemptions", status_code=201)
def request_redemption(payload: RedemptionCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    if reward_balance(db, mechanic.id) < payload.points_cost:
        raise HTTPException(status_code=409, detail="Insufficient reward points.")
    item = RewardRedemption(mechanic_id=mechanic.id, reward_name=payload.reward_name.strip(),
                            points_cost=payload.points_cost)
    db.add(item); db.commit()
    return {"data": {"redemption_id": item.id, "status": item.status,
                     "message": "Redemption submitted; points are deducted only after approval."}}

@router.get("/admin/rewards/redemptions/pending")
def pending_redemptions(user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    rows = db.scalars(select(RewardRedemption).where(RewardRedemption.status == "pending")
                      .order_by(RewardRedemption.created_at)).all()
    return {"data": [{"redemption_id": x.id, "mechanic_id": x.mechanic_id,
        "mechanic_code": db.get(Mechanic, x.mechanic_id).mechanic_code,
        "reward_name": x.reward_name, "points_cost": x.points_cost} for x in rows]}

@router.patch("/admin/rewards/redemptions/{redemption_id}")
def decide_redemption(redemption_id: str, payload: DecisionInput,
                      user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    item = db.scalar(select(RewardRedemption).where(RewardRedemption.id == redemption_id).with_for_update())
    if not item: raise HTTPException(status_code=404, detail="Redemption not found.")
    if item.status != "pending": raise HTTPException(status_code=409, detail="Redemption has already been decided.")
    if payload.approved:
        if reward_balance(db, item.mechanic_id) < item.points_cost:
            raise HTTPException(status_code=409, detail="Insufficient points at approval time.")
        db.add(RewardLedgerEntry(mechanic_id=item.mechanic_id, entry_type="debit",
            points=item.points_cost, source_type="redemption", source_id=item.id,
            description=f"Approved redemption: {item.reward_name}", created_by=user.id))
        item.status = "approved"
    else:
        item.status = "rejected"
    item.decision_note = payload.note.strip()
    item.decided_by = user.id
    item.decided_at = datetime.now(timezone.utc)
    db.commit()
    return {"data": {"redemption_id": item.id, "status": item.status}}

@router.post("/admin/rewards/credits", status_code=201)
def credit_rewards(payload: RewardCreditInput, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    mechanic = db.scalar(select(Mechanic).where(Mechanic.mechanic_code == payload.mechanic_code))
    if not mechanic: raise HTTPException(status_code=404, detail="Mechanic not found.")
    row = RewardLedgerEntry(mechanic_id=mechanic.id, entry_type="credit", points=payload.points,
        source_type=payload.source_type, source_id=payload.source_id,
        description=payload.description.strip(), created_by=user.id)
    db.add(row)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This source has already generated a reward credit.")
    return {"data": {"entry_id": row.id, "mechanic_code": mechanic.mechanic_code,
                     "points_credited": row.points, "balance": reward_balance(db, mechanic.id)}}
