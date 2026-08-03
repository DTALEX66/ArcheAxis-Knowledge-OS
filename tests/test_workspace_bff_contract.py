from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient


def _database(tmp_path):
    path = tmp_path / "workspace.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE workspace_jobs_v1 (
                job_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE research_packages_v1 (
                canonical_url TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            INSERT INTO workspace_jobs_v1 VALUES
                ('job-internal-1', 'succeeded', '2026-08-01T02:00:00Z'),
                ('job-internal-2', 'queued', '2026-08-01T01:00:00Z');
            INSERT INTO research_packages_v1 VALUES
                ('https://example.com/source', 'candidate', '2026-08-01T03:00:00Z');
            """
        )
    return path


def test_bff_v1_is_read_only_and_hides_persistence_identifiers(monkeypatch, tmp_path) -> None:
    from app.main import app
    from app.workspace import router

    database = _database(tmp_path)
    monkeypatch.setattr(router, "DB_PATH", database)
    client = TestClient(app)

    response = client.get("/workspace/api/v1/activity?limit=2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "v1"
    assert len(payload["items"]) == 2
    assert payload["next_cursor"]
    assert all(item["public_ref"].startswith("wr1_") for item in payload["items"])
    assert "job-internal-1" not in response.text
    assert "job-internal-2" not in response.text
    assert "command_id" not in response.text
    assert "package_id" not in response.text

    next_page = client.get(
        "/workspace/api/v1/activity",
        params={"limit": 2, "cursor": payload["next_cursor"]},
    )
    assert next_page.status_code == 200
    assert len(next_page.json()["items"]) == 1
    assert next_page.json()["items"][0]["kind"] == "job"
    assert next_page.json()["items"][0]["updated_at"] == "2026-08-01T01:00:00Z"

    assert client.post("/workspace/api/v1/activity").status_code == 405


def test_bff_v1_object_resolution_and_uniform_unknown_reference(monkeypatch, tmp_path) -> None:
    from app.main import app
    from app.workspace import bff, router

    database = _database(tmp_path)
    monkeypatch.setattr(router, "DB_PATH", database)
    client = TestClient(app)

    reference = bff.public_ref("source", "https://example.com/source")
    resolved = client.get(f"/workspace/api/v1/objects/{reference}")
    assert resolved.status_code == 200
    assert resolved.json() == {
        "schema_version": "v1",
        "kind": "source",
        "public_ref": reference,
        "label": "研究资料",
        "source": "https://example.com/source",
        "state": "candidate",
        "updated_at": "2026-08-01T03:00:00Z",
    }
    assert "canonical_url" not in resolved.text

    for unknown in ("bad", "wr1_" + "0" * 32):
        missing = client.get(f"/workspace/api/v1/objects/{unknown}")
        assert missing.status_code == 404
        assert missing.json() == {"detail": "workspace object was not found"}


def test_bff_v1_rejects_invalid_cursor_and_reports_unavailable(monkeypatch, tmp_path) -> None:
    from app.main import app
    from app.workspace import router

    database = _database(tmp_path)
    monkeypatch.setattr(router, "DB_PATH", database)
    client = TestClient(app)
    assert client.get("/workspace/api/v1/activity?limit=0").status_code == 422
    assert client.get("/workspace/api/v1/activity?cursor=not-a-cursor").status_code == 422

    missing_database = tmp_path / "missing.sqlite"
    monkeypatch.setattr(router, "DB_PATH", missing_database)
    unavailable = client.get("/workspace/api/v1/activity")
    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "workspace projection is unavailable"}


def test_bff_v1_home_uses_the_real_workspace_status_projection(monkeypatch, tmp_path) -> None:
    from app.main import app
    from app.workspace import router
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(router, "DB_PATH", database)

    response = TestClient(app).get("/workspace/api/v1/home")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "v1"
    assert payload["components"]["api"] == "available"
    assert payload["components"]["database"] == "available"
    assert "job_id" not in response.text
    assert "package_id" not in response.text
    assert "database_path" not in response.text
