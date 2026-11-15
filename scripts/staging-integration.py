#!/usr/bin/env python3
"""Fail-closed staging integration checks; no writes or SMS unless explicitly opted in."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


class CheckFailure(RuntimeError):
    pass


def safe_detail(value: str) -> str:
    value = re.sub(r"(?i)(authorization|token|password|secret|api[_-]?key)\s*[:=]\s*\S+", r"\1=[REDACTED]", str(value))
    value = re.sub(r"\bAC[a-f0-9]{32}\b", "[REDACTED_SID]", value, flags=re.I)
    value = re.sub(r"\bSK[a-f0-9]{32}\b", "[REDACTED_KEY]", value, flags=re.I)
    value = re.sub(r"\+\d{8,15}", "[REDACTED_PHONE]", value)
    return value[:500]


def request(url: str, timeout: float, headers: dict | None = None):
    req = urllib.request.Request(url, headers={"User-Agent": "EUROGRIP-PITSTOP-Integration-Check/1.0", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read(1_000_000)
    except urllib.error.HTTPError as exc:
        raise CheckFailure(f"HTTP {exc.code}") from exc
    except Exception as exc:
        raise CheckFailure(f"request failed ({type(exc).__name__})") from exc


def env_file_values(path: Path) -> dict[str, str]:
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


class Runner:
    def __init__(self):
        self.checks = []

    def add(self, name, fn, *, skipped=False):
        if skipped:
            self.checks.append({"name": name, "status": "skipped", "detail": "not opted in"})
            print(f"SKIP {name}: not opted in")
            return
        try:
            detail = fn()
            self.checks.append({"name": name, "status": "passed", "detail": safe_detail(detail)})
            print(f"PASS {name}: {safe_detail(detail)}")
        except Exception as exc:
            detail = safe_detail(str(exc)) or type(exc).__name__
            self.checks.append({"name": name, "status": "failed", "detail": detail})
            print(f"FAIL {name}: {detail}")

    def report(self):
        statuses = [x["status"] for x in self.checks]
        return {
            "suite": "EUROGRIP PITSTOP OS staging integration",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "passed" if "failed" not in statuses else "failed",
            "summary": {key: statuses.count(key) for key in ("passed", "failed", "skipped")},
            "checks": self.checks,
            "side_effects": {
                "sms_sent": False,
                "storage_object_written": any(x["name"] == "S3 disposable-prefix round-trip" and x["status"] == "passed" for x in self.checks),
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", required=True, help="Staging gateway URL")
    parser.add_argument("--api", help="API base URL if different from gateway")
    parser.add_argument("--allow-http", action="store_true", help="Permit HTTP only for localhost/private isolated test")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--report", type=Path, help="Write sanitized JSON report")
    parser.add_argument("--env-file", type=Path, help="Optional env file; only validates presence/placeholders")
    parser.add_argument("--check-twilio", action="store_true", help="Explicitly make a read-only Twilio account API request")
    parser.add_argument("--storage-roundtrip", action="store_true", help="Write/read/delete one disposable S3 object")
    parser.add_argument("--confirm-storage-write", action="store_true", help="Required to permit disposable S3 object write/delete")
    parser.add_argument("--storage-test-prefix", default="", help="Required isolated object prefix, e.g. staging-verification/operator-123")
    args = parser.parse_args()

    if args.timeout <= 0 or args.timeout > 60:
        parser.error("--timeout must be greater than 0 and at most 60 seconds")
    web = args.web.rstrip("/")
    api = (args.api or args.web).rstrip("/")
    for value, label in ((web, "--web"), (api, "--api")):
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            parser.error(f"{label} must be an absolute HTTP(S) URL")
        if not args.allow_http and parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            parser.error(f"{label} must use HTTPS; --allow-http is for isolated local tests only")

    if args.storage_roundtrip:
        if not args.confirm_storage_write:
            parser.error("--storage-roundtrip requires --confirm-storage-write")
        prefix = args.storage_test_prefix.strip("/")
        if not prefix.startswith("staging-verification/") or ".." in prefix.split("/") or len(prefix) < 25:
            parser.error("--storage-test-prefix must be a unique path under staging-verification/ (at least 25 characters)")
    elif args.confirm_storage_write or args.storage_test_prefix:
        parser.error("storage confirmation/prefix options require --storage-roundtrip")

    runner = Runner()

    def gateway():
        status, _, body = request(web + "/healthz", args.timeout)
        if status != 200 or body.strip().lower() != b"ok":
            raise CheckFailure("expected HTTP 200 and body 'ok'")
        return "gateway health endpoint returned HTTP 200"

    def liveness():
        status, headers, body = request(api + "/health/live", args.timeout)
        payload = json.loads(body)
        if status != 200 or payload.get("status") != "ok":
            raise CheckFailure("API liveness check did not return healthy")
        normalized = {k.lower(): v for k, v in headers.items()}
        if not normalized.get("X-Request-ID".lower()):
            raise CheckFailure("missing request correlation header")
        for key, expected in (("x-content-type-options", "nosniff"), ("x-frame-options", "DENY"), ("referrer-policy", "no-referrer")):
            if normalized.get(key, "").lower() != expected.lower():
                raise CheckFailure(f"security header {key} missing or incorrect")
        return "API live; request ID and security headers present"

    def readiness():
        status, _, body = request(api + "/health/ready", args.timeout)
        payload = json.loads(body)
        if status != 200 or payload.get("status") != "ready":
            raise CheckFailure("API is not ready")
        checks = payload.get("checks", {})
        required = ("database", "redis", "object_storage")
        bad = [name for name in required if checks.get(name) != "connected"]
        if bad:
            raise CheckFailure("dependency readiness incomplete: " + ", ".join(bad))
        return "database, Redis and object storage report connected"

    runner.add("web gateway", gateway)
    runner.add("API liveness and security headers", liveness)
    runner.add("API dependency readiness", readiness)

    if args.env_file:
        def env_check():
            values = env_file_values(args.env_file)
            required = ("POSTGRES_PASSWORD", "REDIS_PASSWORD", "JWT_SECRET", "CLIENT_FINGERPRINT_SECRET",
                        "CORS_ORIGINS", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER",
                        "METRICS_TOKEN", "MINIO_APP_USER", "MINIO_APP_PASSWORD")
            missing = [key for key in required if not values.get(key) or "CHANGE_ME" in values.get(key, "")]
            if missing:
                raise CheckFailure("missing or placeholder settings: " + ", ".join(missing))
            for key in ("JWT_SECRET", "CLIENT_FINGERPRINT_SECRET", "METRICS_TOKEN", "MINIO_APP_PASSWORD"):
                if len(values[key]) < 32:
                    raise CheckFailure(f"{key} must be at least 32 characters")
            origin = values["CORS_ORIGINS"]
            if "*" in origin or not all(x.strip().startswith("https://") for x in origin.split(",")):
                raise CheckFailure("CORS_ORIGINS must contain explicit HTTPS origins")
            return f"{len(required)} required settings present; values not emitted"
        runner.add("staging environment configuration", env_check)

    if args.check_twilio:
        def twilio_check():
            sid, token = os.getenv("TWILIO_ACCOUNT_SID", ""), os.getenv("TWILIO_AUTH_TOKEN", "")
            if not sid or not token or "CHANGE_ME" in sid + token:
                raise CheckFailure("TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN missing or placeholder")
            import base64
            import urllib.error
            import urllib.request
            auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
            req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
                                         headers={"Authorization": f"Basic {auth}"})
            try:
                with urllib.request.urlopen(req, timeout=args.timeout) as response:
                    data = json.loads(response.read())
            except Exception as exc:
                raise CheckFailure(f"Twilio read-only account check failed ({type(exc).__name__})") from exc
            if str(data.get("status", "")).lower() != "active":
                raise CheckFailure("Twilio account is not active")
            return "Twilio account credentials accepted; no SMS sent"
        runner.add("Twilio read-only account verification", twilio_check)
    else:
        runner.add("Twilio read-only account verification", lambda: "", skipped=True)

    if args.storage_roundtrip:
        def storage_check():
            import boto3
            from botocore.config import Config
            bucket = os.getenv("S3_BUCKET", "pitstop-private")
            endpoint = os.getenv("S3_ENDPOINT_URL") or None
            client = boto3.client("s3", region_name=os.getenv("S3_REGION") or None,
                                  endpoint_url=endpoint, aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID") or None,
                                  aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY") or None,
                                  config=Config(s3={"addressing_style": "path"}, connect_timeout=3, read_timeout=args.timeout,
                                                retries={"max_attempts": 1}))
            client.head_bucket(Bucket=bucket)
            key = args.storage_test_prefix.rstrip("/") + "/probe-" + uuid.uuid4().hex
            payload = ("pitstop-staging-probe-" + uuid.uuid4().hex).encode()
            try:
                client.put_object(Bucket=bucket, Key=key, Body=payload, ContentType="text/plain")
                got = client.get_object(Bucket=bucket, Key=key)["Body"].read()
                if got != payload:
                    raise CheckFailure("S3 read-back did not match the probe payload")
            finally:
                try:
                    client.delete_object(Bucket=bucket, Key=key)
                except Exception as exc:
                    raise CheckFailure("probe object cleanup failed; inspect the isolated prefix") from exc
            return "disposable object uploaded, read back and deleted"
        runner.add("S3 disposable-prefix round-trip", storage_check)
    else:
        runner.add("S3 disposable-prefix round-trip", lambda: "", skipped=True)

    report = runner.report()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        try:
            args.report.chmod(0o600)
        except OSError:
            pass
        print(f"Sanitized report written to {args.report}")
    print(f"STAGING INTEGRATION {report['status'].upper()}: {report['summary']}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
