"""Pipeline console: multi-format intake flows end-to-end into Library, conversion

runs, evidence anchors and readable converted content (MFX pipeline closure).

These tests pin the contract that a batch import is not a dead-end artifacts
directory: originals are retained in the Source Archive, each conversion is
recorded as an immutable ConversionRun with an EvidenceAnchor, failures keep
the original plus a readable (sanitised) reason, and the Library projection
exposes format / engine / error so the product UI can render the whole pipe.
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient


def _poll_until(client: TestClient, batch_id: str, terminal: str = "finished") -> dict:
    deadline = time.time() + 20
    while time.time() < deadline:
        status = client.get(f"/workspace/api/batch/{batch_id}/status").json()
        if status.get("state") in (terminal, "shutdown", "paused") or status.get("completed") + status.get("failed", 0) >= status.get("total", 0):
            return status
        time.sleep(0.1)
    raise AssertionError(f"batch {batch_id} did not reach {terminal}: {status}")


def _setup_runtime(tmp_path: Path, monkeypatch) -> TestClient:
    """Build a migrated local runtime like the closed-loop workspace tests."""
    import app.workspace.router as router
    from app.main import app
    from shared.migration_runner import MigrationOperator

    store = tmp_path / "workspace.sqlite"
    store.touch()
    operator = MigrationOperator(
        db_path=store, backup_dir=tmp_path / "workspace-backups"
    )
    operator.apply("research.sqlite")
    operator.apply("workspace.sqlite")
    monkeypatch.setattr(router, "DB_PATH", store)
    return TestClient(app)


def test_upload_intake_flows_into_library_with_format_engine(tmp_path: Path, monkeypatch) -> None:
    client = _setup_runtime(tmp_path, monkeypatch)

    upload = client.post(
        "/workspace/api/intake/upload",
        files={"file": ("notes.txt", b"# Local note\n\npipeline works", "text/plain")},
    )
    assert upload.status_code == 200, upload.text
    payload = upload.json()
    assert payload["source_type"] == "file"
    assert payload["file_name"] == "notes.txt"
    assert payload["format"] == "txt"
    assert payload["engine"] == "passthrough"
    assert payload["char_count"] > 0
    assert payload["raw_sha256"] and len(payload["raw_sha256"]) == 64
    # Internal identifiers (conversion_run_id / anchor_id) deliberately do not
    # cross the product boundary; the UI reaches run detail via raw_sha256.
    assert "conversion_run_id" not in payload
    assert "evidence_anchor_id" not in payload

    listed = client.get("/workspace/api/library").json()["items"]
    item = next(item for item in listed if item["raw_sha256"] == payload["raw_sha256"])
    assert item["conversion_state"] == "retained"
    assert item["format"] == "txt"
    assert item["engine"] == "passthrough"
    assert item["error_reason"] is None

    converted = client.get(f"/workspace/api/library/{payload['raw_sha256']}/converted")
    assert converted.status_code == 200
    assert converted.headers["X-Content-Type-Options"] == "nosniff"
    assert converted.headers["content-type"].startswith("application/json")
    body = converted.json()
    assert body["engine"] == "passthrough"
    assert "pipeline works" in body["content"]

    run = client.get(f"/workspace/api/library/{payload['raw_sha256']}/conversion-run")
    assert run.status_code == 200
    run_body = run.json()
    assert run_body["engine"] == "passthrough"
    assert run_body["block_count"] >= 1
    assert run_body["loss_notes"] == []
    assert "path" not in run.text.lower() or str(tmp_path) not in run.text


def test_batch_import_persists_originals_and_conversions_into_library(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "imports"
    source.mkdir()
    (source / "a.md").write_text("# Alpha\nfirst markdown file", encoding="utf-8")
    (source / "b.txt").write_text("plain text pipeline", encoding="utf-8")
    client = _setup_runtime(tmp_path, monkeypatch)

    started = client.post(
        "/workspace/api/batch/import",
        json={"batch_id": "batch-pipe-1", "source_dir": str(source), "pattern": "**/*", "max_files": 10},
    )
    assert started.status_code == 200, started.text
    batch_id = started.json()["batch_id"]
    status = _poll_until(client, batch_id)
    assert status["completed"] == 2
    assert status["failed"] == 0

    items = client.get("/workspace/api/library").json()["items"]
    assert {item["source_name"] for item in items} == {"a.md", "b.txt"}
    for item in items:
        assert item["conversion_state"] == "retained"
        assert item["engine"] in ("passthrough",)
        assert item["format"] in ("md", "txt")

    # Batch-created anchors must not leak internal run/block identities.
    anchors = client.get("/workspace/api/evidence/anchors").json()["items"]
    for anchor in anchors:
        assert "conversion_run_id" not in anchor["locator"]
        assert "derived_document_id" not in anchor["locator"]
        assert "block_ids" not in anchor["locator"]


def test_batch_import_failure_retains_original_and_readable_reason(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "imports"
    source.mkdir()
    (source / "good.md").write_text("# Good\nconvertible", encoding="utf-8")
    (source / "bad.canvas").write_text("{\"nodes\": broken", encoding="utf-8")
    client = _setup_runtime(tmp_path, monkeypatch)

    started = client.post(
        "/workspace/api/batch/import",
        json={"batch_id": "batch-pipe-2", "source_dir": str(source), "pattern": "**/*", "max_files": 10},
    )
    assert started.status_code == 200
    status = _poll_until(client, started.json()["batch_id"])
    assert status["completed"] == 1
    assert status["failed"] == 1

    # The batch failure list must never leak an absolute host path.
    failed_entry = status["results"]["bad.canvas"]
    assert failed_entry["status"] == "failed"
    assert "bad.canvas" in failed_entry["error"]
    assert str(source) not in failed_entry["error"]

    items = client.get("/workspace/api/library").json()["items"]
    by_name = {item["source_name"]: item for item in items}
    assert by_name["good.md"]["conversion_state"] == "retained"
    bad = by_name["bad.canvas"]
    assert bad["conversion_state"] == "requires_attention"
    assert bad["error_reason"] and "bad.canvas" in bad["error_reason"]
    assert str(source) not in bad["error_reason"]
    assert len(bad["error_reason"]) <= 300


def test_library_converted_endpoints_fail_closed(tmp_path: Path, monkeypatch) -> None:
    client = _setup_runtime(tmp_path, monkeypatch)

    assert client.get("/workspace/api/library/not-a-hash/converted").status_code == 422
    missing = "a" * 64
    assert client.get(f"/workspace/api/library/{missing}/converted").status_code == 404
    assert client.get(f"/workspace/api/library/{missing}/conversion-run").status_code == 404
    assert client.get(f"/workspace/api/library/{'a' * 63}/converted").status_code == 422


def test_batch_import_pause_resume_shutdown(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "imports"
    source.mkdir()
    for index in range(3):
        (source / f"n{index}.md").write_text(f"# Note {index}\ncontent {index}", encoding="utf-8")
    client = _setup_runtime(tmp_path, monkeypatch)

    started = client.post(
        "/workspace/api/batch/import",
        json={"batch_id": "batch-pipe-3", "source_dir": str(source), "pattern": "**/*", "max_files": 10, "rate_per_second": 0.2},
    )
    assert started.status_code == 200
    batch_id = started.json()["batch_id"]

    paused = client.post(f"/workspace/api/batch/{batch_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["state"] in ("paused", "running", "finished")
    resumed = client.post(f"/workspace/api/batch/{batch_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["state"] in ("running", "finished")
    status = _poll_until(client, batch_id)
    assert status["completed"] == 3

    second = client.post(
        "/workspace/api/batch/import",
        json={"batch_id": "batch-pipe-4", "source_dir": str(source), "pattern": "**/*", "max_files": 10, "rate_per_second": 0.2},
    )
    assert second.status_code == 200
    second_id = second.json()["batch_id"]
    shut = client.post(f"/workspace/api/batch/{second_id}/shutdown")
    assert shut.status_code == 200
    assert shut.json()["state"] == "shutdown"
    assert client.get(f"/workspace/api/batch/{second_id}/status").json()["state"] in ("shutdown", "finished")


def test_conversion_error_sanitization_covers_drive_unc_and_keeps_urls() -> None:
    from app.workspace.service import _sanitize_conversion_error

    windows = _sanitize_conversion_error(
        "No engine could convert pdf file 'D:\\资料\\课程\\a.pdf': boom"
    )
    assert "D:\\资料" not in windows
    assert "a.pdf" in windows

    unc = _sanitize_conversion_error(
        "No engine could convert md file '\\\\server\\share\\notes.md': boom"
    )
    assert "\\\\server\\share" not in unc
    assert "notes.md" in unc

    posix = _sanitize_conversion_error(
        "No engine could convert html file '/home/runner/work/a.html': boom"
    )
    assert "/home/runner" not in posix
    assert "a.html" in posix

    url = _sanitize_conversion_error(
        "fetch failed for https://example.com/article?x=1: 404"
    )
    assert "https://example.com/article?x=1" in url

    bounded = _sanitize_conversion_error("x" * 400)
    assert len(bounded) == 300
    assert _sanitize_conversion_error("") == "conversion failed"
