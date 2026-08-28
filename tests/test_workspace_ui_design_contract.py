"""Production Workspace must use the approved OSUI v3 shell and Chinese-first language."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

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


def test_legacy_knowledge_dashboard_redirects_to_the_single_product_shell() -> None:
    response = TestClient(app).get("/kb/", follow_redirects=False)

    assert response.status_code in {302, 307, 308}
    assert response.headers["location"] == "/workspace#knowledge"


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


def test_tauri_creates_recovery_webview_before_blocking_backend_startup() -> None:
    source = (ROOT / "src-tauri/src/main.rs").read_text(encoding="utf-8")
    setup = source[source.index(".setup(move |app|"):source.index(".on_window_event")]

    assert setup.index("WebviewWindowBuilder::new") < setup.index("std::thread::spawn")
    assert setup.index("std::thread::spawn") < setup.index("BackendProcess::launch")


def test_loopback_workspace_withholds_raw_api_errors_and_internal_receipts() -> None:
    script = (ROOT / "app/workspace/ui/assets/app.js").read_text(encoding="utf-8")
    page = INDEX.read_text(encoding="utf-8")

    assert "err.message" not in script
    assert "JSON.stringify(data,null,2)" not in script
    assert '"锚点 " + data.anchor_id' not in script
    assert "证据锚点已记录" in script
    assert "/workspace/api/pdf/" not in page
    assert "EvidenceAnchor" not in page
    assert "打开保留的 PDF 原件" in page
    assert "sha256:<64位hex>" not in script
    assert 'aria-label="PDF 内容键"' not in page
    assert 'aria-label="选择 PDF 原件"' in page
    assert 'aria-label="选择证据锚点"' in page
    assert "refreshPdfSources" in script
    assert "refreshPdfAnchors" in script
    assert "addAnchorOption" in script
    for epoch in ("renderEpoch", "searchEpoch", "annotationEpoch", "jumpEpoch", "anchorEpoch"):
        assert epoch in script
    assert "return state.contentKey" in script
    assert "typeof payload.detail" not in script
    assert "previousLoadingTask.destroy()" in script
    assert "state.renderedPage === state.page" in script
    assert "state.renderedContentKey === state.contentKey" in script
    assert "beginPdfNavigation({ preserveSearch: true })" in script
    assert "beginPdfNavigation({ preserveJump: true })" in script
    assert 'case "pdf-prev": if (state.doc && state.page > 1) { beginPdfNavigation();' in script
    assert 'case "pdf-zoom-in": beginPdfNavigation();' in script
    assert "const rendered = await renderPage();" in script
    assert "state.renderedPage !== page || state.renderedContentKey !== key" in script
    for visible_internal in (
        "JSON.stringify(payload.loss_report)",
        "source_hash.slice",
        "detail.current_hash",
        "payload.backup_path",
        "payload.restored_from",
        "option.textContent=`${backup.backup_name}",
    ):
        assert visible_internal not in script
