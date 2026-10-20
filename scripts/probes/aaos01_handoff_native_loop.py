"""BE10 page-16 native reader probe; invoked only by the owned WebDriver controller.

The setup creates one synthetic note through trusted UI in a fresh owned workspace.
All Core calls made by this module are read-only. No external receiver is contacted.
"""
import hashlib
import json
import time
import uuid


ALLOWED_READS = {"ui_state_read", "documents_list", "document_get"}
READER = "//section[@aria-label='跨项目固定引用']"
MODAL = "//*[@role='dialog' and contains(.,'跨项目固定引用阅读')]"


def core_read(bridge, operation, payload=None):
    if operation not in ALLOWED_READS:
        raise AssertionError("BE10 probe may not issue a Core write or bypass the reader")
    return bridge(operation, payload or {})


def proposal(workspace, document, *, lifetime_ms=30_000, workspace_id=None):
    now = int(time.time() * 1000)
    assert 1_000 <= lifetime_ms <= 30_000
    assert document["version"] >= 1 and len(document["content_sha256"]) == 64
    return {
        "schema": "archeaxis.project-handoff/v1",
        "protocol": "archeaxis.project-observer/v1",
        "idempotency_key": uuid.uuid4().hex,
        "producer": {"namespace": "archeaxis", "workspace_id": workspace_id or workspace["workspace_id"],
                     "restore_epoch": workspace["restore_epoch"]},
        "consumer": {"namespace": "work-lab", "instance_id": uuid.uuid4().hex},
        "created_at_ms": now, "expires_at_ms": now + lifetime_ms,
        "authority": "PREPARATION_ONLY",
        "payload": {"kind": "context", "source": {
            "reference": {key: document[key] for key in ("document_id", "version", "content_sha256")},
            "selection": {"kind": "whole_object"}, "selection_qualification": "UNVERIFIED"},
            "purpose": "research", "authorization_scope": "REFERENCE_METADATA_ONLY"},
    }


def reader_state(js):
    return js("""const root=[...document.querySelectorAll('[aria-label="跨项目固定引用"]')]
      .find(n=>n.getClientRects().length&&!n.closest('[hidden],[inert],[aria-hidden="true"]'));
      const dialogs=[...document.querySelectorAll('[role="dialog"]')].filter(n=>n.getClientRects().length&&!n.closest('[hidden],[inert],[aria-hidden="true"]'));
      const reader=dialogs.find(n=>n.textContent.includes('跨项目固定引用阅读'));
      const body=reader?.querySelector('[aria-label="本机固定版本只读正文"]');
      return {page:location.hash,open:!!reader,body:body?.querySelector('[aria-label="固定版本全文"]')?.textContent??null,
        error:reader?.querySelector('[role="alert"]')?.textContent??null,
        proposalText:reader?.querySelector('textarea[aria-label="上下文提案 JSON"]')?.value??null,
        preview:!!reader?.querySelector('[aria-label="提案只读预览"]'),
        rootVisible:!!root};""")


def diagnostic_identity(js):
    return js("""const rows=[...document.querySelectorAll('[aria-label="诊断控制台"] details[open]')]
      .filter(n=>n.getClientRects().length&&!n.closest('[hidden],[inert],[aria-hidden="true"]')&&
        n.querySelector('summary')?.textContent.startsWith('跨项目固定正文身份 ·'));
      return rows.length===1?JSON.parse(rows[0].querySelector('pre').textContent):null;""")


def assert_snapshot_identity(identity, selected):
    assert isinstance(identity, dict), "Native diagnostic receipt missing"
    assert identity["reference"] == selected["payload"]["source"]["reference"]
    assert identity["producer"] == selected["producer"]
    assert identity["reference_state"] == "CURRENT"
    assert identity["scope"] == "LOCAL_HUMAN_READ_ONLY"
    assert identity["source_authentication"] == identity["selection_qualification"] == "UNVERIFIED"
    assert identity["grants_execution"] is False and identity["grants_knowledge_acceptance"] is False
    assert "editor_json" not in identity, "Diagnostic identity must not include body"
    canonical = json.dumps(selected, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    expected_sha = hashlib.sha256(b"archeaxis.project-handoff/v1\x00" + canonical).hexdigest()
    assert identity["proposal_sha256"] == expected_sha, "Native receipt fingerprint differs from selected proposal"


def preview(ui, js, wait, selected):
    ui.type("上下文提案 JSON", json.dumps(selected, ensure_ascii=False), "textarea", MODAL)
    ui.click_revealed("预览引用信息", MODAL)
    wait("return !![...document.querySelectorAll('[role=\"dialog\"]')].find(n=>n.textContent.includes('跨项目固定引用阅读')&&n.querySelector('[aria-label=\"提案只读预览\"]'))")
    observed = reader_state(js)
    assert observed["open"] and observed["preview"] and observed["body"] is None


def run(*, ui, bridge, js, wait, restart, screenshot, report):
    report.update(status="IN_PROGRESS", evidence_level="REAL_TAURI_WEBDRIVER_WITH_SYNTHETIC_NOTE",
                  boundaries=["Same owned Core and Tauri host", "No external receiver or OS URI", "No model call or Owner acceptance"],
                  core_calls=[])

    def read(operation, payload=None):
        report["core_calls"].append(operation)
        return core_read(bridge, operation, payload)

    # Setup uses product UI, never a hidden Core write, and requires a fresh isolated data root.
    assert read("documents_list")["snapshot_count"] == 0
    ui.page("02")
    ui.click_revealed("新建笔记")
    wait("return !!document.querySelector('[aria-label=\"文档草稿\"]')")
    phrase = "BE10 native pinned body " + uuid.uuid4().hex
    ui.keys('[aria-label="文档草稿"]', "\ue009a\ue000" + phrase, "css selector")
    ui.click_revealed("保存草稿")
    wait("return [...document.querySelectorAll('[role=\"status\"]')].some(n=>n.textContent.includes('已保存版本 2'))")
    documents = read("documents_list")["documents"]
    assert len(documents) == 1, "Synthetic UI setup created an unexpected document count"
    document = read("document_get", {"document_id": documents[0]["document_id"]})
    assert document["version"] >= 2 and document["text_projection"] == phrase
    before = document.copy()
    workspace = read("ui_state_read")
    assert not workspace["recovery_requires_confirmation"]
    report["setup"] = {"kind":"SYNTHETIC_UI_ORIGINAL_NOTE", "document_id":document["document_id"],
                       "selected_version":document["version"], "content_sha256":document["content_sha256"],
                       "body_sha256":hashlib.sha256(phrase.encode()).hexdigest()}

    ui.page("16")
    wait("return location.hash==='#page=16' && !!document.querySelector('[aria-label=\"跨项目固定引用\"]')")
    ui.click_revealed("预览跨项目引用", READER)
    selected = proposal(workspace, document)
    preview(ui, js, wait, selected)
    ui.click_revealed("打开固定版本全文", MODAL)
    wait("return !![...document.querySelectorAll('[role=\"dialog\"]')].find(n=>n.textContent.includes('跨项目固定引用阅读')&&n.querySelector('[aria-label=\"固定版本全文\"]'))")
    observed = reader_state(js)
    assert observed["page"] == "#page=16" and observed["body"] == phrase, "Rendered pinned body differed from the selected Core version"
    screenshot("be10-pinned-body.png")
    ui.click_revealed_selector(MODAL + "//button[@aria-label='查看诊断详情：跨项目固定正文身份']")
    wait("return !![...document.querySelectorAll('[aria-label=\"诊断控制台\"] details[open]')].find(n=>n.textContent.includes('跨项目固定正文身份'))")
    identity = diagnostic_identity(js)
    assert_snapshot_identity(identity, selected)
    report["pinned"] = {"status":"PASS", "reference":identity["reference"],
                        "proposal_sha256":identity["proposal_sha256"], "rendered_body_sha256":hashlib.sha256(observed["body"].encode()).hexdigest(),
                        "diagnostic_body_excluded":True}
    ui.click_revealed("关闭运行诊断", "//*[@role='dialog']")
    ui.click_revealed("关闭并返回", MODAL)
    assert not reader_state(js)["open"]
    restart()
    assert read("document_get", {"document_id": document["document_id"]}) == before
    ui.page("16")
    ui.click_revealed("预览跨项目引用", READER)
    reopened = reader_state(js)
    assert reopened["open"] and reopened["body"] is None and reopened["proposalText"] == "" and not reopened["preview"]
    report["cold_reopen"] = "PASS"

    # Wrong producer identity is sent through the reader UI; there must be no preview or body.
    wrong = proposal(workspace, document, workspace_id="0" * 32 if workspace["workspace_id"] != "0" * 32 else "1" * 32)
    ui.type("上下文提案 JSON", json.dumps(wrong, ensure_ascii=False), "textarea", MODAL)
    ui.click_revealed("预览引用信息", MODAL)
    wait("return !![...document.querySelectorAll('[role=\"dialog\"]')].find(n=>n.textContent.includes('跨项目固定引用阅读')&&n.querySelector('[role=\"alert\"]'))")
    rejected = reader_state(js)
    assert "工作区身份或恢复版本已变化" in (rejected["error"] or "")
    assert not rejected["preview"] and rejected["body"] is None
    assert rejected["proposalText"] == json.dumps(wrong, ensure_ascii=False), "Rejected proposal was not retained for inspection"
    screenshot("be10-wrong-identity.png")
    report["wrong_identity"] = {"status":"PASS", "ui_rejected":True, "body_absent":True, "proposal_retained":True}

    # A short valid TTL proves the mounted reader clears an already previewed proposal.
    expiring = proposal(workspace, document, lifetime_ms=20_000)
    preview(ui, js, wait, expiring)
    ui.click_revealed("打开固定版本全文", MODAL)
    wait("return !![...document.querySelectorAll('[role=\"dialog\"]')].find(n=>n.textContent.includes('跨项目固定引用阅读')&&n.querySelector('[aria-label=\"固定版本全文\"]'))")
    assert reader_state(js)["body"] == phrase, "Expiry case never opened the selected body"
    wait("return !![...document.querySelectorAll('[role=\"dialog\"]')].find(n=>n.textContent.includes('跨项目固定引用阅读')&&n.textContent.includes('提案已到期'))", seconds=30)
    expired = reader_state(js)
    assert expired["body"] is None and not expired["preview"] and expired["error"]
    assert expired["proposalText"] == json.dumps(expiring, ensure_ascii=False), "Expired proposal was not retained for inspection"
    screenshot("be10-expired.png")
    report["expiry"] = {"status":"PASS", "body_absent":True, "preview_cleared":True, "proposal_retained":True}
    ui.click_revealed("关闭并返回", MODAL)
    assert read("document_get", {"document_id": document["document_id"]}) == before
    assert set(report["core_calls"]) <= ALLOWED_READS
    report["status"] = "PASS"
