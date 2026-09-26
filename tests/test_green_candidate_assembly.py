from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.release.assemble_green_candidate import _native_path, assemble


def test_assembly_bundles_desktop_and_core_with_hash_manifest(tmp_path: Path) -> None:
    project = tmp_path / "project"
    local = project / ".project-local"
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    (desktop / "ArcheAxis.Desktop.exe").write_bytes(b"desktop")
    (desktop / "hostfxr.dll").write_bytes(b"runtime")
    core = tmp_path / "archeaxis-api.exe"
    core.write_bytes(b"core")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "python.exe").write_bytes(b"python")

    result = assemble(
        desktop,
        core,
        local / "build" / "green-candidates",
        "0.0.0-test",
        runtime=runtime,
        project_root=project,
        source_commit="abc123",
        source_tree="tree123",
    )

    assert result.zip_path.is_file()
    with open(_native_path(result.root / "desktop" / "ArcheAxis.Desktop.exe"), "rb") as stream:
        assert stream.read() == b"desktop"
    with open(_native_path(result.root / "core" / "archeaxis-api.exe"), "rb") as stream:
        assert stream.read() == b"core"
    with open(_native_path(result.root / "candidate-manifest.json"), encoding="utf-8") as stream:
        manifest = json.load(stream)
    assert manifest["schema"] == "archeaxis.green-candidate/v1"
    assert manifest["files"]["desktop/ArcheAxis.Desktop.exe"]["sha256"]
    assert manifest["files"]["core/archeaxis-api.exe"]["sha256"]
    assert manifest["files"]["runtime/python.exe"]["sha256"]
    assert manifest["provenance"]["source_commit"] == "abc123"
    assert manifest["provenance"]["source_tree"] == "tree123"
    assert manifest["provenance"]["source_snapshot"] is None
    launcher = result.root / "启动绿色候选.vbs"
    assert launcher.is_file()
    launcher_text = launcher.read_text(encoding="utf-8")
    assert '"ARCHAXIS_CORE_BIN"' in launcher_text
    assert "desktop\\ArcheAxis.Desktop.exe" in launcher_text

    # Reassembly exercises the generated-tree cleanup path, which must work
    # even when runtime files make the candidate tree deeply nested on Windows.
    second = assemble(
        desktop,
        core,
        local / "build" / "green-candidates",
        "0.0.0-test",
        runtime=runtime,
        project_root=project,
    )
    assert second.root == result.root
    assert (second.root / "启动绿色候选.vbs").is_file()


def test_assembly_rejects_output_outside_project_local(tmp_path: Path) -> None:
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    (desktop / "ArcheAxis.Desktop.exe").write_bytes(b"desktop")
    core = tmp_path / "core.exe"
    core.write_bytes(b"core")

    with pytest.raises(ValueError, match="project-local"):
        assemble(desktop, core, tmp_path / "outside", "0.0.0-test", project_root=tmp_path / "project")


def test_assembly_rejects_reparse_inputs(tmp_path: Path) -> None:
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    (desktop / "ArcheAxis.Desktop.exe").write_bytes(b"desktop")
    core = tmp_path / "core.exe"
    core.write_bytes(b"core")
    link = desktop / "external-link"
    try:
        link.symlink_to(core)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(ValueError, match="reparse"):
        assemble(desktop, core, tmp_path / "project" / ".project-local/out", "test", project_root=tmp_path / "project")


def test_assembly_refuses_source_snapshot_change_during_packaging(tmp_path: Path, monkeypatch) -> None:
    import scripts.release.assemble_green_candidate as assembler

    desktop = tmp_path / "desktop"
    desktop.mkdir()
    (desktop / "ArcheAxis.Desktop.exe").write_bytes(b"desktop")
    core = tmp_path / "core.exe"
    core.write_bytes(b"core")
    project = tmp_path / "project"
    project.mkdir()
    snapshots = [
        {"algorithm": "aaos-source-snapshot/v1", "sha256": "a" * 64},
        {"algorithm": "aaos-source-snapshot/v1", "sha256": "b" * 64},
    ]
    monkeypatch.setattr(assembler, "_source_snapshot_or_none", lambda _root: snapshots.pop(0))

    with pytest.raises(ValueError, match="source worktree changed"):
        assemble(desktop, core, project / ".project-local/out", "test", project_root=project)


def test_assembly_rejects_a_snapshot_staled_by_the_build(tmp_path: Path) -> None:
    import subprocess

    from scripts.release.candidate import working_tree_snapshot

    desktop = tmp_path / "desktop"
    desktop.mkdir()
    (desktop / "ArcheAxis.Desktop.exe").write_bytes(b"desktop")
    core = tmp_path / "core.exe"
    core.write_bytes(b"core")
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.name", "Test"], check=True)
    (project / ".gitignore").write_text(".project-local/\n", encoding="utf-8")
    source = project / "build-input.txt"
    source.write_text("before build\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(project), "add", ".gitignore", "build-input.txt"], check=True)
    subprocess.run(["git", "-C", str(project), "commit", "-qm", "fixture"], check=True)
    captured = working_tree_snapshot(project)
    source.write_text("changed during build\n", encoding="utf-8")

    with pytest.raises(ValueError, match="captured source snapshot does not match"):
        assemble(
            desktop,
            core,
            project / ".project-local/out",
            "test",
            project_root=project,
            source_snapshot=captured,
        )


def test_assembly_bundles_workers_and_portable_profile(tmp_path: Path) -> None:
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    for name in ("ArcheAxis.Desktop.exe", "hostfxr.dll", "hostpolicy.dll", "ArcheAxis.Desktop.runtimeconfig.json"):
        (desktop / name).write_bytes(name.encode())
    core = tmp_path / "core.exe"
    core.write_bytes(b"core")
    runtime = tmp_path / "runtime"
    (runtime / "python").mkdir(parents=True)
    (runtime / "python" / "python.exe").write_bytes(b"python")
    workers = tmp_path / "workers"
    (workers / "transport").mkdir(parents=True)
    (workers / "transport" / "text_ndjson.py").write_text("print('ok')\n", encoding="utf-8")
    result = assemble(desktop, core, tmp_path / "project" / ".project-local/out", "test",
                      runtime=runtime, workers=workers, project_root=tmp_path / "project")
    profile = json.loads((result.root / "worker-profile.json").read_text(encoding="utf-8"))
    assert profile["python"] == "runtime/python.exe"
    assert (result.root / "workers/transport/text_ndjson.py").is_file()


def test_assembly_includes_files_beyond_legacy_windows_path_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os
    import zipfile

    project = tmp_path / "project"
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    (desktop / "ArcheAxis.Desktop.exe").write_bytes(b"desktop")
    core = tmp_path / "core.exe"
    core.write_bytes(b"core")
    runtime = tmp_path / "runtime"
    runtime.mkdir()

    nested = runtime
    while len(str(nested / "payload.dll")) < 260:
        nested = nested / "runtime-component-with-a-long-name"
    os.makedirs(_native_path(nested), exist_ok=True)
    with open(_native_path(nested / "payload.dll"), "wb") as payload:
        payload.write(b"long-path-runtime-payload")

    # Reproduce Windows Path.is_file() reporting False once the ordinary path
    # crosses MAX_PATH, while the native extended path remains readable.
    original_is_file = Path.is_file

    def legacy_path_is_file(path: Path) -> bool:
        if path.drive and len(str(path)) >= 240:
            return False
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", legacy_path_is_file)
    result = assemble(
        desktop,
        core,
        project / ".project-local/out",
        "long-path-test",
        runtime=runtime,
        project_root=project,
    )

    relative = "runtime/" + nested.relative_to(runtime).as_posix() + "/payload.dll"
    with open(_native_path(result.root / "candidate-manifest.json"), encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    assert relative in manifest["files"]
    assert manifest["files"][relative]["bytes"] == len(b"long-path-runtime-payload")
    with zipfile.ZipFile(_native_path(result.zip_path)) as archive:
        assert any(name.endswith(relative) for name in archive.namelist())
    assert '"ARCHEAXIS_WORKER_PROFILE"' in (result.root / "启动绿色候选.vbs").read_text(encoding="utf-8")


def test_assembly_resolves_relative_runtime_and_worker_roots(tmp_path: Path, monkeypatch) -> None:
    import os
    import zipfile

    monkeypatch.chdir(tmp_path)
    project = Path("project")
    desktop = Path("desktop")
    desktop.mkdir()
    (desktop / "ArcheAxis.Desktop.exe").write_bytes(b"desktop")
    core = Path("core.exe")
    core.write_bytes(b"core")
    runtime = Path("runtime")
    workers = Path("workers")
    nested_runtime = runtime
    nested_workers = workers
    while len(str((tmp_path / nested_runtime / "LICENSE.txt").resolve())) < 260:
        nested_runtime /= "runtime-component-with-a-long-name"
    while len(str((tmp_path / nested_workers / "worker.py").resolve())) < 260:
        nested_workers /= "worker-component-with-a-long-name"
    os.makedirs(_native_path((tmp_path / nested_runtime).resolve()), exist_ok=True)
    os.makedirs(_native_path((tmp_path / nested_workers).resolve()), exist_ok=True)
    with open(_native_path((tmp_path / nested_runtime / "LICENSE.txt").resolve()), "w", encoding="utf-8") as stream:
        stream.write("runtime license")
    with open(_native_path((tmp_path / nested_workers / "worker.py").resolve()), "w", encoding="utf-8") as stream:
        stream.write("print('worker')\n")

    result = assemble(
        desktop,
        core,
        project / ".project-local/out",
        "relative-long-input-test",
        runtime=runtime,
        workers=workers,
        project_root=project,
    )

    with zipfile.ZipFile(_native_path(result.zip_path)) as archive:
        assert any(name.endswith("/runtime/" + nested_runtime.relative_to(runtime).as_posix() + "/LICENSE.txt")
                   for name in archive.namelist())
        assert any(name.endswith("/workers/" + nested_workers.relative_to(workers).as_posix() + "/worker.py")
                   for name in archive.namelist())
