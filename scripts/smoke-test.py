#!/usr/bin/env python3
"""Read-only deployment smoke checks for the Pitstop OS gateway and API."""
import argparse
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "EUROGRIP-PITSTOP-Smoke/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read()
    except Exception as exc:
        print(f"FAIL {url}: {type(exc).__name__}")
        return None, {}, b""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", default="http://localhost:8080")
    parser.add_argument("--api", default=None, help="Optional separate API base URL.")
    parser.add_argument("--allow-http", action="store_true", help="Allow HTTP only for localhost.")
    args = parser.parse_args()
    web = args.web.rstrip("/")
    api = (args.api or web).rstrip("/")
    parsed = urlparse(web)
    if parsed.scheme != "https" and not (args.allow_http and parsed.hostname in ("localhost", "127.0.0.1", "::1")):
        print("FAIL public staging smoke checks require HTTPS (or --allow-http for localhost)")
        return 2

    checks = []
    def check(name, ok, detail):
        checks.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")

    status, _, body = fetch(web + "/healthz")
    check("web gateway", status == 200 and body.strip().lower() == b"ok", f"HTTP {status}")

    status, headers, body = fetch(api + "/health/live")
    live_ok = status == 200
    try:
        payload = json.loads(body)
        live_ok = live_ok and payload.get("status") == "ok"
    except ValueError:
        live_ok = False
    for header, expected in (("x-request-id", None), ("x-content-type-options", "nosniff"),
                             ("x-frame-options", "DENY"), ("referrer-policy", "no-referrer")):
        actual = headers.get(header, "")
        live_ok = live_ok and (bool(actual) if expected is None else actual.lower() == expected.lower())
    check("API liveness and security headers", live_ok, f"HTTP {status}")

    status, _, body = fetch(api + "/health/ready")
    ready_ok = status == 200
    try:
        readiness = json.loads(body)
        ready_ok = ready_ok and readiness.get("status") == "ready"
        deps = readiness.get("checks", {})
        ready_ok = ready_ok and all(deps.get(key) == "connected" for key in ("database", "redis", "object_storage"))
    except ValueError:
        ready_ok = False
    check("API dependency readiness", ready_ok, f"HTTP {status}; requires DB, Redis and object storage connected")

    if not all(checks):
        print(f"SMOKE TEST FAILED: {sum(checks)}/{len(checks)} checks passed")
        return 1
    print(f"SMOKE TEST PASSED: {sum(checks)}/{len(checks)} checks passed")
    print("This is an infrastructure check, not authenticated workflow or provider acceptance.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
