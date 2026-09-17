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
    assert manifest["files"]["core/archeaxis-api.exe"]["sha256"]
    assert manifest["files"]["runtime/python.exe"]["sha256"]
    assert manifest["provenance"] == {"source_commit": "abc123", "source_tree": "tree123"}
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
    assert '"ARCHEAXIS_WORKER_PROFILE"' in (result.root / "启动绿色候选.vbs").read_text(encoding="utf-8")
