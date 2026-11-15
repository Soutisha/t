\
#!/usr/bin/env python3
"""Read-only go/no-go gate for a controlled EUROGRIP PITSTOP OS pilot.

This tool verifies HTTPS staging health and role-aware API access, then checks
that required human/provider/operational evidence has been recorded. It does
not send SMS, mutate application data, create users, or deploy infrastructure.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_EVIDENCE = (
    "business_scope_approved",
    "privacy_notice_and_consent_approved",
    "retention_and_deletion_policy_approved",
    "external_tls_and_dns_verified",
    "twilio_real_otp_journey_passed",
    "minio_scoped_identity_verified",
    "encrypted_backup_restore_drill_passed",
    "monitoring_alert_delivery_tested",
    "manual_critical_workflows_signed_off",
    "rollback_and_stop_procedure_rehearsed",
    "participant_recruitment_and_consent_approved",
)
REQUIRED_OWNER_ROLES = (
    "business_owner",
    "technical_owner",
    "privacy_data_owner",
    "support_contact",
    "pilot_coordinator",
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load required checker: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_approval_document(path: Path) -> tuple[list[dict], dict]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Approval file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Approval file is not valid JSON (line {exc.lineno}).") from exc
    if not isinstance(doc, dict):
        raise ValueError("Approval document must be a JSON object.")

    owners = doc.get("owners")
    if not isinstance(owners, dict):
        owners = {}
    owner_results = []
    for role in REQUIRED_OWNER_ROLES:
        entry = owners.get(role, {})
        valid = isinstance(entry, dict) and bool(str(entry.get("role_title", "")).strip())
        owner_results.append({
            "gate": f"owner:{role}",
            "passed": valid,
            "detail": "role assignment recorded" if valid else "missing accountable role assignment",
        })

    evidence = doc.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    evidence_results = []
    for key in REQUIRED_EVIDENCE:
        item = evidence.get(key, {})
        valid = (
            isinstance(item, dict)
            and item.get("status") == "approved"
            and bool(str(item.get("evidence_ref", "")).strip())
            and bool(str(item.get("approved_by_role", "")).strip())
            and bool(str(item.get("approved_at", "")).strip())
        )
        evidence_results.append({
            "gate": f"evidence:{key}",
            "passed": valid,
            "detail": "approval and evidence reference recorded" if valid
                      else "requires status=approved, evidence_ref, approved_by_role and approved_at",
        })

    scope = doc.get("pilot_scope")
    if not isinstance(scope, dict):
        scope = {}
    try:
        cohort = int(scope.get("cohort_size", 0))
    except (TypeError, ValueError):
        cohort = 0
    scope_ok = (
        bool(str(scope.get("geography", "")).strip())
        and bool(str(scope.get("start_date", "")).strip())
        and bool(str(scope.get("end_date", "")).strip())
        and 1 <= cohort <= 100
        and isinstance(scope.get("approved_features"), list)
        and len(scope.get("approved_features", [])) > 0
    )
    scope_result = {
        "gate": "pilot_scope",
        "passed": scope_ok,
        "detail": "geography, dates, cohort (1–100) and feature scope recorded"
                  if scope_ok else "scope requires geography, start/end dates, cohort_size 1–100 and approved_features",
    }
    return owner_results + evidence_results + [scope_result], {
        "scope": {
            "geography_recorded": bool(str(scope.get("geography", "")).strip()),
            "cohort_size": cohort,
            "approved_feature_count": len(scope.get("approved_features", []))
                                      if isinstance(scope.get("approved_features"), list) else 0,
        }
    }


def run_gate(base_url: str, mechanic_token: str, admin_token: str,
             approval_file: Path, report_file: Path | None = None) -> dict:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Pilot launch gate requires an absolute HTTPS staging URL.")
    if not mechanic_token or not admin_token:
        raise ValueError("Mechanic and administrator tokens must be supplied through environment variables.")

    approval_checks, metadata = validate_approval_document(approval_file)

    staging = load_module("phase27_staging_verify", ROOT / "scripts" / "staging-verify.py")
    acceptance = load_module("phase27_pilot_acceptance", ROOT / "scripts" / "pilot-acceptance.py")

    runtime_checks = []
    try:
        staging.verify(base_url, require_https=True)
        runtime_checks.append({
            "gate": "staging_infrastructure",
            "passed": True,
            "detail": "gateway, API security headers and DB/Redis/object-storage readiness verified",
        })
    except Exception as exc:
        runtime_checks.append({
            "gate": "staging_infrastructure",
            "passed": False,
            "detail": str(exc)[:500],
        })

    try:
        result = acceptance.run_acceptance(base_url, mechanic_token, admin_token)
        runtime_checks.append({
            "gate": "role_aware_api_acceptance",
            "passed": result["summary"]["status"] == "passed",
            "detail": f'{result["summary"]["passed"]}/{result["summary"]["total"]} read-only role checks passed',
            "checks": result["checks"],
        })
    except Exception as exc:
        runtime_checks.append({
            "gate": "role_aware_api_acceptance",
            "passed": False,
            "detail": f"acceptance runner failed ({type(exc).__name__})",
        })

    all_checks = approval_checks + runtime_checks
    passed = sum(1 for item in all_checks if item["passed"])
    total = len(all_checks)
    failed_gates = [item["gate"] for item in all_checks if not item["passed"]]
    report = {
        "suite": "EUROGRIP PITSTOP OS controlled pilot launch gate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "staging_origin": f"{parsed.scheme}://{parsed.netloc}",
        "decision": "GO" if not failed_gates else "NO_GO",
        "summary": {"passed": passed, "failed": total - passed, "total": total},
        "scope_summary": metadata["scope"],
        "failed_gates": failed_gates,
        "checks": all_checks,
        "limitations": [
            "Human/provider evidence is checked for documented approval fields, not independently authenticated.",
            "The gate is read-only and does not send SMS, mutate records, deploy services or recruit participants.",
            "A GO result is a release recommendation only; the accountable business owner retains final authority.",
        ],
    }
    if report_file:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        try:
            report_file.chmod(0o600)
        except OSError:
            pass
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="HTTPS staging gateway URL")
    parser.add_argument("--approval-file", required=True, type=Path,
                        help="Completed launch approval JSON; never commit real approval records")
    parser.add_argument("--mechanic-token-env", default="PILOT_MECHANIC_TOKEN")
    parser.add_argument("--admin-token-env", default="PILOT_ADMIN_TOKEN")
    parser.add_argument("--report", type=Path, help="Optional restricted JSON report path")
    args = parser.parse_args()
    try:
        report = run_gate(
            args.base_url,
            os.environ.get(args.mechanic_token_env, ""),
            os.environ.get(args.admin_token_env, ""),
            args.approval_file,
            args.report,
        )
    except ValueError as exc:
        print(f"LAUNCH GATE ERROR: {exc}", file=sys.stderr)
        return 2

    for check in report["checks"]:
        print(f'{"PASS" if check["passed"] else "FAIL"} {check["gate"]}: {check["detail"]}')
    summary = report["summary"]
    print(f'PILOT LAUNCH DECISION: {report["decision"]} ({summary["passed"]}/{summary["total"]} gates passed)')
    if report["failed_gates"]:
        print("Outstanding gates: " + ", ".join(report["failed_gates"]))
    if args.report:
        print(f"Sanitized report written to {args.report}; access tokens and approver names are not included.")
    return 0 if report["decision"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
