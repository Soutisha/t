import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pilot-launch-gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("phase27_pilot_launch_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_document():
    module = load_gate()
    return {
        "pilot_scope": {
            "geography": "Approved test geography",
            "start_date": "2026-12-01",
            "end_date": "2026-12-14",
            "cohort_size": 8,
            "approved_features": ["Passport", "Academy"],
        },
        "owners": {role: {"role_title": role.replace("_", " ").title()}
                   for role in module.REQUIRED_OWNER_ROLES},
        "evidence": {
            key: {
                "status": "approved",
                "evidence_ref": f"controlled-record/{key}",
                "approved_by_role": "accountable_owner",
                "approved_at": "2026-11-15T10:00:00Z",
            }
            for key in module.REQUIRED_EVIDENCE
        },
    }


def test_launch_gate_requires_every_owner_and_evidence_item(tmp_path):
    module = load_gate()
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(valid_document()))
    checks, metadata = module.validate_approval_document(path)
    assert all(item["passed"] for item in checks)
    assert metadata["scope"]["cohort_size"] == 8


def test_launch_gate_fails_closed_for_pending_evidence(tmp_path):
    module = load_gate()
    document = valid_document()
    document["evidence"]["twilio_real_otp_journey_passed"]["status"] = "pending"
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(document))
    checks, _ = module.validate_approval_document(path)
    failed = [item["gate"] for item in checks if not item["passed"]]
    assert failed == ["evidence:twilio_real_otp_journey_passed"]


def test_launch_gate_rejects_missing_evidence_reference(tmp_path):
    module = load_gate()
    document = valid_document()
    document["evidence"]["encrypted_backup_restore_drill_passed"]["evidence_ref"] = ""
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(document))
    checks, _ = module.validate_approval_document(path)
    assert not next(item for item in checks if item["gate"] == "evidence:encrypted_backup_restore_drill_passed")["passed"]


def test_launch_gate_rejects_invalid_cohort_size(tmp_path):
    module = load_gate()
    document = valid_document()
    document["pilot_scope"]["cohort_size"] = 101
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(document))
    checks, _ = module.validate_approval_document(path)
    assert not next(item for item in checks if item["gate"] == "pilot_scope")["passed"]


def test_launch_gate_requires_https_and_tokens(tmp_path):
    module = load_gate()
    approval = tmp_path / "approval.json"
    approval.write_text(json.dumps(valid_document()))
    try:
        module.run_gate("http://staging.example.org", "mechanic", "admin", approval)
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("HTTP staging URL must be rejected")
    try:
        module.run_gate("https://staging.example.org", "", "admin", approval)
    except ValueError as exc:
        assert "tokens" in str(exc)
    else:
        raise AssertionError("Missing mechanic token must be rejected")
