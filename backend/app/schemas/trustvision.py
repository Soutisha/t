from pydantic import BaseModel, Field

class FraudCaseDecision(BaseModel):
    decision: str = Field(pattern="^(cleared|confirmed_fraud|needs_information)$")
    reviewer_note: str = Field(default="", max_length=2000)

class OCRCorrection(BaseModel):
    invoice_number: str | None = Field(default=None, max_length=120)
    dealer_name: str | None = Field(default=None, max_length=160)
    invoice_date: str | None = Field(default=None, max_length=40)
    product_name: str | None = Field(default=None, max_length=160)
    sku: str | None = Field(default=None, max_length=80)
    quantity: int | None = Field(default=None, ge=0, le=100000)
    total_amount: str | None = Field(default=None, max_length=60)
