"""SIMULATED independent dispatch/guard regressions; no host, model or database."""
import copy
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(os.environ.get("AAOS_PROBE_TEST_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / "scripts/probes"))


def load(name):
    path = ROOT / "scripts/probes" / (name + ".py")
    assert path.exists(), "Independent native journey implementation missing"
    spec = importlib.util.spec_from_file_location(name + "_isolated_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LaunchReached(Exception):
    pass


def parse_until_environment(flags):
    native = load("aaos01_tauri_webdriver_loop")
    with patch.object(sys, "argv", ["probe", "--host", "never-launch.exe", *flags]), patch.object(native, "probe_environment", side_effect=LaunchReached):
        native.main()


@pytest.mark.parametrize("mode", ["recovery", "cancel"])
def test_independent_cli_reaches_environment_without_grouped_answer_retest(mode):
    with pytest.raises(LaunchReached):
        parse_until_environment(["--material-companion-" + mode + "-loop", "--material-companion-actual-model", "--material-companion-model", "owned-model"])


@pytest.mark.parametrize("extra", [[], ["--material-companion-actual-model"], ["--material-companion-model", "owned-model"], ["--material-companion-actual-model", "--material-companion-model", "bad model"], ["--material-companion-actual-model", "--material-companion-model", "owned-model", "--grouped-common-owner-loop"], ["--material-companion-actual-model", "--material-companion-model", "owned-model", "--grouped-run-ai"], ["--material-companion-actual-model", "--material-companion-model", "owned-model", "--character-memory-loop"], ["--material-companion-actual-model", "--material-companion-model", "owned-model", "--installer", "never.exe"], ["--material-companion-actual-model", "--material-companion-model", "owned-model", "--material-companion-cancel-loop"]])
def test_cli_rejects_missing_authorization_or_mixed_journey_before_environment(extra):
    with pytest.raises(SystemExit) as error:
        parse_until_environment(["--material-companion-recovery-loop", *extra])
    assert error.value.code == 2


@pytest.mark.parametrize("flags", [["--material-companion-model", "m"], ["--material-companion-actual-model"]])
def test_orphan_independent_options_rejected_before_environment(flags):
    with pytest.raises(SystemExit) as error:
        parse_until_environment(flags)
    assert error.value.code == 2


def test_existing_grouped_material_still_requires_saved_complete_ai_chain():
    with pytest.raises(SystemExit) as error:
        parse_until_environment(["--grouped-material-companion-loop"])
    assert error.value.code == 2


def test_isolation_rejects_draft_environment_before_launch():
    with patch.dict(os.environ, {"AAOS01_LEARNING_DRAFT_ONLY": "1"}):
        with pytest.raises(SystemExit) as error:
            parse_until_environment(["--material-companion-cancel-loop", "--material-companion-actual-model", "--material-companion-model", "m"])
    assert error.value.code == 2


@pytest.mark.parametrize("action", ["pointer_click", "wheel", "value"])
def test_native_independent_command_uses_real_actions_protocol(action):
    native = load("aaos01_tauri_webdriver_loop")
    calls = []
    body = {"x": 10, "y": 20} if action == "pointer_click" else {"x": 10, "y": 20, "deltaX": 0, "deltaY": 120} if action == "wheel" else {"text": "owned"}
    native.independent_element_command(lambda *args: calls.append(args), "session", "element", action, body)
    assert len(calls) == 1
    method, path, payload = calls[0]
    assert method == "POST"
    if action == "value":
        assert path == "/session/session/element/element/value" and payload == body
    else:
        assert path == "/session/session/actions"
        device = payload["actions"][0]
        assert device["type"] == ("pointer" if action == "pointer_click" else "wheel")
        assert [a["type"] for a in device["actions"]] == (["pointerMove", "pointerDown", "pointerUp"] if action == "pointer_click" else ["scroll"])


def scenario():
    grouped = load("aaos01_grouped_owner_loop")
    real_mc = load("aaos01_material_companion_loop")
    trace, report = [], {}
    state = {"doc": None, "typed": "", "epoch": "initial", "saved": None, "wrong": False, "existing": False, "fail": False, "page": None}
    profile = {"endpoint": "http://127.0.0.1:1234/v1", "protocol": "openai", "model": "owned-model", "credential_ref": None, "max_tokens": 1024, "timeout_s": 120}
    class UI:
        def page(self, page, **kw):
            trace.append(("page", page, kw)); state["page"] = page
        def click_revealed(self, label, scope=""):
            trace.append(("click", label))
            if label == "新建笔记":
                state["page"] = "03"
                state["doc"] = {"document_id": "d", "title": "原创笔记", "version": 1, "text_projection": "", "source_id": None, "source_revision": None, "content_sha256": "a" * 64}
            elif label == "保存草稿":
                state["doc"].update(version=2, text_projection=state["typed"], content_sha256="b" * 64)
            elif label == "确认恢复整个工作区": state["epoch"] = "restored"
        def click(self, label, scope=""): return self.click_revealed(label, scope)
        def keys(self, selector, text, using="xpath"):
            trace.append(("keys", selector, using)); state["typed"] = text.replace("\ue009a\ue000", "")
        def reveal_selector(self, selector): trace.append(("reveal", selector))
        def click_revealed_selector(self, selector):
            trace.append(("click_selector", selector)); assert state["page"] == "02"; state["page"] = "03"
    def bridge(op, payload=None):
        trace.append(("read", op))
        if op == "sources_list": return {"sources": []}
        if op == "documents_list": return {"snapshot_count": int(state["doc"] is not None or state["existing"]), "documents": [state["doc"]] if state["doc"] else []}
        if op == "document_get": return copy.deepcopy(state["doc"])
        if op == "machine_tasks_list": return {"items": [], "next_cursor": None}
        if op == "model_configuration_get": return {"revision": 0, "profiles": {}, "bindings": []}
        if op == "workspace_backups": return {"backups": [{"backup_id": "backup"}] if any(t == ("click", "创建一致备份") for t in trace) else []}
        if op == "ui_state_read": return {"restore_epoch": state["epoch"], "state": {"owned": True}, "recovery_candidates": {"owned": True}, "recovery_requires_confirmation": not any(t == ("click", "保留恢复候选") for t in trace)}
        raise AssertionError(op)
    def poll(read, op, payload, predicate, seconds=30):
        value = read(op, payload); assert predicate(value); return value
    def save(ui, read, wait, stage, model, purposes):
        assert purposes == ("material", "companion") and model == "owned-model"
        trace.append(("binding", purposes)); ui.page("19")
        stage["saved_deep_binding"] = {"configuration": {"restore_epoch": "initial"}, "resolved": {p: {"purpose": p, "lane": "deep", "profile": profile} for p in purposes}}
        state["saved"] = stage["saved_deep_binding"]
    def config(*args, restored):
        trace.append(("configuration", restored)); args[0].page("19")
    def restored_reader(ui, read, js, wait, doc):
        trace.append(("reader", doc["document_id"])); assert state["page"] == "03"; assert read("document_get", {"document_id": doc["document_id"]}) == doc
        return {"status": "PASS"}
    controls = SimpleNamespace(xpath_literal=grouped.xpath_literal, machine_tasks=grouped.machine_tasks, save_deep_model_binding=save, read_saved_model_configuration=config, restored_reader=restored_reader, poll=poll)
    class MC:
        def run(self, ui, read, js, wait, screenshot, document, saved, stage):
            trace.append(("mc.run",))
            if state["fail"]:
                stage["execution_results"] = {"material": {"http_status": 200, "response": {"outcome": "failed", "reason_code": "timeout"}}}
                raise AssertionError("failed terminal")
            stage["status"] = "PASS"
        def reopen(self, *args): trace.append(("mc.reopen", args[-1]))
        def run_cancel(self, ui, read, js, wait, screenshot, document, stage, poll):
            trace.append(("mc.run_cancel",))
            stage["purposes"] = {}
            for p in ("material", "companion"):
                request = {"request_id": p, "session_id": "s", "model_configuration": copy.deepcopy(state["saved"]["resolved"][p]), "model": "owned-model", "max_tokens": 1024, "timeout_s": 120, "material": {"kind": "document", "document_id": document["document_id"], "version": document["version"], "content_sha256": document["content_sha256"], "block_id": None} if p == "material" else None}
                if state["wrong"]: request["model_configuration"]["purpose"] = "answer"
                preview = {"plan": {"request": request}, "plan_sha256": "a" * 64}
                receipt = {**preview, "request_id": p, "session_id": "s", "authority": "candidate", "grants_knowledge_acceptance": False, "answer": None, "provider_stop_state": "UNKNOWN", "schema": "archeaxis.material-answer/v1" if p == "material" else "archeaxis.conversation-receipt/v1", "outcome": "failed", "state": "cancelled", "reason_code": "material_question_cancelled" if p == "material" else "conversation_cancelled"}
                stage["purposes"][p] = {"preview": preview, "receipt": receipt}
        def reopen_cancel(self, *args): trace.append(("mc.reopen_cancel",))
        assert_cancelled_receipt = staticmethod(real_mc.assert_cancelled_receipt)
    kwargs = dict(ui=UI(), read=grouped.readonly_bridge(bridge), js=lambda s: None, wait=lambda *a, **kw: trace.append(("wait",)), restart=lambda: trace.append(("restart",)), screenshot=lambda name: trace.append(("screenshot", name)), grouped=controls, material=MC(), selected_model="owned-model", report=report)
    return kwargs, state, trace, report


@pytest.mark.parametrize("mode", ["recovery", "cancel"])
def test_actual_independent_dispatch_has_no_answer_retest_or_acceptance(mode):
    helper = load("aaos01_material_independent_loop")
    kwargs, state, trace, report = scenario()
    helper.run(mode=mode, **kwargs)
    assert report["engineering_status"] == "PASS" and report["closed_loop_verified"] is False
    assert report["owner_acceptance"] == "NOT_EXECUTED"
    assert ("binding", ("material", "companion")) in trace
    assert ("mc.run",) in trace if mode == "recovery" else ("mc.run",) not in trace
    assert ("mc.run_cancel",) in trace if mode == "cancel" else ("mc.run_cancel",) not in trace
    assert trace.count(("restart",)) == (2 if mode == "recovery" else 1)
    assert ("configuration", False) in trace
    assert ("mc.reopen", "cold_reopen") in trace if mode == "recovery" else ("mc.reopen_cancel",) in trace
    if mode == "recovery":
        assert ("mc.reopen", "backup_restore") in trace and ("configuration", True) in trace
    assert not any(t[0] == "read" and t[1] in {"answer", "retest", "knowledge_create", "document_draft"} for t in trace)


def test_existing_workspace_refused_before_any_ui_write():
    helper = load("aaos01_material_independent_loop")
    kwargs, state, trace, report = scenario(); state["existing"] = True
    with pytest.raises(AssertionError): helper.run(mode="cancel", **kwargs)
    assert not any(t[0] in {"click", "keys", "binding", "mc.run_cancel"} for t in trace)
    assert report["engineering_status"] == "FAIL"


def test_200_failed_terminal_does_not_become_success_or_proceed_to_recovery():
    helper = load("aaos01_material_independent_loop")
    kwargs, state, trace, report = scenario(); state["fail"] = True
    with pytest.raises(AssertionError): helper.run(mode="recovery", **kwargs)
    assert report["engineering_status"] == "FAIL" and ("restart",) not in trace
    assert report["material_companion"]["execution_results"]["material"]["http_status"] == 200


def test_cancel_refuses_wrong_saved_binding_before_cold_restart():
    helper = load("aaos01_material_independent_loop")
    kwargs, state, trace, report = scenario(); state["wrong"] = True
    with pytest.raises(AssertionError): helper.run(mode="cancel", **kwargs)
    assert report["engineering_status"] == "FAIL" and ("restart",) not in trace


def test_unknown_mode_refused_before_ui_work():
    helper = load("aaos01_material_independent_loop")
    kwargs, state, trace, report = scenario()
    with pytest.raises(ValueError): helper.run(mode="fake", **kwargs)
    assert trace == []


def test_harness_dispatch_runs_real_independent_helper_with_readonly_bridge(monkeypatch):
    native = load("aaos01_tauri_webdriver_loop")
    helper = load("aaos01_material_independent_loop")
    real_grouped = load("aaos01_grouped_owner_loop")
    kwargs, state, trace, report = scenario()
    grouped = kwargs["grouped"]
    def construct(*args):
        assert args[3] is command and args[5] is accept
        trace.append(("controls_constructed",))
        return kwargs["ui"]
    grouped.GroupedUI = construct
    grouped.readonly_bridge = real_grouped.readonly_bridge
    def modules(name, path):
        assert path.name in {"aaos01_material_independent_loop.py", "aaos01_material_companion_loop.py"}
        return helper if path.name == "aaos01_material_independent_loop.py" else kwargs["material"]
    monkeypatch.setattr(native, "load", modules)
    command, accept = object(), object()
    receipt = {}
    assert native.run_material_independent_branch(mode="cancel", selected_model="owned-model", grouped=grouped, js=kwargs["js"], wait=kwargs["wait"], element=object(), command=command, bridge=kwargs["read"], restart=kwargs["restart"], screenshot=kwargs["screenshot"], accept_navigation_alert=accept, receipt=receipt)
    assert receipt["material_companion_independent"]["mode"] == "cancel"
    assert ("controls_constructed",) in trace and ("mc.run",) not in trace
    assert ("mc.run_cancel",) in trace and ("mc.reopen_cancel",) in trace


def test_independent_ui_test_double_matches_real_grouped_reveal_signature():
    import inspect
    grouped = load("aaos01_grouped_owner_loop")
    kwargs, state, trace, report = scenario()
    assert tuple(inspect.signature(type(kwargs["ui"]).reveal_selector).parameters) == tuple(inspect.signature(grouped.GroupedUI.reveal_selector).parameters)


@pytest.mark.parametrize("mutation", ["request_id", "plan_sha256", "answer", "provider_stop_state", "material", "model_configuration"])
def test_cancel_binding_projection_keeps_identity_and_no_answer_guards(mutation):
    helper = load("aaos01_material_independent_loop")
    kwargs, state, trace, report = scenario()
    kwargs["grouped"].save_deep_model_binding(kwargs["ui"], kwargs["read"], kwargs["wait"], report, "owned-model", ("material", "companion"))
    document = {"document_id":"d","version":2,"content_sha256":"b"*64}
    stage = {}; kwargs["material"].run_cancel(kwargs["ui"], kwargs["read"], kwargs["js"], kwargs["wait"], kwargs["screenshot"], document, stage, kwargs["grouped"].poll)
    value = stage["purposes"]["material"]
    if mutation in {"request_id", "plan_sha256", "answer", "provider_stop_state"}:
        value["receipt"][mutation] = {"answer": "late"} if mutation == "answer" else "other"
    else:
        value["preview"]["plan"]["request"][mutation] = {} if mutation == "material" else {"purpose":"answer"}
    with pytest.raises(AssertionError): helper.assert_cancel_bindings(stage, state["saved"], document, kwargs["material"])
