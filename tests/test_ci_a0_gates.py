from __future__ import annotations

import json
import re
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


def test_ci_runs_windows_runtime_smoke() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "windows-runtime-smoke:" in workflow
    assert "runs-on: windows-latest" in workflow
    assert "python -m app.runtime_entrypoint migrate" in workflow
    assert "python scripts/runtime_http_smoke.py" in workflow


def test_ci_minimal_jobs_include_runtime_server_without_editable_install() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    test_job = _job_section(workflow, "test", "lint")
    ci_requirements = (ROOT / "requirements-ci.txt").read_text(encoding="utf-8").lower()

    assert "uvicorn[standard]>=" in ci_requirements
    assert "uv pip install --system --no-deps -e ." not in test_job


def test_ci_builds_and_tests_the_windows_desktop_shell() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    desktop_job = _job_section(workflow, "desktop-shell", "a0-gates")

    assert "desktop-shell:" in workflow
    assert 'python-version: "3.11"' in desktop_job
    assert "python -m desktop.scripts.prepare_bundle" in desktop_job
    assert "cargo install cargo-audit --version 0.22.2 --locked" in desktop_job
    assert "cargo audit --file Cargo.lock" in desktop_job
    assert "cargo test --test backend_lifecycle -- --ignored --nocapture" in desktop_job
    assert "npm run tauri -- build --bundles nsis" in desktop_job
    assert "Verify the installed NSIS lifecycle" in desktop_job
    assert "./desktop/scripts/verify_nsis_install.ps1" in desktop_job
    assert (
        'Get-ChildItem "desktop/src-tauri/target/release/bundle/nsis/*.exe"'
        in desktop_job
    )


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

    assert {
        package["version"],
        package_lock["version"],
        package_lock["packages"][""]["version"],
        tauri["version"],
        cargo_version.group(1),
    } == {product_version}


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
    assert (
        "needs: [test, lint, wheel-smoke, browser-smoke, windows-runtime-smoke, desktop-shell]"
        in workflow
    )
    assert 'if: ${{ always() }}' in workflow
    assert "exit 1" in workflow
