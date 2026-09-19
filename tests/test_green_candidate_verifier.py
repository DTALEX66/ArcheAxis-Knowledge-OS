from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.release.assemble_green_candidate import assemble
from scripts.release.verify_green_candidate import main, verify


def _candidate(tmp_path: Path) -> Path:
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    for name in ("ArcheAxis.Desktop.exe", "hostfxr.dll", "hostpolicy.dll", "ArcheAxis.Desktop.runtimeconfig.json"):
        (desktop / name).write_bytes(name.encode())
    core = tmp_path / "core.exe"
    core.write_bytes(b"core")
    project = tmp_path / "project"
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


def test_verifier_requires_workers_when_requested(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    result = verify(candidate, require_workers=True)
    assert result["ok"] is False
    assert any("worker file missing" in problem for problem in result["problems"])
