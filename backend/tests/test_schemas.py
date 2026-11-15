import pytest
from pydantic import ValidationError
from app.schemas.auth import OTPRequest, MechanicRegistration

def test_phone_requires_e164():
    assert OTPRequest(phone_e164="+919876543210").phone_e164.startswith("+")
    with pytest.raises(ValidationError):
        OTPRequest(phone_e164="9876543210")

def test_non_stockist_advocate_is_valid():
    payload = MechanicRegistration(
        phone_e164="+919876543210", display_name="Demo Mechanic", shop_name="Demo Tyres",
        shop_type="puncture_shop", address_text="12 Demo Road", city="Kolkata", state="West Bengal",
        experience_years=5, languages=["Bengali", "English"],
        participation_type="non_stockist_advocate", location_consent=False,
        consent_policy_version="v1"
    )
    assert payload.participation_type == "non_stockist_advocate"
