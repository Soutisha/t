from pydantic import BaseModel, Field

class ToolProductCreate(BaseModel):
    sku: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="general", max_length=80)
    points_cost: int = Field(default=0, ge=0, le=1000000)
    initial_quantity: int = Field(default=0, ge=0, le=100000)

class ToolRequestCreate(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=20)
    reason: str = Field(min_length=5, max_length=1000)

class DecisionInput(BaseModel):
    approved: bool
    note: str = Field(default="", max_length=1000)

class RewardCreditInput(BaseModel):
    mechanic_code: str = Field(min_length=3, max_length=32)
    points: int = Field(gt=0, le=100000)
    source_type: str = Field(min_length=2, max_length=40)
    source_id: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=3, max_length=500)

class RedemptionCreate(BaseModel):
    reward_name: str = Field(min_length=2, max_length=140)
    points_cost: int = Field(gt=0, le=1000000)
