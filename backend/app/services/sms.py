from dataclasses import dataclass
import httpx

from app.core.config import settings


class SmsDeliveryError(RuntimeError):
    """Raised when the configured SMS provider cannot accept a message."""


@dataclass(frozen=True)
class SmsReceipt:
    provider: str
    message_id: str
    status: str


class TwilioSmsProvider:
    def __init__(self, *, account_sid: str | None = None, auth_token: str | None = None,
                 from_number: str | None = None, timeout: float = 10.0):
        self.account_sid = account_sid or settings.twilio_account_sid
        self.auth_token = auth_token or settings.twilio_auth_token
        self.from_number = from_number or settings.twilio_from_number
        self.timeout = timeout
        if not all((self.account_sid, self.auth_token, self.from_number)):
            raise SmsDeliveryError("Twilio credentials are not configured.")

    @property
    def messages_url(self) -> str:
        return f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

    def send(self, to_number: str, body: str) -> SmsReceipt:
        try:
            response = httpx.post(
                self.messages_url,
                data={"To": to_number, "From": self.from_number, "Body": body},
                auth=(self.account_sid, self.auth_token),
                timeout=httpx.Timeout(self.timeout, connect=min(3.0, self.timeout)),
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SmsDeliveryError("Twilio did not accept the SMS request.") from exc
        if not isinstance(payload, dict):
            raise SmsDeliveryError("Twilio returned an invalid message receipt.")
        message_id = payload.get("sid")
        if not isinstance(message_id, str) or not message_id.startswith("SM"):
            raise SmsDeliveryError("Twilio returned an invalid message receipt.")
        return SmsReceipt(
            provider="twilio",
            message_id=message_id,
            status=str(payload.get("status") or "accepted"),
        )


def get_sms_provider():
    if settings.sms_provider == "twilio":
        return TwilioSmsProvider()
    raise SmsDeliveryError("SMS delivery is not configured.")
