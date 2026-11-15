import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
SPEC = importlib.util.spec_from_file_location("pilot_acceptance", SCRIPTS / "pilot-acceptance.py")
pilot_acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot_acceptance)


def test_acceptance_passes_all_role_scoped_checks(monkeypatch):
    def fake_get(base, path, token, timeout=12.0):
        if path == pilot_acceptance.ADMIN_ONLY_PROBE and token == "mechanic-token":
            return 403, {}
        if token == "mechanic-token" and path in pilot_acceptance.MECHANIC_GETS:
            return 200, {"data": []}
        if token == "admin-token" and path in pilot_acceptance.ADMIN_GETS:
            return 200, {"data": []}
        return 401, {}
    monkeypatch.setattr(pilot_acceptance, "get_status", fake_get)
    report = pilot_acceptance.run_acceptance(
        "https://staging.example.test", "mechanic-token", "admin-token"
    )
    assert report["summary"]["status"] == "passed"
    assert report["summary"]["failed"] == 0
    assert report["summary"]["total"] == len(pilot_acceptance.MECHANIC_GETS) + len(pilot_acceptance.ADMIN_GETS) + 1


def test_acceptance_fails_if_mechanic_can_access_admin_route(monkeypatch):
    def fake_get(base, path, token, timeout=12.0):
        if path == pilot_acceptance.ADMIN_ONLY_PROBE and token == "mechanic-token":
            return 200, {"data": []}
        return 200, {"data": []}
    monkeypatch.setattr(pilot_acceptance, "get_status", fake_get)
    report = pilot_acceptance.run_acceptance(
        "https://staging.example.test", "mechanic-token", "admin-token"
    )
    probe = report["checks"][-1]
    assert probe["passed"] is False
    assert probe["expected"] == 403


def test_acceptance_marks_endpoint_failure(monkeypatch):
    def fake_get(base, path, token, timeout=12.0):
        if path == "/api/v1/toolbank/catalog":
            return 503, {}
        if path == pilot_acceptance.ADMIN_ONLY_PROBE and token == "mechanic-token":
            return 403, {}
        return 200, {"data": []}
    monkeypatch.setattr(pilot_acceptance, "get_status", fake_get)
    report = pilot_acceptance.run_acceptance(
        "https://staging.example.test", "mechanic-token", "admin-token"
    )
    assert report["summary"]["status"] == "failed"
    assert any(x["path"] == "/api/v1/toolbank/catalog" and not x["passed"] for x in report["checks"])
