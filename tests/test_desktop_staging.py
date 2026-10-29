from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from desktop.scripts.assemble_distributions import (
    _assembly_output,
    assemble_green,
    assemble_portable,
)
from desktop.scripts.stage_runtime import stage_runtime
from desktop.scripts.prepare_bundle import runtime_build_environment


@pytest.fixture
def runtime_repository(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.startswith("ARCHEAXIS_") or name in {"CARGO_TARGET_DIR", "UV_CACHE_DIR", "UV_PROJECT_ENVIRONMENT"}:
            monkeypatch.delenv(name)
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text(".project-local/\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", ".gitignore"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    return root


def test_runtime_builds_share_owner_cache_but_isolate_wheel_environments(runtime_repository):
    root = runtime_repository
    linked = root / ".project-local/worktrees/linked"
    subprocess.run(["git", "-C", str(root), "worktree", "add", "--detach", str(linked)], check=True, capture_output=True)
    first = runtime_build_environment(root)
    second = runtime_build_environment(linked)
    third = runtime_build_environment(linked)
    assert first["UV_CACHE_DIR"] == second["UV_CACHE_DIR"] == third["UV_CACHE_DIR"] == str(root / ".project-local/cache/uv")
    assert len({value["UV_PROJECT_ENVIRONMENT"] for value in (first, second, third)}) == 3
    for value in (first, second, third):
        assert Path(value["UV_PROJECT_ENVIRONMENT"]).is_relative_to(Path(value["ARCHEAXIS_RUN_ROOT"]) / "tmp")
    assert not (linked / ".project-local/cache/uv-desktop").exists()


def test_runtime_preparation_reuses_only_its_allocated_run(runtime_repository, monkeypatch):
    first = runtime_build_environment(runtime_repository)
    for name, value in first.items():
        monkeypatch.setenv(name, value)
    second = runtime_build_environment(runtime_repository)
    assert first["ARCHEAXIS_RUN_ROOT"] == second["ARCHEAXIS_RUN_ROOT"]
    assert first["UV_PROJECT_ENVIRONMENT"] == second["UV_PROJECT_ENVIRONMENT"]
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(runtime_repository / ".project-local/runs/foreign/run"))
    with pytest.raises(RuntimeError, match="foreign run"):
        runtime_build_environment(runtime_repository)


def test_runtime_preparation_refuses_foreign_checkout_before_allocating(runtime_repository, monkeypatch):
    monkeypatch.setenv("ARCHEAXIS_WORKTREE_ROOT", str(runtime_repository.parent / "foreign"))
    with pytest.raises(RuntimeError, match="foreign worktree"):
        runtime_build_environment(runtime_repository)
    assert not (runtime_repository / ".project-local/runs").exists()


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


@pytest.mark.parametrize("minor", [13, 11])
def test_bundle_runtime_requires_python312_before_any_preparation(monkeypatch, tmp_path, minor):
    from unittest.mock import Mock
    from desktop.scripts import prepare_bundle

    repository = tmp_path / "repo"
    repository.mkdir()
    destination = repository / ".project-local/rt"
    marker = tmp_path / "existing-runtime-ready.marker"
    marker.write_bytes(b"preserve existing runtime marker")
    monkeypatch.setattr(prepare_bundle, "sys", SimpleNamespace(version_info=(3, minor, 0)))
    boundaries = {}
    for name in ("stage_runtime", "runtime_build_environment", "_run"):
        boundaries[name] = Mock(side_effect=AssertionError("preparation must not begin"))
        monkeypatch.setattr(prepare_bundle, name, boundaries[name])
    uv_lookup = Mock(side_effect=AssertionError("uv must not be looked up"))
    monkeypatch.setattr(prepare_bundle.shutil, "which", uv_lookup)

    with pytest.raises(RuntimeError, match=r"请使用 Python 3\.12.*Python 3\." + str(minor)):
        prepare_bundle.prepare_bundle_runtime(repository=repository, destination=destination)

    for boundary in boundaries.values():
        boundary.assert_not_called()
    uv_lookup.assert_not_called()
    assert not destination.parent.exists()
    assert marker.read_bytes() == b"preserve existing runtime marker"


def test_bundle_runtime_python312_reaches_existing_stage_pipeline(monkeypatch, tmp_path):
    from contextlib import nullcontext
    from desktop.scripts import prepare_bundle

    repository = tmp_path / "repo"
    destination = repository / ".project-local/rt"
    observed = []
    monkeypatch.setattr(prepare_bundle, "sys", SimpleNamespace(version_info=(3, 12, 9)))
    monkeypatch.setattr(prepare_bundle.shutil, "which", lambda name: "synthetic-uv" if name == "uv" else None)
    monkeypatch.setattr(prepare_bundle, "runtime_build_environment", lambda root: {"ARCHEAXIS_RUN_ROOT": str(tmp_path / "run")})
    monkeypatch.setattr(prepare_bundle, "BuildTimings", lambda *_: SimpleNamespace(stage=lambda name: nullcontext({})))

    class ReachedOriginalStage(Exception):
        pass

    def original_stage_boundary(**kwargs):
        observed.append(kwargs)
        raise ReachedOriginalStage

    monkeypatch.setattr(prepare_bundle, "stage_runtime", original_stage_boundary)
    with pytest.raises(ReachedOriginalStage):
        prepare_bundle.prepare_bundle_runtime(repository=repository, destination=destination)
    assert observed == [{"repository": repository.resolve(), "destination": destination.resolve()}]
    assert not destination.exists()


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


def test_root_tauri_shell_checks_drafts_then_closes_without_blocking_event_loop() -> None:
    """X/Alt+F4/Exit hold Core until one close decision, then use graceful shutdown."""
    repository = Path(__file__).resolve().parents[1]
    source = (repository / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")

    assert "if let WindowEvent::CloseRequested { api, .. } = event" in source
    assert "api.prevent_close();" in source
    assert "window.destroy();" not in source
    # The process fallback still reclaims its owned Core off the event loop.
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
    assert "close_window_allowed(window.label())?" in exit_command
    assert "window.close()" in exit_command
    assert "begin_backend_exit" not in exit_command
    assert "operations" not in exit_command
    assert ".lock()" not in exit_command

    finish = source.split("fn finish_application_exit", 1)[1].split(
        "fn close_window_allowed", 1
    )[0]
    assert "begin_backend_exit(state" in finish
    assert "app.exit(code)" in finish
    assert 'Some("GRACEFUL" | "NO_OWNED_CORE")' in finish
    assert "cancel_main_window_menu(&app)" in finish

    close_handler = source.split(".on_window_event(|window, event| {", 1)[1].split(
        "// Select the application-local runtime", 1
    )[0]
    assert "request_application_close(window);" in close_handler
    assert "cleanup_backend_on_exit" not in close_handler
    assert "app_handle().exit(" not in close_handler
    assert "thread::sleep" not in close_handler

    confirmation = source.split("fn confirm_owned_application_close", 1)[1].split(
        "fn request_application_close", 1
    )[0]
    assert "GetWindowThreadProcessId" in confirmation
    assert "owner != std::process::id()" in confirmation
    assert "MessageBoxW" in confirmation and "0x134" in confirmation  # YES/NO, default NO
    assert "decision == Some(6)" in confirmation
    assert "state.finish(&id, true)" in confirmation
    assert '"cancelled"' in confirmation and '"failed"' in confirmation


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

    output = tmp_path / "out"
    green = assemble_green(exe, runtime, frontend, identity, "0.6.0", output)
    portable = assemble_portable(exe, runtime, frontend, identity, "0.6.0", output)

    with zipfile.ZipFile(green) as archive:
        green_members = set(archive.namelist())
    with zipfile.ZipFile(portable) as archive:
        portable_members = set(archive.namelist())

    assert "ArcheAxis.Knowledge.Green-x64/runtime/python/python.exe" in green_members
    assert "ArcheAxis.Knowledge.Portable-x64/runtime/python/python.exe" in portable_members
    assert "ArcheAxis.Knowledge.Portable-x64/portable.flag" in portable_members
    assert "ArcheAxis.Knowledge.Portable-x64/data/" in portable_members
    assert not any("/app/runtime/" in name for name in portable_members)
    assert not (tmp_path / "ArcheAxis.Knowledge.Green-x64").exists()
    assert not (tmp_path / "ArcheAxis.Knowledge.Portable-x64").exists()
    assert green.parent == output


def test_distribution_default_output_is_anchored_to_repository_root() -> None:
    expected = Path(__file__).resolve().parents[1] / ".project-local/task-runtime/release-assembly"
    assert _assembly_output(None) == expected


def test_backend_candidate_delegates_layout_to_the_authoritative_stager(monkeypatch, tmp_path):
    """Stub dependency installation, but execute the authority's actual layout code."""
    import importlib.util
    import io
    import sys

    from desktop.scripts import prepare_bundle

    repository = Path(__file__).resolve().parents[1]
    script = repository / "scripts/release/stage_backend_runtime.py"
    spec = importlib.util.spec_from_file_location("candidate_stager_test", script)
    authority = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(authority)
    monkeypatch.setattr(authority, "validate_app_local_vc_runtime", lambda runtime: None)
    monkeypatch.setattr(authority, "validate_cpp_runtime", lambda runtime: {})
    monkeypatch.setattr(prepare_bundle, "resolve_vc_runtime", lambda explicit=None: tmp_path / "vc-donor")
    def synthetic_vc(runtime, root, vc_runtime=None):
        for name in ("vcruntime140.dll", "vcruntime140_1.dll"):
            for directory in (root, root / "core"):
                directory.mkdir(parents=True, exist_ok=True)
                (directory / name).write_bytes(b"synthetic " + name.encode())
        return {"files": 2}
    monkeypatch.setattr(authority, "stage_app_local_vc_runtime", synthetic_vc)
    destination = tmp_path / "candidate"
    core = tmp_path / "archeaxis-api.exe"
    core.write_bytes(b"synthetic Core fixture")
    observed = []
    monkeypatch.delenv("CARGO_TARGET_DIR", raising=False)

    def prepare_runtime(*, repository, destination):
        python = destination / "runtime/python/python.exe"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"synthetic interpreter fixture")
        packages = python.parent / "Lib/site-packages"
        (packages / "fastapi/.agents").mkdir(parents=True)
        (packages / "fastapi/.agents/upstream.md").write_text("upstream")
        info = packages / "fastapi-1.0.dist-info"
        info.mkdir()
        (info / "RECORD").write_text("fastapi/.agents/upstream.md,,\n")
        return python

    def stage(command, *, cwd=None, check=None, **kwargs):
        if command and str(command[0]).endswith("python.exe") and str(script) not in {str(item) for item in command}:
            return SimpleNamespace(stdout="3.13.0\n", stderr="", returncode=0)
        observed.append(command)
        assert command[:3] == [sys.executable, "-B", str(script)]
        assert cwd == repository and check is True
        with monkeypatch.context() as context:
            context.setattr(sys, "argv", command[2:])
            context.setattr(authority, "packager_identity", lambda: "synthetic-tooling")
            context.setattr(authority.os, "popen", lambda *_: io.StringIO("synthetic-version"))
            assert authority.main() == 0

    monkeypatch.setattr(prepare_bundle, "prepare_bundle_runtime", prepare_runtime)
    monkeypatch.setattr(prepare_bundle.subprocess, "check_output", lambda command, **_: "synthetic-tree\n" if "HEAD^{tree}" in command else "synthetic-commit\n")
    monkeypatch.setattr(prepare_bundle.subprocess, "run", stage)
    python = prepare_bundle.prepare_backend_candidate(repository=repository, destination=destination, core=core)

    assert len(observed) == 1
    assert observed[0][observed[0].index("--vc-runtime") + 1] == str(tmp_path / "vc-donor")
    assert python == destination / "runtime/python.exe"
    assert python.read_bytes() == b"synthetic interpreter fixture"
    config = json.loads((repository / "src-tauri/tauri.conf.json").read_text())
    for resource in config["bundle"]["resources"].values():
        assert (destination / resource).exists(), resource
    profile = json.loads((destination / "worker-profile.json").read_text())
    assert profile["python"] == "runtime/python.exe"
    assert profile["script"] == "workers/transport/text_ndjson.py"
    assert (destination / "runtime/Lib/site-packages/fastapi/.agents/upstream.md").is_file()
