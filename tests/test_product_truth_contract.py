from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WORKSPACE = "Human–AI Learning Workspace"
EXPECTED_POSITIONING = (
    "ArcheAxis Workspace is a local-first, evidence-driven Human–AI learning and knowledge workspace"
)


def test_public_product_truth_uses_learning_workspace_positioning() -> None:
    manifest = json.loads((ROOT / "app" / "release-manifest.json").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme_head = "\n".join(
        (ROOT / "README.md").read_text(encoding="utf-8").splitlines()[:60]
    )

    assert manifest["product"]["english_name"] == "ArcheAxis Workspace"
    assert manifest["product"]["workspace_english_name"] == EXPECTED_WORKSPACE
    assert EXPECTED_POSITIONING in readme_head
    assert "认知闭环" not in readme_head
    assert 'description = "Local-first, evidence-driven Human–AI learning and knowledge workspace' in pyproject
    assert '"learning-workspace"' in pyproject


def test_desktop_readiness_projection_uses_public_workspace_name() -> None:
    router = (ROOT / "app" / "workspace" / "router.py").read_text(encoding="utf-8")
    protocol = (ROOT / "desktop" / "src-tauri" / "src" / "protocol.rs").read_text(
        encoding="utf-8"
    )

    assert f'"workspace": "{EXPECTED_WORKSPACE}"' in router
    assert EXPECTED_WORKSPACE in protocol
    assert "ArcheAxis Cognitive Workspace" not in router
    assert "ArcheAxis Cognitive Workspace" not in protocol
