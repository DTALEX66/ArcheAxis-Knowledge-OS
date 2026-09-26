from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.release.assemble_green_candidate import assemble
from scripts.release.verify_green_candidate import _native_path, main, verify


def _candidate(tmp_path: Path) -> Path:
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    for name in ("ArcheAxis.Desktop.exe", "hostfxr.dll", "hostpolicy.dll", "ArcheAxis.Desktop.runtimeconfig.json"):
        (desktop / name).write_bytes(name.encode())
    core = tmp_path / "core.exe"
    core.write_bytes(b"core")
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.name", "Test"], check=True)
    (project / ".gitignore").write_text(".project-local/\n", encoding="utf-8")
    (project / "build-input.txt").write_text("source v1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(project), "add", ".gitignore", "build-input.txt"], check=True)
    subprocess.run(["git", "-C", str(project), "commit", "-qm", "fixture"], check=True)
    return assemble(
        desktop,
        core,
        project / ".project-local/out",
        "test",
        project_root=project,
        source_commit="commit",
        source_tree="tree",
    ).root


def test_verifier_accepts_complete_candidate(tmp_path: Path) -> None:
    result = verify(_candidate(tmp_path))
    assert result["ok"] is True
    assert result["scope"] == "desktop-core-only"
    assert result["runtime_included"] is False
    assert result["files"] == 6


def test_verifier_rejects_tampered_file(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    (candidate / "core/archeaxis-api.exe").write_bytes(b"tampered")
    assert verify(candidate)["ok"] is False


def test_verifier_reads_manifested_and_unmanifested_deep_windows_paths(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    relative = "runtime/" + "/".join(f"segment-{index:02d}" for index in range(9)) + "/payload.bin"
    payload = candidate.joinpath(*relative.split("/"))
    os.makedirs(_native_path(payload.parent), exist_ok=True)
    with open(_native_path(payload), "wb") as stream:
        stream.write(b"deep payload")
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][relative] = {
        "bytes": len(b"deep payload"),
        "sha256": hashlib.sha256(b"deep payload").hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert verify(candidate)["ok"] is True

    unmanifested = candidate / "runtime" / "extra" / "deep" / "stowaway.bin"
    os.makedirs(_native_path(unmanifested.parent), exist_ok=True)
    with open(_native_path(unmanifested), "wb") as stream:
        stream.write(b"unmanifested")
    result = verify(candidate)
    assert result["ok"] is False
    assert "unmanifested file in candidate: runtime/extra/deep/stowaway.bin" in result["problems"]


def test_verifier_can_require_runtime_for_full_green_audit(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    result = verify(candidate, require_runtime=True)
    assert result["ok"] is False
    assert any("runtime directory is required" in problem for problem in result["problems"])


def test_verifier_rejects_source_provenance_mismatch(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    result = verify(candidate, expected_commit="different", expected_tree="different")
    assert result["ok"] is False
    assert "candidate source commit mismatch" in result["problems"]
    assert "candidate source tree mismatch" in result["problems"]


def test_current_source_gate_accepts_matching_snapshot_and_rejects_changed_source(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    project = candidate.parents[2]

    matching = verify(candidate, require_current_source=True, current_source_root=project)
    assert matching["ok"] is True, matching["problems"]

    (project / "build-input.txt").write_text("source v2\n", encoding="utf-8")
    result = verify(candidate, require_current_source=True, current_source_root=project)
    assert result["ok"] is False
    assert "the current worktree differs from the candidate source snapshot" in result["problems"]


def test_current_source_gate_requires_a_source_root(tmp_path: Path) -> None:
    result = verify(_candidate(tmp_path), require_current_source=True)
    assert result["ok"] is False
    assert any("current source root is required" in item for item in result["problems"])


def test_verifier_can_require_non_blank_provenance(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["provenance"] = {"source_commit": "", "source_tree": None}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = verify(candidate, require_provenance=True)

    assert result["ok"] is False
    assert "candidate provenance source_commit is missing or blank" in result["problems"]
    assert "candidate provenance source_tree is missing or blank" in result["problems"]


def test_cli_exposes_require_provenance_gate(tmp_path: Path, monkeypatch, capsys) -> None:
    candidate = _candidate(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["verify_green_candidate.py", str(candidate), "--require-provenance"],
    )

    assert main() == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_cli_current_source_gate_recomputes_snapshot(tmp_path: Path, monkeypatch, capsys) -> None:
    candidate = _candidate(tmp_path)
    project = candidate.parents[2]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_green_candidate.py",
            str(candidate),
            "--require-current-source",
            "--source-root",
            str(project),
        ],
    )

    assert main() == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_verifier_requires_workers_when_requested(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    result = verify(candidate, require_workers=True)
    assert result["ok"] is False
    assert any("worker file missing" in problem for problem in result["problems"])
