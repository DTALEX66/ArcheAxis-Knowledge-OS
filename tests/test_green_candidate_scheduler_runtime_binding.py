from __future__ import annotations

import tempfile
from pathlib import Path

from scripts.release.assemble_green_candidate import assemble


def test_candidate_launcher_binds_bundled_scheduler_python() -> None:
    with tempfile.TemporaryDirectory(prefix="aaos-candidate-scheduler-") as raw:
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
