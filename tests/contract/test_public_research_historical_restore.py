"""Restore an explicitly selected public-research receipt without network access.

The receipt and its backup must already exist and be named by the caller. This
exercises a new Core against historical public test data, not a new live search,
installed candidate, real-person review, or full J2 acceptance.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REQUIRED_ENV = ("AAOS_TEST_CORE_EXE", "AAOS_TEST_PUBLIC_RESEARCH_RECEIPT", "AAOS_TEST_PUBLIC_RESEARCH_RECEIPT_SHA256")


@pytest.mark.skipif(not all(os.environ.get(name) for name in REQUIRED_ENV), reason="explicit Core and receipt identity required")
def test_historical_public_research_restores_sources_without_network(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    receipt_path = Path(os.environ["AAOS_TEST_PUBLIC_RESEARCH_RECEIPT"]).resolve(strict=True)
    expected_receipt_sha = os.environ["AAOS_TEST_PUBLIC_RESEARCH_RECEIPT_SHA256"]
    assert re.fullmatch(r"[a-f0-9]{64}", expected_receipt_sha)
    receipt_bytes = receipt_path.read_bytes()
    assert hashlib.sha256(receipt_bytes).hexdigest() == expected_receipt_sha
    core_exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)
    core_sha = hashlib.sha256(core_exe.read_bytes()).hexdigest()
    historical = json.loads(receipt_bytes)
    assert historical["ok"] is True and historical["evidence_level"] == "REAL_CORE_PUBLIC_NETWORK"
    assert historical["source_consistent"] is True and historical["candidate_consistent"] is True
    channels = {(item["family"], item["provider"], item["status"]) for item in historical["channel_statuses"]}
    assert {("encyclopedia", "wikipedia", "complete"), ("community", "stackexchange", "complete"),
            ("research", "openalex", "complete")} <= channels

    workspace = receipt_path.parent / "public-research-workspace"
    assert Path(historical["workspace"]).resolve(strict=True) == workspace.resolve(strict=True)
    backup = historical["backup"]
    assert backup["verified"] is True and re.fullmatch(r"[a-f0-9]{32}\.sqlite", backup["filename"])
    artifact = workspace / "backups" / backup["filename"]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
    object_dir = Path(str(artifact) + ".objects")
    objects = backup["source_sha_list"]
    assert len(objects) == len(set(objects)) == 6

    def verify_backup_objects():
        for digest in objects:
            assert re.fullmatch(r"[a-f0-9]{64}", digest)
            assert hashlib.sha256((object_dir / digest).read_bytes()).hexdigest() == digest
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]

    verify_backup_objects()
    steps = {item["label"]: item for item in historical["steps"]}
    search = steps["public_search"]["body"]
    old_state = steps["workspace"]["body"]
    original_target = {key: search[key] for key in ("request_id", "workspace_id", "restore_epoch")}
    assert original_target["workspace_id"] == old_state["workspace_id"]
    assert original_target["restore_epoch"] == old_state["restore_epoch"]

    restored = subprocess.run([str(core_exe), "--maintenance-restore",
        str(tmp_path / "workspace.sqlite"), str(artifact)], capture_output=True, text=True, timeout=120, check=False)
    restore_receipt = json.loads(restored.stdout) if restored.stdout else {}
    assert restored.returncode == 0 and restore_receipt.get("ok") is True
    assert restore_receipt.get("authorization_requires_new_grants") is True
    core = Core(core_exe, tmp_path, Path(sys.executable))

    def call(method, path, body=None, expected=200):
        assert path.startswith("/api/") and "\r" not in path and "\n" not in path
        status, result = core.request(method, path, body)
        assert status == expected, (method, path, status, result)
        return result

    def check_saved(label):
        step = steps[label]
        assert step["method"] == "GET" and step["status"] == 200
        assert call("GET", step["path"]) == step["body"]

    try:
        core.start()
        # This launch never registers a public-research worker or makes a search request.
        assert core.request("GET", "/api/v1/capabilities/research.public")[0] == 404
        state = call("GET", "/api/v1/workspace/ui-state")
        assert state["workspace_id"] == old_state["workspace_id"]
        assert state["restore_epoch"] != old_state["restore_epoch"]
        call("POST", "/api/v1/research/public/read", original_target, expected=409)
        current_target = {**original_target, "restore_epoch": state["restore_epoch"]}
        assert call("POST", "/api/v1/research/public/read", current_target) == search
        labels = [f"{family}_{kind}" for family in ("community", "encyclopedia", "research")
                  for kind in ("raw_original", "selected_original", "resolve")]
        labels += ["research_read", "package", "export", "admission_read"]
        for label in labels:
            check_saved(label)
        core.stop()
        core.start()
        assert call("POST", "/api/v1/research/public/read", current_target) == search
        for label in labels:
            check_saved(label)
        verify_backup_objects()
        assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == expected_receipt_sha
        assert hashlib.sha256(core_exe.read_bytes()).hexdigest() == core_sha
        if output := os.environ.get("AAOS_TEST_PUBLIC_RESTORE_OUTPUT"):
            result = {"schema": "aaos.public-research-historical-restore/v1", "ok": True,
                "input_receipt_sha256": expected_receipt_sha, "input_backup_sha256": backup["sha256"],
                "core_sha256": core_sha, "receipt_and_core_identity_unchanged": True,
                "families": sorted({item[0] for item in channels if item[2] == "complete"}),
                "source_objects_verified": len(objects), "saved_reads_verified": labels,
                "old_restore_epoch_refused": True, "new_epoch_read_only": True, "restart_verified": True,
                "new_network_calls": 0, "historical_review": "scripted human-principal fixture",
                "scope": "historical public-data restore on a new debug Core; not installed or Owner acceptance"}
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
    finally:
        core.stop()
