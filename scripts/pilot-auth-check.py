#!/usr/bin/env python3
"""Exercise OTP login for an existing staging pilot account; SMS send is opt-in."""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request


def post_json(url: str, payload: dict, timeout: float = 15.0):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "EUROGRIP-PITSTOP-Pilot-Auth-Check/1.0",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = "provider/API rejected the request"
        try:
            payload = json.loads(exc.read())
            detail = str(payload.get("detail", detail))
        except Exception:
            pass
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Request failed ({type(exc).__name__}).") from exc


def get_json(url: str, token: str, timeout: float = 15.0):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "EUROGRIP-PITSTOP-Pilot-Auth-Check/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Authenticated profile request returned HTTP {exc.code}.") from exc
    except Exception as exc:
        raise RuntimeError(f"Profile request failed ({type(exc).__name__}).") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Staging base URL, e.g. https://staging.example.org")
    parser.add_argument("--phone", required=True, help="Existing pilot account phone number in E.164 format")
    parser.add_argument("--send-otp", action="store_true", help="Request a real OTP; may incur SMS charges")
    parser.add_argument("--confirm-send", action="store_true", help="Explicitly approve sending one OTP SMS")
    parser.add_argument("--allow-http", action="store_true", help="Allow HTTP only on isolated test networks")
    args = parser.parse_args()
    from urllib.parse import urlparse
    import getpass as gp

    parsed = urlparse(args.base_url)
    if parsed.scheme != "https" and not (args.allow_http and parsed.hostname in ("localhost", "127.0.0.1")):
        print("ERROR: HTTPS is required unless --allow-http is used for localhost.", file=sys.stderr)
        return 2
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", args.phone):
        print("ERROR: --phone must be a valid E.164 number.", file=sys.stderr)
        return 2
    if not args.send_otp or not args.confirm_send:
        print("ERROR: This journey sends an OTP. Supply both --send-otp and --confirm-send.", file=sys.stderr)
        return 2

    base = args.base_url.rstrip("/")
    try:
        status, request_body = post_json(base + "/api/v1/auth/otp/request", {"phone_e164": args.phone})
        if status != 200:
            raise RuntimeError(f"OTP request returned HTTP {status}.")
        data = request_body.get("data", {})
        if data.get("delivery") != "twilio":
            raise RuntimeError("OTP delivery did not report the configured Twilio provider.")
        print("PASS OTP request accepted by the application and Twilio adapter.")
        code = gp.getpass("Enter the OTP received on the pilot device (input hidden): ").strip()
        if not re.fullmatch(r"[0-9]{6}", code):
            raise RuntimeError("OTP must contain exactly six digits.")
        status, login = post_json(base + "/api/v1/auth/otp/verify",
                                  {"phone_e164": args.phone, "code": code})
        token = login.get("data", {}).get("access_token")
        if status != 200 or not token:
            raise RuntimeError("OTP verification did not return an access token.")
        print("PASS OTP verification returned an access token.")
        status, profile = get_json(base + "/api/v1/me", token)
        user = profile.get("data", {})
        if status != 200 or user.get("phone_e164") != args.phone:
            raise RuntimeError("Authenticated profile did not match the pilot account.")
        print("PASS authenticated /me profile matches the pilot account.")
        print("PILOT AUTH JOURNEY PASSED. Token was held in process memory and was not printed or saved.")
        return 0
    except RuntimeError as exc:
        print(f"PILOT AUTH JOURNEY FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
