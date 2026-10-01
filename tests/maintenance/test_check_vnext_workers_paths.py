"""Project-local temporary path contract for the worker smoke checker."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/check_vnext_workers.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_vnext_workers", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_worker_checker_tempdir_stays_inside_project_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load()
    managed_root = tmp_path / ".project-local" / "run-1"
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(managed_root))
    with module._managed_tempdir("test-") as value:
        created = Path(value)
        assert created.is_dir()
        assert created.is_relative_to(tmp_path / ".project-local")
    assert not created.exists()


def _path_outside(dev_root: Path) -> Path:
    """A path that is provably not inside `dev_root`, derived from it.

    Neither convenient source of an "outside" path works here: this repository redirects
    pytest's `tmp_path` *and* the system temporary directory under `.project-local/runs/`,
    and `ROOT.parent` is outside `.project-local` in a canonical checkout but inside it in a
    git worktree under `.project-local/worktrees/`. Climbing out of the ancestor chain gives
    an answer that holds in every layout, without writing anything.
    """
    candidate = Path(dev_root.anchor)
    for part in dev_root.parts[1:]:
        candidate = candidate / part
        sibling = candidate.parent / "archeaxis-outside-the-managed-root"
        if not sibling.is_relative_to(dev_root):
            return sibling
    raise AssertionError("could not derive a path outside the managed root")


def test_worker_checker_rejects_external_temp_root(monkeypatch: pytest.MonkeyPatch):
    """A run root outside `.project-local` is refused.

    The old form used `ROOT.parent`, which is outside `.project-local` in a canonical
    checkout but *inside* it in a git worktree under `.project-local/worktrees/` - so it
    failed for the layout rather than for the rule, and in that layout the checker correctly
    accepted the path, meaning the test was not testing the rule at all.
    """
    module = _load()
    dev_root = Path(os.environ["ARCHEAXIS_DEV_ROOT"])
    outside = _path_outside(dev_root)
    assert not outside.is_relative_to(dev_root)
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(outside))
    with pytest.raises(RuntimeError, match=r"inside \.project-local"):
        module._managed_tempdir("test-")


def test_worker_checker_rejects_parent_traversal(monkeypatch: pytest.MonkeyPatch):
    module = _load()
    dev_root = Path(os.environ["ARCHEAXIS_DEV_ROOT"])
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(dev_root / ".." / "escaped"))
    with pytest.raises(RuntimeError, match=r"inside \.project-local"):
        module._managed_tempdir("test-")


def test_worker_checker_accepts_launcher_run_root():
    module = _load()
    run_root = Path(os.environ["ARCHEAXIS_RUN_ROOT"])
    with module._managed_tempdir("launcher-") as value:
        assert Path(value).is_relative_to(run_root)
