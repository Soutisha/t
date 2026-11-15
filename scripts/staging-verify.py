#!/usr/bin/env python3
"""Verify a deployed staging web gateway and API readiness without mutating data."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


class VerificationError(RuntimeError):
    pass


def request(url: str, timeout: float = 8.0):
    req = urllib.request.Request(url, headers={"User-Agent": "EUROGRIP-PITSTOP-Staging-Check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read()
            headers = {key.lower(): value for key, value in response.headers.items()}
            return response.status, headers, body
    except urllib.error.HTTPError as exc:
        raise VerificationError(f"{url} returned HTTP {exc.code}") from exc
    except Exception as exc:
        raise VerificationError(f"{url} could not be reached ({type(exc).__name__})") from exc


def verify(base_url: str, *, require_https: bool = True, api_url: str | None = None):
    base = base_url.rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise VerificationError("Base URL must be an absolute HTTP(S) URL.")
    if require_https and parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise VerificationError("Staging URL must use HTTPS. Use --allow-http only for an isolated test environment.")

    checks = []
    def passed(name: str, detail: str):
        checks.append((name, True, detail))
        print(f"PASS {name}: {detail}")

    def run(name, fn):
        try:
            detail = fn()
            passed(name, detail)
            return True
        except VerificationError as exc:
            checks.append((name, False, str(exc)))
            print(f"FAIL {name}: {exc}")
            return False

    def web_health():
        status, _, body = request(base + "/healthz")
        if status != 200 or body.strip().lower() != b"ok":
            raise VerificationError("Expected HTTP 200 and body 'ok'.")
        return "HTTP 200"

    api_base = (api_url or base).rstrip("/")
    def live():
        status, headers, body = request(api_base + "/health/live")
        if status != 200:
            raise VerificationError(f"Expected HTTP 200, got {status}.")
        try:
            payload = json.loads(body)
        except ValueError as exc:
            raise VerificationError("Liveness endpoint did not return JSON.") from exc
        if payload.get("status") != "ok":
            raise VerificationError("Liveness payload status is not 'ok'.")
        if not headers.get("x-request-id"):
            raise VerificationError("Missing X-Request-ID response header.")
        for header, expected in (("x-content-type-options", "nosniff"),
                                 ("x-frame-options", "DENY"),
                                 ("referrer-policy", "no-referrer")):
            if headers.get(header, "").lower() != expected.lower():
                raise VerificationError(f"Missing or incorrect {header} security header.")
        return "HTTP 200; request ID and security headers present"

    def ready():
        status, _, body = request(api_base + "/health/ready")
        if status != 200:
            raise VerificationError(f"Expected HTTP 200, got {status}.")
        try:
            payload = json.loads(body)
        except ValueError as exc:
            raise VerificationError("Readiness endpoint did not return JSON.") from exc
        if payload.get("status") != "ready":
            raise VerificationError("Readiness status is not 'ready'.")
        required = ("database", "redis", "object_storage")
        actual = payload.get("checks", {})
        for dependency in required:
            if actual.get(dependency) != "connected":
                raise VerificationError(f"{dependency} is not connected: {actual.get(dependency, 'missing')}")
        return "database, Redis and object storage connected"

    results = [
        run("web gateway", web_health),
        run("API liveness/security headers", live),
        run("API readiness/dependencies", ready),
    ]
    if not all(results):
        failures = "; ".join(f"{name}: {detail}" for name, ok, detail in checks if not ok)
        raise VerificationError(f"Staging checks failed: {failures}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", required=True, help="Web gateway base URL, e.g. https://staging.example.org")
    parser.add_argument("--api", help="Optional private API base URL. Defaults to the web gateway.")
    parser.add_argument("--allow-http", action="store_true", help="Allow HTTP only for isolated staging/test networks.")
    args = parser.parse_args()
    try:
        verify(args.web, require_https=not args.allow_http, api_url=args.api)
    except VerificationError as exc:
        print(f"STAGING VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1
    print("STAGING VERIFICATION PASSED. This is an infrastructure gate, not a full product acceptance test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
