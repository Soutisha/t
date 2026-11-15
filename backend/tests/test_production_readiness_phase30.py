import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "production-readiness.py"


def load():
    spec = importlib.util.spec_from_file_location("phase30_production_readiness", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def good_env():
    return {
        "POSTGRES_PASSWORD": "p" * 32, "REDIS_PASSWORD": "r" * 32,
        "MINIO_ROOT_USER": "root-user", "MINIO_ROOT_PASSWORD": "m" * 32,
        "MINIO_APP_USER": "pitstop-api", "MINIO_APP_PASSWORD": "a" * 32,
        "JWT_SECRET": "j" * 32, "CLIENT_FINGERPRINT_SECRET": "c" * 32,
        "CORS_ORIGINS": "https://pilot.example.org", "SMS_PROVIDER": "twilio",
        "TWILIO_ACCOUNT_SID": "AC" + "a" * 32, "TWILIO_AUTH_TOKEN": "t" * 32,
        "TWILIO_FROM_NUMBER": "+14155552671", "METRICS_TOKEN": "z" * 32,
    }


def test_good_configuration_passes_static_checks():
    checks = load().validate(good_env(), ROOT)
    assert all(item["status"] == "passed" for item in checks), checks


def test_placeholders_and_wildcard_cors_fail_closed():
    env = good_env()
    env["JWT_SECRET"] = "CHANGE_ME"
    env["CORS_ORIGINS"] = "*"
    checks = load().validate(env, ROOT)
    failed = {item["name"] for item in checks if item["status"] == "failed"}
    assert "required deployment settings" in failed
    assert "cryptographic secret strength" in failed
    assert "explicit HTTPS CORS origins" in failed


def test_minio_root_and_application_credentials_must_differ():
    env = good_env()
    env["MINIO_APP_USER"] = env["MINIO_ROOT_USER"]
    checks = load().validate(env, ROOT)
    assert next(x for x in checks if x["name"] == "separate MinIO identities")["status"] == "failed"


def test_invalid_twilio_sender_format_fails():
    env = good_env()
    env["TWILIO_FROM_NUMBER"] = "5551234"
    checks = load().validate(env, ROOT)
    assert next(x for x in checks if x["name"] == "provider identifier formats")["status"] == "failed"


def test_env_parser_is_plain_text_not_shell_execution(tmp_path):
    module = load()
    path = tmp_path / ".env"
    path.write_text('JWT_SECRET="$(echo bad)"\nA=value\n')
    assert module.parse_env(path)["JWT_SECRET"] == '$(echo bad)'
