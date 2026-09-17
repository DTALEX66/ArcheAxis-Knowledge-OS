"""Project-local temporary path contract for the worker smoke checker."""

from __future__ import annotations

import importlib.util
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


def test_worker_checker_rejects_external_temp_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load()
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(ROOT.parent / "worker-outside-test"))
    with pytest.raises(RuntimeError, match=r"inside \.project-local"):
        module._managed_tempdir("test-")
