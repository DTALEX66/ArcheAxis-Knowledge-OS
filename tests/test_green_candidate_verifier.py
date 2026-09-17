from __future__ import annotations

from pathlib import Path

from scripts.release.assemble_green_candidate import assemble
from scripts.release.verify_green_candidate import verify


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


def test_verifier_requires_workers_when_requested(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    result = verify(candidate, require_workers=True)
    assert result["ok"] is False
    assert any("worker file missing" in problem for problem in result["problems"])
