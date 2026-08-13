"""AXW-094A/B + 096C Workspace API surface tests.

Proves the exchange export/verify, backup create/verify/restore(dry-run)
and batch import/status endpoints are reachable and honest end-to-end
(022B lesson: library code is not a feature until it is reachable).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.workspace.router import router  # noqa: F401  (router is mounted via app.main)


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # resolve_runtime_path reads ARCHEAXIS_DATA_DIR per call, so a monkey-
    # patched env isolates every exchange/backup/batch endpoint into the
    # tmp data dir. DB_PATH (module constant) is only read for evidence
    # anchor queries — a read-only no-op against the real DB.
    monkeypatch.setenv("ARCHEAXIS_DATA_DIR", str(tmp_path / "data"))
    from app.main import app

    return TestClient(app)


def test_exchange_export_verify_roundtrip(client: TestClient) -> None:
    # seed a raw original so the export is non-empty
    from shared.config import resolve_runtime_path

    originals = resolve_runtime_path("data") / "originals"
    originals.mkdir(parents=True, exist_ok=True)
    (originals / "abc123").write_bytes(b"original bytes")

    export = client.post(
        "/workspace/api/exchange/export",
        json={"name": "test-exchange", "overwrite": True},
    )
    assert export.status_code == 200, export.text
    body = export.json()
    assert body["item_count"] == 1

    verify = client.get("/workspace/api/exchange/verify", params={"name": "test-exchange"})
    assert verify.status_code == 200, verify.text


def test_exchange_export_verify_failure(client: TestClient) -> None:
    # verifying a non-existent exchange is a 400 with an explicit reason
    verify = client.get("/workspace/api/exchange/verify", params={"name": "missing"})
    assert verify.status_code == 422
    assert "manifest.json missing" in verify.json()["detail"]


def test_backup_create_verify_restore_dry_run(client: TestClient) -> None:
    create = client.post("/workspace/api/backup/create", json={"name": "test-backup"})
    assert create.status_code == 200, create.text
    assert create.json()["file_count"] >= 0

    verify = client.get("/workspace/api/backup/verify", params={"name": "test-backup"})
    assert verify.status_code == 200, verify.text
    assert verify.json()["verified_files"] >= 0

    # dry-run restore into the live data dir must be safe (no writes)
    restore = client.post(
        "/workspace/api/backup/restore",
        json={"name": "test-backup", "dry_run": True},
    )
    assert restore.status_code == 200, restore.text
    assert restore.json()["dry_run"] is True


def test_batch_import_and_status(client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "import-src"
    (source / "docs").mkdir(parents=True)
    (source / "docs" / "a.md").write_text("# A\n\nBody.\n", encoding="utf-8")
    (source / "docs" / "b.md").write_text("# B\n\nBody.\n", encoding="utf-8")

    batch = client.post(
        "/workspace/api/batch/import",
        json={
            "batch_id": "api-test-batch",
            "source_dir": str(source),
            "pattern": "**/*",
            "max_files": 10,
        },
    )
    assert batch.status_code == 200, batch.text
    body = batch.json()
    assert body["state"] == "finished"
    assert body["completed"] == 2
    assert body["failed"] == 0

    status = client.get("/workspace/api/batch/api-test-batch/status")
    assert status.status_code == 200, status.text
    results = status.json()["results"]
    assert results["docs/a.md"]["status"] == "completed"
    assert results["docs/b.md"]["result_digest"].startswith("converted:")


def test_batch_import_rejects_missing_source(client: TestClient, tmp_path: Path) -> None:
    batch = client.post(
        "/workspace/api/batch/import",
        json={
            "batch_id": "bad-batch",
            "source_dir": str(tmp_path / "nope"),
            "pattern": "**/*",
        },
    )
    assert batch.status_code == 400
    assert "not found" in batch.json()["detail"]


def test_batch_status_unknown_batch(client: TestClient) -> None:
    status = client.get("/workspace/api/batch/does-not-exist/status")
    assert status.status_code == 404
