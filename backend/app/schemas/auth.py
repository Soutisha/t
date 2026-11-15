from pydantic import BaseModel, Field, field_validator
import re

class OTPRequest(BaseModel):
    phone_e164: str = Field(min_length=8, max_length=16)
    @field_validator("phone_e164")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
            raise ValueError("Use E.164 format, for example +919876543210")
        return value

class OTPVerify(BaseModel):
    phone_e164: str
    code: str = Field(min_length=6, max_length=6)

class MechanicRegistration(BaseModel):
    phone_e164: str
    display_name: str = Field(min_length=2, max_length=120)
    shop_name: str = Field(min_length=2, max_length=160)
    shop_type: str = Field(min_length=2, max_length=50)
    address_text: str = Field(min_length=5, max_length=1000)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    experience_years: int = Field(ge=0, le=70)
    languages: list[str] = Field(min_length=1, max_length=10)
    service_categories: list[str] = Field(default_factory=list, max_length=20)
    participation_type: str = Field(pattern="^(stockist|non_stockist_advocate|interested|training_participant)$")
    location_consent: bool = False
    consent_policy_version: str = Field(min_length=1, max_length=30)

class UserSummary(BaseModel):
    id: str
    phone_e164: str
    display_name: str
    status: str
    roles: list[str]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary
