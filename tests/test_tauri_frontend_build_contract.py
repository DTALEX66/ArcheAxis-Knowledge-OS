"""Regression guard for the legacy Tauri recovery shell's embedded frontend."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_formal_tauri_build_watches_its_effective_frontend() -> None:
    source = (ROOT / "src-tauri" / "build.rs").read_text(encoding="utf-8")

    assert "fn watch_tree" in source
    assert 'pointer("/build/frontendDist")' in source
    assert 'watch_tree(&manifest.join(frontend_dist))' in source
    assert 'cargo:rerun-if-env-changed=TAURI_CONFIG' in source
    assert 'cargo:rerun-if-changed=' in source
