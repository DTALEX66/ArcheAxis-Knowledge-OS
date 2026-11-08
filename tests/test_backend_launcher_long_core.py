"""Opt-in Windows smoke of a real Core under an owned synthetic long root."""

import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

from scripts.release import backend_launcher as launcher


@pytest.mark.skipif(os.name != "nt", reason="Windows extended-path regression")
def test_real_core_launches_and_answers_from_long_root(tmp_path, monkeypatch):
    source_name = os.environ.get("ARCHEAXIS_TEST_CORE_BIN")
    expected_sha = os.environ.get("ARCHEAXIS_TEST_CORE_SHA256")
    if not source_name or not expected_sha:
        pytest.skip("explicitly pinned Core is required")
    source = Path(source_name)
    with source.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == expected_sha

    padding = 265 - len(str(tmp_path)) - 1
    assert 0 < padding < 255
    root = tmp_path / ("r" * padding)
    core = launcher.filesystem_path(root / launcher.CORE_RELATIVE)
    core.parent.mkdir(parents=True)
    shutil.copyfile(source, core)
    with core.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == expected_sha
    for relative in ("runtime/python.exe", "workers/transport/text_ndjson.py"):
        path = launcher.filesystem_path(root / relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic placeholder; this smoke does not run workers")
    profile = {
        "schema": launcher.PROFILE_SCHEMA,
        "python": "runtime/python.exe",
        "script": "workers/transport/text_ndjson.py",
        "staging": "data/worker-staging",
    }
    launcher.filesystem_path(root / launcher.PROFILE_NAME).write_text(
        json.dumps(profile), encoding="utf-8"
    )
    monkeypatch.setattr(launcher, "ROOT", root)
    data_root = root / "synthetic-data-directory"
    assert len(str(root)) > 260
    assert len(str(root / launcher.CORE_RELATIVE)) > 260
    assert len(str(data_root / "workspace.sqlite")) > 260

    child, base, receipt, tokens = launcher.start(data_root, 0)
    try:
        assert receipt["openmaic_node_worker_error"] == "absent"
        version_status, _ = launcher.call(
            base, "GET", "/api/v1/system/version", tokens=tokens, role="human"
        )
        workspace_status, _ = launcher.call(
            base, "GET", "/api/v1/workspaces/info", tokens=tokens, role="human"
        )
        assert version_status == 200
        assert workspace_status == 200
        created_status, created = launcher.call(
            base, "POST", "/api/v1/documents",
            {"create_request_id": "synthetic-long-core-document",
             "title": "Synthetic document", "editor_json": {"type": "doc", "content": []}},
            tokens=tokens, role="human",
        )
        assert created_status == 201
        document_id = created["document_id"]
    finally:
        launcher.stop(child)

    # A broken optional manifest also leaves ordinary persisted documents usable.
    launcher.filesystem_path(root / "backend-runtime-manifest.json").write_bytes(b"{}")
    child, base, receipt, tokens = launcher.start(data_root, 0)
    try:
        assert receipt["openmaic_node_worker_error"] == "manifest_invalid"
        read_status, document = launcher.call(
            base, "GET", f"/api/v1/documents/{document_id}", tokens=tokens, role="human"
        )
        assert read_status == 200
        assert document["document_id"] == document_id
    finally:
        launcher.stop(child)
