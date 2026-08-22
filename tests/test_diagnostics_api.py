from __future__ import annotations

from fastapi.testclient import TestClient


def test_diagnostics_returns_safe_versioned_status() -> None:
    from app.main import app

    response = TestClient(app).get("/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "v1"
    assert payload["health"]["status"] == "ok"
    assert payload["migrations"]
    assert set(payload["migrations"]).issubset(
        {"applied", "pending", "failed", "rolled_back", "unavailable"}
    )
    assert payload["release"] == {
        "status": "unreleased",
        "version": "0.6.4",
        "channel": "development",
        "source_commit": "unavailable",
    }
    assert "backup_path" not in response.text
    assert "database_path" not in response.text


def test_diagnostics_contains_no_secrets_or_auth_state() -> None:
    """AXW-097: diagnostics must never carry secrets, credentials, auth
    state, private-body content, or absolute private paths — even nested."""
    from app.main import app

    response = TestClient(app).get("/diagnostics")
    assert response.status_code == 200
    text = response.text.lower()

    for secret_marker in (
        "token",
        "secret",
        "password",
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "cookie",
        "private_key",
        "ssh",
    ):
        assert secret_marker not in text, f"diagnostics leaked secret marker: {secret_marker}"

    for path_marker in (r"c:\\", r"/users/", r"/home/", r"\\users\\", ":/"):
        assert path_marker not in text, f"diagnostics leaked absolute path marker: {path_marker}"


def test_diagnostics_does_not_promote_unverified_release_override(monkeypatch) -> None:
    from app.main import app
    from shared.config import config

    monkeypatch.setitem(config._data["app"], "release_version", "2026.07.20+build.42")

    response = TestClient(app).get("/diagnostics")

    assert response.status_code == 200
    assert response.json()["release"] == {
        "status": "unreleased",
        "version": "0.6.4",
        "channel": "development",
        "source_commit": "unavailable",
    }


def test_diagnostics_rejects_unsafe_release_version(monkeypatch) -> None:
    from app.main import app
    from shared.config import config

    monkeypatch.setitem(config._data["app"], "release_version", "build/../../secret")

    response = TestClient(app).get("/diagnostics")

    assert response.status_code == 200
    assert response.json()["release"] == {
        "status": "unreleased",
        "version": "0.6.4",
        "channel": "development",
        "source_commit": "unavailable",
    }


def test_release_version_environment_override(monkeypatch) -> None:
    from shared.config import Config

    monkeypatch.setenv("COGNITIVE_RELEASE_VERSION", "2026.07.20+build.42")

    assert Config().get("app.release_version") == "2026.07.20+build.42"


def test_diagnostics_marks_empty_migration_status_unavailable(monkeypatch) -> None:
    from app.main import app
    from shared.migration_runner import MigrationOperator

    monkeypatch.setattr(MigrationOperator, "__init__", lambda _self: None)
    monkeypatch.setattr(MigrationOperator, "status", lambda _self: [])

    response = TestClient(app).get("/diagnostics")

    assert response.status_code == 200
    assert response.json()["migrations"] == {"unavailable": 1}
