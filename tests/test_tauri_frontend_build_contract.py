"""Regression guard for the legacy Tauri recovery shell's embedded frontend."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_tauri_build_watches_project_local_recovery_frontend() -> None:
    source = (ROOT / "src-tauri" / "build.rs").read_text(encoding="utf-8")

    assert "fn watch_tree" in source
    assert 'Path::new("../.project-local/build/frontend-dist")' in source
    assert 'cargo:rerun-if-changed=' in source
