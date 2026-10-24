"""SIMULATED positive/negative journey regression; no inference or service."""
import copy
import html
import importlib.util
import json
import os
from pathlib import Path

import pytest

from tests.dom_harness import evaluate, reader_dom

ROOT = Path(os.environ.get("AAOS_PROBE_TEST_ROOT", str(Path(__file__).resolve().parents[1])))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/probes" / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


DOCUMENT = {"document_id": "owned-document", "source_id": "owned-source", "version": 12,
            "source_revision": "a" * 64, "content_sha256": "b" * 64,
            "title": "相同 '标题\" 🧭", "text_projection": "Authored 合成正文\n第二行\n",
            "editor_json": {"type": "doc", "content": []}}


def test_saved_deep_journey_reports_cli_intent_and_persisted_budget():
    from tests.test_grouped_native_owner_probe import GroupedNativeProbeTests
    case = GroupedNativeProbeTests()
    case.setUp()
    result = case.exercise_simulated_ai(False, selected_max_tokens=2048, save_deep_binding=True)
    budget = result["ai_progress"]["explicit_output_budget"]
    assert isinstance(budget, dict), "Scalar CLI value misreports saved DEEP effective budget"
    assert budget["requested_cli_max_tokens"] == 2048
    assert budget["effective_by_purpose"]["answer"]["max_tokens"] == 2048


@pytest.mark.parametrize("kind", ["manual", "queue"])
@pytest.mark.parametrize("scene", ["closed", "open", "hidden", "aria-hidden", "wrong-page", "ambiguous", "click-rebound", "unwrapped"])
def test_learning_disclosure_uses_owned_visible_summary_without_executing(kind, scene):
    probe = load("identity_disclosure", "aaos01_grouped_owner_loop.py")
    label = {"manual":"按键定位学习项目", "queue":"学习队列工具"}[kind]
    state = {"open":scene == "open", "page":"19" if scene == "wrong-page" else "12"}
    actions = []

    def js(script):
        hidden = ' hidden' if scene == "hidden" else ' aria-hidden="true"' if scene == "aria-hidden" else ""
        inner = '<ul aria-label="复习队列"><li><button data-learning-item-key="owned">业务标题</button></li></ul>' if kind == "queue" else '<form><label>学习项目键<input value="owned"></label><button>读取项目</button></form>'
        disclosure = '<details aria-label="' + label + '"' + (' open' if state["open"] else '') + hidden + '><summary>业务入口</summary>' + inner + '</details>'
        markup = '<div aria-label="当前页面" data-current-page-id="' + state["page"] + '"></div>'
        markup += inner if scene == "unwrapped" else disclosure
        if scene == "ambiguous": markup += disclosure
        # A retained hidden page must never become the clicked target.
        markup += '<section hidden>' + disclosure + '</section>'
        return evaluate(script, markup)

    ui = probe.GroupedUI(js, lambda *_:None, lambda *_:None, lambda *_:pytest.fail("Disclosure must not execute/submit"), [])

    def click(selector):
        assert "summary" in selector and label in selector
        actions.append(selector)
        state["open"] = True  # The trusted summary click is the only state transition.
        if scene == "click-rebound": state["page"] = "06"

    ui.click_revealed_selector = click
    if scene in ("closed", "open") or scene == "unwrapped" and kind == "queue":
        ui.open_learning_disclosure(kind)
        assert len(actions) == (1 if scene == "closed" else 0)
    else:
        with pytest.raises(AssertionError): ui.open_learning_disclosure(kind)
        assert len(actions) == (1 if scene == "click-rebound" else 0)


def test_manual_type_read_and_identity_queue_click_open_the_existing_disclosure_first():
    probe = load("identity_disclosure_callers", "aaos01_grouped_owner_loop.py")
    actions = []
    ui = probe.GroupedUI(lambda _:None, lambda *_:None, lambda *_:"node", lambda *a:actions.append(("input", a[1])), [])
    ui.open_learning_disclosure = lambda kind:actions.append(("disclosure",kind))
    ui.click_selector = lambda selector:actions.append(("click",selector))
    ui.type("学习项目键", "owned-identity")
    assert actions[0] == ("disclosure","manual")
    actions.clear(); ui.click("读取项目")
    assert actions[0] == ("disclosure","manual") and "读取项目" in actions[1][1]
    actions.clear(); ui.click("owned-identity", "//ul[@aria-label='复习队列']")
    assert actions[0] == ("disclosure","queue") and "@data-learning-item-key='owned-identity'" in actions[1][1]


def test_review_title_reveal_opens_queue_before_layout_hit_test(monkeypatch):
    probe = load("identity_disclosure_layout", "aaos01_grouped_owner_loop.py")
    actions = []
    ui = probe.GroupedUI(lambda _:actions.append("hit-test") or {"ready":True}, lambda *_:None,lambda *_:"node",lambda *_:None,[])
    ui.open_learning_disclosure = lambda kind:actions.append("open-" + kind)
    monkeypatch.setattr(probe.time,"sleep",lambda *_:None)
    ui.reveal_selector(probe.button_selector("owned", "//ul[@aria-label='复习队列']"))
    assert actions == ["open-queue","hit-test"]


@pytest.mark.parametrize("change", [None, "same-question-item", "same-question-assessment", "knowledge-version", "source", "hidden", "wrong-page", "wrong-question", "core"])
def test_learning_restore_binds_rendered_question_diagnostic_and_full_core(change):
    probe = load("identity_learning_restore", "aaos01_grouped_owner_loop.py")
    key = "course:owned:artifact:owned"
    assessment = {"assessment_id":"owned-assessment","question_version":2,"knowledge_id":"owned-knowledge","knowledge_version":"owned-knowledge","source_id":"owned-source","anchor_id":"owned-anchor","question":"相同业务问题？","content":"synthetic answer"}
    expected = {"item_key":key,**{k:assessment[k] for k in ("assessment_id","question_version","knowledge_id","knowledge_version","source_id","anchor_id")}}
    identity = copy.deepcopy(expected)
    fields = {"same-question-item":"item_key","same-question-assessment":"assessment_id","knowledge-version":"knowledge_version","source":"source_id"}
    if change in fields: identity[fields[change]] = "foreign"
    state = {"diagnostic":False}
    clicks = []

    def js(script):
        question = "wrong question" if change == "wrong-question" else assessment["question"]
        markup = '<div aria-label="当前页面" data-current-page-id="' + ('12' if change == "wrong-page" else '06') + '"></div><div class="stitch-learning-review"' + (' hidden' if change == "hidden" else '') + '><article><h3>复习题</h3><p>' + question + '</p></article></div>'
        if state["diagnostic"]:
            markup += '<div role="dialog"><section aria-label="诊断控制台"><details open><summary>学习项目与题目版本 · 对象与来源 · synthetic</summary><pre>' + html.escape(json.dumps(identity)) + '</pre></details></section></div>'
        return evaluate(script, markup)

    class UI:
        def click_revealed_selector(self, selector):
            assert "学习项目与题目版本" in selector
            clicks.append("diagnostic"); state["diagnostic"] = True
        def click_revealed(self,label,scope):
            assert label == "关闭运行诊断"
            clicks.append("close"); state["diagnostic"] = False

    def wait(script): assert js(script), "Wrong or hidden business learning view"
    def read(op,payload):
        assert op == "assessment_get" and payload == {"item_key":key}
        return {**assessment,"content":"changed answer"} if change == "core" else copy.deepcopy(assessment)

    if change is None:
        result = probe.restored_learning_view(UI(),read,js,wait,key,assessment)
        assert result["status"] == "PASS" and result["identity"] == expected
        assert clicks == ["diagnostic","close"]
    else:
        with pytest.raises(AssertionError): probe.restored_learning_view(UI(),read,js,wait,key,assessment)
        if clicks: assert clicks[-1] == "close"


@pytest.mark.parametrize("change", [None, "title", "text", "version", "hidden", "aria-hidden", "css-hidden", "page", "same-title-id", "source", "hash", "revision", "core", "changed-after-close"])
def test_reader_binds_visible_business_content_and_current_ui_identity(change):
    probe = load("identity_reader", "aaos01_grouped_owner_loop.py")
    state = {"diagnostic": False, "closed": False}
    identity = {k: DOCUMENT[k] for k in ("document_id", "source_id", "source_revision", "content_sha256")}
    fields = {"same-title-id":"document_id", "source":"source_id", "hash":"content_sha256", "revision":"source_revision"}
    if change in fields:
        identity[fields[change]] = "wrong-object"
    clicks, reads = [], []

    def js(script):
        options = {"diagnostic":state["diagnostic"], "identity":identity}
        options.update({
            "title": {"title":"wrong", "changed-after-close":"wrong" if state["closed"] else DOCUMENT["title"]}.get(change),
            "text": "wrong body" if change == "text" else None,
            "version": 1 if change == "version" else None,
            "hidden": {"hidden":"hidden", "aria-hidden":'aria-hidden="true"', "css-hidden":'style="display:none"'}.get(change, ""),
            "page": "02" if change == "page" else "03",
        })
        return evaluate(script, reader_dom(DOCUMENT, **options))

    def wait(script):
        assert js(script), "Rendered reader is hidden or wrong page"

    class UI:
        def click_revealed_selector(self, selector):
            assert "文档与来源详细信息" in selector
            clicks.append("diagnostic")
            state["diagnostic"] = True

        def click_revealed(self, label, scope):
            assert label == "关闭运行诊断"
            clicks.append("close")
            state.update(diagnostic=False, closed=True)

    def read(op, payload):
        assert op == "document_get" and payload == {"document_id":DOCUMENT["document_id"]}
        reads.append(op)
        return {**DOCUMENT, "editor_json": {}} if change == "core" else copy.deepcopy(DOCUMENT)

    if change is None:
        value = probe.restored_reader(UI(), read, js, wait, DOCUMENT)
        assert value["status"] == "PASS" and value["identity"] == identity
        assert clicks == ["diagnostic", "close"] and reads == ["document_get"]
    else:
        with pytest.raises(AssertionError):
            probe.restored_reader(UI(), read, js, wait, DOCUMENT)
        if "diagnostic" in clicks:
            assert clicks[-1] == "close", "Owned diagnostic must close even after identity rejection"


@pytest.mark.parametrize("saved", [False, True])
@pytest.mark.parametrize("requested", [2048, 4096])
def test_budget_report_distinguishes_cli_intent_and_purpose_effective_request(saved, requested):
    probe = load("identity_budget", "aaos01_grouped_owner_loop.py")
    purposes = ("answer", "retest", "material", "companion") if saved else ("answer",)
    resolved = {p:{"purpose":p,"lane":"deep","profile":{"max_tokens":1024}} for p in purposes}
    stage = {"saved_deep_binding":{"resolved":resolved}} if saved else {}
    for purpose in purposes:
        request = {"max_tokens":1024 if saved else requested}
        if saved:
            request["model_configuration"] = resolved[purpose]
        original = copy.deepcopy(request)
        probe.record_output_budget(stage, requested, purpose, request)
        assert request == original, "Reporting must never change payload/model budget"
        row = stage["explicit_output_budget"]["effective_by_purpose"][purpose]
        assert row == {"max_tokens":original["max_tokens"],"source":"SAVED_DEEP_BINDING" if saved else "COMPATIBILITY_PER_TASK_UI","evidence":"PERSISTED_REQUEST"}
        assert stage["explicit_output_budget"]["requested_cli_max_tokens"] == requested
        with pytest.raises(AssertionError):
            probe.record_output_budget(stage, requested, purpose, {**request,"max_tokens":999})
        if saved:
            wrong = copy.deepcopy(request); wrong["model_configuration"]["purpose"] = "foreign"
            with pytest.raises(AssertionError):
                probe.record_output_budget(stage, requested, purpose, wrong)


def cancellation_stage():
    stage = {"questions":{},"purposes":{}}
    for purpose in ("material", "companion"):
        request = {"request_id":purpose + "-original", "session_id":"owned-session", "question":"owned " + purpose,"purpose":"synthetic cancellation"}
        preview = {"plan":{"request":request},"plan_sha256":"c" * 64}
        receipt = {**preview,"request_id":request["request_id"],"session_id":"owned-session",
                   "answer":None,"provider_stop_state":"UNKNOWN","authority":"candidate","grants_knowledge_acceptance":False,
                   "schema":"archeaxis.material-answer/v1" if purpose == "material" else "archeaxis.conversation-receipt/v1",
                   "outcome":"failed","state":"cancelled","reason_code":"material_question_cancelled" if purpose == "material" else "conversation_cancelled"}
        identity = {"request_id":request["request_id"]}
        if purpose == "companion": identity["session_id"] = "owned-session"
        stage["purposes"][purpose] = {"preview":preview,"receipt":receipt,"identity":identity,"history":{"session_id":"owned-session","events":[{"kind":"cancelled"}]}}
    return stage


@pytest.mark.parametrize("mutation", [None, "wrong-material-id", "wrong-plan", "answer", "wrong-restored-input", "wrong-history", "execution"])
def test_cancel_reopen_accepts_actual_terminal_copy_without_weakening_identity(monkeypatch, mutation):
    probe = load("identity_cancel", "aaos01_material_companion_loop.py")
    stage = cancellation_stage()
    if mutation == "wrong-plan": stage["purposes"]["material"]["receipt"]["plan_sha256"] = "wrong"
    if mutation == "answer": stage["purposes"]["material"]["receipt"]["answer"] = {"answer":"late answer"}
    actions = []
    monkeypatch.setattr(probe, "install_observer", lambda *a,**k:None)
    monkeypatch.setattr(probe, "remove_observer", lambda *a:{})
    monkeypatch.setattr(probe, "open_material", lambda *a:"//section[@aria-label='固定版本材料问答']")
    monkeypatch.setattr(probe, "proof", lambda *a:{"overflow":False,"rows":[{"operation":"conversation_request"}] if mutation == "execution" else []})

    class UI:
        def click_revealed(self, label, scope): actions.append(label)
        def page(self, page): assert page == "14"
        def reveal_selector(self, selector): pass
        def click_selector(self, selector): assert "owned-session" in selector

    def js(script):
        question = "wrong" if mutation == "wrong-restored-input" else "owned material"
        markup = '<section aria-label="固定版本材料问答"><label>材料问题<input value="' + question + '"></label><input value="synthetic cancellation"><select><option value="deep" selected>deep</option></select><p role="status">原请求执行失败，历史回执已读回；没有再次推理。</p></section><section aria-label="正式陪伴会话"><p>当前会话：owned-session</p><p>请求已取消，没有生成可用回答；原请求已保留。</p><div class="xiaoqi-avatar" data-visible-state="interrupted"></div></section>'
        return evaluate(script, markup)

    def read(op, payload):
        if op == "conversation_history":
            assert payload["body"]["session_id"] == "owned-session"
            return {} if mutation == "wrong-history" else stage["purposes"]["companion"]["history"]
        purpose = "material" if op == "material_question_status" else "companion"
        assert payload == {"body":stage["purposes"][purpose]["identity"]}
        value = copy.deepcopy(stage["purposes"][purpose]["receipt"])
        if mutation == "wrong-material-id" and purpose == "material": value["request_id"] = "other"
        return value

    def wait(script):
        assert js(script), "Actual terminal copy predicate failed"

    def run():
        probe.reopen_cancel(UI(),read,js,wait,actions.append,{},stage)

    if mutation is None:
        run()
        assert stage["cold_reopen"]["status"] == "PASS"
        assert stage["cold_reopen"]["observed_after_attach_execution_calls"] == 0
        assert actions == ["恢复本版材料的上次提问", "cancel-material-cold-reopen.png", "重读历史", "cancel-companion-cold-reopen.png"]
    else:
        with pytest.raises(AssertionError): run()
