"""Guard the single project-local output roots used by active build entrypoints."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_frontend_and_tauri_share_the_canonical_frontend_output() -> None:
    vite = _read("frontend/vite.config.ts")
    tauri = _read("src-tauri/tauri.conf.json")
    build = _read("src-tauri/build.rs")

    canonical = ".project-local/build/frontend-dist"
    assert canonical in vite
    assert canonical in tauri
    assert canonical in build
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
    assert 'uv pip install --python $python' in source
    assert 'scripts\\runtime\\dev.py' in source
    assert 'app.runtime_entrypoint core' in source


def test_windows_batch_launcher_routes_cache_and_core_to_project_runtime() -> None:
    source = _read("run_windows.bat")

    assert ".project-local\\task-runtime" in source
    assert "set \"TEMP=%RUNTIME%\\tmp\"" in source
    assert "set \"PIP_CACHE_DIR=%CACHE%\\pip\"" in source
    assert "uv pip install --python \"%PYTHON%\"" in source
    assert "scripts\\runtime\\dev.py" in source
    assert "app.runtime_entrypoint core" in source
