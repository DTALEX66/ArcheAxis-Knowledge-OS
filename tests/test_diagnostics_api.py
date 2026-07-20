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
    assert "backup_path" not in response.text
    assert "database_path" not in response.text


def test_diagnostics_marks_empty_migration_status_unavailable(monkeypatch) -> None:
    from app.main import app
    from shared.migration_runner import MigrationOperator

    monkeypatch.setattr(MigrationOperator, "__init__", lambda _self: None)
    monkeypatch.setattr(MigrationOperator, "status", lambda _self: [])

    response = TestClient(app).get("/diagnostics")

    assert response.status_code == 200
    assert response.json()["migrations"] == {"unavailable": 1}
