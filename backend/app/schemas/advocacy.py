from datetime import datetime
from pydantic import BaseModel, Field

class ProductCreate(BaseModel):
    sku: str = Field(min_length=2, max_length=60)
    product_name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=3000)
    tyre_type: str = Field(default="", max_length=80)
    specifications_json: str = "{}"

class RecommendationCreate(BaseModel):
    product_id: str
    customer_reference_hash: str | None = Field(default=None, max_length=128)
    referral_source: str = Field(default="mechanic", max_length=40)
    notes: str = Field(default="", max_length=1000)
    location_label: str = Field(default="", max_length=140)

class EvidenceInput(BaseModel):
    evidence_type: str = Field(min_length=2, max_length=40)
    storage_reference: str = Field(min_length=5, max_length=500)
    confidence: str = Field(default="low", pattern="^(low|medium|high)$")

class FitmentCreate(BaseModel):
    product_id: str
    recommendation_id: str | None = None
    vehicle_reference: str = Field(default="", max_length=100)
    location_label: str = Field(default="", max_length=140)
    fitment_date: datetime | None = None
    evidence: list[EvidenceInput] = Field(default_factory=list, max_length=10)

class DealerReferralCreate(BaseModel):
    recommendation_id: str | None = None
    dealer_reference: str = Field(min_length=2, max_length=100)
    dealer_name: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=1000)

class StockistRegistrationCreate(BaseModel):
    shop_reference: str = Field(default="", max_length=100)
    dealer_reference: str | None = Field(default=None, max_length=100)
    notes: str = Field(default="", max_length=1000)

class CustomerFeedbackCreate(BaseModel):
    recommendation_id: str | None = None
    rating: int = Field(ge=1, le=5)
    feedback_text: str = Field(default="", max_length=1500)

class CampaignCreate(BaseModel):
    campaign_code: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    starts_at: datetime
    ends_at: datetime
    active: bool = False

class VerificationDecision(BaseModel):
    approved: bool
    note: str = Field(default="", max_length=1000)

class DealerSalesCreate(BaseModel):
    dealer_reference: str = Field(min_length=2, max_length=100)
    invoice_reference: str = Field(min_length=2, max_length=100)
    recommendation_id: str | None = None
    product_id: str
    quantity: int = Field(gt=0, le=100000)
    sale_date: datetime

class DealerStockingCreate(BaseModel):
    dealer_reference: str = Field(min_length=2, max_length=100)
    stocking_reference: str = Field(min_length=2, max_length=100)
    mechanic_code: str | None = Field(default=None, max_length=32)
    product_id: str
    quantity: int = Field(gt=0, le=100000)
    stock_date: datetime
