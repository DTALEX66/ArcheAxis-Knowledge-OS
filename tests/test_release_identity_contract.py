from __future__ import annotations

import json
import subprocess
import sys
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


def test_candidate_identity_injector_writes_non_public_ci_qualification(tmp_path) -> None:
    injector = ROOT / "scripts" / "release_candidate_inject_identity.py"
    output = tmp_path / "release-identity.json"

    result = subprocess.run(
        [
            sys.executable,
            str(injector),
            "--commit",
            "34ca0fbd5ae636314a3403c473bde9247ef95907",
            "--tree",
            "d144559cdd81e1ca58223281ea8bdcbd27821716",
            "--tag",
            "v0.6.9",
            "--version",
            "0.6.9",
            "--verification-ci-run-id",
            "30548553629",
            "--verification-ci-url",
            "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "schema_version": "candidate-1.0.0",
        "candidate": {
            "tag": "v0.6.9",
            "version": "0.6.9",
            "channel": "stable",
            "public": False,
        },
        "source": {
            "commit": "34ca0fbd5ae636314a3403c473bde9247ef95907",
            "tree": "d144559cdd81e1ca58223281ea8bdcbd27821716",
            "verification_ci_run_id": 30548553629,
            "verification_ci_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
        },
    }


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
    product_version = json.loads((ROOT / "app/release-manifest.json").read_text(encoding="utf-8"))[
        "product"
    ]["version"]
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


def test_staged_candidate_identity_matches_complete_manifest(tmp_path):
    import importlib.util
    import hashlib

    spec = importlib.util.spec_from_file_location(
        "identity_staged_fixture", ROOT / "scripts/release_candidate_inject_identity.py"
    )
    injector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(injector)
    (tmp_path / "runtime").mkdir()
    raw = b"fixture-runtime"
    (tmp_path / "runtime/python.exe").write_bytes(raw)
    manifest = tmp_path / "backend-runtime-manifest.json"
    data = {
        "schema": "archeaxis.backend-runtime/v1",
        "runtime_source": {"commit": "a" * 40, "tree": "b" * 40},
        "built_from": {"source_commit": "a" * 40, "source_tree": "b" * 40},
        "files": {
            "runtime/python.exe": {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        },
    }
    manifest.write_text(json.dumps(data))
    identity = {
        "source": {"commit": "a" * 40, "tree": "b" * 40},
        "schema_version": "candidate-1.0.0",
    }
    output = tmp_path / "runtime/release-identity.json"
    injector.inject_staged_identity(manifest, output, identity)
    registered = json.loads(manifest.read_text())
    actual = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()}
    assert actual == set(registered["files"]) | {manifest.name}
    metadata = registered["files"]["runtime/release-identity.json"]
    assert metadata == {
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    for bad in [dict(identity, source={"commit": "b" * 40})]:
        import pytest

        with pytest.raises(ValueError):
            injector.inject_staged_identity(manifest, output, bad)
    import pytest

    with pytest.raises(ValueError):
        injector.inject_staged_identity(manifest, tmp_path / "outside.json", identity)
    with pytest.raises(ValueError):
        injector.inject_staged_identity(
            manifest, output, {"schema_version": "wrong", "source": {"commit": "a" * 40}}
        )
    (tmp_path / "unknown-extra.txt").write_text("extra")
    with pytest.raises(ValueError):
        injector.inject_staged_identity(manifest, output, identity)
    (tmp_path / "unknown-extra.txt").unlink()
    registered["schema"] = "wrong"
    manifest.write_text(json.dumps(registered))
    with pytest.raises(ValueError):
        injector.inject_staged_identity(manifest, output, identity)


def test_staged_identity_rejects_linked_output_before_mutation(tmp_path):
    import importlib.util
    import pytest

    spec = importlib.util.spec_from_file_location(
        "identity_link_fixture", ROOT / "scripts/release_candidate_inject_identity.py"
    )
    injector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(injector)
    (tmp_path / "runtime").mkdir()
    original = tmp_path / "sentinel.txt"
    original.write_text("keep")
    output = tmp_path / "runtime/release-identity.json"
    try:
        output.symlink_to(original)
    except OSError:
        pytest.skip("OS does not grant fixture symlink creation")
    with pytest.raises(ValueError):
        injector.inject_staged_identity(
            tmp_path / "backend-runtime-manifest.json",
            output,
            {"schema_version": "candidate-1.0.0", "source": {"commit": "a" * 40}},
        )
    assert original.read_text() == "keep"


def test_staged_identity_cli_binds_runtime_and_build_trees(tmp_path):
    import hashlib

    root = tmp_path / "candidate"
    (root / "runtime").mkdir(parents=True)
    raw = b"actual-cli-fixture"
    (root / "runtime/python.exe").write_bytes(raw)
    manifest = root / "backend-runtime-manifest.json"
    identity = root / "runtime/release-identity.json"
    data = {
        "schema": "archeaxis.backend-runtime/v1",
        "runtime_source": {"commit": "a" * 40, "tree": "b" * 40},
        "built_from": {"source_commit": "a" * 40, "source_tree": "b" * 40},
        "files": {
            "runtime/python.exe": {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        },
    }
    command = [
        sys.executable,
        "-B",
        str(ROOT / "scripts/release_candidate_inject_identity.py"),
        "--commit",
        "a" * 40,
        "--tree",
        "b" * 40,
        "--tag",
        "v0.6.9",
        "--version",
        "0.6.9",
        "--verification-ci-run-id",
        "1",
        "--verification-ci-url",
        "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/1",
        "--output",
        str(identity),
        "--manifest",
        str(manifest),
    ]
    for section, field in [
        ("runtime_source", "tree"),
        ("built_from", "source_tree"),
        ("built_from", "source_commit"),
    ]:
        bad = json.loads(json.dumps(data))
        bad[section][field] = "c" * 40
        manifest.write_text(json.dumps(bad))
        before = manifest.read_bytes()
        result = subprocess.run(command, capture_output=True, timeout=15)
        assert result.returncode == 1
        assert manifest.read_bytes() == before and not identity.exists()
    manifest.write_text(json.dumps(data))
    result = subprocess.run(command, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    after = json.loads(manifest.read_text())
    assert after["files"]["runtime/release-identity.json"] == {
        "bytes": identity.stat().st_size,
        "sha256": hashlib.sha256(identity.read_bytes()).hexdigest(),
    }
    assert json.loads(identity.read_text())["source"]["tree"] == "b" * 40
    assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == set(
        after["files"]
    ) | {manifest.name}
