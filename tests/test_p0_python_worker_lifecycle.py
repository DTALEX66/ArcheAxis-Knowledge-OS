"""P0-W01: compose the capability-store gate with the real text worker.

This is deliberately a test-only contract.  The production worker remains
owned by Rust Core; this test does not add a second Python-side runner or claim
that the current desktop launch path consults ``CapabilityStore``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.capability.store import CapabilityStore
from shared.plugin_manifest import PluginManifest, load_manifest_from_mapping

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "services" / "python-workers" / "transport" / "text_ndjson.py"
PLUGIN_ID = "ax.builtin.worker.text-ndjson"


def _manifest() -> PluginManifest:
    return load_manifest_from_mapping(
        {
            "manifest_version": "1.0",
            "plugin_id": PLUGIN_ID,
            "name": "Text NDJSON Worker (P0 contract fixture)",
            "version": "1.0.0",
            "api_contract": "1.x",
            "permissions": ["files.read", "files.write", "process"],
            "platform": {"os": "any", "arch": "any"},
            "entry": WORKER.relative_to(ROOT).as_posix(),
            "data_ownership": {
                "declared": True,
                "note": "writes candidate outputs only inside the Core-owned staging directory",
            },
            "healthcheck": "worker-hello:text.extract",
        }
    )


def _request(staging: Path, raw: bytes, request_id: str) -> dict[str, Any]:
    digest = hashlib.sha256(raw).hexdigest()
    input_dir = staging / "input"
    output_dir = staging / "output"
    input_dir.mkdir(parents=True)
    output_dir.mkdir()
    (input_dir / digest).write_bytes(raw)
    return {
        "schema": "archeaxis.worker-request/v1",
        "type": "job_request",
        "request_id": request_id,
        "job_id": f"job-{request_id}",
        "attempt": 1,
        "protocol_minor": 0,
        "capability": "text.extract",
        "capability_version": "1",
        "deadline_ms": 5000,
        "inputs": [
            {
                "uri": f"job://input/{digest}",
                "sha256": digest,
                "media_type": "text/plain",
            }
        ],
        "parameters": {},
    }


def _launch(entry: Path, staging: Path, request: dict[str, Any]) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], dict[str, Any]]:
    process = subprocess.run(
        [sys.executable, "-B", "-S", str(entry), "--staging-root", str(staging)],
        input=json.dumps(request) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    frames = process.stdout.splitlines()
    assert len(frames) == 2, process.stdout + process.stderr
    hello, response = (json.loads(frame) for frame in frames)
    return process, hello, response


Launcher = Callable[
    [Path, Path, dict[str, Any]],
    tuple[subprocess.CompletedProcess[str], dict[str, Any], dict[str, Any]],
]


class _TemporaryWorkerGate:
    """Test-only enable/disable gate around the repository's real worker."""

    def __init__(
        self,
        store: CapabilityStore,
        manifest: PluginManifest,
        launcher: Launcher = _launch,
    ) -> None:
        self.store = store
        self.manifest = manifest
        self.launcher = launcher

    def execute(
        self, staging: Path, request: dict[str, Any]
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], dict[str, Any]]:
        installed = {record.plugin_id for record in self.store.list_installed()}
        if self.manifest.plugin_id not in installed:
            raise RuntimeError(f"worker plugin is not enabled: {self.manifest.plugin_id}")
        entry = (ROOT / self.manifest.entry).resolve()
        if not entry.is_relative_to(ROOT) or entry != WORKER.resolve() or not entry.is_file():
            raise RuntimeError("worker manifest entry is not the repository text worker")
        return self.launcher(entry, staging, request)


def _assert_success(
    staging: Path,
    process: subprocess.CompletedProcess[str],
    hello: dict[str, Any],
    response: dict[str, Any],
) -> None:
    assert process.returncode == 0, process.stderr
    assert hello == {
        "schema": "archeaxis.worker-hello/v1",
        "type": "hello",
        "protocol": {"major": 1, "min_minor": 0, "max_minor": 0},
        "worker": {"name": "python-worker-text-ndjson", "version": "1"},
        "capabilities": ["text.extract"],
        "schemas": [
            "archeaxis.text/v1",
            "archeaxis.document-structure/v1",
            "archeaxis.loss-receipt/v1",
        ],
    }
    assert response["status"] == "succeeded"
    assert {output["kind"] for output in response["outputs"]} == {
        "text",
        "document_structure",
        "loss_report",
    }
    for output in response["outputs"]:
        assert output["authority_effect"] == "candidate_or_measurement_only"
        payload = (staging / "output" / output["sha256"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == output["sha256"]
        assert len(payload) == output["byte_length"]


def test_real_text_worker_health_execute_failure_disable_and_enable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest()
    assert manifest.healthcheck == "worker-hello:text.extract"
    store = CapabilityStore(tmp_path / "capability-store")
    store.install_builtin(manifest)
    gate = _TemporaryWorkerGate(store, manifest)

    success_staging = tmp_path / "staging-success"
    success = gate.execute(
        success_staging,
        _request(success_staging, b"first\r\nsecond\n", "success"),
    )
    _assert_success(success_staging, *success)

    failure_staging = tmp_path / "staging-failure"
    failed_process, failed_hello, failed_response = gate.execute(
        failure_staging,
        _request(failure_staging, b"\xff\xfe\x01", "failure"),
    )
    assert failed_hello["capabilities"] == ["text.extract"]
    assert failed_process.returncode != 0
    assert failed_response["status"] == "failed"
    assert failed_response["outputs"] == []
    assert list((failure_staging / "output").iterdir()) == []

    disabled = store.disable(PLUGIN_ID)
    assert disabled.status == "disabled"
    launches = 0

    def forbidden_launch(
        entry: Path, staging: Path, request: dict[str, Any]
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], dict[str, Any]]:
        nonlocal launches
        launches += 1
        raise AssertionError("disabled worker must not be started")

    monkeypatch.setattr(gate, "launcher", forbidden_launch)
    disabled_staging = tmp_path / "staging-disabled"
    disabled_request = _request(disabled_staging, b"must not run\n", "disabled")
    with pytest.raises(RuntimeError, match="not enabled"):
        gate.execute(disabled_staging, disabled_request)
    assert launches == 0
    assert list((disabled_staging / "output").iterdir()) == []

    enabled = store.enable(PLUGIN_ID)
    assert enabled.status == "installed"
    monkeypatch.setattr(gate, "launcher", _launch)
    restored_staging = tmp_path / "staging-restored"
    restored = gate.execute(
        restored_staging,
        _request(restored_staging, b"restored\n", "restored"),
    )
    _assert_success(restored_staging, *restored)

    for staging in (
        success_staging,
        failure_staging,
        disabled_staging,
        restored_staging,
    ):
        assert {path.name for path in staging.iterdir()} <= {"input", "output"}
    assert not list(tmp_path.rglob("*.db"))
    assert not list(tmp_path.rglob("*.sqlite"))
