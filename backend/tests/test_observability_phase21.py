from fastapi.testclient import TestClient
from fastapi import HTTPException, Request
import pytest
from pydantic import ValidationError
from app.main import app, metrics
from app.core.config import settings, Settings


def test_metrics_endpoint_exposes_request_counters_in_development():
    previous = settings.app_env
    settings.app_env = "development"
    try:
        with TestClient(app) as client:
            client.get("/health/live")
            response = client.get("/internal/metrics")
        assert response.status_code == 200
        assert "pitstop_http_requests_total" in response.text
        assert 'path="/health/live"' in response.text
    finally:
        settings.app_env = previous


def test_production_settings_require_a_metrics_bearer_token():
    base = dict(
        app_env="production", otp_dev_return_code=False,
        jwt_secret="j" * 48, client_fingerprint_secret="f" * 48,
        redis_url="redis://localhost:6379/0",
        cors_origins="https://portal.example.org", sms_provider="twilio",
        twilio_account_sid="ACtest", twilio_auth_token="token",
        twilio_from_number="+15005550006",
        object_storage_backend="s3", s3_bucket="pitstop-private",
        s3_access_key_id="pitstop-api", s3_secret_access_key="s" * 48,
    )
    try:
        Settings(**base)
        assert False, "production must reject missing metrics token"
    except ValidationError:
        pass
    configured = Settings(**base, metrics_token="m" * 48)
    assert configured.metrics_token == "m" * 48


def test_metrics_handler_enforces_production_bearer_token():
    previous_env, previous_token = settings.app_env, settings.metrics_token
    settings.app_env, settings.metrics_token = "production", "t" * 48
    def make_request(auth=None):
        headers = [] if auth is None else [(b"authorization", auth.encode())]
        return Request({
            "type": "http", "method": "GET", "path": "/internal/metrics",
            "headers": headers, "query_string": b"", "scheme": "http",
            "server": ("test", 80), "client": ("127.0.0.1", 1234),
        })
    try:
        with pytest.raises(HTTPException) as error:
            metrics(make_request())
        assert error.value.status_code == 401
        output = metrics(make_request("Bearer " + settings.metrics_token))
        assert "pitstop_http_requests_total" in output
    finally:
        settings.app_env, settings.metrics_token = previous_env, previous_token


def test_production_settings_reject_missing_minio_application_identity():
    base = dict(
        app_env="production", otp_dev_return_code=False,
        jwt_secret="j" * 48, client_fingerprint_secret="f" * 48,
        redis_url="redis://localhost:6379/0",
        cors_origins="https://portal.example.org", sms_provider="twilio",
        twilio_account_sid="ACtest", twilio_auth_token="token",
        twilio_from_number="+15005550006", metrics_token="m" * 48,
        object_storage_backend="s3", s3_bucket="pitstop-private",
    )
    with pytest.raises(ValidationError):
        Settings(**base)
