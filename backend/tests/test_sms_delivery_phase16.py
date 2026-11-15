from types import SimpleNamespace
import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.models import OTPChallenge
from app.services.auth import request_otp


def test_twilio_sms_delivery_is_invoked_without_exposing_otp(monkeypatch):
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "otp_dev_return_code", False)
    monkeypatch.setattr(settings, "sms_provider", "twilio")
    monkeypatch.setattr(settings, "twilio_account_sid", "AC00000000000000000000000000000000")
    monkeypatch.setattr(settings, "twilio_auth_token", "test-auth-token")
    monkeypatch.setattr(settings, "twilio_from_number", "+15005550006")
    calls = []
    def fake_post(url, data, auth, timeout):
        calls.append((url, data, auth, timeout))
        request = httpx.Request("POST", url)
        return httpx.Response(201, request=request, json={"sid": "SM1234567890", "status": "queued"})
    monkeypatch.setattr(httpx, "post", fake_post)
    db = SessionLocal()
    try:
        challenge_id, dev_code = request_otp(db, "+919876543210")
        assert challenge_id
        assert dev_code is None
        assert len(calls) == 1
        assert calls[0][1]["To"] == "+919876543210"
        row = db.scalar(select(OTPChallenge).where(OTPChallenge.id == challenge_id))
        assert row is not None and row.code_hash
        assert "Body" in calls[0][1]
    finally:
        db.close()


def test_otp_fails_closed_when_sms_provider_is_missing(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "otp_dev_return_code", False)
    monkeypatch.setattr(settings, "sms_provider", "none")
    monkeypatch.setattr(settings, "twilio_account_sid", "")
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc:
            request_otp(db, "+919876543211")
        assert exc.value.status_code == 503
    finally:
        db.close()


def test_twilio_delivery_error_does_not_create_challenge(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "otp_dev_return_code", False)
    monkeypatch.setattr(settings, "sms_provider", "twilio")
    monkeypatch.setattr(settings, "twilio_account_sid", "AC00000000000000000000000000000000")
    monkeypatch.setattr(settings, "twilio_auth_token", "test-auth-token")
    monkeypatch.setattr(settings, "twilio_from_number", "+15005550006")
    def failed_post(*args, **kwargs):
        request = httpx.Request("POST", "https://api.twilio.com")
        response = httpx.Response(400, request=request)
        raise httpx.HTTPStatusError("bad request", request=request, response=response)
    monkeypatch.setattr(httpx, "post", failed_post)
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc:
            request_otp(db, "+919876543212")
        assert exc.value.status_code == 502
        assert db.scalar(select(OTPChallenge).where(OTPChallenge.phone_e164 == "+919876543212")) is None
    finally:
        db.close()
