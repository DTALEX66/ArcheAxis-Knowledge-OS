from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _job_section(workflow: str, name: str, next_name: str) -> str:
    return workflow.split(f"\n  {name}:", 1)[1].split(f"\n  {next_name}:", 1)[0]


def test_ci_runs_javascript_and_real_browser_gates() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "node --check app/workspace/ui/assets/app.js" in workflow
    assert "browser-smoke:" in workflow
    assert "python scripts/a0_browser_smoke.py" in workflow
    assert "python -m playwright install --with-deps chromium" in workflow


def test_ci_supports_explicit_full_qualification_for_a_selected_sha() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "force_full:" in workflow
    assert "Run every qualification gate for the selected SHA" in workflow
    assert "CI_FORCE_FULL: ${{ inputs.force_full || vars.CI_FORCE_FULL || contains(github.event.head_commit.message, '[full-qualification]') }}" in workflow


def test_ci_runs_risk_owned_python_targets_without_the_primary_suite() -> None:
    """Targeted GatePlan IDs must select a focused job, not the full suite."""
    workflow = WORKFLOW.read_text(encoding="utf-8")

    for job_name, gate_name, target in (
        ("format-targeted", "format-targeted", "tests/test_ingestion.py"),
        ("migration-targeted", "migration-targeted", "tests/test_migration_runner.py"),
        ("security-targeted", "security-targeted", "tests/test_approved_paths.py"),
    ):
        block = workflow.split(f"\n  {job_name}:", 1)[1]
        assert f"contains(needs.gateplan.outputs.required_gates, '{gate_name}')" in block
        assert target in block

    primary = _job_section(workflow, "test", "format-targeted")
    assert "contains(needs.gateplan.outputs.required_gates, 'format-targeted')" not in primary
    assert "contains(needs.gateplan.outputs.required_gates, 'migration-targeted')" not in primary
    assert "contains(needs.gateplan.outputs.required_gates, 'security-targeted')" not in primary


def test_ci_publishes_lock_bound_release_candidate_provenance() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    desktop = _job_section(workflow, "desktop-build", "installer-lifecycle")

    assert "cache: npm" in desktop
    assert "release-candidate.json" in desktop
    assert "release-candidate" in desktop
    assert "src-tauri/Cargo.lock" in desktop
    assert "frontend/package-lock.json" in desktop
    assert "uv.lock" in desktop


def test_release_qualifies_candidate_then_rebuilds_public_installer_with_identity() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "gh run download" in workflow
    assert "release-candidate" in workflow
    assert "release-candidate.json" in workflow
    assert "candidate provenance commit mismatch" in workflow
    assert "candidate installer SHA-256 mismatch" in workflow
    assert "candidate executable SHA-256 mismatch" in workflow
    release_build = "tauri.cmd build --config src-tauri/tauri.conf.json --bundles nsis"
    assert release_build in workflow
    assert workflow.index("Prepare bundled runtime and inject exact release identity") < workflow.index(
        "Build Windows NSIS installer"
    )
    assert workflow.index("Build Windows NSIS installer") < workflow.index(
        "Verify installed NSIS lifecycle"
    )


def test_ci_runs_windows_runtime_smoke() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "windows-runtime-smoke:" in workflow
    assert "runs-on: windows-latest" in workflow
    assert "python -m app.runtime_entrypoint migrate" in workflow
    assert "python scripts/runtime_http_smoke.py" in workflow


def test_ci_minimal_jobs_include_runtime_server_without_editable_install() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    test_job = _job_section(workflow, "test", "lint")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ci_group = project["dependency-groups"]["ci"]

    assert "uvicorn[standard]>=0.22" in ci_group
    assert "playwright>=1.61,<1.62" in ci_group
    assert "uv export --frozen --only-group ci" in test_job
    assert "--require-hashes -r locked-ci.txt" in test_job
    assert "uv pip install --system --no-deps -e ." not in test_job
    assert "fetch-depth: 0" in test_job


def test_ci_builds_and_tests_the_windows_desktop_shell() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    desktop_job = _job_section(workflow, "desktop-build", "installer-lifecycle")

    assert "desktop-fast:" in workflow
    assert "desktop-build:" in workflow
    assert "installer-lifecycle:" in workflow
    assert '".hermes/task-runtime/tauri-build.log"' in desktop_job
    assert "& cmd.exe /d /s /c" in desktop_job
    assert "Tauri Windows build failed with exit code" in desktop_job
    assert "::error title=tauri-build::" in desktop_job
    assert 'python-version: "3.12"' in desktop_job
    assert "python -m desktop.scripts.prepare_bundle" in desktop_job
    desktop_fast = _job_section(workflow, "desktop-fast", "desktop-build")
    assert desktop_fast.index("Prepare the installed Python runtime") < desktop_fast.index(
        "Test the canonical Windows desktop shell"
    )
    assert "cargo install cargo-audit --version 0.22.2 --locked" in desktop_job
    assert "cargo audit --file Cargo.lock" in desktop_job
    assert "frontend\\node_modules\\.bin\\tauri.cmd build --config src-tauri\\tauri.conf.json --bundles nsis" in desktop_job
    assert "timeout-minutes: 30" in desktop_job
    lifecycle_job = _job_section(workflow, "installer-lifecycle", "a0-gates")
    assert "./desktop/scripts/verify_nsis_install.ps1" in lifecycle_job
    assert "actions/upload-artifact@" in desktop_job
    assert "actions/download-artifact@" in lifecycle_job
    assert (
        'Get-ChildItem "src-tauri/target/release/bundle/nsis/*.exe"'
        not in desktop_job
    )
    assert 'Remove-Item -LiteralPath "src-tauri/target/release/bundle/nsis"' in desktop_job
    assert 'Get-ChildItem "src-tauri/target/release/bundle/nsis" -Filter "*.exe" -File' in desktop_job
    assert 'ArcheAxis Knowledge_$($package.version)_x64-setup.exe' in desktop_job
    assert 'Write-Host "NSIS installers found:' in desktop_job


def test_desktop_close_request_destroys_native_window_before_exit() -> None:
    source = (ROOT / "desktop/src-tauri/src/lib.rs").read_text(encoding="utf-8")

    close_handler = source.split(".on_window_event(|window, event|", 1)[1].split(
        ".build(tauri::generate_context!())", 1
    )[0]
    assert "WindowEvent::CloseRequested" in close_handler
    assert "api.prevent_close()" in close_handler
    assert "window.app_handle().exit(0)" in close_handler
    assert "window.destroy()" in close_handler
    assert "window.close()" not in close_handler
    assert "thread::sleep" not in close_handler


def test_desktop_shell_uses_the_product_version_everywhere() -> None:
    product_version = json.loads(
        (ROOT / "app/release-manifest.json").read_text(encoding="utf-8")
    )["product"]["version"]
    package = json.loads((ROOT / "desktop/package.json").read_text(encoding="utf-8"))
    package_lock = json.loads(
        (ROOT / "desktop/package-lock.json").read_text(encoding="utf-8")
    )
    tauri = json.loads(
        (ROOT / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8")
    )
    cargo_version = re.search(
        r'^version = "([^"]+)"$',
        (ROOT / "desktop/src-tauri/Cargo.toml").read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    assert cargo_version is not None

    cargo_lock_root = re.search(
        r'name = "archeaxis-desktop-shell"\nversion = "([^"]+)"',
        (ROOT / "desktop/src-tauri/Cargo.lock").read_text(encoding="utf-8"),
    )
    assert cargo_lock_root is not None, "Cargo.lock root package not found"

    assert {
        package["version"],
        package_lock["version"],
        package_lock["packages"][""]["version"],
        tauri["version"],
        cargo_version.group(1),
        cargo_lock_root.group(1),
    } == {product_version}

    root_tauri = json.loads((ROOT / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    root_cargo = tomllib.loads((ROOT / "src-tauri/Cargo.toml").read_text(encoding="utf-8"))
    frontend = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    assert {root_tauri["version"], root_cargo["package"]["version"], frontend["version"]} == {
        product_version
    }


def test_v0_6_4_development_version_uses_one_version_everywhere() -> None:
    expected_version = "0.6.4"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = json.loads(
        (ROOT / "app/release-manifest.json").read_text(encoding="utf-8")
    )
    package = json.loads((ROOT / "desktop/package.json").read_text(encoding="utf-8"))
    package_lock = json.loads(
        (ROOT / "desktop/package-lock.json").read_text(encoding="utf-8")
    )
    tauri = json.loads(
        (ROOT / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8")
    )
    cargo = tomllib.loads(
        (ROOT / "desktop/src-tauri/Cargo.toml").read_text(encoding="utf-8")
    )
    release_workflow = (
        ROOT / ".github/workflows/release.yml"
    ).read_text(encoding="utf-8")

    assert {
        project["project"]["version"],
        manifest["product"]["version"],
        package["version"],
        package_lock["version"],
        package_lock["packages"][""]["version"],
        tauri["version"],
        cargo["package"]["version"],
    } == {expected_version}
    # release workflow consumes the tag-derived version dynamically and
    # verifies the four sources against the tag (AXW-REL-002): no hardcoded
    # version/asset names may remain
    assert "--version ${{ steps.resolve_version.outputs.release_version }}" in release_workflow
    assert "Resolve and verify release version" in release_workflow
    assert "release_version=" in release_workflow
    assert "'pyproject.toml' = $pyVersion" in release_workflow
    assert "'package.json' = $pkgVersion" in release_workflow
    assert "'tauri.conf.json' = $tauriVersion" in release_workflow
    assert "ArcheAxis.Knowledge-v${{ steps.resolve_version.outputs.release_version }}-Windows-x64-Setup.exe" in release_workflow
    assert "frontend/package-lock.json" in release_workflow
    assert "src-tauri/Cargo.lock" in release_workflow
    assert "--exe src-tauri/target/release/ArcheAxis.exe" in release_workflow
    assert "--frontend frontend/dist" in release_workflow
    assert f"--version {expected_version}" not in release_workflow
    assert (
        'name = "archeaxis-workspace"\nversion = "0.6.4"\nsource = { editable = "." }'
        in (ROOT / "uv.lock").read_text(encoding="utf-8")
    )
    for path in ("config/defaults.yaml", "app/main.py", "desktop/scripts/verify_nsis_install.ps1"):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert expected_version in text
        assert "0.5.0" not in text
    lifecycle = (ROOT / "desktop/scripts/verify_nsis_install.ps1").read_text(
        encoding="utf-8"
    )
    assert "v0.6.4" in lifecycle
    assert "function Wait-ArcheAxisWindow" in lifecycle
    assert "$Shell.Refresh()" in lifecycle
    assert "class ArcheAxisWindow" in lifecycle
    assert "FindVisibleTopLevelWindow([uint32]$Shell.Id)" in lifecycle
    assert "PostClose($WindowHandle, [uint32]$Shell.Id)" in lifecycle
    assert ".CloseMainWindow()" not in lifecycle
    assert "desktop shell rejected WM_CLOSE" in lifecycle
    assert "desktop shell did not exit after WM_CLOSE" in lifecycle


def test_wheel_gate_requires_release_and_workspace_assets() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    wheel_job = _job_section(workflow, "wheel-smoke", "browser-smoke")

    for member in (
        '"app/release-manifest.json"',
        '"app/workspace/ui/index.html"',
        '"app/workspace/ui/assets/styles.css"',
        '"app/workspace/ui/assets/app.js"',
    ):
        assert member in workflow
    assert "assert client.get(\"/workspace\").status_code == 200" in workflow
    assert "assert client.get(\"/workspace/api/status\").status_code == 200" in workflow
    assert "payload['job_id']" not in wheel_job
    assert "SELECT job_id, aggregate_id FROM workspace_jobs_v1" in wheel_job


def test_ci_exposes_one_stable_a0_required_check() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "a0-gates:" in workflow
    assert "gateplan" in workflow.split("a0-gates:", 1)[0] or "needs:" in workflow
    assert 'if: ${{ always() }}' in workflow
    assert "exit 1" in workflow
    # ci-verdict semantics: validates required gates, allows legit not-required skip
    assert "Validate required gates against GatePlan" in workflow
    assert "REQUIRED_GATES" in workflow
    assert "ci-verdict: all required gates success" in workflow


def test_ci_verdict_requires_semantic_gate_ids_not_job_names() -> None:
    """AXW-003A: the aggregator must gate on GatePlan semantic IDs, not the
    GitHub job name. GatePlan emits `py-primary` for the OS/KB suite and
    `static` for convention/architecture checks. A `require test` that matches
    the job name instead of the gate ID can never fire, letting a required
    `py-primary` failure slip through as a green ci-verdict.
    """
    workflow = WORKFLOW.read_text(encoding="utf-8")
    verdict = workflow.split("Validate required gates against GatePlan", 1)[1]

    # The aggregator must reference every required-conditional gate by its
    # semantic GatePlan ID (the same string the classifier emits), not a bare
    # GitHub job name.
    for gate_id in (
        "py-primary",
        "static",
        "lint",
        "py-compat",
        "wheel-smoke",
        "browser-smoke",
        "windows-runtime",
        "desktop-fast",
        "desktop-build",
        "installer-lifecycle",
    ):
        assert f"require {gate_id}" in verdict, f"ci-verdict missing require {gate_id}"

    # The job name `test` is not a GatePlan ID; requiring it is a no-op that
    # would mask a required py-primary failure. Its presence is the AXW-003A bug.
    assert "require test " not in verdict.replace("test ", "", 0).replace(
        "py-primary", ""
    ) or "require test " not in verdict


def test_ci_verdict_does_not_require_orphan_job_name_test() -> None:
    """AXW-003A reverse regression: ci-verdict must never `require test` because
    GatePlan never emits a `test` gate; `py-primary` is the semantic ID for the
    OS/KB/integration suite. Requiring `test` (the GitHub job name) is dead code
    that lets a required py-primary suite failure pass the aggregate.
    """
    workflow = WORKFLOW.read_text(encoding="utf-8")
    verdict = workflow.split("Validate required gates against GatePlan", 1)[1]
    # The verdict body must not contain a `require test` invocation (job-name gate).
    # It may mention `test` in the env var TEST_RESULT only, not as a require key.
    assert "require test " not in verdict
    # Sanity: the suite env var that carries the OS/KB test result is present.
    assert "TEST_RESULT" in verdict


def test_selective_heavy_jobs_gate_on_gateplan() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    # Heavy jobs depend on gateplan and skip when their gate is not required,
    # BUT run under full-qualification or when gateplan fails (fail-closed).
    for job, gate in (
        ("wheel-smoke", "wheel-smoke"),
        ("browser-smoke", "browser-smoke"),
        ("windows-runtime-smoke", "windows-runtime"),
    ):
        block = workflow.split(f"\n  {job}:", 1)[1]
        assert "needs: gateplan" in block, f"{job} missing gateplan dependency"
        assert f"contains(needs.gateplan.outputs.required_gates, '{gate}')" in block
        # fail-closed: gateplan failure OR full-qualification forces the job to run
        assert "needs.gateplan.result != 'success'" in block
        assert "full_qualification == 'true'" in block

    for job, gate in (
        ("desktop-fast", "desktop-fast"),
        ("desktop-build", "desktop-build"),
        ("installer-lifecycle", "installer-lifecycle"),
    ):
        block = workflow.split(f"\n  {job}:", 1)[1]
        assert gate in block
        assert "needs.gateplan.result != 'success'" in block
        assert "full_qualification == 'true'" in block


def test_runtime_policy_uses_python_311_floor_and_python_312_desktop() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "app" / "release-manifest.json").read_text(encoding="utf-8"))
    test_job = _job_section(workflow, "test", "lint")

    assert project["project"]["requires-python"] == ">=3.11"
    assert manifest["product"]["requires_python"] == ">=3.11"
    assert project["tool"]["ruff"]["target-version"] == "py311"
    assert {"UP017", "UP042"} <= set(project["tool"]["ruff"]["lint"]["ignore"])
    assert project["tool"]["mypy"]["python_version"] == "3.11"
    assert 'python-version: ["3.12"]' in test_job
    compat_job = _job_section(workflow, "py-compat", "lint")
    assert 'python-version: ["3.11", "3.13"]' in compat_job
    assert '"3.10"' not in test_job
    ci_adapters = project["dependency-groups"]["ci-adapters"]
    for requirement in (
        "markitdown[pdf,docx,pptx,xlsx]>=0.1",
        "newspaper4k>=0.9",
        "readabilipy>=0.3",
        "trafilatura>=1.6",
        "youtube-transcript-api>=1.2",
    ):
        assert requirement in ci_adapters
    assert "--only-group ci-adapters" in test_job
    assert "ffmpeg tesseract-ocr" in test_job
    assert "cache-dependency-glob: uv.lock" in workflow

    for job_name, next_name in (
        ("lint", "wheel-smoke"),
        ("wheel-smoke", "browser-smoke"),
        ("browser-smoke", "windows-runtime-smoke"),
        ("windows-runtime-smoke", "desktop-fast"),
        ("desktop-fast", "desktop-build"),
        ("desktop-build", "installer-lifecycle"),
    ):
        assert 'python-version: "3.12"' in _job_section(workflow, job_name, next_name)
