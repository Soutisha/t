from datetime import datetime, timezone
import json
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.models import Mechanic, User
from app.models.passport import MechanicAdvocacyMilestone
from app.models.advocacy import (
    AdvocacyProduct, AdvocacyRecommendation, FitmentRecord, AdvocacyEvidence,
    DealerReferral, StockistRegistration, DealerSalesRecord, DealerStockingRecord,
    CustomerFeedback, AdvocacyCampaign, CampaignParticipation, AdvocacyEventLedger
)
from app.schemas.advocacy import (
    ProductCreate, RecommendationCreate, FitmentCreate, DealerReferralCreate, EvidenceInput,
    StockistRegistrationCreate, CustomerFeedbackCreate, CampaignCreate,
    VerificationDecision, DealerSalesCreate, DealerStockingCreate
)
from app.services.advocacy import (
    new_referral_code, product_qr_token, verify_product_qr_token, record_event
)

router = APIRouter()
ADMIN = ("administrator", "eurogrip_admin")
DEALER = ("dealer", "distributor", "administrator", "eurogrip_admin")

def mechanic_for(user: User, db: Session) -> Mechanic:
    mechanic = db.scalar(select(Mechanic).where(Mechanic.user_id == user.id))
    if not mechanic:
        raise HTTPException(status_code=404, detail="Mechanic profile not found.")
    return mechanic

def active_product(product_id: str, db: Session) -> AdvocacyProduct:
    product = db.get(AdvocacyProduct, product_id)
    if not product or not product.active:
        raise HTTPException(status_code=404, detail="Product not found or inactive.")
    return product

def add_evidence(db: Session, user: User, payloads, *, fitment_id=None, recommendation_id=None):
    for item in payloads:
        db.add(AdvocacyEvidence(fitment_id=fitment_id, recommendation_id=recommendation_id,
            evidence_type=item.evidence_type, storage_reference=item.storage_reference,
            confidence=item.confidence, submitted_by=user.id))

@router.get("/advocacy/products")
def products(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AdvocacyProduct).where(AdvocacyProduct.active.is_(True))
                      .order_by(AdvocacyProduct.product_name)).all()
    return {"data": [{"product_id": p.id, "sku": p.sku, "product_name": p.product_name,
        "description": p.description, "tyre_type": p.tyre_type,
        "specifications_json": p.specifications_json} for p in rows]}

@router.post("/admin/advocacy/products", status_code=201)
def create_product(payload: ProductCreate, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    if db.scalar(select(AdvocacyProduct).where(AdvocacyProduct.sku == payload.sku)):
        raise HTTPException(status_code=409, detail="Product SKU already exists.")
    try:
        specifications = json.loads(payload.specifications_json)
        if not isinstance(specifications, dict):
            raise ValueError("specifications must be a JSON object")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=422, detail="specifications_json must be a valid JSON object.")
    product = AdvocacyProduct(sku=payload.sku, product_name=payload.product_name,
        description=payload.description, tyre_type=payload.tyre_type,
        specifications_json=json.dumps(specifications, separators=(",", ":")))
    db.add(product); db.commit()
    return {"data": {"product_id": product.id, "sku": product.sku, "product_name": product.product_name}}

@router.get("/admin/advocacy/products/{product_id}/qr")
def product_qr(product_id: str, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    product = active_product(product_id, db)
    token = product_qr_token(product.id)
    return {"data": {"product_id": product.id, "sku": product.sku,
        "signed_token": token, "verification_path": f"/api/v1/advocacy/products/identify/{token}"}}

@router.get("/admin/advocacy/products/{product_id}/qr.png")
def product_qr_png(product_id: str, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    product = active_product(product_id, db)
    token = product_qr_token(product.id)
    try:
        import qrcode
        qr = qrcode.make(f"{settings.public_api_base_url.rstrip('/')}/api/v1/advocacy/products/identify/{token}")
        output = BytesIO()
        qr.save(output, format="PNG")
        return Response(content=output.getvalue(), media_type="image/png",
                        headers={"Cache-Control": "no-store"})
    except ImportError:
        raise HTTPException(status_code=503, detail="QR image dependency is unavailable.")

@router.get("/advocacy/products/identify/{token}")
def identify_product(token: str, db: Session = Depends(get_db)):
    product_id = verify_product_qr_token(token)
    if not product_id:
        raise HTTPException(status_code=404, detail="Invalid product QR token.")
    product = db.get(AdvocacyProduct, product_id)
    if not product or not product.active:
        raise HTTPException(status_code=404, detail="Product is not registered or is inactive.")
    return {"data": {"valid": True, "product_id": product.id, "sku": product.sku,
        "product_name": product.product_name, "tyre_type": product.tyre_type}}

@router.post("/advocacy/recommendations", status_code=201)
def create_recommendation(payload: RecommendationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    product = active_product(payload.product_id, db)
    recommendation = AdvocacyRecommendation(mechanic_id=mechanic.id, product_id=product.id,
        referral_code=new_referral_code(), customer_reference_hash=payload.customer_reference_hash,
        referral_source=payload.referral_source, notes=payload.notes.strip(), status="submitted")
    db.add(recommendation); db.flush()
    record_event(db, mechanic_id=mechanic.id, product_id=product.id,
        event_type="recommendation", source_id=recommendation.id,
        referral_source=payload.referral_source, location_reference=payload.location_label, verification_status="submitted")
    db.commit()
    return {"data": {"recommendation_id": recommendation.id,
        "referral_code": recommendation.referral_code, "product": product.product_name,
        "status": recommendation.status,
        "message": "Recommendation recorded; it is not counted as a fitment or sale."}}

@router.post("/advocacy/recommendations/{recommendation_id}/evidence", status_code=201)
def recommendation_evidence(recommendation_id: str, payload: list[EvidenceInput], user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    rec = db.get(AdvocacyRecommendation, recommendation_id)
    if not rec or rec.mechanic_id != mechanic.id:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    if len(payload) > 10: raise HTTPException(status_code=422, detail="Maximum 10 evidence references.")
    # Evidence references are metadata only; binary uploads are handled in a later secure file service.
    for item in payload:
        db.add(AdvocacyEvidence(recommendation_id=rec.id, evidence_type=item.evidence_type,
            storage_reference=item.storage_reference, confidence=item.confidence, submitted_by=user.id))
    db.commit()
    return {"data": {"recommendation_id": rec.id, "evidence_count": len(payload)}}

@router.get("/advocacy/me/events")
def my_advocacy_events(user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    rows = db.scalars(select(AdvocacyEventLedger).where(AdvocacyEventLedger.mechanic_id == mechanic.id)
                      .order_by(AdvocacyEventLedger.event_date.desc())).all()
    return {"data": [{"event_id": x.id, "event_type": x.event_type, "source_id": x.source_id,
        "product_id": x.product_id, "verification_status": x.verification_status,
        "confidence": x.confidence, "reward_eligible": x.reward_eligible,
        "event_date": x.event_date} for x in rows]}

@router.post("/advocacy/fitments", status_code=201)
def create_fitment(payload: FitmentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    product = active_product(payload.product_id, db)
    if payload.recommendation_id:
        rec = db.get(AdvocacyRecommendation, payload.recommendation_id)
        if not rec or rec.mechanic_id != mechanic.id or rec.product_id != product.id:
            raise HTTPException(status_code=422, detail="Linked recommendation must belong to this mechanic and product.")
    fitment = FitmentRecord(mechanic_id=mechanic.id, product_id=product.id,
        recommendation_id=payload.recommendation_id, vehicle_reference=payload.vehicle_reference,
        fitment_date=payload.fitment_date or datetime.now(timezone.utc),
        evidence_confidence=max([x.confidence for x in payload.evidence], key=lambda v: {"low":0,"medium":1,"high":2}[v]) if payload.evidence else "low",
        verification_status="pending")
    db.add(fitment); db.flush()
    add_evidence(db, user, payload.evidence, fitment_id=fitment.id)
    record_event(db, mechanic_id=mechanic.id, product_id=product.id,
        event_type="fitment", source_id=fitment.id, verification_status="pending",
        confidence=fitment.evidence_confidence, location_reference=payload.location_label, event_date=fitment.fitment_date)
    db.commit()
    return {"data": {"fitment_id": fitment.id, "status": "pending",
        "evidence_count": len(payload.evidence),
        "message": "Fitment awaits review; recommendation and fitment remain separate records."}}

@router.post("/advocacy/dealer-referrals", status_code=201)
def create_dealer_referral(payload: DealerReferralCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    if payload.recommendation_id:
        rec = db.get(AdvocacyRecommendation, payload.recommendation_id)
        if not rec or rec.mechanic_id != mechanic.id:
            raise HTTPException(status_code=422, detail="Recommendation does not belong to this mechanic.")
    item = DealerReferral(mechanic_id=mechanic.id, recommendation_id=payload.recommendation_id,
        dealer_reference=payload.dealer_reference, dealer_name=payload.dealer_name,
        notes=payload.notes.strip())
    db.add(item); db.flush()
    record_event(db, mechanic_id=mechanic.id, product_id=None,
        event_type="dealer_referral", source_id=item.id, referral_source="mechanic",
        dealer_reference=payload.dealer_reference, verification_status="submitted")
    return_id = item.id
    db.commit()
    return {"data": {"dealer_referral_id": return_id, "status": "submitted"}}

@router.post("/advocacy/stockist-registrations", status_code=201)
def register_stockist(payload: StockistRegistrationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    # Optional and separate: non-stockist advocates can use all recommendation/fitment workflows.
    item = StockistRegistration(mechanic_id=mechanic.id, shop_reference=payload.shop_reference,
        dealer_reference=payload.dealer_reference, notes=payload.notes.strip())
    db.add(item); db.flush()
    record_event(db, mechanic_id=mechanic.id, product_id=None,
        event_type="stockist_registration", source_id=item.id, verification_status="pending")
    db.commit()
    return {"data": {"registration_id": item.id, "status": "pending",
        "message": "Stockist status is not active until verified."}}

@router.post("/advocacy/customer-feedback", status_code=201)
def customer_feedback(payload: CustomerFeedbackCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    if payload.recommendation_id:
        rec = db.get(AdvocacyRecommendation, payload.recommendation_id)
        if not rec or rec.mechanic_id != mechanic.id:
            raise HTTPException(status_code=422, detail="Recommendation does not belong to this mechanic.")
    row = CustomerFeedback(mechanic_id=mechanic.id, recommendation_id=payload.recommendation_id,
        rating=payload.rating, feedback_text=payload.feedback_text.strip())
    db.add(row); db.commit()
    return {"data": {"feedback_id": row.id, "verification_status": row.verification_status}}

@router.get("/advocacy/campaigns")
def campaigns(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AdvocacyCampaign).where(AdvocacyCampaign.active.is_(True))
                      .order_by(AdvocacyCampaign.starts_at)).all()
    return {"data": [{"campaign_id": x.id, "campaign_code": x.campaign_code, "title": x.title,
        "description": x.description, "starts_at": x.starts_at, "ends_at": x.ends_at} for x in rows]}

@router.post("/admin/advocacy/campaigns", status_code=201)
def create_campaign(payload: CampaignCreate, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    if payload.ends_at <= payload.starts_at: raise HTTPException(status_code=422, detail="Campaign end must follow its start.")
    item = AdvocacyCampaign(campaign_code=payload.campaign_code, title=payload.title,
        description=payload.description, starts_at=payload.starts_at, ends_at=payload.ends_at,
        active=payload.active)
    db.add(item)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Campaign code already exists.")
    return {"data": {"campaign_id": item.id, "campaign_code": item.campaign_code}}

@router.post("/advocacy/campaigns/{campaign_id}/participation", status_code=201)
def join_campaign(campaign_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mechanic = mechanic_for(user, db)
    campaign = db.get(AdvocacyCampaign, campaign_id)
    if not campaign or not campaign.active: raise HTTPException(status_code=404, detail="Active campaign not found.")
    row = CampaignParticipation(campaign_id=campaign.id, mechanic_id=mechanic.id)
    db.add(row); db.flush()
    record_event(db, mechanic_id=mechanic.id, product_id=None,
        event_type="campaign_participation", source_id=row.id, verification_status="registered")
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="You have already joined this campaign.")
    return {"data": {"participation_id": row.id, "status": row.status}}

@router.get("/admin/advocacy/review-queue")
def review_queue(user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    recs = db.scalars(select(AdvocacyRecommendation).where(AdvocacyRecommendation.status == "submitted")).all()
    fits = db.scalars(select(FitmentRecord).where(FitmentRecord.verification_status == "pending")).all()
    stockists = db.scalars(select(StockistRegistration).where(StockistRegistration.status == "pending")).all()
    sales = db.scalars(select(DealerSalesRecord).where(DealerSalesRecord.verification_status == "dealer_submitted")).all()
    stock = db.scalars(select(DealerStockingRecord).where(DealerStockingRecord.verification_status == "dealer_submitted")).all()
    return {"data": {"recommendations": [{"id": x.id, "mechanic_id": x.mechanic_id, "product": x.product.product_name} for x in recs],
        "fitments": [{"id": x.id, "mechanic_id": x.mechanic_id, "product": x.product.product_name,
                      "confidence": x.evidence_confidence} for x in fits],
        "stockist_registrations": [{"id": x.id, "mechanic_id": x.mechanic_id, "shop_reference": x.shop_reference} for x in stockists],
        "dealer_sales": [{"id": x.id, "invoice_reference": x.invoice_reference, "quantity": x.quantity} for x in sales],
        "dealer_stocking": [{"id": x.id, "stocking_reference": x.stocking_reference, "quantity": x.quantity} for x in stock]}}

@router.patch("/admin/advocacy/recommendations/{item_id}/verification")
def verify_recommendation(item_id: str, payload: VerificationDecision, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    item = db.get(AdvocacyRecommendation, item_id)
    if not item: raise HTTPException(status_code=404, detail="Recommendation not found.")
    if item.status != "submitted": raise HTTPException(status_code=409, detail="Recommendation has already been reviewed.")
    item.status = "verified" if payload.approved else "rejected"
    event = db.scalar(select(AdvocacyEventLedger).where(
        AdvocacyEventLedger.event_type == "recommendation", AdvocacyEventLedger.source_id == item.id))
    if event:
        event.verification_status = item.status
        event.confidence = "high" if payload.approved else event.confidence
    if payload.approved:
        db.add(MechanicAdvocacyMilestone(mechanic_id=item.mechanic_id,
            milestone_code="recommendation_verified", source_id=item.id,
            description="Administrator-verified product recommendation", verified=True))
    db.commit()
    return {"data": {"recommendation_id": item.id, "status": item.status}}

@router.patch("/admin/advocacy/fitments/{item_id}/verification")
def verify_fitment(item_id: str, payload: VerificationDecision, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    item = db.get(FitmentRecord, item_id)
    if not item: raise HTTPException(status_code=404, detail="Fitment not found.")
    if item.verification_status != "pending": raise HTTPException(status_code=409, detail="Fitment has already been reviewed.")
    item.verification_status = "verified" if payload.approved else "rejected"
    item.reviewer_id = user.id; item.reviewer_note = payload.note.strip()
    item.reward_eligible = payload.approved
    event = db.scalar(select(AdvocacyEventLedger).where(
        AdvocacyEventLedger.event_type == "fitment", AdvocacyEventLedger.source_id == item.id))
    if event:
        event.verification_status = item.verification_status
        event.reward_eligible = item.reward_eligible
        event.confidence = "high" if payload.approved else event.confidence
    if payload.approved:
        db.add(MechanicAdvocacyMilestone(mechanic_id=item.mechanic_id,
            milestone_code="fitment_verified", source_id=item.id,
            description="Administrator-verified tyre fitment", verified=True))
    db.commit()
    return {"data": {"fitment_id": item.id, "verification_status": item.verification_status,
                     "reward_eligible": item.reward_eligible}}

@router.patch("/admin/advocacy/stockist-registrations/{item_id}/verification")
def verify_stockist(item_id: str, payload: VerificationDecision, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    item = db.get(StockistRegistration, item_id)
    if not item: raise HTTPException(status_code=404, detail="Stockist registration not found.")
    if item.status != "pending": raise HTTPException(status_code=409, detail="Registration has already been reviewed.")
    item.status = "verified" if payload.approved else "rejected"
    item.verified_by = user.id; item.verified_at = datetime.now(timezone.utc) if payload.approved else None
    event = db.scalar(select(AdvocacyEventLedger).where(
        AdvocacyEventLedger.event_type == "stockist_registration", AdvocacyEventLedger.source_id == item.id))
    if event: event.verification_status = item.status
    if payload.approved:
        db.add(MechanicAdvocacyMilestone(mechanic_id=item.mechanic_id,
            milestone_code="stockist_verified", source_id=item.id,
            description="Administrator-verified stockist registration", verified=True))
    db.commit()
    return {"data": {"registration_id": item.id, "status": item.status}}

@router.post("/dealer/advocacy/sales-records", status_code=201)
def dealer_sales(payload: DealerSalesCreate, user: User = Depends(require_roles(*DEALER)), db: Session = Depends(get_db)):
    product = active_product(payload.product_id, db)
    rec = None
    if payload.recommendation_id:
        rec = db.get(AdvocacyRecommendation, payload.recommendation_id)
        if not rec or rec.product_id != product.id:
            raise HTTPException(status_code=422, detail="Recommendation does not match the selected product.")
    row = DealerSalesRecord(dealer_user_id=user.id, dealer_reference=payload.dealer_reference,
        invoice_reference=payload.invoice_reference, recommendation_id=payload.recommendation_id,
        product_id=product.id, quantity=payload.quantity, sale_date=payload.sale_date,
        verification_status="dealer_submitted")
    db.add(row); db.flush()
    if rec:
        record_event(db, mechanic_id=rec.mechanic_id, product_id=product.id,
            event_type="sale", source_id=row.id, referral_source="dealer",
            dealer_reference=payload.dealer_reference, event_date=payload.sale_date,
            verification_status="dealer_submitted")
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Invoice reference already submitted by this dealer.")
    return {"data": {"sales_record_id": row.id, "verification_status": row.verification_status,
        "attributed_recommendation_id": rec.id if rec else None}}

@router.post("/dealer/advocacy/stocking-records", status_code=201)
def dealer_stocking(payload: DealerStockingCreate, user: User = Depends(require_roles(*DEALER)), db: Session = Depends(get_db)):
    product = active_product(payload.product_id, db)
    mechanic = db.scalar(select(Mechanic).where(Mechanic.mechanic_code == payload.mechanic_code)) if payload.mechanic_code else None
    if payload.mechanic_code and not mechanic:
        raise HTTPException(status_code=404, detail="Mechanic code not found.")
    row = DealerStockingRecord(dealer_user_id=user.id, dealer_reference=payload.dealer_reference,
        stocking_reference=payload.stocking_reference, mechanic_id=mechanic.id if mechanic else None,
        product_id=product.id, quantity=payload.quantity, stock_date=payload.stock_date,
        verification_status="dealer_submitted")
    db.add(row); db.flush()
    if mechanic:
        record_event(db, mechanic_id=mechanic.id, product_id=product.id,
            event_type="stocking", source_id=row.id, referral_source="dealer",
            dealer_reference=payload.dealer_reference, event_date=payload.stock_date,
            verification_status="dealer_submitted")
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Stocking reference already submitted by this dealer.")
    return {"data": {"stocking_record_id": row.id, "verification_status": row.verification_status,
        "mechanic_attributed": bool(mechanic)}}

@router.patch("/admin/advocacy/dealer-sales/{item_id}/verification")
def verify_dealer_sale(item_id: str, payload: VerificationDecision, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    item = db.get(DealerSalesRecord, item_id)
    if not item: raise HTTPException(status_code=404, detail="Sales record not found.")
    if item.verification_status != "dealer_submitted": raise HTTPException(status_code=409, detail="Sales record already reviewed.")
    item.verification_status = "verified" if payload.approved else "rejected"
    event = db.scalar(select(AdvocacyEventLedger).where(AdvocacyEventLedger.event_type == "sale", AdvocacyEventLedger.source_id == item.id))
    if event: event.verification_status = item.verification_status
    db.commit()
    return {"data": {"sales_record_id": item.id, "verification_status": item.verification_status}}

@router.patch("/admin/advocacy/dealer-stocking/{item_id}/verification")
def verify_dealer_stocking(item_id: str, payload: VerificationDecision, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    item = db.get(DealerStockingRecord, item_id)
    if not item: raise HTTPException(status_code=404, detail="Stocking record not found.")
    if item.verification_status != "dealer_submitted": raise HTTPException(status_code=409, detail="Stocking record already reviewed.")
    item.verification_status = "verified" if payload.approved else "rejected"
    event = db.scalar(select(AdvocacyEventLedger).where(AdvocacyEventLedger.event_type == "stocking", AdvocacyEventLedger.source_id == item.id))
    if event: event.verification_status = item.verification_status
    db.commit()
    return {"data": {"stocking_record_id": item.id, "verification_status": item.verification_status}}
