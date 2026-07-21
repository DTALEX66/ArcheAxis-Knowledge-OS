from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


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


def test_ci_builds_and_tests_the_windows_desktop_shell() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "desktop-shell:" in workflow
    assert 'python-version: "3.11.15"' in workflow
    assert "python -m desktop.scripts.prepare_bundle" in workflow
    assert "cargo test --test backend_lifecycle -- --ignored --nocapture" in workflow
    assert "npm run tauri -- build --bundles nsis" in workflow
    assert "desktop/src-tauri/target/release/bundle/nsis/*.exe" in workflow
    assert "Verify the installed NSIS lifecycle" in workflow
    assert "desktop/scripts/verify_nsis_install.ps1" in workflow


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

    for member in (
        '"app/release-manifest.json"',
        '"app/workspace/ui/index.html"',
        '"app/workspace/ui/assets/styles.css"',
        '"app/workspace/ui/assets/app.js"',
    ):
        assert member in workflow
    assert "assert client.get(\"/workspace\").status_code == 200" in workflow
    assert "assert client.get(\"/workspace/api/status\").status_code == 200" in workflow


def test_ci_exposes_one_stable_a0_required_check() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "a0-gates:" in workflow
    assert (
        "needs: [test, lint, wheel-smoke, browser-smoke, windows-runtime-smoke, desktop-shell]"
        in workflow
    )
    assert 'if: ${{ always() }}' in workflow
    assert "exit 1" in workflow
