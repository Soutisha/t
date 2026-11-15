import base64, json, time
from fastapi.testclient import TestClient
from app.core.security import create_access_token, decode_access_token
from app.core.config import settings
from app.main import app
from app.db.base import Base
from app.db.session import engine

def test_jwt_has_issuer_audience_and_rejects_wrong_signature():
    token=create_access_token("user-123",["mechanic"])
    claims=decode_access_token(token)
    assert claims["iss"]==settings.jwt_issuer
    assert claims["aud"]==settings.jwt_audience
    parts=token.split(".")
    tampered=parts[0]+"."+parts[1]+"."+base64.urlsafe_b64encode(b"wrong").decode().rstrip("=")
    try:
        decode_access_token(tampered)
        assert False, "tampered token must be rejected"
    except ValueError:
        pass

def test_security_headers_and_request_id_are_added():
    with TestClient(app) as client:
        response=client.get("/health/live")
    assert response.status_code==200
    assert response.headers.get("X-Request-ID")
    assert response.headers["X-Content-Type-Options"]=="nosniff"
    assert response.headers["X-Frame-Options"]=="DENY"
    assert response.headers["Referrer-Policy"]=="no-referrer"

def test_unverified_mobile_cannot_register_mechanic():
    with TestClient(app) as client:
        response=client.post("/api/v1/onboarding/mechanics",json={
            "phone_e164":"+917000000091","display_name":"Test Mechanic",
            "shop_type":"tyre_shop","experience_years":2,"languages":["English"],
            "service_categories":["tyres"],"participation_type":"interested",
            "shop_name":"Test Shop","address_text":"Main Road","city":"Kolkata",
            "state":"West Bengal","location_consent":False,"consent_policy_version":"1.0"
        })
    assert response.status_code==401


def test_production_settings_reject_weak_secrets_and_dev_otp():
    from pydantic import ValidationError
    from app.core.config import Settings
    try:
        Settings(app_env="production", otp_dev_return_code=True,
                 jwt_secret="weak", client_fingerprint_secret="weak", redis_url="redis://localhost:6379/0",
                 cors_origins="https://portal.example.com", sms_provider="twilio",
                 twilio_account_sid="ACtest", twilio_auth_token="token", twilio_from_number="+15005550006",
        metrics_token="m" * 48, object_storage_backend="s3",
        s3_bucket="pitstop-private", s3_access_key_id="pitstop-api",
        s3_secret_access_key="s" * 48)
        assert False, "weak production configuration must fail"
    except ValidationError:
        pass
    configured=Settings(app_env="production", otp_dev_return_code=False,
        jwt_secret="j"*48, client_fingerprint_secret="f"*48, redis_url="redis://localhost:6379/0",
        cors_origins="https://portal.example.com", sms_provider="twilio",
        twilio_account_sid="ACtest", twilio_auth_token="token", twilio_from_number="+15005550006",
        metrics_token="m" * 48, object_storage_backend="s3",
        s3_bucket="pitstop-private", s3_access_key_id="pitstop-api",
        s3_secret_access_key="s" * 48)
    assert configured.app_env=="production"
