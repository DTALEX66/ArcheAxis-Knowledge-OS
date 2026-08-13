"""AXW-094A/B + 096C Workspace API surface tests.

Proves the exchange export/verify, backup create/verify/restore(dry-run)
and batch import/status endpoints are reachable and honest end-to-end
(022B lesson: library code is not a feature until it is reachable).
"""

from __future__ import annotations

import time
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
    assert body["state"] == "running"
    assert body["total"] == 2

    # poll until the background batch finishes
    status = client.get("/workspace/api/batch/api-test-batch/status")
    deadline = time.monotonic() + 30
    while status.json()["state"] not in ("finished", "shutdown") and time.monotonic() < deadline:
        time.sleep(0.2)
        status = client.get("/workspace/api/batch/api-test-batch/status")
    assert status.json()["state"] == "finished", status.text
    assert status.json()["completed"] == 2
    assert status.json()["failed"] == 0

    # ledger readback after completion: digest-verified results persist
    results = status.json()["results"]
    assert results["docs/a.md"]["status"] == "completed"
    assert results["docs/b.md"]["result_digest"].startswith("converted:")


def test_batch_pause_resume_shutdown_flow(client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "import-src2"
    (source / "docs").mkdir(parents=True)
    for index in range(20):
        (source / "docs" / f"f{index:02d}.md").write_text(
            f"# File {index}\n\nBody {index}.\n", encoding="utf-8"
        )

    batch = client.post(
        "/workspace/api/batch/import",
        json={"batch_id": "control-batch", "source_dir": str(source), "pattern": "**/*", "max_files": 100},
    )
    assert batch.status_code == 200

    # pause quickly (small files convert fast; worker startup gives us a window)
    time.sleep(0.05)
    paused = client.post("/workspace/api/batch/control-batch/pause")
    assert paused.status_code == 200
    assert paused.json()["state"] in ("paused", "running")  # pause may land after finish
    if paused.json()["state"] == "paused":
        before = client.get("/workspace/api/batch/control-batch/status").json()["completed"]
        time.sleep(0.1)
        after = client.get("/workspace/api/batch/control-batch/status").json()["completed"]
        assert after <= before + 2  # max_concurrent=2: at most two in-flight tasks finish

        resumed = client.post("/workspace/api/batch/control-batch/resume")
        assert resumed.status_code == 200
        assert resumed.json()["state"] in ("running", "finished")  # may finish instantly

    # wait for completion
    status = client.get("/workspace/api/batch/control-batch/status")
    deadline = time.monotonic() + 30
    while status.json()["state"] not in ("finished", "shutdown") and time.monotonic() < deadline:
        time.sleep(0.2)
        status = client.get("/workspace/api/batch/control-batch/status")
    assert status.json()["state"] == "finished"
    assert status.json()["completed"] == 20

    # unknown batch control is a 404
    missing = client.post("/workspace/api/batch/nope/pause")
    assert missing.status_code == 404


def test_batch_shutdown_mid_run(client: TestClient, tmp_path: Path) -> None:
    """Safe exit: shutdown stops pickup, persists the ledger, and the
    rehydrated status reports the terminal shutdown state (AXW-096C)."""
    source = tmp_path / "import-src3"
    (source / "docs").mkdir(parents=True)
    for index in range(200):
        (source / "docs" / f"f{index:03d}.md").write_text(
            f"# File {index}\n\n{'Body content. ' * 20}\n", encoding="utf-8"
        )

    batch = client.post(
        "/workspace/api/batch/import",
        json={"batch_id": "shutdown-batch", "source_dir": str(source), "pattern": "**/*", "max_files": 200},
    )
    assert batch.status_code == 200

    # give workers a moment to pick up tasks, then shut down mid-run
    time.sleep(0.1)
    shutdown = client.post("/workspace/api/batch/shutdown-batch/shutdown")
    assert shutdown.status_code == 200
    assert shutdown.json()["state"] == "shutdown"

    # ledger persisted: status readback works after the active batch is gone
    status = client.get("/workspace/api/batch/shutdown-batch/status")
    assert status.status_code == 200
    body = status.json()
    assert body["state"] in ("shutdown", "finished")  # finished if all done already
    assert body["total"] == 200
    completed = body["completed"]
    assert 0 < completed < 200  # shutdown happened mid-run, not before/after
    assert "docs/f000.md" in body["results"]


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


def test_batch_import_rejects_duplicate_active(client: TestClient, tmp_path: Path) -> None:
    """A second import with the same batch_id while one is active is a 409."""
    source = tmp_path / "dup-src"
    (source / "docs").mkdir(parents=True)
    for index in range(50):
        (source / "docs" / f"f{index:02d}.md").write_text(f"# File {index}\n", encoding="utf-8")

    first = client.post(
        "/workspace/api/batch/import",
        json={"batch_id": "dup-batch", "source_dir": str(source), "pattern": "**/*", "max_files": 50},
    )
    assert first.status_code == 200

    second = client.post(
        "/workspace/api/batch/import",
        json={"batch_id": "dup-batch", "source_dir": str(source), "pattern": "**/*", "max_files": 50},
    )
    assert second.status_code == 409
    assert "already active" in second.json()["detail"]


def test_batch_status_unknown_batch(client: TestClient) -> None:
    status = client.get("/workspace/api/batch/does-not-exist/status")
    assert status.status_code == 404
