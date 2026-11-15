import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

def hash_secret(value: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt, 310_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"

def verify_secret(value: str, encoded: str) -> bool:
    try:
        salt_b64, digest_b64 = encoded.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", value.encode(), salt, 310_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def create_access_token(subject: str, roles: list[str]) -> str:
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({
        "sub": subject, "roles": roles, "iat": now,
        "exp": now + settings.jwt_ttl_minutes * 60,
        "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
        "jti": secrets.token_urlsafe(16)
    }, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(signature)}"

def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header, payload, signature = token.split(".")
        header_data = json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
        if header_data.get("alg") != "HS256" or header_data.get("typ") != "JWT":
            raise ValueError("Unsupported token algorithm")
        signing_input = f"{header}.{payload}".encode()
        expected = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
        supplied = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("Invalid signature")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        now = int(time.time())
        if int(claims["exp"]) <= now or int(claims.get("iat", 0)) > now + 30:
            raise ValueError("Expired or not-yet-valid token")
        if claims.get("iss") != settings.jwt_issuer or claims.get("aud") != settings.jwt_audience:
            raise ValueError("Invalid token issuer or audience")
        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise ValueError("Invalid token subject")
        return claims
    except Exception as exc:
        raise ValueError("Invalid or expired access token") from exc

def utcnow() -> datetime:
    return datetime.now(timezone.utc)
