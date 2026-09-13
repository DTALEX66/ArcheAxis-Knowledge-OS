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

    assert ".project-local/task-runtime/wheel-smoke/dist" in ci
    assert ".project-local/build/release-assets" in release
    assert "uv build --wheel --out-dir release-assets" not in release
    assert "--out-dir dist" not in ci


def test_distribution_assembler_does_not_stage_in_repository_root() -> None:
    source = _read("desktop/scripts/assemble_distributions.py")

    assert "def _assembly_output" in source
    assert "Path(GREEN_DIR)" not in source
    assert "Path(PORTABLE_DIR)" not in source
    assert 'Path(f"ArcheAxis.Knowledge-v{version}-Windows-x64-Green.zip")' not in source
    assert 'Path(f"ArcheAxis.Knowledge-v{version}-Windows-x64-Portable.zip")' not in source
