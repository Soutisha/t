#!/usr/bin/env python3
"""Run the complete synthetic pilot workflow suite against an isolated SQLite DB.

No real SMS, cloud storage, participant accounts, production DB, rewards or
external provider actions are performed by this runner. Provider calls in the
test suite are mocked. This is a local integration rehearsal, not live pilot
acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def junit_summary(path: Path) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall(".//testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    details = []
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.attrib.get(key, "0"))
        for case in suite.findall("testcase"):
            status = "passed"
            failure = case.find("failure")
            error = case.find("error")
            skipped = case.find("skipped")
            if failure is not None:
                status = "failed"
            elif error is not None:
                status = "error"
            elif skipped is not None:
                status = "skipped"
            details.append({
                "test": f'{case.attrib.get("classname", "")}.{case.attrib.get("name", "")}',
                "status": status,
                "duration_seconds": float(case.attrib.get("time", "0") or 0),
            })
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    totals["status"] = "passed" if totals["failures"] == 0 and totals["errors"] == 0 else "failed"
    return {"summary": totals, "tests": details}


def run_rehearsal(report_path: Path | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="pitstop-pilot-rehearsal-") as tmp:
        tmp_path = Path(tmp)
        database = tmp_path / "rehearsal.sqlite"
        junit = tmp_path / "junit.xml"
        env = os.environ.copy()
        env.update({
            "APP_ENV": "development",
            "DATABASE_URL": f"sqlite:///{database}",
            "OTP_DEV_RETURN_CODE": "true",
        })
        command = [
            sys.executable, "-m", "pytest", "-q",
            "--junitxml", str(junit),
            "tests",
        ]
        completed = subprocess.run(
            command, cwd=BACKEND, env=env, capture_output=True,
            text=True, timeout=300,
        )
        if not junit.exists():
            raise RuntimeError(
                "Pytest did not produce a JUnit report. "
                f"Exit code: {completed.returncode}. Output: {(completed.stdout + completed.stderr)[-2000:]}"
            )
        result = junit_summary(junit)
        report = {
            "suite": "EUROGRIP PITSTOP OS synthetic pilot workflow rehearsal",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "execution_mode": "isolated temporary SQLite database",
            "external_side_effects": False,
            "real_sms_sent": False,
            "real_cloud_storage_used": False,
            "production_database_used": False,
            "summary": result["summary"],
            "test_results": result["tests"],
            "limitations": [
                "Twilio/provider tests use mocks; no real SMS was sent.",
                "TrustVision storage/API tests use test-local storage or adapters, not the live MinIO service.",
                "No live staging URL, pilot user tokens, production data or participant cohort is tested.",
                "Passing synthetic tests does not replace the HTTPS staging verifier, authenticated pilot acceptance, provider checks or human go/no-go approval.",
            ],
            "pytest_exit_code": completed.returncode,
        }
        if report_path:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            try:
                report_path.chmod(0o600)
            except OSError:
                pass
        print(f'PILOT WORKFLOW REHEARSAL {result["summary"]["status"].upper()}: '
              f'{result["summary"]["passed"]}/{result["summary"]["tests"]} passed; '
              f'{result["summary"]["failures"]} failures; {result["summary"]["errors"]} errors; '
              f'{result["summary"]["skipped"]} skipped.')
        print("Isolation: temporary SQLite database; no real SMS, cloud or production side effects.")
        if report_path:
            print(f"Sanitized report: {report_path}")
        if completed.returncode != 0:
            print((completed.stdout + completed.stderr)[-5000:], file=sys.stderr)
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    try:
        report = run_rehearsal(args.report)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"REHEARSAL ERROR: {exc}", file=sys.stderr)
        return 2
    return 0 if report["summary"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
