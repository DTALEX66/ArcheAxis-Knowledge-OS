"""Guard the single project-local output roots used by active build entrypoints."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_legacy_frontend_and_tauri_share_the_recovery_build_output() -> None:
    vite = _read("frontend/vite.config.ts")
    tauri = _read("src-tauri/tauri.conf.json")
    build = _read("src-tauri/build.rs")

    legacy_output = ".project-local/build/frontend-dist"
    assert legacy_output in vite
    assert legacy_output in tauri
    assert legacy_output in build
    assert '"frontendDist": "../frontend/dist"' not in tauri


def test_ci_and_release_stage_generated_files_project_locally() -> None:
    ci = _read(".github/workflows/ci.yml")
    release = _read(".github/workflows/release.yml")
    gitignore = _read(".gitignore")

    assert ".project-local/task-runtime/wheel-smoke/dist" in ci
    assert ".project-local/build/release-assets" in release
    assert "uv build --wheel --out-dir release-assets" not in release
    assert "--out-dir dist" not in ci
    assert 'Path("dist").glob' not in ci
    assert "release-assets/" in gitignore


def test_distribution_assembler_does_not_stage_in_repository_root() -> None:
    source = _read("desktop/scripts/assemble_distributions.py")

    assert "def _assembly_output" in source
    assert "Path(GREEN_DIR)" not in source
    assert "Path(PORTABLE_DIR)" not in source
    assert 'Path(f"ArcheAxis.Knowledge-v{version}-Windows-x64-Green.zip")' not in source
    assert 'Path(f"ArcheAxis.Knowledge-v{version}-Windows-x64-Portable.zip")' not in source


def test_release_checksum_example_uses_project_local_inputs() -> None:
    source = _read("scripts/release_checksum.py")

    assert "--wheel dist/" not in source
    assert ".project-local/build/release-assets/" in source


def test_primary_launchers_use_the_project_runtime_router() -> None:
    shell = _read("run_all.sh")
    batch = _read("run_all.bat")

    assert shell.count("scripts/runtime/dev.py") == 2
    assert batch.count("scripts\\runtime\\dev.py") == 2
    assert "dev.py -- python -m app.runtime_entrypoint migrate" in shell
    assert "dev.py -- python -m app.runtime_entrypoint core" in shell
    assert "dev.py -- python -m app.runtime_entrypoint migrate" in batch
    assert "dev.py -- python -m app.runtime_entrypoint core" in batch


def test_windows_launcher_routes_bootstrap_and_core_to_project_runtime() -> None:
    source = _read("run_windows.ps1")

    assert '.project-local\\task-runtime' in source
    assert '$env:TEMP' in source
    assert '$env:PIP_CACHE_DIR' in source
    assert '& $uv pip install --python $python' in source
    assert '& $uv venv' in source
    assert 'python -m venv' not in source
    assert 'scripts\\runtime\\dev.py' in source
    assert 'app.runtime_entrypoint core' in source


def test_windows_batch_launcher_routes_cache_and_core_to_project_runtime() -> None:
    source = _read("run_windows.bat")

    assert ".project-local\\task-runtime" in source
    assert "set \"TEMP=%RUNTIME%\\tmp\"" in source
    assert "set \"PIP_CACHE_DIR=%CACHE%\\pip\"" in source
    assert '"%UV%" pip install --python "%PYTHON%"' in source
    assert '"%UV%" venv ".venv"' in source
    assert 'python -m venv' not in source
    assert "scripts\\runtime\\dev.py" in source
    assert "app.runtime_entrypoint core" in source


def test_ocr_worker_accepts_explicit_tesseract_path() -> None:
    source = _read("services/python-workers/vision/worker_ocr.py")
    assert 'os.environ.get("TESSERACT_CMD"' in source
    assert "configured TESSERACT_CMD does not exist" in source


def test_windows_launcher_handles_uv_command_and_file_fallbacks() -> None:
    source = _read("run_windows.ps1")
    assert "$uvCommand.Source" in source
    assert "$uvCommand.FullName" in source


def test_rust_lifecycle_smoke_uses_managed_runtime_paths() -> None:
    source = _read("desktop/src-tauri/tests/backend_lifecycle.rs")
    assert ".project-local/task-runtime" in source
    assert ".project-local/build/venv/Scripts/python.exe" in source
    assert ".hermes/" not in source
    assert ".venv/" not in source


def test_rust_runtime_resolves_managed_development_python() -> None:
    source = _read("desktop/src-tauri/src/runtime.rs")
    assert 'root.join(".project-local/build/venv/Scripts/python.exe")' in source
    assert 'root.join(".venv/Scripts/python.exe")' not in source


def test_worker_checker_has_no_unmanaged_system_temp_directory() -> None:
    source = _read("scripts/ci/check_vnext_workers.py")
    assert "def _managed_tempdir" in source
    assert "with tempfile.TemporaryDirectory()" not in source
    assert "ARCHEAXIS_RUN_ROOT" in source


def test_formal_desktop_window_is_the_archeaxis_workspace_shell() -> None:
    xaml = _read("apps/ArcheAxis.Desktop/MainWindow.axaml")
    code = _read("apps/ArcheAxis.Desktop/MainWindow.axaml.cs")
    # The import body streams the same JSON contract instead of buffering the
    # whole source plus its base64 text in memory, so the content_base64 key is
    # emitted by the dedicated HttpContent rather than inline in the window.
    streaming = _read("apps/ArcheAxis.Desktop/StreamingImportContent.cs")

    assert "Welcome to Avalonia!" not in xaml
    assert "星环知识平台" in xaml
    assert "选择资料并导入" in xaml
    assert "打开学习路径" in xaml
    assert 'Click="OnImportClick"' in xaml
    assert 'Click="OnLearningClick"' in xaml
    assert "CoreStatusText.Text" in code
    assert "OpenFilePickerAsync" in code
    assert 'HttpMethod.Post' in code
    assert '"/api/v1/imports"' in code
    assert '"/api/v1/learning/items"' in code
    assert "StreamingImportContent" in code
    assert "content_base64" in streaming


def test_desktop_smoke_requires_an_explicit_managed_database_path() -> None:
    source = _read("apps/ArcheAxis.Desktop/Program.cs")

    assert "provide an explicit project-local database path" in source
    assert "Path.GetTempPath()" not in source


def test_desktop_release_is_self_contained_for_clean_green_machines() -> None:
    project = _read("apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj")

    assert "<RuntimeIdentifier>win-x64</RuntimeIdentifier>" in project
    assert "<SelfContained>true</SelfContained>" in project
