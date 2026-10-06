from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from scripts.release.assemble_green_candidate import assemble


@contextmanager
def candidate_fixture_directory():
    # Keep the full canonical test-root depth. Only cleanup's private filesystem
    # operation gets a Windows extended path; product inputs retain normal paths.
    raw = tempfile.mkdtemp(prefix="aaos-candidate-scheduler-")
    owned = Path(raw).absolute()
    parent = Path(tempfile.gettempdir()).absolute()
    assert owned.parent == parent and owned.name.startswith("aaos-candidate-scheduler-")
    try:
        yield raw
    finally:
        cleanup = str(owned)
        if os.name == "nt" and not cleanup.startswith("\\\\?\\"):
            cleanup = (
                "\\\\?\\UNC\\" + cleanup[2:] if cleanup.startswith("\\\\") else "\\\\?\\" + cleanup
            )
        shutil.rmtree(cleanup)
        assert not Path(cleanup).exists(), "owned candidate fixture cleanup failed"


def test_candidate_launcher_binds_bundled_scheduler_python() -> None:
    with candidate_fixture_directory() as raw:
        temp = Path(raw)
        project = temp / "project"
        desktop = temp / "desktop"
        desktop.mkdir()
        (desktop / "ArcheAxis.Desktop.exe").write_bytes(b"desktop")
        core = temp / "core.exe"
        core.write_bytes(b"core")
        runtime = temp / "runtime"
        runtime.mkdir()
        (runtime / "python.exe").write_bytes(b"python")

        result = assemble(
            desktop,
            core,
            project / ".project-local" / "staging",
            "scheduler-python-contract",
            runtime=runtime,
            project_root=project,
        )
        launcher = (result.root / "启动绿色候选.vbs").read_text(encoding="utf-8")

        assert '"ARCHEAXIS_PYTHON"' in launcher
        assert 'root & "\\runtime\\python.exe"' in launcher
