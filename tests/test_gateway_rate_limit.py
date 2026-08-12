from __future__ import annotations

import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from shared import auth
from shared.config import Config, config, validate_runtime_config
from shared.rate_limit import RateLimiter


def test_rate_limiter_returns_retry_metadata_and_recovers_after_window():
    now = 100.0
    limiter = RateLimiter(max_requests=2, window_seconds=10, clock=lambda: now)

    first = limiter.check("anonymous:203.0.113.10")
    second = limiter.check("anonymous:203.0.113.10")
    blocked = limiter.check("anonymous:203.0.113.10")

    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after_seconds == 10

    now = 110.0
    recovered = limiter.check("anonymous:203.0.113.10")
    assert recovered.allowed is True
    assert recovered.remaining == 1


def test_gateway_selects_stricter_write_and_token_policies(monkeypatch):
    monkeypatch.setitem(
        config._data,
        "rate_limit",
        {
            "enabled": True,
            "window_seconds": 60,
            "ordinary_read": 2,
            "sensitive_write": 1,
            "auth_token": 1,
            "trusted_proxies": [],
        },
    )
    client = TestClient(app, client=("198.51.100.7", 50000))

    assert client.get("/version").status_code == 200
    assert client.get("/version").status_code == 200
    read_blocked = client.get("/version")
    assert read_blocked.status_code == 429
    assert read_blocked.json() == {
        "error": "rate_limit_exceeded",
        "detail": "request rate limit exceeded",
        "policy": "ordinary_read",
        "retry_after_seconds": 60,
    }
    assert read_blocked.headers["Retry-After"] == "60"
    assert read_blocked.headers["X-RateLimit-Limit"] == "2"
    assert read_blocked.headers["X-RateLimit-Remaining"] == "0"

    assert client.post("/route", json={"content": "bounded write"}).status_code == 200
    write_blocked = client.post("/route", json={"content": "bounded write"})
    assert write_blocked.status_code == 429
    assert write_blocked.json()["policy"] == "sensitive_write"

    assert client.post("/auth/token").status_code == 403
    token_blocked = client.post("/auth/token")
    assert token_blocked.status_code == 429
    assert token_blocked.json()["policy"] == "auth_token"


def test_api_key_and_jwt_subjects_have_isolated_opaque_buckets(monkeypatch):
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    monkeypatch.setitem(
        config._data,
        "rate_limit",
        {
            "enabled": True,
            "window_seconds": 61,
            "ordinary_read": 1,
            "sensitive_write": 1,
            "auth_token": 1,
            "trusted_proxies": [],
        },
    )
    key_one = secrets.token_urlsafe(32)
    key_two = secrets.token_urlsafe(32)
    monkeypatch.setattr(
        auth,
        "validate_api_key",
        lambda value: {"role": "admin", "name": "shared-name"}
        if value in {key_one, key_two}
        else None,
    )
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "rate-limit-test-jwt-secret")
    jwt = auth.create_token("shared-name", role="admin")
    client = TestClient(app, client=("198.51.100.8", 50000))

    assert client.get("/tools", headers={"X-API-Key": key_one}).status_code == 200
    assert client.get("/tools", headers={"X-API-Key": key_two}).status_code == 200
    api_blocked = client.get("/tools", headers={"X-API-Key": key_one})
    assert api_blocked.status_code == 429

    jwt_headers = {"Authorization": f"Bearer {jwt}"}
    assert client.get("/tools", headers=jwt_headers).status_code == 200
    jwt_blocked = client.get("/tools", headers=jwt_headers)
    assert jwt_blocked.status_code == 429

    returned = f"{api_blocked.headers} {api_blocked.text} {jwt_blocked.headers} {jwt_blocked.text}"
    assert key_one not in returned
    assert key_two not in returned
    assert jwt not in returned
    assert "shared-name" not in returned


def test_proxy_headers_are_rejected_unless_direct_peer_is_explicitly_trusted(monkeypatch):
    settings = {
        "enabled": True,
        "window_seconds": 62,
        "ordinary_read": 1,
        "sensitive_write": 1,
        "auth_token": 1,
        "trusted_proxies": [],
    }
    monkeypatch.setitem(config._data, "rate_limit", settings)
    untrusted = TestClient(app, client=("198.51.100.20", 50000))

    rejected = untrusted.get(
        "/version",
        headers={"X-Forwarded-For": "203.0.113.1", "Forwarded": "for=203.0.113.2"},
    )
    assert rejected.status_code == 400

    direct_one = TestClient(app, client=("198.51.100.20", 50000))
    direct_two = TestClient(app, client=("198.51.100.21", 50000))
    assert direct_one.get("/version").status_code == 200
    assert direct_two.get("/version").status_code == 200
    assert direct_one.get("/version").status_code == 429

    settings["window_seconds"] = 63
    settings["trusted_proxies"] = ["10.0.0.0/8"]
    trusted = TestClient(app, client=("10.0.0.5", 50000))
    assert trusted.get("/version", headers={"X-Forwarded-For": "203.0.113.10"}).status_code == 200
    assert trusted.get("/version", headers={"X-Forwarded-For": "203.0.113.11"}).status_code == 200
    assert trusted.get("/version", headers={"X-Forwarded-For": "203.0.113.10"}).status_code == 429


def test_concurrent_gateway_calls_cannot_oversubscribe_a_bucket(monkeypatch):
    monkeypatch.setitem(
        config._data,
        "rate_limit",
        {
            "enabled": True,
            "window_seconds": 64,
            "ordinary_read": 8,
            "sensitive_write": 4,
            "auth_token": 2,
            "trusted_proxies": [],
        },
    )

    def request_once(_: int) -> int:
        client = TestClient(app, client=("198.51.100.30", 50000))
        return client.get("/version").status_code

    with ThreadPoolExecutor(max_workers=20) as executor:
        statuses = list(executor.map(request_once, range(20)))

    assert statuses.count(200) == 8
    assert statuses.count(429) == 12


def test_production_cannot_disable_gateway_rate_limiting(monkeypatch):
    monkeypatch.setenv("COGNITIVE_API_KEY", "test-api-key-0123456789abcdef-ABCDEFGH")
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "test-jwt-secret-fedcba9876543210-HGFEDCBA")
    current = Config()
    current._data["app"]["environment"] = "production"
    current._data["auth"]["enabled"] = True
    current._data["cors"] = {
        "allow_origins": ["https://ui.example"],
        "allow_methods": ["GET", "POST"],
        "allow_headers": ["Authorization", "Content-Type", "X-API-Key"],
    }
    current._data["rate_limit"]["enabled"] = False

    with pytest.raises(RuntimeError, match="rate limiting"):
        validate_runtime_config(current)


def test_rate_limit_configuration_requires_stricter_sensitive_policies():
    current = Config()
    current._data["rate_limit"]["ordinary_read"] = 10
    current._data["rate_limit"]["sensitive_write"] = 10

    with pytest.raises(RuntimeError, match="stricter"):
        validate_runtime_config(current)


def test_invalid_token_requests_are_limited_before_credential_validation(monkeypatch):
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    monkeypatch.setitem(
        config._data,
        "rate_limit",
        {
            "enabled": True,
            "window_seconds": 65,
            "ordinary_read": 5,
            "sensitive_write": 3,
            "auth_token": 2,
            "trusted_proxies": [],
        },
    )
    validation_calls = 0

    def reject_request(*_args):
        nonlocal validation_calls
        validation_calls += 1
        return None

    monkeypatch.setattr(auth, "authenticate_request", reject_request)
    client = TestClient(app, client=("198.51.100.40", 50000))
    headers = {"X-API-Key": "invalid-credential"}

    assert client.post("/auth/token", headers=headers).status_code == 401
    assert client.post("/auth/token", headers=headers).status_code == 401
    blocked = client.post("/auth/token", headers=headers)
    assert blocked.status_code == 429
    assert blocked.json()["policy"] == "auth_token"
    assert validation_calls == 2


def test_server_rewritten_proxy_identity_is_rejected_without_trust_policy(monkeypatch):
    monkeypatch.setitem(
        config._data,
        "rate_limit",
        {
            "enabled": True,
            "window_seconds": 69,
            "ordinary_read": 3,
            "sensitive_write": 2,
            "auth_token": 1,
            "trusted_proxies": [],
        },
    )
    # Simulate Uvicorn having already replaced scope['client'] from this header.
    client = TestClient(app, client=("203.0.113.55", 50000))

    for header, value in (
        ("X-Forwarded-For", "203.0.113.55"),
        ("Forwarded", "for=203.0.113.55"),
        ("X-Real-IP", "203.0.113.55"),
    ):
        response = client.get("/version", headers={header: value})
        assert response.status_code == 400
        assert response.json() == {
            "error": "untrusted_proxy_headers",
            "detail": "proxy identity headers require an explicit trusted-proxy policy",
        }

    blocked = client.get("/version", headers={"X-Forwarded-For": "198.51.100.250"})
    assert blocked.status_code == 429
    assert blocked.json() == {
        "error": "rate_limit_exceeded",
        "detail": "request rate limit exceeded",
        "policy": "ordinary_read",
        "retry_after_seconds": 69,
    }


def test_rate_limiter_caps_buckets_and_reclaims_stale_identities():
    now = 200.0
    limiter = RateLimiter(
        max_requests=2,
        window_seconds=10,
        max_keys=2,
        clock=lambda: now,
    )

    assert limiter.check("identity-a").allowed is True
    assert limiter.check("identity-b").allowed is True
    for index in range(100):
        denied = limiter.check(f"rotating-identity-{index}")
        assert denied.allowed is False
    assert limiter.stats()["active_keys"] == 2

    now = 210.0
    recovered = limiter.check("identity-c")
    assert recovered.allowed is True
    assert limiter.stats()["active_keys"] == 1


def test_gateway_fails_closed_when_policy_bucket_cap_is_reached(monkeypatch):
    monkeypatch.setitem(
        config._data,
        "rate_limit",
        {
            "enabled": True,
            "window_seconds": 67,
            "ordinary_read": 5,
            "sensitive_write": 3,
            "auth_token": 2,
            "max_buckets_per_policy": 2,
            "trusted_proxies": [],
        },
    )

    first = TestClient(app, client=("198.51.100.50", 50000))
    second = TestClient(app, client=("198.51.100.51", 50000))
    rotating = TestClient(app, client=("2001:db8::1", 50000))

    assert first.get("/version").status_code == 200
    assert second.get("/version").status_code == 200
    blocked = rotating.get("/version")
    assert blocked.status_code == 429
    assert blocked.json()["policy"] == "ordinary_read"


def test_ambiguous_api_key_and_authorization_headers_are_rejected_before_auth(monkeypatch):
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    monkeypatch.setitem(
        config._data,
        "rate_limit",
        {
            "enabled": True,
            "window_seconds": 68,
            "ordinary_read": 2,
            "sensitive_write": 1,
            "auth_token": 1,
            "max_buckets_per_policy": 100,
            "trusted_proxies": [],
        },
    )
    auth_calls = 0

    def should_not_authenticate(*_args):
        nonlocal auth_calls
        auth_calls += 1
        return {"sub": "valid-key", "role": "admin", "auth_method": "api_key"}

    monkeypatch.setattr(auth, "authenticate_request", should_not_authenticate)
    client = TestClient(app, client=("198.51.100.60", 50000))

    for fake_key in ("rotating-fake-key-1", "rotating-fake-key-2"):
        response = client.get(
            "/tools",
            headers={
                "Authorization": "Bearer valid-api-key",
                "X-API-Key": fake_key,
            },
        )
        assert response.status_code == 400
        assert response.json() == {
            "error": "ambiguous_credentials",
            "detail": "send exactly one of Authorization or X-API-Key",
        }

    blocked = client.get(
        "/tools",
        headers={
            "Authorization": "Bearer valid-api-key",
            "X-API-Key": "rotating-fake-key-3",
        },
    )
    assert blocked.status_code == 429
    assert blocked.json()["policy"] == "ordinary_read"
    assert auth_calls == 0


def test_deployment_entrypoints_use_the_lease_aware_core_launcher():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "Dockerfile").exists()
    assert not (root / "docker-compose.yml").exists()

    ecosystem = (root / "ecosystem.config.cjs").read_text(encoding="utf-8")
    assert "app.main:app" not in ecosystem
    assert "app.runtime_entrypoint core" in ecosystem

    adapter = root / "app" / "runtime_entrypoint.py"
    launch_lines = [
        line for line in adapter.read_text(encoding="utf-8").splitlines()
        if "app.main:app" in line
    ]
    assert launch_lines, f"missing app.main launch in {adapter}"
    assert "--no-proxy-headers" in adapter.read_text(encoding="utf-8")

def test_local_launchers_delegate_to_the_lease_aware_core_entrypoint(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    launchers = (
        root / "run_windows.bat",
        root / "run_windows.ps1",
        root / "run_all.bat",
        root / "run_all.sh",
    )
    for launcher in launchers:
        text = launcher.read_text(encoding="utf-8")
        assert "app.main:app" not in text, launcher
        assert "app.runtime_entrypoint core" in text, launcher

    runtime_entrypoint = (root / "app" / "runtime_entrypoint.py").read_text(encoding="utf-8")
    assert '"--no-proxy-headers"' in runtime_entrypoint

    calls = []
    from app import runtime_entrypoint
    from app.cli import cmd_serve

    monkeypatch.setattr(runtime_entrypoint, "run_core", lambda args: calls.append(args))
    monkeypatch.delenv("ARCHEAXIS_PORT", raising=False)
    cmd_serve(port=8123)
    assert len(calls) == 1
    assert os.environ["ARCHEAXIS_PORT"] == "8123"
