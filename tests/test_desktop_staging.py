from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from desktop.scripts.assemble_distributions import assemble_green, assemble_portable
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
    destination = repository / ".hermes/rt"
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
    destination = repository / ".hermes/rt"
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
        "../../.hermes/rt/runtime": "runtime"
    }


def test_tauri_maps_webview_profile_to_the_resolved_runtime_data_root() -> None:
    repository = Path(__file__).resolve().parents[1]
    source = (repository / "desktop/src-tauri/src/lib.rs").read_text(encoding="utf-8")

    assert ".data_directory(runtime.data_dir.clone())" in source


def test_root_tauri_shell_creates_its_webview_at_the_resolved_data_root() -> None:
    repository = Path(__file__).resolve().parents[1]
    config = json.loads(
        (repository / "src-tauri/tauri.conf.json").read_text(encoding="utf-8")
    )
    source = (repository / "src-tauri/src/main.rs").read_text(encoding="utf-8")

    assert config["app"]["windows"] == []
    assert "portable_root_for_executable" in source
    assert ".data_directory(webview_data_dir)" in source


def test_root_tauri_shell_closes_its_window_and_exits_after_shutdown() -> None:
    """The packaged root shell must not survive a WM_CLOSE on Windows."""
    repository = Path(__file__).resolve().parents[1]
    source = (repository / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")

    assert "WindowEvent::CloseRequested { api, .. }" in source
    assert "api.prevent_close();" in source
    assert "window.destroy();" not in source
    # Tauri forbids AppHandle::exit directly inside its event-loop callback.
    # Core shutdown must also run off the native callback because it waits for
    # the child process before the exit request is dispatched.
    assert "let app_handle = window.app_handle().clone();" in source
    assert "CLOSE_WATCHDOG_TIMEOUT" in source
    assert "std::thread::sleep(CLOSE_WATCHDOG_TIMEOUT);" in source
    assert "std::process::exit(0);" in source
    assert ".try_lock()" in source
    assert "std::thread::spawn(move || {" in source
    assert "state.take()" in source
    close_handler = source.split(".on_window_event(|window, event| {", 1)[1].split(
        "        })\n        .build", 1
    )[0]
    assert close_handler.index("std::thread::spawn") < close_handler.index("process.shutdown")
    assert close_handler.index("process.shutdown") < close_handler.index("app_handle.exit(0)")


def test_vite_root_is_stable_when_tauri_builds_through_a_windows_junction() -> None:
    repository = Path(__file__).resolve().parents[1]
    vite = (repository / "frontend" / "vite.config.ts").read_text(encoding="utf-8")

    assert 'fileURLToPath(new URL(".", import.meta.url))' in vite
    assert "root: frontendRoot" in vite


def test_portable_launcher_sets_an_explicit_data_root() -> None:
    repository = Path(__file__).resolve().parents[1]
    launcher = (
        repository / "desktop/portable/launch_portable.ps1"
    ).read_text(encoding="utf-8")

    assert "$env:COGNITIVE_PORTABLE_ROOT = $dataRoot" in launcher
    assert "Start-Process -FilePath $portableExe" in launcher
    assert "COGNITIVE_DATA_DIR" not in launcher


def test_green_and_portable_archives_keep_the_shell_runtime_contract(
    monkeypatch, tmp_path
) -> None:
    exe = tmp_path / "ArcheAxis.exe"
    runtime = tmp_path / "runtime"
    frontend = tmp_path / "frontend"
    identity = tmp_path / "release-identity.json"
    exe.write_bytes(b"shell")
    (runtime / "python").mkdir(parents=True)
    (runtime / "python/python.exe").write_bytes(b"python")
    frontend.mkdir()
    (frontend / "index.html").write_text("<main />", encoding="utf-8")
    identity.write_text('{"release": {}}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    green = assemble_green(exe, runtime, frontend, identity, "0.6.0")
    portable = assemble_portable(exe, runtime, frontend, identity, "0.6.0")

    with zipfile.ZipFile(green) as archive:
        green_members = set(archive.namelist())
    with zipfile.ZipFile(portable) as archive:
        portable_members = set(archive.namelist())

    assert "ArcheAxis.Knowledge.Green-x64/runtime/python/python.exe" in green_members
    assert "ArcheAxis.Knowledge.Portable-x64/runtime/python/python.exe" in portable_members
    assert "ArcheAxis.Knowledge.Portable-x64/portable.flag" in portable_members
    assert "ArcheAxis.Knowledge.Portable-x64/data/" in portable_members
    assert not any("/app/runtime/" in name for name in portable_members)
