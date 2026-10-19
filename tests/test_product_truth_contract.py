from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WORKSPACE = "Human–AI Learning Workspace"
# Public prose may be Chinese; preserve the product meaning, not an old English sentence.
EXPECTED_POSITIONING_TERMS = ("本地优先", "原件保全", "证据可追溯", "人机双向学习", "可信知识工作台")


def test_public_product_truth_uses_learning_workspace_positioning() -> None:
    manifest = json.loads((ROOT / "app" / "release-manifest.json").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme_head = "\n".join(
        (ROOT / "README.md").read_text(encoding="utf-8").splitlines()[:60]
    )

    assert manifest["product"]["english_name"] == "ArcheAxis Knowledge"
    assert manifest["product"]["name"] == "星环知识系统"
    assert manifest["product"]["workspace_english_name"] == EXPECTED_WORKSPACE
    introduction = next(line for line in readme_head.splitlines()
                        if line.strip() and not line.startswith("#"))
    for term in EXPECTED_POSITIONING_TERMS:
        assert term in introduction, (term, introduction)
    assert "星环知识系统（ArcheAxis Knowledge）" in readme_head
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
