#!/usr/bin/env python3
"""Read-only, role-aware acceptance checks for an already deployed pilot."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MECHANIC_GETS = (
    "/api/v1/me",
    "/api/v1/me/privacy/consents",
    "/api/v1/toolbank/catalog",
    "/api/v1/toolbank/requests/me",
    "/api/v1/rewards/me",
    "/api/v1/academy/courses",
    "/api/v1/academy/my-learning",
    "/api/v1/academy/certificates/me",
    "/api/v1/trustvision/me/evidence",
    "/api/v1/advocacy/products",
    "/api/v1/advocacy/me/events",
    "/api/v1/advocacy/campaigns",
)
ADMIN_GETS = (
    "/api/v1/admin/onboarding/pending",
    "/api/v1/admin/trustvision/review-queue",
    "/api/v1/admin/toolbank/requests/pending",
    "/api/v1/admin/rewards/redemptions/pending",
    "/api/v1/admin/academy/courses",
    "/api/v1/admin/advocacy/review-queue",
    "/api/v1/admin/analytics/operations",
)
ADMIN_ONLY_PROBE = "/api/v1/admin/analytics/operations"


def get_status(base_url: str, path: str, token: str, timeout: float = 12.0) -> tuple[int, dict]:
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "User-Agent": "EUROGRIP-PITSTOP-Pilot-Acceptance/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            try:
                payload = json.loads(raw) if raw else {}
            except ValueError:
                payload = {}
            return response.status, payload
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except Exception as exc:
        raise RuntimeError(f"{path}: request failed ({type(exc).__name__})") from exc


def check_role(base_url: str, role: str, token: str, paths: tuple[str, ...]) -> list[dict]:
    results = []
    for path in paths:
        try:
            status, payload = get_status(base_url, path, token)
            ok = status == 200 and isinstance(payload, dict)
            results.append({
                "role": role, "path": path, "expected": 200, "actual": status,
                "passed": ok, "detail": "read-only endpoint returned HTTP 200" if ok else "unexpected status or response",
            })
        except RuntimeError as exc:
            results.append({"role": role, "path": path, "expected": 200, "actual": None,
                            "passed": False, "detail": str(exc)})
    return results


def run_acceptance(base_url: str, mechanic_token: str, admin_token: str) -> dict:
    results = []
    results.extend(check_role(base_url, "mechanic", mechanic_token, MECHANIC_GETS))
    results.extend(check_role(base_url, "administrator", admin_token, ADMIN_GETS))
    try:
        status, _ = get_status(base_url, ADMIN_ONLY_PROBE, mechanic_token)
        passed = status == 403
        results.append({
            "role": "mechanic", "path": ADMIN_ONLY_PROBE, "expected": 403,
            "actual": status, "passed": passed,
            "detail": "admin-only route correctly denied" if passed else "mechanic token was not denied with HTTP 403",
        })
    except RuntimeError as exc:
        results.append({"role": "mechanic", "path": ADMIN_ONLY_PROBE, "expected": 403,
                        "actual": None, "passed": False, "detail": str(exc)})
    total = len(results)
    passed_count = sum(1 for result in results if result["passed"])
    return {
        "suite": "EUROGRIP PITSTOP OS pilot read-only acceptance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url.rstrip("/"),
        "summary": {"passed": passed_count, "failed": total - passed_count, "total": total,
                    "status": "passed" if passed_count == total else "failed"},
        "checks": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Staging gateway URL")
    parser.add_argument("--mechanic-token-env", default="PILOT_MECHANIC_TOKEN",
                        help="Environment variable containing a mechanic access token")
    parser.add_argument("--admin-token-env", default="PILOT_ADMIN_TOKEN",
                        help="Environment variable containing an administrator access token")
    parser.add_argument("--allow-http-localhost", action="store_true",
                        help="Allow HTTP only for localhost test deployments")
    parser.add_argument("--report", help="Optional JSON report path; tokens are never written")
    args = parser.parse_args()
    from urllib.parse import urlparse
    parsed = urlparse(args.base_url)
    if parsed.scheme != "https" and not (
        args.allow_http_localhost and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        print("ERROR: HTTPS is required for pilot acceptance.", file=sys.stderr)
        return 2
    mechanic_token = os.environ.get(args.mechanic_token_env, "")
    admin_token = os.environ.get(args.admin_token_env, "")
    if not mechanic_token or not admin_token:
        print("ERROR: Provide both mechanic and administrator tokens through environment variables.", file=sys.stderr)
        return 2
    report = run_acceptance(args.base_url, mechanic_token, admin_token)
    for check in report["checks"]:
        print(f"{'PASS' if check['passed'] else 'FAIL'} [{check['role']}] {check['path']} "
              f"expected={check['expected']} actual={check['actual']}")
    summary = report["summary"]
    print(f"PILOT ACCEPTANCE {summary['status'].upper()}: {summary['passed']}/{summary['total']} checks passed")
    if args.report:
        target = Path(args.report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        try:
            target.chmod(0o600)
        except OSError:
            pass
        print(f"Report written to {target}; access tokens are not included.")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
