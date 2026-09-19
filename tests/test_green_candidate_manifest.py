"""Regression tests for the project-local Green candidate manifest gate."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_green_candidate", ROOT / "scripts" / "release" / "verify_green_candidate.py"
)
assert SPEC and SPEC.loader
VERIFY_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY_MODULE)


def _write_candidate(tmp_path: Path) -> Path:
    candidate = tmp_path / "candidate"
    for relative in VERIFY_MODULE.REQUIRED:
        path = candidate / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"fixture:{relative}".encode("utf-8"))
    files = {}
    for relative in VERIFY_MODULE.REQUIRED:
        path = candidate / relative
        payload = path.read_bytes()
        files[relative] = {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    (candidate / "candidate-manifest.json").write_text(
        json.dumps(
            {
                "schema": "archeaxis.green-candidate/v1",
                "version": "test",
                "provenance": {"source_commit": "a" * 40, "source_tree": "b" * 40},
                "files": files,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return candidate


def test_verify_checks_manifest_bytes_and_hashes_and_provenance(tmp_path: Path) -> None:
    candidate = _write_candidate(tmp_path)

    result = VERIFY_MODULE.verify(
        candidate,
        expected_commit="a" * 40,
        expected_tree="b" * 40,
    )

    assert result["ok"] is True
    assert result["files"] == len(VERIFY_MODULE.REQUIRED)


def test_verify_rejects_manifest_byte_count_tampering(tmp_path: Path) -> None:
    candidate = _write_candidate(tmp_path)
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][VERIFY_MODULE.REQUIRED[-1]]["bytes"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = VERIFY_MODULE.verify(candidate)

    assert result["ok"] is False
    assert any("byte count mismatch" in problem for problem in result["problems"])


def test_verify_fails_closed_for_malformed_files_manifest(tmp_path: Path) -> None:
    candidate = _write_candidate(tmp_path)
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = VERIFY_MODULE.verify(candidate)

    assert result["ok"] is False
    assert "candidate files manifest is missing or invalid" in result["problems"]


def test_verify_rejects_manifest_path_escape(tmp_path: Path) -> None:
    candidate = _write_candidate(tmp_path)
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["../outside.bin"] = {"bytes": 0, "sha256": "0" * 64}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = VERIFY_MODULE.verify(candidate)

    assert result["ok"] is False
    assert any("unsafe candidate manifest path" in problem for problem in result["problems"])
