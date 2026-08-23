from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DEVELOPMENT_VERSION = "0.6.9"


def test_development_version_is_one_truth_across_runtime_and_desktop_surfaces() -> None:
    manifest = json.loads((ROOT / "app/release-manifest.json").read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "desktop/package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((ROOT / "desktop/package-lock.json").read_text(encoding="utf-8"))
    tauri = json.loads((ROOT / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    cargo = tomllib.loads((ROOT / "desktop/src-tauri/Cargo.toml").read_text(encoding="utf-8"))
    release_workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    status = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8")
    lifecycle = (ROOT / "desktop/scripts/verify_nsis_install.ps1").read_text(encoding="utf-8")

    assert manifest["product"]["version"] == EXPECTED_DEVELOPMENT_VERSION
    assert project["project"]["version"] == EXPECTED_DEVELOPMENT_VERSION
    assert package["version"] == EXPECTED_DEVELOPMENT_VERSION
    assert package_lock["version"] == EXPECTED_DEVELOPMENT_VERSION
    assert package_lock["packages"][""]["version"] == EXPECTED_DEVELOPMENT_VERSION
    assert tauri["version"] == EXPECTED_DEVELOPMENT_VERSION
    assert cargo["package"]["version"] == EXPECTED_DEVELOPMENT_VERSION
    assert f"--version {EXPECTED_DEVELOPMENT_VERSION}" not in release_workflow  # dynamic since AXW-REL-002
    assert "--version ${{ steps.resolve_version.outputs.release_version }}" in release_workflow
    assert "ArcheAxis.Knowledge-v${{ steps.resolve_version.outputs.release_version }}-Windows-x64-Setup.exe" in release_workflow
    assert f"**当前版本**：`{EXPECTED_DEVELOPMENT_VERSION}`" in readme
    assert f"源码版本为 `{EXPECTED_DEVELOPMENT_VERSION}`" in status
    assert f"-ne '{EXPECTED_DEVELOPMENT_VERSION}'" in lifecycle
    assert f"-ne 'v{EXPECTED_DEVELOPMENT_VERSION}'" in lifecycle


def test_source_release_remains_private_development_state() -> None:
    manifest = json.loads((ROOT / "app/release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["release"] == {
        "status": "unreleased",
        "channel": "development",
        "public": False,
    }


def test_stale_pre_alpha_version_does_not_remain_in_current_truth_docs() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    status = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert "**当前版本**：`0.4.2`" not in readme
    assert "源码版本为 `0.4.2`" not in status
