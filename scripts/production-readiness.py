#!/usr/bin/env python3
"""Static production deployment preflight; never deploys or changes infrastructure."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


PLACEHOLDERS = ("CHANGE_ME", "replace-this", "example.invalid", "YOUR_", "TODO")
REQUIRED = (
    "POSTGRES_PASSWORD", "REDIS_PASSWORD", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD",
    "MINIO_APP_USER", "MINIO_APP_PASSWORD", "JWT_SECRET", "CLIENT_FINGERPRINT_SECRET",
    "CORS_ORIGINS", "SMS_PROVIDER", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER", "METRICS_TOKEN",
)


def parse_env(path: Path) -> dict[str, str]:
    result = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip("'\"")
    return result


def validate(env: dict[str, str], repo: Path) -> list[dict]:
    checks = []

    def add(name: str, ok: bool, detail: str):
        checks.append({"name": name, "status": "passed" if ok else "failed", "detail": detail})

    missing = [key for key in REQUIRED if not env.get(key)]
    placeholders = [key for key in REQUIRED if any(marker.lower() in env.get(key, "").lower() for marker in PLACEHOLDERS)]
    add("required deployment settings", not missing and not placeholders,
        "all required keys populated" if not missing and not placeholders else
        "missing keys: " + ", ".join(missing) + ("; placeholder keys: " + ", ".join(placeholders) if placeholders else ""))

    strong = [key for key in ("JWT_SECRET", "CLIENT_FINGERPRINT_SECRET", "METRICS_TOKEN", "MINIO_APP_PASSWORD")
              if len(env.get(key, "")) >= 32]
    add("cryptographic secret strength", len(strong) == 4,
        "four required secrets meet 32-character minimum" if len(strong) == 4 else
        "weak or missing: " + ", ".join(set(("JWT_SECRET", "CLIENT_FINGERPRINT_SECRET", "METRICS_TOKEN", "MINIO_APP_PASSWORD")) - set(strong)))

    origins = [x.strip() for x in env.get("CORS_ORIGINS", "").split(",") if x.strip()]
    cors_ok = bool(origins) and all(urlparse(x).scheme == "https" and urlparse(x).netloc for x in origins) and "*" not in env.get("CORS_ORIGINS", "")
    add("explicit HTTPS CORS origins", cors_ok, "explicit HTTPS origins configured" if cors_ok else "CORS_ORIGINS must be comma-separated HTTPS origins without wildcard")

    sid_ok = bool(re.fullmatch(r"AC[a-fA-F0-9]{32}", env.get("TWILIO_ACCOUNT_SID", "")))
    phone_ok = bool(re.fullmatch(r"\+[1-9]\d{7,14}", env.get("TWILIO_FROM_NUMBER", "")))
    add("provider identifier formats", sid_ok and phone_ok,
        "Twilio account SID and sender number formats valid" if sid_ok and phone_ok else "Twilio SID or E.164 sender format invalid")

    root_user, app_user = env.get("MINIO_ROOT_USER", ""), env.get("MINIO_APP_USER", "")
    add("separate MinIO identities", bool(root_user and app_user and root_user != app_user),
        "root and application identities are distinct" if root_user and app_user and root_user != app_user else "MinIO root and app identities must be distinct")

    compose = repo / "docker-compose.yml"
    compose_text = compose.read_text(encoding="utf-8") if compose.exists() else ""
    required_fragments = (
        "APP_ENV: production", "OTP_DEV_RETURN_CODE: \"false\"", "OBJECT_STORAGE_BACKEND: s3",
        "S3_ACCESS_KEY_ID: ${MINIO_APP_USER}", "S3_SECRET_ACCESS_KEY: ${MINIO_APP_PASSWORD}",
        "condition: service_healthy", "condition: service_completed_successfully",
    )
    missing_fragments = [fragment for fragment in required_fragments if fragment not in compose_text]
    add("production compose security invariants", not missing_fragments,
        "production mode, OTP safeguard, S3 app identity and dependency ordering present" if not missing_fragments else
        "missing compose invariants: " + ", ".join(missing_fragments))

    policy = repo / "minio/policies/pitstop-evidence-rw.json"
    policy_ok = False
    if policy.exists():
        try:
            data = json.loads(policy.read_text(encoding="utf-8"))
            serialized = json.dumps(data)
            policy_ok = "pitstop-private" in serialized and "s3:*" not in serialized
        except Exception:
            policy_ok = False
    add("MinIO scoped policy file", policy_ok,
        "policy JSON exists and references the private bucket without wildcard s3:*" if policy_ok else "policy missing, invalid JSON, or overly broad")

    migration = repo / "backend/migrations"
    add("Alembic migration assets", migration.exists() and any(migration.rglob("*.py")),
        "migration scripts present" if migration.exists() and any(migration.rglob("*.py")) else "migration assets missing")

    backups = all((repo / f"scripts/{name}").exists() for name in ("backup.sh", "backup-verify.sh", "restore.sh"))
    add("backup and restore procedures", backups,
        "backup, verification and restore scripts present" if backups else "one or more backup/restore scripts missing")

    runbook = (repo / "docs/PHASE_30_PRODUCTION_DEPLOYMENT_AND_PILOT_READINESS.md").exists()
    add("production runbook", runbook, "Phase 30 runbook present" if runbook else "Phase 30 runbook missing")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--check-compose", action="store_true", help="Run docker compose config; read-only validation")
    args = parser.parse_args()
    if not args.env_file.is_file():
        print(f"ERROR: environment file not found: {args.env_file}", file=sys.stderr)
        return 2
    checks = validate(parse_env(args.env_file), args.repo.resolve())
    if args.check_compose:
        if not shutil.which("docker"):
            checks.append({"name": "docker compose config", "status": "skipped", "detail": "Docker CLI unavailable"})
        else:
            proc = subprocess.run(["docker", "compose", "--env-file", str(args.env_file), "config", "--quiet"],
                                  cwd=args.repo, capture_output=True, text=True, timeout=60)
            checks.append({"name": "docker compose config", "status": "passed" if proc.returncode == 0 else "failed",
                           "detail": "compose configuration valid" if proc.returncode == 0 else "compose config validation failed; inspect local CLI output"})
    failed = sum(x["status"] == "failed" for x in checks)
    skipped = sum(x["status"] == "skipped" for x in checks)
    report = {
        "suite": "EUROGRIP PITSTOP OS production deployment preflight",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": "READY_FOR_OPERATOR_REVIEW" if failed == 0 else "BLOCKED",
        "summary": {"passed": len(checks)-failed-skipped, "failed": failed, "skipped": skipped, "total": len(checks)},
        "checks": checks,
        "limitations": ["Static preflight only; does not deploy, connect to providers, send SMS, or prove live service health.",
                        "READY_FOR_OPERATOR_REVIEW is not authorization to launch a participant pilot."],
    }
    for item in checks:
        print(f"{item['status'].upper()} {item['name']}: {item['detail']}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        try: args.report.chmod(0o600)
        except OSError: pass
    print(f"PRODUCTION PREFLIGHT {report['decision']}: {report['summary']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
