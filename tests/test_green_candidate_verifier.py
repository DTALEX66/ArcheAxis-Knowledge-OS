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
    return assemble(desktop, core, project / ".project-local/out", "test", project_root=project).root


def test_verifier_accepts_complete_candidate(tmp_path: Path) -> None:
    result = verify(_candidate(tmp_path))
    assert result["ok"] is True
    assert result["files"] == 5


def test_verifier_rejects_tampered_file(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    (candidate / "core/archeaxis-api.exe").write_bytes(b"tampered")
    assert verify(candidate)["ok"] is False
