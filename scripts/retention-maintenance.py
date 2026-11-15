#!/usr/bin/env python3
"""Dry-run-first retention maintenance. Windows must be approved and configured by the data owner."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.retention import execute_retention, retention_candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Delete records matching configured retention windows.")
    parser.add_argument("--confirm-retention-policy", action="store_true",
                        help="Confirm the data owner approved the configured retention windows.")
    args = parser.parse_args()
    if args.execute and not args.confirm_retention_policy:
        print("ERROR: --execute requires --confirm-retention-policy.", file=sys.stderr)
        return 2
    if args.execute and os.environ.get("RETENTION_EXECUTION_APPROVED") != "1":
        print("ERROR: Set RETENTION_EXECUTION_APPROVED=1 after approval by the data owner.", file=sys.stderr)
        return 2
    db = SessionLocal()
    try:
        if args.execute:
            report = execute_retention(db)
            report["mode"] = "executed"
        else:
            report = {"mode": "dry_run", "candidates": retention_candidates(db)}
        report["configured_policy"] = {
            "otp_retention_hours": settings.otp_retention_hours,
            "security_audit_retention_days": settings.security_audit_retention_days,
            "user_activity_retention_days": settings.user_activity_retention_days,
        }
        print(json.dumps(report, indent=2, default=str))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
