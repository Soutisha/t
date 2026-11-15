import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_staging_verifier():
    path = ROOT / "scripts" / "staging-verify.py"
    spec = importlib.util.spec_from_file_location("staging_verify_phase26", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_staging_deploy_requires_explicit_confirmation():
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "staging-deploy.sh")],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2
    assert "--deploy" in result.stderr
    assert "deployment not started" in result.stderr


def test_staging_deploy_help_is_read_only():
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "staging-deploy.sh"), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "--deploy" in result.stdout


def test_staging_verifier_rejects_public_http():
    verifier = load_staging_verifier()
    try:
        verifier.verify("http://staging.example.org", require_https=True)
    except verifier.VerificationError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("Public HTTP must be rejected")


def test_staging_verifier_requires_absolute_url():
    verifier = load_staging_verifier()
    try:
        verifier.verify("/relative", require_https=False)
    except verifier.VerificationError as exc:
        assert "absolute" in str(exc)
    else:
        raise AssertionError("Relative URL must be rejected")
