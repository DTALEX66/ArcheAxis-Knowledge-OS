from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_source_manifest_uses_v2_verification_release_run_fields() -> None:
    manifest = json.loads((ROOT / "app/release-manifest.json").read_text(encoding="utf-8"))
    source = manifest["source"]
    assert set(source) == {
        "commit",
        "tree",
        "verification_ci_run_id",
        "release_run_id",
        "reason",
    }
    assert source["verification_ci_run_id"] == "unavailable"
    assert source["release_run_id"] == "unavailable"
    assert source["commit"] == "unavailable"
    assert source["tree"] == "unavailable"


def test_release_workflow_passes_verification_run_across_steps_via_outputs() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "id: require_ci" in workflow
    assert "verification_run_id=" in workflow
    assert "verification_run_url=" in workflow
    assert "$env:GITHUB_OUTPUT" in workflow
    # The injection step must consume the step output, not a bare PowerShell var.
    assert "steps.require_ci.outputs.verification_run_id" in workflow
    assert "steps.require_ci.outputs.verification_run_url" in workflow
    # The bare PowerShell variable is only used inside the same require_ci step
    # (to write GITHUB_OUTPUT), never after it.
    require_ci_block = workflow.split("id: require_ci", 1)[1].split(
        "- uses: astral-sh/setup-uv", 1
    )[0]
    assert "$verificationRun" in require_ci_block
    after_require_ci = workflow.split("id: require_ci", 1)[1].split(
        "- uses: astral-sh/setup-uv", 1
    )[1]
    assert "$verificationRun" not in after_require_ci


def test_release_identity_injector_defaults_to_schema_v2() -> None:
    injector = (ROOT / "scripts" / "release_inject_identity.py").read_text(encoding="utf-8")
    assert '"2.0.0"' in injector
    assert 'default="2.0.0"' in injector
    assert "--verification-ci-run-id" in injector
    assert "--verification-ci-url" in injector
    assert "release_run_id" in injector


def test_release_workflow_enforces_schema_v3_and_separate_runs() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "release identity must be schema v3" in workflow
    assert "verification CI run must differ from the release workflow run" in workflow
    assert "verification_ci_run_id" in workflow
    assert "release_run_id" in workflow
    assert "verification_ci_url" in workflow
    assert "release_run_url" in workflow
    # v3 multi-artifact manifest + dependency locks are enforced
    assert "identity artifact manifest differs from public asset set" in workflow
    assert "dependency lock hash mismatch" in workflow
    assert "--artifact-names" in workflow
    assert "--dependency-locks" in workflow
    # No stale single ci_run provenance readback remains.
    assert "identity.source.ci_run" not in workflow
    assert "identity.source.ci_url" not in workflow


def test_cargo_lock_root_package_versions_match_manifest() -> None:
    product_version = json.loads(
        (ROOT / "app/release-manifest.json").read_text(encoding="utf-8")
    )["product"]["version"]
    cargo_toml = (ROOT / "desktop/src-tauri/Cargo.toml").read_text(encoding="utf-8")
    cargo_lock = (ROOT / "desktop/src-tauri/Cargo.lock").read_text(encoding="utf-8")

    toml_version = re.search(r'^version = "([^"]+)"$', cargo_toml, flags=re.MULTILINE)
    lock_root_version = re.search(
        r'name = "archeaxis-desktop-shell"\nversion = "([^"]+)"', cargo_lock
    )
    assert toml_version is not None
    assert lock_root_version is not None
    assert toml_version.group(1) == product_version
    assert lock_root_version.group(1) == product_version
