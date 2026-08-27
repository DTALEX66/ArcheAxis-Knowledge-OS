"""Production Workspace must use the approved OSUI v3 shell and Chinese-first language."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "app/workspace/ui/index.html"
ROUTER = ROOT / "app/workspace/router.py"
STYLES = ROOT / "app/workspace/ui/assets/osui-v3.css"
PRODUCTION_STYLES = ROOT / "app/workspace/ui/assets/osui-production.css"
PRODUCTION_UI = ROOT / "app/workspace/ui/assets/production-ui.js"


def test_workspace_loads_approved_osui_v3_assets() -> None:
    page = INDEX.read_text(encoding="utf-8")
    router = ROUTER.read_text(encoding="utf-8")

    assert STYLES.is_file()
    assert PRODUCTION_STYLES.is_file()
    assert PRODUCTION_UI.is_file()
    assert "/workspace/assets/osui-v3.css" in page
    assert "/workspace/assets/osui-production.css" in page
    assert "/workspace/assets/production-ui.js" in page
    assert '"osui-v3.css"' in router
    assert '"osui-production.css"' in router
    assert '"production-ui.js"' in router


def test_workspace_uses_chinese_first_product_language() -> None:
    page = INDEX.read_text(encoding="utf-8")
    forbidden_visible_copy = (
        "ARCHEAXIS LEARNING WORKSPACE",
        "LOCAL ONLY",
        "ARCHEAXIS KNOWLEDGE",
        "READ-ONLY VAULT WORKBENCH",
        "LOCAL SYSTEM HEALTH",
        "LOCAL JOB CENTER",
        "HUMAN REVIEW QUEUE",
        "KNOWLEDGE CANDIDATES",
        "GOVERNED KNOWLEDGE CANVAS",
        "LEARNING LOOP",
        "MASTERY FEEDBACK",
        "APPROVED RUNTIME KNOWLEDGE",
        "LIFE CYCLE EVIDENCE",
        "CONTEXT &amp; EVIDENCE",
        "LOCAL INTAKE",
        "TRUTH BOUNDARY",
        ">Status<",
        ">Source<",
        ">Evidence<",
        ">Lifecycle<",
        ">Capability<",
        ">JOB<",
        ">DELIVERY<",
        ">REVIEW<",
    )
    for copy in forbidden_visible_copy:
        assert copy not in page

    for required in (
        "可信知识与学习工作台",
        "本地数据库投影",
        "工作台总览",
        "上下文与证据",
        "任务与回执",
        "视觉课件",
        "空间记忆",
    ):
        assert required in page


def test_workspace_implements_archive_desk_composition() -> None:
    page = INDEX.read_text(encoding="utf-8")
    for contract_class in (
        "workbench-hero",
        "hero-ledger",
        "next-actions",
        "research-ledger",
        "evidence-map",
        "source-paper",
        "lesson-studio",
        "spatial-blueprint",
    ):
        assert contract_class in page

    assert "MOCK ADAPTER" not in page
    assert "UNBOUND" not in page
    assert "演示 fixture" not in page


def test_dynamic_operational_states_are_chinese_first() -> None:
    script = (ROOT / "app/workspace/ui/assets/app.js").read_text(encoding="utf-8")

    assert "const operationalStateLabels=" in script
    assert "stateLabel(job.state)" in script
    assert "stateLabel(item.outbox_state)" in script
    assert "stateLabel(item.receipt_state)" in script
    for leaked_surface in (
        "Outbox pending：",
        "Receipt recorded：",
        "Receipt missing：",
        "投递器：${payload.dispatcher}",
    ):
        assert leaked_surface not in script


def test_production_adapter_never_returns_synthetic_success() -> None:
    adapter = PRODUCTION_UI.read_text(encoding="utf-8")

    assert "Promise.resolve({ ok: true" not in adapter
    assert "createIntakeDraft: () => unsupported(" in adapter
    assert "inspectIntake: () => unsupported(" in adapter
    assert "fixture: false" in adapter


def test_tauri_surface_and_ci_share_the_ui_release_gate() -> None:
    frontend = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    tauri = (ROOT / "src-tauri/src/main.rs").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "星环知识平台（ArcheAxis Knowledge）" in frontend
    assert '.title("星环知识平台（ArcheAxis Knowledge）")' in tauri
    assert "Enforce OSUI design and Chinese-first frontend contracts" in workflow
    assert "npm test -- --run" in workflow
