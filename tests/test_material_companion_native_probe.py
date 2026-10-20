"""SIMULATED negative qualification checks; no host/model/database is started."""
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("material_companion_probe_contract", ROOT / "scripts/probes/aaos01_material_companion_loop.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize("text", [
    "Independent synthetic material original-id. ArcheAxis keeps a versioned local note.",
    "合成材料 原始编号甲。版本化笔记用于阅读与复习。🌌",
])
def test_summary_probe_asks_about_selected_body_and_records_case_identity(monkeypatch, text):
    """真正run入口的问句与样本绑定；隔离随机ID不伪装为另一份材料。"""
    class StopBeforeUIError(Exception):
        pass

    calls = []

    def observe(js, questions):
        calls.append(questions)
        raise StopBeforeUIError()

    monkeypatch.setattr(probe, "install_observer", observe)
    document = {"document_id": "owned-note", "version": 2,
                "content_sha256": "a" * 64, "text_projection": text}
    saved = {"resolved": {p: {"profile": {"credential_ref": None}}
                           for p in ("material", "companion")}}
    stage = {}
    with pytest.raises(StopBeforeUIError):
        probe.run(None, None, None, None, None, document, saved, stage)
    assert calls[0]["material_question"] == "请用一句中文概括当前已选文本的主题。"
    case = stage["material_summary_case"]
    assert case["revision"] == "selected-text-summary/v2"
    assert case["document"] == {k: document[k] for k in ("document_id", "version", "content_sha256")}
    assert case["context_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert case["context_utf8_bytes"] == len(text.encode("utf-8"))
    assert case["question"] == calls[0]["material_question"]
    assert case["quality_qualification"] == "NOT_ASSESSED"


def fixture(purpose):
    profile = {"model": "synthetic-selected", "endpoint": "http://127.0.0.1:1234/v1", "protocol": "openai", "max_tokens": 1024, "timeout_s": 120, "credential_ref": None}
    resolved = {"purpose": purpose, "lane": "deep", "profile": profile, "configuration_revision": 1, "workspace_id": "synthetic-owned", "restore_epoch": "initial"}
    request = {"request_id": "original", "session_id": "original-session", "model_configuration": resolved, "model": profile["model"], "max_tokens": 1024, "timeout_s": 120}
    preview = {"plan": {"request": request}, "plan_sha256": "a" * 64}
    receipt = {**preview, "request_id": "original", "session_id": "original-session", "schema": "archeaxis.material-answer/v1" if purpose == "material" else "archeaxis.conversation-receipt/v1", "outcome": "succeeded", "state": "completed", "authority": "candidate", "grants_knowledge_acceptance": False, "answer": {**profile, "answer": "SYNTHETIC final answer", "requested_model": profile["model"], "observed_model": profile["model"], "finish_reason": "stop", "truncated": False, "answer_source": "content"}, "answer_sha256": hashlib.sha256(b"SYNTHETIC final answer").hexdigest()}
    return receipt, preview, resolved


@pytest.mark.parametrize("purpose", ["material", "companion"])
def test_receipt_rejects_wrong_identity_binding_destination_empty_or_nonterminal(purpose):
    receipt, preview, resolved = fixture(purpose)
    probe.assert_bound_receipt(receipt, preview, resolved, purpose)
    mutations = [lambda r: r.update(request_id="other"), lambda r: r.update(plan_sha256="b" * 64), lambda r: r.update(authority="accepted"), lambda r: r.update(grants_knowledge_acceptance=True), lambda r: r["answer"].update(answer="  "), lambda r: r["answer"].update(model="different"), lambda r: r["answer"].update(endpoint="https://external.invalid"), lambda r: r["plan"]["request"]["model_configuration"].update(configuration_revision=2), lambda r: r.update(outcome="failed", state="cancelled"), lambda r: r["answer"].update(observed_model="other"), lambda r: r["answer"].update(finish_reason="length"), lambda r: r["answer"].update(truncated=True), lambda r: r["answer"].update(answer_source="reasoning_content")]
    for mutate in mutations:
        bad = copy.deepcopy(receipt); mutate(bad)
        with pytest.raises(AssertionError):
            probe.assert_bound_receipt(bad, preview, resolved, purpose)


def test_call_counter_rejects_duplicate_pending_wrong_origin_or_overflow():
    row = {"operation": "conversation_request", "preview": False, "own": True, "completed": True, "status": 200}
    expected = [("conversation_request", False)]
    probe.assert_calls({"rows": [row], "overflow": False}, expected)
    for bad in [{"rows": [row, row], "overflow": False}, {"rows": [row], "overflow": True}, *({"rows": [{**row, **change}], "overflow": False} for change in [{"preview": True}, {"own": False}, {"completed": False}, {"status": 503}, {"error": "BRIDGE_REJECTED"}])]:
        with pytest.raises(AssertionError):
            probe.assert_calls(bad, expected)
    with pytest.raises(AssertionError):
        probe.assert_calls({"rows": [row], "overflow": False}, [])


@pytest.mark.parametrize("purpose", ["material", "companion"])
def test_cancelled_receipt_rejects_wrong_identity_answer_or_provider_stop_claim(purpose):
    receipt, preview, _ = fixture(purpose)
    receipt.update(answer=None, provider_stop_state="UNKNOWN", outcome="failed", state="cancelled", reason_code="material_question_cancelled" if purpose == "material" else "conversation_cancelled")
    probe.assert_cancelled_receipt(receipt, preview, purpose)
    mutations = [dict(request_id="other"), dict(plan_sha256="b" * 64), dict(answer={"answer":"late"}), dict(provider_stop_state="STOPPED"), dict(reason_code="timeout"), dict(authority="accepted"), dict(grants_knowledge_acceptance=True)]
    for mutation in mutations:
        with pytest.raises(AssertionError):
            probe.assert_cancelled_receipt({**receipt, **mutation}, preview, purpose)


def test_cli_refuses_material_companion_without_saved_actual_model_before_launch():
    value = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py"), "--host", str(ROOT / ".project-local/never-launched.exe"), "--grouped-material-companion-loop"], capture_output=True, text=True, encoding="utf-8")
    assert value.returncode == 2 and "material/companion requires" in value.stderr


def test_cli_refuses_cancellation_without_explicit_material_companion_journey():
    value = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py"), "--host", str(ROOT / ".project-local/never-launched.exe"), "--grouped-material-companion-cancel"], capture_output=True, text=True, encoding="utf-8")
    assert value.returncode == 2 and "cancellation requires" in value.stderr


def test_cancel_observer_binds_only_original_identity_and_retains_ack():
    scripts = []
    probe.install_observer(scripts.append, {"conversation_request": "owned"}, include_cancel=True)
    harness = """
const window={__TAURI__:{core:{invoke:async(_c,a)=>({status:200,body:{...a.request.payload.body,cancel_requested:true,provider_stop_state:'UNKNOWN'}})}}};
eval(SOURCE);
const invoke=(operation,body)=>window.__TAURI__.core.invoke('core_command',{request:{operation,payload:{body}}});
(async()=>{await invoke('conversation_request',{session_id:'s',request_id:'r',question:'owned',preview:false});await invoke('conversation_cancel',{session_id:'s',request_id:'r'});await invoke('conversation_cancel',{session_id:'foreign',request_id:'r'});console.log(JSON.stringify(window.__aaosMC.proof));})().catch(e=>{console.error(e);process.exitCode=1;});
""".replace("SOURCE", json.dumps(scripts[0]))
    value = subprocess.run([shutil.which("node") or "node", "-e", harness], capture_output=True, text=True, encoding="utf-8", check=True)
    rows = json.loads(value.stdout)["rows"]
    assert len(rows) == 3 and rows[1]["own"] and not rows[2]["own"]
    assert rows[1]["request"] == {"session_id":"s", "request_id":"r"}
    assert rows[1]["terminal_response"]["cancel_requested"] is True
    assert "request" not in rows[2] and "terminal_response" not in rows[2]


def test_returned_material_uses_readonly_recovery_before_waiting_for_answer():
    """复现卸载后的空组件：只有显式恢复才有答案，且截图必须带入视口。"""
    class ReturnedPanel:
        recovered = False
        revealed = False

        def click_revealed(self, label, scope):
            assert label == "恢复本版材料的上次提问" and scope == "//section"
            self.recovered = True

        def reveal_selector(self, selector):
            assert self.recovered and selector == "//section//p[.='original answer']"
            self.revealed = True

    ui = ReturnedPanel()

    def wait(script):
        assert ui.recovered, "Navigated component has no receipt before read-only recovery"
        assert '原请求历史回执已读回' in script or "querySelectorAll('p')" in script

    probe.recover_material(ui, wait, "//section", "original answer")
    assert ui.revealed


def test_observer_retains_own_terminal_metadata_without_recording_other_content():
    scripts = []
    probe.install_observer(scripts.append, {"material_question": "owned synthetic"})
    harness = """
const window={__TAURI__:{core:{invoke:async()=>({status:200,body:{
 schema:'archeaxis.material-answer/v1',request_id:'original',outcome:'failed',
 reason_code:'material_model_timeout',plan_sha256:'aaa',answer:{answer:'do not copy'},
 secret:'not retained'}})}}};
eval(SOURCE);
const call=question=>window.__TAURI__.core.invoke('core_command',{request:{operation:'material_question',payload:{body:{question,request_id:'original',preview:false}}}});
(async()=>{await call('owned synthetic');await call('other context');console.log(JSON.stringify(window.__aaosMC.proof));})().catch(e=>{console.error(e);process.exitCode=1;});
""".replace("SOURCE", json.dumps(scripts[0]))
    result = subprocess.run([shutil.which("node") or "node", "-e", harness], capture_output=True, text=True, encoding="utf-8", check=True)
    rows = json.loads(result.stdout)["rows"]
    assert rows[0]["terminal_response"]["reason_code"] == "material_model_timeout"
    assert "answer" not in rows[0]["terminal_response"] and "secret" not in rows[0]["terminal_response"]
    assert "terminal_response" not in rows[1] and "request" not in rows[1]


@pytest.mark.parametrize("purpose,terminal", [("material", "failed"), ("companion", "cancelled")])
def test_http_200_failed_terminal_is_saved_and_fails_before_success_ui_wait(monkeypatch, purpose, terminal):
    receipt, preview, _ = fixture(purpose)
    receipt.update(outcome=terminal, state=terminal, reason_code="material_model_timeout")
    operation = "material_question" if purpose == "material" else "conversation_request"
    row = {"operation": operation, "preview": False, "own": True, "request_id": "original", "session_id": "original-session", "completed": True, "status": 200, "terminal_response": receipt}
    monkeypatch.setattr(probe, "proof", lambda _: {"rows": [row], "overflow": False})
    waits, stage = [], {}
    with pytest.raises(AssertionError, match="material_model_timeout"):
        probe.wait_execution(lambda _: None, lambda script, **kw: waits.append((script, kw)), stage, purpose, preview)
    assert len(waits) == 1 and "__aaosMC" in waits[0][0]
    assert stage["execution_results"][purpose]["response"]["reason_code"] == "material_model_timeout"


def test_execution_observation_rejects_wrong_plan_or_duplicate_identity(monkeypatch):
    receipt, preview, _ = fixture("material")
    row = {"operation": "material_question", "preview": False, "own": True, "request_id": "original", "completed": True, "status": 200, "terminal_response": receipt}
    monkeypatch.setattr(probe, "proof", lambda _: {"rows": [row], "overflow": False})
    assert probe.wait_execution(lambda _: None, lambda *args, **kwargs: None, {}, "material", preview) == receipt
    for rows in [[{**row, "terminal_response": {**receipt, "plan_sha256": "wrong"}}], [row, row]]:
        monkeypatch.setattr(probe, "proof", lambda _: {"rows": rows, "overflow": False})
        with pytest.raises(AssertionError):
            probe.wait_execution(lambda _: None, lambda *args, **kwargs: None, {}, "material", preview)


@pytest.mark.parametrize("synchronous_alert", [False, True])
def test_owned_cancel_document_selection_confirms_its_guard_before_reader(synchronous_alert):
    class Alert(Exception):
        value = {"error": "unexpected alert open"}
    class UI:
        pending = False
        pages = []
        def page(self, page, confirm_navigation=False):
            assert confirm_navigation and not self.pending
            self.pages.append(page)
        def click_revealed_selector(self, selector):
            assert "打开文档 owned.txt" in selector
            self.pending = True
            if synchronous_alert:
                raise Alert()
        def accept_navigation_alert(self):
            assert self.pending
            self.pending = False
        def js(self, script):
            assert not self.pending
            return True
    ui = UI()
    scope = probe.open_material(ui, lambda script: None, {"title": "owned.txt"}, confirm_navigation=True)
    assert ui.pages == ["02", "20"] and "固定版本材料问答" in scope


def test_cancel_journey_confirms_owned_material_draft_before_companion(monkeypatch):
    """经过材料取消后仍须遵守产品的离开确认；不自动处理未知草稿。"""
    class ReachedCompanionError(Exception):
        pass

    receipt, preview, _ = fixture("material")
    receipt.update(answer=None, outcome="failed", provider_stop_state="UNKNOWN",
                   reason_code="material_question_cancelled")
    identity = {"request_id": "original"}
    rows, screenshots = [], []

    class UI:
        def page(self, page, confirm_navigation=False):
            assert confirm_navigation, "owned synthetic draft confirmation was omitted"
            if page == "14":
                assert screenshots == ["cancel-material.png"]
                raise ReachedCompanionError()

        def type(self, *args, **kwargs):
            pass

        def click_revealed(self, label, scope):
            if label == "预览材料提问":
                row = {"operation": "material_question", "preview": True,
                       "preview_response": preview}
            elif label == "确认提问或查询原请求":
                row = {"operation": "material_question", "preview": False}
            else:
                assert label == "取消材料提问"
                row = {"operation": "material_question_cancel", "preview": False,
                       "request": identity,
                       "terminal_response": {**identity, "cancel_requested": True}}
            rows.append({**row, "own": True, "completed": True, "status": 200})

        def reveal_selector(self, scope):
            pass

    monkeypatch.setattr(probe, "install_observer", lambda *a, **k: None)
    monkeypatch.setattr(probe, "remove_observer", lambda *a: {})
    monkeypatch.setattr(probe, "proof", lambda *a: {"rows": rows, "overflow": False})
    monkeypatch.setattr(probe, "open_material", lambda *a, **k: "owned-material")
    monkeypatch.setattr(probe, "select_lane", lambda *a: None)
    with pytest.raises(ReachedCompanionError):
        probe.run_cancel(UI(), lambda *a: receipt, lambda *a: None,
                         lambda *a: None, screenshots.append, {}, {},
                         lambda *a, **k: {"execution_state": "UNKNOWN"})
