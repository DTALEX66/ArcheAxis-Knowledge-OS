from __future__ import annotations

import json
from pathlib import Path

import pytest

from desktop.scripts.stage_runtime import stage_runtime


def _fake_python(monkeypatch, root: Path) -> None:
    (root / "Lib/site-packages").mkdir(parents=True)
    (root / "Lib/__pycache__").mkdir()
    (root / "python.exe").write_bytes(b"python")
    (root / "Lib/os.py").write_text("# stdlib", encoding="utf-8")
    (root / "Lib/site-packages/local.py").write_text("# local", encoding="utf-8")
    (root / "Lib/__pycache__/os.pyc").write_bytes(b"cache")
    monkeypatch.setattr("desktop.scripts.stage_runtime.sys.base_prefix", str(root))


def test_stage_runtime_copies_base_python_without_local_packages(monkeypatch, tmp_path) -> None:
    repository = tmp_path / "repo"
    source = tmp_path / "base-python"
    destination = repository / ".hermes/desktop-runtime-v1"
    _fake_python(monkeypatch, source)

    staged_python = stage_runtime(repository=repository, destination=destination)

    assert staged_python == destination / "runtime/python/python.exe"
    assert (destination / "runtime/python/Lib/os.py").is_file()
    assert not (destination / "runtime/python/Lib/site-packages").exists()
    assert not (destination / "runtime/python/Lib/__pycache__").exists()


def test_stage_runtime_refuses_paths_outside_project_ignored_root(monkeypatch, tmp_path) -> None:
    source = tmp_path / "base-python"
    _fake_python(monkeypatch, source)

    with pytest.raises(RuntimeError, match="repository .hermes"):
        stage_runtime(
            repository=tmp_path / "repo",
            destination=tmp_path / "outside-runtime",
        )


def test_stage_runtime_refuses_to_overwrite_existing_destination(monkeypatch, tmp_path) -> None:
    repository = tmp_path / "repo"
    source = tmp_path / "base-python"
    destination = repository / ".hermes/desktop-runtime-v1"
    _fake_python(monkeypatch, source)
    destination.mkdir(parents=True)

    with pytest.raises(RuntimeError, match="already exists"):
        stage_runtime(repository=repository, destination=destination)


def test_tauri_maps_the_staged_runtime_to_the_installed_runtime_root() -> None:
    repository = Path(__file__).resolve().parents[1]
    config = json.loads(
        (repository / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8")
    )

    assert config["bundle"]["resources"] == {
        "../../.hermes/desktop-runtime-v1/runtime": "runtime"
    }
