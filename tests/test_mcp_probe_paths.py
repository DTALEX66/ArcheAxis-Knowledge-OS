"""The live MCP probe must isolate databases in the owning development run."""

import importlib.util
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "mcp_probe_paths", REPO / "scripts/probes/r11_mcp_client_smoke.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def test_repeated_probe_allocations_use_distinct_databases_in_current_run():
    run = Path(os.environ["ARCHEAXIS_RUN_ROOT"])
    first = probe.allocate_database()
    second = probe.allocate_database()
    assert first != second
    assert first.is_relative_to(run / "artifacts")
    assert second.is_relative_to(run / "artifacts")
    assert first.parent.is_dir()
    assert not first.exists()


def test_probe_rejects_a_run_outside_its_worktree_before_writing(monkeypatch, tmp_path):
    foreign = tmp_path / "foreign-run"
    foreign.mkdir()
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(foreign))
    with pytest.raises(ValueError, match="different worktree"):
        probe.allocate_database()
    assert list(foreign.iterdir()) == []
