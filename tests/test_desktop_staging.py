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
    destination = repository / ".project-local/rt"
    _fake_python(monkeypatch, source)

    staged_python = stage_runtime(repository=repository, destination=destination)

    assert staged_python == destination / "runtime/python/python.exe"
    assert (destination / "runtime/python/Lib/os.py").is_file()
    assert not (destination / "runtime/python/Lib/site-packages").exists()
    assert not (destination / "runtime/python/Lib/__pycache__").exists()


def test_stage_runtime_refuses_paths_outside_project_ignored_root(monkeypatch, tmp_path) -> None:
    source = tmp_path / "base-python"
    _fake_python(monkeypatch, source)

    with pytest.raises(RuntimeError, match="repository .project-local"):
        stage_runtime(
            repository=tmp_path / "repo",
            destination=tmp_path / "outside-runtime",
        )


def test_stage_runtime_refuses_to_overwrite_existing_destination(monkeypatch, tmp_path) -> None:
    repository = tmp_path / "repo"
    source = tmp_path / "base-python"
    destination = repository / ".project-local/rt"
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
        "../../.project-local/rt/runtime": "runtime"
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


def test_root_tauri_shell_closes_immediately_and_cleans_up_off_event_loop() -> None:
    """WM_CLOSE and explicit Exit must never wait on a long recovery operation."""
    repository = Path(__file__).resolve().parents[1]
    source = (repository / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")

    assert "matches!(event, WindowEvent::CloseRequested { .. })" in source
    assert "api.prevent_close();" not in source
    assert "window.destroy();" not in source
    # Tauri's default WM_CLOSE path remains in control. Core cleanup is always
    # offloaded; the Job Object reclaims the child if app exit wins the race.
    cleanup_helper = source.split("fn cleanup_backend_on_exit", 1)[1].split(
        "#[tauri::command]", 1
    )[0]
    assert "std::thread::spawn(move || {" in cleanup_helper
    assert "process.take()" in cleanup_helper
    assert cleanup_helper.index("std::thread::spawn") < cleanup_helper.index(
        "process.shutdown"
    )

    exit_command = source.split("fn exit_application", 1)[1].split(
        "#[cfg(windows)]\nfn main", 1
    )[0]
    assert "app.exit(code)" in exit_command
    assert "operations" not in exit_command
    assert ".lock()" not in exit_command

    close_handler = source.split(".on_window_event(|window, event| {", 1)[1].split(
        "        })\n        .build", 1
    )[0]
    assert "cleanup_backend_on_exit(state);" in close_handler


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
