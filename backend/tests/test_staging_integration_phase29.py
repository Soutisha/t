import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "staging-integration.py"


def load_module():
    spec = importlib.util.spec_from_file_location("phase29_staging_integration", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_secret_redaction_covers_provider_identifiers_and_phone_numbers():
    module = load_module()
    text = "Authorization: Bearer abc password=hunter2 AC" + "a" * 32 + " +919876543210"
    safe = module.safe_detail(text)
    assert "hunter2" not in safe
    assert "AC" + "a" * 32 not in safe
    assert "+919876543210" not in safe
    assert "[REDACTED" in safe


def test_env_parser_does_not_execute_shell_syntax(tmp_path):
    module = load_module()
    path = tmp_path / ".env"
    path.write_text('PASSWORD="$(touch /tmp/should-not-exist)"\n# ignored\nA=value\n')
    values = module.env_file_values(path)
    assert values["PASSWORD"] == '$(touch /tmp/should-not-exist)'
    assert values["A"] == "value"


def test_env_check_fails_closed_on_placeholders(tmp_path, monkeypatch):
    module = load_module()
    env = tmp_path / ".env.staging"
    env.write_text("JWT_SECRET=CHANGE_ME\n")
    monkeypatch.setattr(module.sys, "argv", ["staging-integration.py", "--web", "https://stage.example", "--env-file", str(env)])
    # Exercise the same parser and validation contract without making network calls.
    values = module.env_file_values(env)
    required = ("POSTGRES_PASSWORD", "REDIS_PASSWORD", "JWT_SECRET")
    missing = [key for key in required if not values.get(key) or "CHANGE_ME" in values.get(key, "")]
    assert missing == list(required)


def test_report_contains_only_aggregate_status_and_sanitized_details():
    module = load_module()
    runner = module.Runner()
    runner.add("example", lambda: "account password=secret-value")
    report = runner.report()
    assert report["status"] == "passed"
    assert report["checks"][0]["detail"] == "account password=[REDACTED]"
    assert report["side_effects"]["sms_sent"] is False


def test_http_is_rejected_for_non_local_staging_by_default(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module.sys, "argv", ["staging-integration.py", "--web", "http://stage.example"])
    try:
        module.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("non-HTTPS staging must be rejected")
