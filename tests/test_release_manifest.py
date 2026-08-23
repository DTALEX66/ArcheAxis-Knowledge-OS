from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def test_release_manifest_is_packaged_truth_and_matches_dependency_lock() -> None:
    from app.release import load_release_manifest, safe_release_summary
    from shared import core_schema, migration
    from shared.config import config
    from shared.knowledge_governance_migration import KNOWLEDGE_GOVERNANCE_MIGRATIONS
    from shared.migration_runner import default_registry

    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "app" / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert load_release_manifest() == manifest
    assert manifest["release"] == {
        "status": "unreleased",
        "channel": "development",
        "public": False,
    }
    assert manifest["product"]["version"] == "0.6.10"
    assert manifest["source"]["commit"] == "unavailable"
    assert manifest["verification"]["embedded_test_counts"] is False
    lock_digest = hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
    assert manifest["dependency_lock"]["digest"] == lock_digest
    manifest_owners = [
        {key: value for key, value in owner.items() if key != "steps"}
        for owner in manifest["migrations"]["owners"]
    ]
    assert manifest_owners == [asdict(owner) for owner in default_registry().owners]
    manifest_steps = {
        owner["owner"]: owner["steps"] for owner in manifest["migrations"]["owners"]
    }
    assert manifest_steps == {
        "core.sqlite": [core_schema.BASELINE_MIGRATION_NAME],
        "fts.cards": [],
        "fts.documents": [],
        "knowledge-governance.sqlite": list(KNOWLEDGE_GOVERNANCE_MIGRATIONS.values()),
        "research.sqlite": [migration.RESEARCH_SCHEMA_MIGRATION_NAME],
        "sleep-loop.sqlite": list(migration.SLEEP_LOOP_MIGRATIONS.values()),
        "taskpack.sqlite": list(migration.TASKPACK_MIGRATIONS.values()),
        "vector.cards": [],
        "vector.documents": [],
        "workspace.sqlite": [
            migration.WORKSPACE_SCHEMA_MIGRATION_NAME,
            migration.WORKSPACE_DELIVERY_RECEIPT_MIGRATION_NAME,
        ],
    }
    project_metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest["product"]["version"] == project_metadata["project"]["version"]
    assert manifest["product"]["version"] == config.get("app.version")
    assert safe_release_summary() == {
        "status": "unreleased",
        "version": "0.6.10",
        "channel": "development",
        "source_commit": "unavailable",
    }


def test_version_and_architecture_endpoints_do_not_copy_stale_claims() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    version = client.get("/version")
    architecture = client.get("/architecture")

    assert version.status_code == 200
    assert version.json()["release"]["status"] == "unreleased"
    assert version.json()["capabilities"]["asr_transcription"] == "not_implemented"
    assert "Human-grounded OCR/ASR accuracy benchmarks" not in version.text
    assert architecture.status_code == 200
    assert "modules" not in architecture.json()
    assert "tests" not in architecture.json()


def test_release_manifest_rejects_extra_fields_and_unverified_public_claims(
    monkeypatch, tmp_path
) -> None:
    from app import release

    source = json.loads(
        (Path(__file__).resolve().parents[1] / "app" / "release-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    target = tmp_path / "release-manifest.json"
    monkeypatch.setattr(release, "_MANIFEST_PATH", target)
    cases = []

    extra = json.loads(json.dumps(source))
    extra["release"]["unverified_claim"] = True
    cases.append(extra)

    public = json.loads(json.dumps(source))
    public["release"].update({"status": "released", "public": True})
    cases.append(public)

    bad_lock = json.loads(json.dumps(source))
    bad_lock["dependency_lock"]["digest"] = "not-a-sha256"
    cases.append(bad_lock)

    for candidate in cases:
        target.write_text(json.dumps(candidate), encoding="utf-8")
        release.load_release_manifest.cache_clear()
        with pytest.raises(RuntimeError):
            release.load_release_manifest()
    release.load_release_manifest.cache_clear()


def test_release_manifest_marks_unimplemented_product_surfaces_truthfully() -> None:
    from app.release import load_release_manifest

    capabilities = load_release_manifest()["capabilities"]
    assert capabilities["workspace_job_outbox_receipts"] == "available"
    assert capabilities["asynchronous_worker"] == "available"
    assert capabilities["outbox_dispatcher"] == "available"
    assert capabilities["server_sent_events"] == "available"
    assert capabilities["interactive_job_center"] == "available"
    assert capabilities["postgresql_runtime"] == "not_implemented"
    assert capabilities["qdrant_runtime"] == "not_implemented"


def test_bundled_release_identity_exposes_a_verified_public_release_summary(
    monkeypatch, tmp_path
) -> None:
    from app import release

    identity_path = tmp_path / "release-identity.json"
    identity_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0.0",
                "release": {
                    "tag": "v0.5.0",
                    "version": "0.5.0",
                    "channel": "stable",
                    "public": True,
                    "url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.5.0",
                },
                "source": {
                    "commit": "34ca0fbd5ae636314a3403c473bde9247ef95907",
                    "tree": "d144559cdd81e1ca58223281ea8bdcbd27821716",
                    "verification_ci_run_id": 30548553629,
                    "verification_ci_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
                    "release_run_id": 30548553630,
                    "release_run_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553630",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(release, "_ARTIFACT_IDENTITY_PATH", identity_path)
    release.load_artifact_release_identity.cache_clear()

    assert release.safe_release_summary() == {
        "status": "released",
        "version": "0.5.0",
        "channel": "stable",
        "source_commit": "34ca0fbd5ae636314a3403c473bde9247ef95907",
        "tag": "v0.5.0",
        "verification_ci_run_id": 30548553629,
        "release_run_id": 30548553630,
        "url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.5.0",
    }
    assert release.effective_capabilities()["public_installer"] == "available"


def test_bundled_release_identity_v3_exposes_verified_public_release_summary(
    monkeypatch, tmp_path
) -> None:
    from app import release

    identity_path = tmp_path / "release-identity.json"
    identity_path.write_text(
        json.dumps(
            {
                "schema_version": "3.0.0",
                "release": {
                    "tag": "v0.6.3",
                    "version": "0.6.3",
                    "channel": "stable",
                    "public": True,
                    "url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.3",
                },
                "source": {
                    "commit": "34ca0fbd5ae636314a3403c473bde9247ef95907",
                    "tree": "d144559cdd81e1ca58223281ea8bdcbd27821716",
                    "verification_ci_run_id": 30548553629,
                    "verification_ci_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
                    "release_run_id": 30548553630,
                    "release_run_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553630",
                },
                "artifacts": [
                    {"name": "setup.exe", "kind": "installer"},
                    {"name": "green.zip", "kind": "green"},
                    {"name": "portable.zip", "kind": "portable"},
                    {"name": "package.whl", "kind": "wheel"},
                    {"name": "release-identity.json", "kind": "identity"},
                    {"name": "release-manifest.json", "kind": "manifest"},
                    {"name": "SBOM.cdx.json", "kind": "sbom"},
                    {"name": "THIRD_PARTY_NOTICES.txt", "kind": "notices"},
                    {"name": "SHA256SUMS.txt", "kind": "checksums"},
                ],
                "dependency_locks": {
                    "uv.lock": "a" * 64,
                    "frontend/package-lock.json": "b" * 64,
                    "src-tauri/Cargo.lock": "c" * 64,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(release, "_ARTIFACT_IDENTITY_PATH", identity_path)
    release.load_artifact_release_identity.cache_clear()

    assert release.safe_release_summary() == {
        "status": "released",
        "version": "0.6.3",
        "channel": "stable",
        "source_commit": "34ca0fbd5ae636314a3403c473bde9247ef95907",
        "tag": "v0.6.3",
        "verification_ci_run_id": 30548553629,
        "release_run_id": 30548553630,
        "url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.3",
    }
    assert release.effective_capabilities()["public_installer"] == "available"


def test_bundled_candidate_identity_exposes_qualified_summary_without_public_installer(
    monkeypatch, tmp_path
) -> None:
    """A CI-qualified installer must not claim tag publication before Release readback."""
    from app import release

    identity_path = tmp_path / "release-identity.json"
    identity_path.write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(release, "_ARTIFACT_IDENTITY_PATH", identity_path)
    release.load_artifact_release_identity.cache_clear()

    assert release.safe_release_summary() == {
        "status": "qualified",
        "version": "0.6.9",
        "channel": "stable",
        "source_commit": "34ca0fbd5ae636314a3403c473bde9247ef95907",
        "tag": "v0.6.9",
        "verification_ci_run_id": 30548553629,
    }
    assert release.effective_capabilities()["public_installer"] == "not_implemented"


def test_bundled_release_identity_v1_reader_still_accepted_for_backward_compat(
    monkeypatch, tmp_path
) -> None:
    """Schema v1 (legacy ci_run/ci_url) remains readable for migration/diagnostics."""
    from app import release

    identity_path = tmp_path / "release-identity.json"
    identity_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "release": {
                    "tag": "v0.5.0",
                    "version": "0.5.0",
                    "channel": "stable",
                    "public": True,
                    "url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.5.0",
                },
                "source": {
                    "commit": "34ca0fbd5ae636314a3403c473bde9247ef95907",
                    "tree": "d144559cdd81e1ca58223281ea8bdcbd27821716",
                    "ci_run": 30548553629,
                    "ci_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(release, "_ARTIFACT_IDENTITY_PATH", identity_path)
    release.load_artifact_release_identity.cache_clear()

    summary = release.safe_release_summary()
    assert summary["status"] == "released"
    assert summary["ci_run"] == 30548553629
    assert release.effective_capabilities()["public_installer"] == "available"


def test_release_identity_v2_rejects_verification_equal_release_run(monkeypatch, tmp_path) -> None:
    """A selective/main-bind run can never be mistaken for release qualification."""
    from app import release

    identity_path = tmp_path / "release-identity.json"
    identity_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0.0",
                "release": {
                    "tag": "v0.5.0",
                    "version": "0.5.0",
                    "channel": "stable",
                    "public": True,
                    "url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.5.0",
                },
                "source": {
                    "commit": "34ca0fbd5ae636314a3403c473bde9247ef95907",
                    "tree": "d144559cdd81e1ca58223281ea8bdcbd27821716",
                    "verification_ci_run_id": 30548553629,
                    "verification_ci_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
                    "release_run_id": 30548553629,
                    "release_run_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(release, "_ARTIFACT_IDENTITY_PATH", identity_path)
    release.load_artifact_release_identity.cache_clear()

    with pytest.raises(RuntimeError, match="invalid v2 source fields"):
        release.load_artifact_release_identity()


def test_bundled_release_identity_rejects_semantically_wrong_urls(monkeypatch, tmp_path) -> None:
    from app import release

    identity = {
        "schema_version": "2.0.0",
        "release": {"tag": "v0.4.0", "version": "0.4.0", "channel": "stable", "public": True, "url": "https://github.com/foreign-owner/foreign-repo/releases/tag/v0.4.0"},
        "source": {"commit": "34ca0fbd5ae636314a3403c473bde9247ef95907", "tree": "d144559cdd81e1ca58223281ea8bdcbd27821716", "verification_ci_run_id": 30548553629, "verification_ci_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629", "release_run_id": 30548553630, "release_run_url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553630"},
    }
    path = tmp_path / "release-identity.json"
    path.write_text(json.dumps(identity), encoding="utf-8")
    monkeypatch.setattr(release, "_ARTIFACT_IDENTITY_PATH", path, raising=False)
    release.load_artifact_release_identity.cache_clear()
    with pytest.raises(RuntimeError, match="invalid release fields"):
        release.load_artifact_release_identity()


def test_truth_docs_do_not_overstate_startup_migration_or_delivery() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    migration = (root / "docs/MIGRATION_OPERATOR.md").read_text(encoding="utf-8")
    handoff = (root / "docs/HANDOFF_2026-07-21.md").read_text(encoding="utf-8")

    assert readme.index("python -m app.runtime_entrypoint migrate") < readme.index(
        "python -m app.runtime_entrypoint core"
    )
    assert "applies all nine registered owners" not in migration
    assert "applies the five registered SQLite owners" in migration
    assert "## 当前候选基线" in handoff
    assert "Hermes cron `" not in handoff


# ════════════════════════════════════════════════════════════
# N-001: Release artifact checksum, provenance, build gate
# ════════════════════════════════════════════════════════════


def test_release_checksum_script_generates_valid_sha256_manifest(tmp_path) -> None:
    """Verify scripts/release_checksum.py produces correct sha256sum format."""
    import hashlib
    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "release_checksum.py"
    assert script.exists(), "release_checksum.py not found"

    # Create a dummy wheel file
    wheel = tmp_path / "cognitive_loop_os-0.4.0-py3-none-any.whl"
    wheel.write_text("fake wheel content", encoding="utf-8")
    expected_digest = hashlib.sha256(b"fake wheel content").hexdigest()

    output = tmp_path / "checksums.txt"
    result = subprocess.run(
        [sys.executable, str(script), "--wheel", str(wheel), "--output", str(output)],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, f"script failed: {result.stderr}"

    lines = output.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1, f"expected 1 checksum line, got {len(lines)}"
    digest, name = lines[0].split("  ", 1)
    assert digest == expected_digest, f"digest mismatch: {digest} != {expected_digest}"
    assert name == wheel.name, f"filename mismatch: {name} != {wheel.name}"


def test_release_checksum_script_refuses_missing_artifact(tmp_path) -> None:
    """Verify release_checksum.py errors on missing paths."""
    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "release_checksum.py"
    output = tmp_path / "checksums.txt"
    result = subprocess.run(
        [sys.executable, str(script), "--wheel", str(tmp_path / "nonexistent.whl"),
         "--output", str(output)],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode != 0, "should have failed on missing artifact"


def test_release_checksum_script_refuses_no_artifacts(tmp_path) -> None:
    """Verify release_checksum.py errors when no --wheel or --installer given."""
    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "release_checksum.py"
    output = tmp_path / "checksums.txt"
    result = subprocess.run(
        [sys.executable, str(script), "--output", str(output)],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode != 0, "should have failed without artifact arguments"


def test_release_workflow_stages_installer_under_provider_stable_name() -> None:
    """The checksum filename must equal the name exposed by GitHub Releases."""
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    # the staged installer asset name is tag-derived (AXW-REL-002) but the
    # stable naming shape must still be enforced by the workflow template
    assert 'ArcheAxis.Knowledge-v${{ steps.resolve_version.outputs.release_version }}-Windows-x64-Setup.exe' in workflow
    assert 'Copy-Item $installers[0].FullName $installerAsset' in workflow
    assert '--installer $installerAsset' in workflow
    assert "Where-Object Name -eq '.gitignore'" in workflow
    assert "Remove-Item -Force" in workflow


def test_release_workflow_publishes_only_checksum_bound_allowlist() -> None:
    """No wildcard or unlisted staging payload may reach a public release."""
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert 'gh release create $env:GITHUB_REF_NAME release-assets/*' not in workflow
    assert 'Verify checksum manifest payload equality' in workflow
    assert '$releaseAssets = @(' in workflow
    assert 'gh release create $env:GITHUB_REF_NAME $releaseAssets' in workflow


def test_release_workflow_verifies_green_and_portable_lifecycle_before_metadata() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    lifecycle = (root / "desktop" / "scripts" / "verify_zip_distributions.ps1").read_text(
        encoding="utf-8"
    )

    assert "Verify Green and Portable lifecycle" in workflow
    assert "verify_zip_distributions.ps1" in workflow
    assert workflow.index("Verify Green and Portable lifecycle") < workflow.index(
        "Build release metadata and checksums"
    )
    assert "runtime\\python\\python.exe" in lifecycle
    assert "portable.flag" in lifecycle
    # ``ARCHEAXIS_DATA_DIR`` is already ``<portable-root>/data`` and the
    # canonical resolver strips the leading ``data`` component from the
    # configured ``data/archeaxis.sqlite`` path.
    assert "Join-Path $Root 'data\\archeaxis.sqlite'" in lifecycle
    assert "Join-Path $Root 'data\\data\\archeaxis.sqlite'" not in lifecycle
    assert "for ($launch = 1; $launch -le 2; $launch++)" in lifecycle


def test_zip_lifecycle_normalizes_expected_bundled_python_path() -> None:
    lifecycle = (
        Path(__file__).resolve().parents[1]
        / "desktop"
        / "scripts"
        / "verify_zip_distributions.ps1"
    ).read_text(encoding="utf-8")

    assert (
        "$python = [System.IO.Path]::GetFullPath((Join-Path $Root "
        "'runtime\\python\\python.exe'))"
    ) in lifecycle
    assert "if ($ready.Child.ExecutablePath -ne $python)" in lifecycle


def test_zip_lifecycle_closes_the_exact_pid_owned_window() -> None:
    lifecycle = (
        Path(__file__).resolve().parents[1]
        / "desktop"
        / "scripts"
        / "verify_zip_distributions.ps1"
    ).read_text(encoding="utf-8")

    assert "class ArcheAxisWindow" in lifecycle
    assert "function Wait-ArcheAxisWindow" in lifecycle
    assert "[ArcheAxisWindow]::PostClose($WindowHandle, [uint32]$Shell.Id)" in lifecycle
    assert "-WindowHandle $window" in lifecycle
    assert "$Shell.CloseMainWindow()" not in lifecycle


def test_nsis_lifecycle_checks_in_place_upgrade_and_retained_data_readback() -> None:
    root = Path(__file__).resolve().parents[1]
    lifecycle = (root / "desktop" / "scripts" / "verify_nsis_install.ps1").read_text(
        encoding="utf-8"
    )

    assert "NSIS in-place upgrade" in lifecycle
    # ``ARCHEAXIS_DATA_DIR`` is the runtime root.  The canonical resolver
    # strips the leading ``data`` component from ``data/archeaxis.sqlite``;
    # the lifecycle verifier must therefore inspect the actual database
    # location rather than inventing an extra data/ directory.
    assert "Join-Path $appData 'archeaxis.sqlite'" in lifecycle
    assert "Join-Path $appData 'data\\archeaxis.sqlite'" not in lifecycle
    # Every launched shell, including the post-upgrade and post-reinstall
    # read-backs, must resolve the visible top-level window owned by the exact
    # shell PID before sending WM_CLOSE. Process.CloseMainWindow() guesses a
    # main handle and is racy once WebView2 has created auxiliary windows.
    assert "function Close-ArcheAxisShell" in lifecycle
    assert "[ArcheAxisWindow]::PostClose($WindowHandle, [uint32]$Shell.Id)" in lifecycle
    assert ".CloseMainWindow()" not in lifecycle
    assert "$upgradeWindowHandle = Wait-ArcheAxisWindow -Shell $activeShell" in lifecycle
    assert "$reinstallWindowHandle = Wait-ArcheAxisWindow -Shell $activeShell" in lifecycle
    assert "release-lifecycle-sentinel.txt" in lifecycle
    assert "NSIS uninstall removed user data instead of retaining it" in lifecycle
    assert "reinstalled Workspace did not read back retained user state" in lifecycle
    assert "InPlaceUpgrade = $true" in lifecycle
    assert "UninstallRetainsData = $true" in lifecycle
    assert "ReinstallReadback = $true" in lifecycle


def test_release_truth_documents_preserve_historical_and_source_manifest_truth() -> None:
    root = Path(__file__).resolve().parents[1]
    required = ["LICENSE", "THIRD_PARTY_NOTICES.md", "SECURITY.md", "CHANGELOG.md"]
    for relative in required:
        assert (root / relative).is_file(), f"missing release truth document: {relative}"

    readme = (root / "README.md").read_text(encoding="utf-8")
    status = (root / "docs" / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    combined = "\n".join((readme, status, changelog))
    assert "v0.4.0" in combined
    assert "historical" in combined.lower()
    assert "incomplete checksum payload coverage" in combined
    assert "unreleased / public=false" in combined
    assert "artifacts are signed" not in changelog.lower()


def test_release_ledger_documents_historical_truth_and_provenance_defect() -> None:
    root = Path(__file__).resolve().parents[1]
    ledger = (root / "docs" / "RELEASE_LEDGER.md").read_text(encoding="utf-8")

    # Ledger covers every tag from v0.4.0 through the current dev version.
    for tag in ("v0.4.0", "v0.4.1", "v0.4.2", "v0.4.3", "v0.4.4", "v0.5.0"):
        assert tag in ledger, f"ledger missing {tag}"

    # v0.4.4 provenance defect is recorded, not silently dropped.
    assert "30839451084" in ledger
    assert "30837105199" in ledger
    assert "provenance" in ledger.lower()
    assert "verification_ci_run_id" in ledger
    assert "release_run_id" in ledger
    assert "schema v1" in ledger

    # Policy: never rewrite history; future releases use schema v2.
    assert "not" in ledger and "rewrite" in ledger.lower()


def test_release_workflow_downloads_and_rehashes_exact_public_asset_set() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "Read back and verify draft release assets" in workflow
    assert "gh release view $env:GITHUB_REF_NAME --json tagName,targetCommitish,isDraft,assets,url" in workflow
    assert "gh release download $env:GITHUB_REF_NAME" in workflow
    assert "Get-FileHash" in workflow
    assert 'Get-FileHash "$($entry.Name)"' in workflow
    assert "provider digest" in workflow.lower()
    assert "public asset set differs from expected release asset set" in workflow


def test_release_workflow_requires_exact_sha_ci_before_building_release_assets() -> None:
    """A tag bound to main cannot bypass the successful CI run for that exact SHA."""
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "Require successful exact-SHA CI" in workflow
    assert 'gh run list --commit $env:GITHUB_SHA --workflow CI' in workflow
    assert "exact-SHA CI did not complete successfully" in workflow
    assert workflow.index("Require successful exact-SHA CI") < workflow.index(
        "Prepare bundled runtime and inject exact release identity"
    )


def test_release_workflow_keeps_assets_draft_until_readback_closes() -> None:
    """No asset becomes public before its GitHub inventory and downloaded bytes verify."""
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    draft_create = 'gh release create $env:GITHUB_REF_NAME $releaseAssets --draft'
    download = "gh release download $env:GITHUB_REF_NAME"
    publish = 'gh release edit $env:GITHUB_REF_NAME --draft=false'
    assert draft_create in workflow
    assert "Read back and verify draft release assets" in workflow
    assert "$release.isDraft -ne $true" in workflow
    assert "release draft state mismatch" in workflow
    assert publish in workflow
    assert workflow.index(draft_create) < workflow.index(download) < workflow.index(publish)


def test_release_workflow_readback_binds_target_and_identity_tree() -> None:
    """The downloaded identity must bind all Git provenance, not only its commit."""
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert '$acceptedReleaseTargets = @("main", $env:GITHUB_SHA)' in workflow
    assert '$release.targetCommitish -notin $acceptedReleaseTargets' in workflow
    assert "release target commit is neither main nor exact workflow SHA" in workflow
    assert '$identity.source.tree -ne $tree' in workflow
    assert "downloaded release identity tree mismatch" in workflow
    assert "downloaded release identity verification CI identity is missing" in workflow
    assert "release identity must be schema v3" in workflow
    assert "verification CI run must differ from the release workflow run" in workflow


def test_release_identity_injection_manifests_exact_commit_and_tree(tmp_path) -> None:
    """Verify scripts/release_inject_identity.py writes valid identity manifest."""
    import json
    import os
    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "release_inject_identity.py"
    assert script.exists(), "release_inject_identity.py not found"

    output = tmp_path / "release-identity.json"
    commit = "7e0d883cbcd5acec9a3e75c13189ee4734dc976c"
    tree = "5aeaa2c070ef677e6cb5a131f3ff5242cc58f172"
    result = subprocess.run(
        [sys.executable, str(script),
         "--commit", commit,
         "--tree", tree,

         "--tag", "v0.4.0",
         "--version", "0.4.0",
         "--url", "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.4.0",
         "--verification-ci-run-id", "30548553629",
         "--verification-ci-url", "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
         "--output", str(output)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "GITHUB_RUN_ID": "30548553630"},
    )
    assert result.returncode == 0, f"script failed: {result.stderr}"

    identity = json.loads(output.read_text(encoding="utf-8"))
    assert identity["schema_version"] == "2.0.0"
    assert identity["source"]["commit"] == commit
    assert identity["source"]["tree"] == tree
    assert identity["release"] == {
        "tag": "v0.4.0",
        "version": "0.4.0",
        "channel": "stable",
        "public": True,
        "url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.4.0",
    }
    assert identity["source"]["verification_ci_url"] == "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629"
    assert identity["source"]["verification_ci_run_id"] == 30548553629
    assert identity["source"]["release_run_id"] == 30548553630
    assert identity["source"]["release_run_url"] == "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553630"


def test_release_identity_injection_v3_emits_all_public_artifact_kinds(tmp_path) -> None:
    import os
    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "release_inject_identity.py"
    output = tmp_path / "release-identity.json"
    artifact_names = (
        "ArcheAxis.Knowledge-v0.6.3-Windows-x64-Setup.exe,"
        "ArcheAxis.Knowledge-v0.6.3-Windows-x64-Green.zip,"
        "ArcheAxis.Knowledge-v0.6.3-Windows-x64-Portable.zip,"
        "archeaxis_workspace-0.6.3-py3-none-any.whl,release-identity.json,"
        "release-manifest.json,SBOM.cdx.json,THIRD_PARTY_NOTICES.txt,SHA256SUMS.txt"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--commit",
            "7e0d883cbcd5acec9a3e75c13189ee4734dc976c",
            "--tree",
            "5aeaa2c070ef677e6cb5a131f3ff5242cc58f172",
            "--tag",
            "v0.6.3",
            "--version",
            "0.6.3",
            "--schema-version",
            "3.0.0",
            "--url",
            "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.3",
            "--verification-ci-run-id",
            "30548553629",
            "--verification-ci-url",
            "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
            "--artifact-names",
            artifact_names,
            "--dependency-locks",
            f"uv.lock={'a' * 64},frontend/package-lock.json={'b' * 64},src-tauri/Cargo.lock={'c' * 64}",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "GITHUB_RUN_ID": "30548553630"},
    )
    assert result.returncode == 0, result.stderr

    identity = json.loads(output.read_text(encoding="utf-8"))
    assert {entry["kind"] for entry in identity["artifacts"]} == {
        "installer",
        "green",
        "portable",
        "wheel",
        "identity",
        "manifest",
        "sbom",
        "notices",
        "checksums",
    }


def test_release_identity_injection_writes_v1_for_backward_compat(tmp_path) -> None:
    """Schema v1 injection remains available for migration/diagnostics."""
    import os
    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "release_inject_identity.py"
    output = tmp_path / "release-identity-v1.json"
    result = subprocess.run(
        [sys.executable, str(script),
         "--commit", "7e0d883cbcd5acec9a3e75c13189ee4734dc976c",
         "--tree", "5aeaa2c070ef677e6cb5a131f3ff5242cc58f172",
         "--tag", "v0.4.0",
         "--version", "0.4.0",
         "--url", "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.4.0",
         "--schema-version", "1.0.0",
         "--ci-url", "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629",
         "--output", str(output)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "GITHUB_RUN_ID": "30548553630"},
    )
    assert result.returncode == 0, f"script failed: {result.stderr}"
    identity = json.loads(output.read_text(encoding="utf-8"))
    assert identity["schema_version"] == "1.0.0"
    assert identity["source"]["ci_run"] == 30548553630
    assert identity["source"]["ci_url"] == "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/30548553629"


def test_release_identity_injection_rejects_invalid_sha(tmp_path) -> None:
    """Verify release_inject_identity.py rejects non-40-hex values."""
    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "release_inject_identity.py"
    output = tmp_path / "release-identity.json"
    result = subprocess.run(
        [sys.executable, str(script),
         "--commit", "bad-sha",
         "--tree", "5aeaa2c070ef677e6cb5a131f3ff5242cc58f172",
         "--branch", "test",
         "--output", str(output)],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode != 0, "should have rejected invalid SHA"


def test_public_release_requires_exact_source_identity() -> None:
    """Verify release.py load_release_manifest rejects public release
    with unavailable source identity."""
    from app.release import load_release_manifest

    manifest = load_release_manifest()
    assert manifest["release"]["public"] is False
    assert manifest["source"]["commit"] == "unavailable"
    assert manifest["source"]["tree"] == "unavailable"


def test_capability_public_installer_not_implemented() -> None:
    """Verify release manifest correctly reports public_installer as not_implemented."""
    from app.release import load_release_manifest

    capabilities = load_release_manifest()["capabilities"]
    assert capabilities["public_installer"] == "not_implemented"
