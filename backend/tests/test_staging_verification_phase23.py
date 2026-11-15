import json
import importlib.util
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
SPEC = importlib.util.spec_from_file_location("staging_verify", SCRIPTS / "staging-verify.py")
staging_verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(staging_verify)


def test_staging_verifier_passes_when_all_services_and_security_headers_are_healthy(monkeypatch, capsys):
    def fake_request(url, timeout=8.0):
        if url.endswith("/healthz"):
            return 200, {}, b"ok"
        if url.endswith("/health/live"):
            return 200, {
                "x-request-id": "req-test",
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "referrer-policy": "no-referrer",
            }, json.dumps({"status": "ok"}).encode()
        if url.endswith("/health/ready"):
            return 200, {}, json.dumps({
                "status": "ready",
                "checks": {
                    "database": "connected",
                    "redis": "connected",
                    "object_storage": "connected",
                },
            }).encode()
        raise AssertionError(url)

    monkeypatch.setattr(staging_verify, "request", fake_request)
    assert staging_verify.verify("https://staging.pitstop.test") is True
    output = capsys.readouterr().out
    assert "PASS web gateway" in output
    assert "PASS API readiness/dependencies" in output


def test_staging_verifier_fails_closed_if_object_storage_is_not_ready(monkeypatch):
    def fake_request(url, timeout=8.0):
        if url.endswith("/healthz"):
            return 200, {}, b"ok"
        if url.endswith("/health/live"):
            return 200, {
                "x-request-id": "req-test",
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "referrer-policy": "no-referrer",
            }, b'{"status":"ok"}'
        return 200, {}, json.dumps({
            "status": "ready",
            "checks": {"database": "connected", "redis": "connected",
                       "object_storage": "unavailable"},
        }).encode()

    monkeypatch.setattr(staging_verify, "request", fake_request)
    with pytest.raises(staging_verify.VerificationError, match="object_storage"):
        staging_verify.verify("https://staging.pitstop.test")


def test_staging_verifier_requires_https_for_non_local_hosts():
    with pytest.raises(staging_verify.VerificationError, match="HTTPS"):
        staging_verify.verify("http://staging.pitstop.test")


def test_staging_verifier_allows_http_for_localhost(monkeypatch):
    def fake_request(url, timeout=8.0):
        if url.endswith("/healthz"):
            return 200, {}, b"ok"
        if url.endswith("/health/live"):
            return 200, {
                "x-request-id": "req-test",
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "referrer-policy": "no-referrer",
            }, b'{"status":"ok"}'
        return 200, {}, b'{"status":"ready","checks":{"database":"connected","redis":"connected","object_storage":"connected"}}'
    monkeypatch.setattr(staging_verify, "request", fake_request)
    assert staging_verify.verify("http://127.0.0.1:8080")
