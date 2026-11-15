import httpx
import pytest

from app.services.sms import SmsDeliveryError, TwilioSmsProvider


def test_twilio_provider_returns_receipt_without_logging_credentials(monkeypatch):
    seen = {}
    def fake_post(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return httpx.Response(201, request=httpx.Request("POST", url),
                              json={"sid": "SM1234567890", "status": "queued"})
    monkeypatch.setattr("app.services.sms.httpx.post", fake_post)
    provider = TwilioSmsProvider(
        account_sid="AC123", auth_token="private-token",
        from_number="+15005550006",
    )
    receipt = provider.send("+14155552671", "Test message")
    assert receipt.provider == "twilio"
    assert receipt.message_id == "SM1234567890"
    assert receipt.status == "queued"
    assert seen["auth"] == ("AC123", "private-token")
    assert seen["data"]["To"] == "+14155552671"
    assert seen["data"]["From"] == "+15005550006"
    assert "private-token" not in repr(receipt)


def test_twilio_provider_rejects_failed_http_response(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(401, request=httpx.Request("POST", url))
    monkeypatch.setattr("app.services.sms.httpx.post", fake_post)
    provider = TwilioSmsProvider(
        account_sid="AC123", auth_token="private-token",
        from_number="+15005550006",
    )
    with pytest.raises(SmsDeliveryError):
        provider.send("+14155552671", "Test message")


def test_twilio_provider_rejects_invalid_receipt(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(201, request=httpx.Request("POST", url),
                              json={"sid": "not-a-twilio-sid"})
    monkeypatch.setattr("app.services.sms.httpx.post", fake_post)
    provider = TwilioSmsProvider(
        account_sid="AC123", auth_token="private-token",
        from_number="+15005550006",
    )
    with pytest.raises(SmsDeliveryError):
        provider.send("+14155552671", "Test message")
