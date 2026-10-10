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


def test_shell_ci_supplies_built_routed_frontend_and_effective_configuration() -> None:
    import yaml
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["desktop-fast"]["steps"]
    build_index = next(index for index, step in enumerate(steps) if "scripts/runtime/frontend.py" in step.get("run", ""))
    test_indices = [index for index, step in enumerate(steps) if "cargo test" in step.get("run", "")]
    assert test_indices
    assert all(build_index < index for index in test_indices)
    assert "npm ci --prefix frontend --ignore-scripts" in steps[build_index]["run"]
    assert "--node $node build" in steps[build_index]["run"]
    assert "$env:ARCHEAXIS_FRONTEND_BUILD_CONTEXT = $env:ARCHEAXIS_RUN_ROOT" in steps[build_index]["run"]
    for index in test_indices:
        assert "$env:TAURI_CONFIG = Get-Content -LiteralPath $env:ARCHEAXIS_TAURI_CONFIG -Raw" in steps[index]["run"]
