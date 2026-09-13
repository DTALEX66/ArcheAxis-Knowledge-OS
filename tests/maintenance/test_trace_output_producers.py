"""Boundaries for the read-only output producer tracer."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/maintenance/trace_output_producers.py"


def load_module():
    spec = importlib.util.spec_from_file_location("trace_output_producers", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init_git(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_trace_finds_tokens_without_private_state(tmp_path: Path):
    init_git(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "runner.py").write_text(
        "from pathlib import Path\nroot = Path(ARCHEAXIS_RUN_ROOT)\nroot.joinpath('out').mkdir()\n",
        encoding="utf-8",
    )
    (tmp_path / ".zcode").mkdir()
    (tmp_path / ".zcode" / "private.py").write_text("TEMP=/secret\n", encoding="utf-8")
    report = load_module().trace_output_producers(tmp_path)
    assert len(report["rows"]) == 1
    assert report["rows"][0]["canonical_path"] == "ARCHEAXIS_RUN_ROOT"
    assert all(".zcode" not in row["entrypoint"] for row in report["rows"])


def test_trace_rejects_non_git_and_protected_drive(tmp_path: Path):
    module = load_module()
    with pytest.raises(ValueError, match="exact Git project root"):
        module.trace_output_producers(tmp_path)
    with pytest.raises(ValueError, match="protected drive"):
        module.trace_output_producers(Path("E:/not-authorized"))


def test_cli_output_must_stay_project_local(tmp_path: Path):
    init_git(tmp_path)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "--output", str(tmp_path / "outside.json")],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 1
    assert "output path" in result.stdout
    assert not (tmp_path / "outside.json").exists()
