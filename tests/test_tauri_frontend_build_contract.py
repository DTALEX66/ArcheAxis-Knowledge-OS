"""Regression guard for the desktop shell's embedded frontend resources."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_tauri_build_script_recursively_watches_frontend_dist() -> None:
    source = (ROOT / "src-tauri" / "build.rs").read_text(encoding="utf-8")

    assert "fn watch_tree" in source
    assert 'Path::new("../frontend/dist")' in source
    assert 'cargo:rerun-if-changed=' in source
