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


def test_ci_builds_and_tests_the_windows_desktop_shell() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    desktop_job = _job_section(workflow, "desktop-shell", "a0-gates")

    assert "desktop-shell:" in workflow
    assert 'python-version: "3.12"' in desktop_job
    assert "python -m desktop.scripts.prepare_bundle" in desktop_job
    assert desktop_job.index("Prepare the installed Python runtime") < desktop_job.index(
        "Test the Windows Rust library"
    )
    assert "cargo install cargo-audit --version 0.22.2 --locked" in desktop_job
    assert "cargo audit --file Cargo.lock" in desktop_job
    assert "cargo test --test backend_lifecycle -- --ignored --nocapture" in desktop_job
    assert "npm run tauri -- build --bundles nsis" in desktop_job
    assert "Verify the installed NSIS lifecycle" in desktop_job
    assert "timeout-minutes: 45" in desktop_job
    assert "./desktop/scripts/verify_nsis_install.ps1" in desktop_job
    assert (
        'Get-ChildItem "desktop/src-tauri/target/release/bundle/nsis/*.exe"'
        not in desktop_job
    )
    assert 'Remove-Item -LiteralPath "src-tauri/target/release/bundle/nsis"' in desktop_job
    assert 'Get-ChildItem "desktop/src-tauri/target/release/bundle/nsis" -Filter "*.exe" -File' in desktop_job
    assert 'ArcheAxis OS_$($package.version)_x64-setup.exe' in desktop_job
    assert 'Write-Host "NSIS installers found:' in desktop_job


def test_desktop_close_request_destroys_native_window_before_exit() -> None:
    source = (ROOT / "desktop/src-tauri/src/lib.rs").read_text(encoding="utf-8")

    close_handler = source.split(".on_window_event(|window, event|", 1)[1].split(
        ".build(tauri::generate_context!())", 1
    )[0]
    assert "WindowEvent::CloseRequested" in close_handler
    assert "window.destroy()" in close_handler
    assert "window.app_handle().exit(0)" in close_handler
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

    assert {
        package["version"],
        package_lock["version"],
        package_lock["packages"][""]["version"],
        tauri["version"],
        cargo_version.group(1),
    } == {product_version}


def test_v0_4_3_release_candidate_uses_one_version_everywhere() -> None:
    expected_version = "0.4.4"
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
    assert f"--version {expected_version}" in release_workflow
    assert (
        'name = "cognitive-loop-os"\nversion = "0.4.4"\nsource = { editable = "." }'
        in (ROOT / "uv.lock").read_text(encoding="utf-8")
    )
    for path in (
        "config/defaults.yaml",
        "config/settings.yaml",
        "shared/config.py",
        "app/main.py",
        "knowledge_base/api.py",
        "desktop/scripts/verify_nsis_install.ps1",
    ):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert expected_version in text
        assert "0.4.0" not in text
    lifecycle = (ROOT / "desktop/scripts/verify_nsis_install.ps1").read_text(
        encoding="utf-8"
    )
    assert "v0.4.4" in lifecycle
    assert "function Wait-ArcheAxisWindow" in lifecycle
    assert "$Shell.Refresh()" in lifecycle
    assert "$Shell.MainWindowHandle -ne [IntPtr]::Zero" in lifecycle
    assert "$closeSent = $activeShell.CloseMainWindow()" in lifecycle
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
    assert (
        "needs: [test, lint, wheel-smoke, browser-smoke, windows-runtime-smoke, desktop-shell]"
        in workflow
    )
    assert 'if: ${{ always() }}' in workflow
    assert "exit 1" in workflow


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
    assert 'python-version: ["3.11", "3.12", "3.13"]' in test_job
    assert '"3.10"' not in test_job
    ci_adapters = project["dependency-groups"]["ci-adapters"]
    for requirement in (
        "markitdown>=0.1",
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
        ("windows-runtime-smoke", "desktop-shell"),
        ("desktop-shell", "a0-gates"),
    ):
        assert 'python-version: "3.12"' in _job_section(workflow, job_name, next_name)
