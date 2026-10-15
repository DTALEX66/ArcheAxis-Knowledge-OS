"""Cache invalidation follows compiler/locks/features, while source edits refresh outputs."""
import json
from pathlib import Path

import pytest

from scripts.runtime import cargo_cache


@pytest.fixture
def cache_source(tmp_path, monkeypatch):
    names = ["Cargo.lock", "src-tauri/Cargo.lock", "Cargo.toml", "crates/a/Cargo.toml", ".cargo/config.toml", ".github/workflows/ci.yml"]
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
    state = {"head": "a" * 40, "dirty": False, "patch": "0" * 64}
    monkeypatch.setattr(cargo_cache.dev, "git", lambda _, *args: "\n".join(names) if args == ("ls-files",) else state["head"])
    monkeypatch.setattr(cargo_cache.dev, "worktree_identity", lambda _: (state["dirty"], state["patch"]))
    return tmp_path, state


def identity(root, **overrides):
    args = {"compiler": "rustc 1.97.1\nhost: x86_64-pc-windows-msvc\n", "profile": "build", "env": {}}
    return cargo_cache.cache_identity(root, **(args | overrides))


def test_source_changes_refresh_output_but_reuse_dependencies(cache_source):
    root, state = cache_source
    before = identity(root)
    state["head"] = "b" * 40
    committed = identity(root)
    assert before["dependency_key"] == committed["dependency_key"]
    assert before["build_prefix"] == committed["build_prefix"]
    assert before["build_key"] != committed["build_key"]
    state.update(dirty=True, patch="c" * 64)
    assert identity(root)["build_key"] != committed["build_key"]


@pytest.mark.parametrize("name", ["Cargo.lock", "src-tauri/Cargo.lock", "crates/a/Cargo.toml", ".cargo/config.toml", ".github/workflows/ci.yml"])
def test_each_workspace_lock_manifest_or_config_invalidates_restoration(cache_source, name):
    root, _ = cache_source
    before = identity(root)
    (root / name).write_text("changed feature or input", encoding="utf-8")
    after = identity(root)
    assert before["dependency_key"] != after["dependency_key"]
    assert before["build_prefix"] != after["build_prefix"]


def test_compiler_flags_and_build_profile_are_not_cross_restored(cache_source):
    root, _ = cache_source
    baseline = identity(root)
    alternatives = [identity(root, compiler="rustc 1.98.0\nhost: x86_64-pc-windows-msvc\n"),
                    identity(root, compiler="rustc 1.97.1\nhost: x86_64-unknown-linux-gnu\n"),
                    identity(root, profile="fast"), identity(root, env={"RUSTFLAGS": "--cfg feature_test"})]
    assert all(item["build_prefix"] != baseline["build_prefix"] for item in alternatives)
    assert "feature_test" not in json.dumps(alternatives[-1])


def test_missing_lock_is_a_blocker(cache_source):
    root, _ = cache_source
    (root / "src-tauri/Cargo.lock").unlink()
    with pytest.raises(FileNotFoundError):
        identity(root)


def test_workflow_caches_effective_paths_and_keeps_outputs_separate():
    import yaml
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    for job in ("desktop-fast", "desktop-build"):
        steps = workflow["jobs"][job]["steps"]
        deps = next(step for step in steps if step.get("id") == "cargo_dependencies")
        outputs = next(step for step in steps if step.get("id") == "cargo_outputs")
        assert deps["with"]["path"].splitlines() == ["${{ env.CARGO_HOME }}/registry", "${{ env.CARGO_HOME }}/git", "${{ env.CARGO_HOME }}/bin/cargo-audit.exe"]
        assert "credentials" not in deps["with"]["path"]
        assert "ARCHEAXIS_CARGO_CORE_TARGET_DIR" in outputs["with"]["path"]
        assert "ARCHEAXIS_CARGO_TAURI_TARGET_DIR" in outputs["with"]["path"]
        assert "steps.cargo_cache.outputs.build_prefix" in outputs["with"]["restore-keys"]
