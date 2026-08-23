from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pytest_temp_roots_stay_inside_project_runtime(tmp_path: Path) -> None:
    common_dir = Path(
        subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    runtime_root = common_dir.parent / ".hermes" / "task-runtime"

    assert Path(tempfile.gettempdir()).resolve().is_relative_to(runtime_root.resolve())
    assert tmp_path.resolve().is_relative_to(runtime_root.resolve())
    assert Path(os.environ["PYTHONPYCACHEPREFIX"]).resolve().is_relative_to(
        runtime_root.resolve()
    )
