"""Current grouped UI engineering journey. No bridge mutations or human signoff.

This helper only runs when the native harness explicitly selects the grouped
branch. Pure contract tests must not launch a host or model.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import re
import time
import uuid
from pathlib import Path

READ_OPERATIONS = frozenset(
    {
        "system_version",
        "sources_list",
        "source_original",
        "source_jobs",
        "documents_list",
        "document_get",
        "document_version",
        "anchors_list",
        "anchor_resolve",
        "jobs_get",
        "job_execution_status",
        "job_output",
        "job_quality",
        "source_job_transform",
        "search",
        "knowledge_get",
        "knowledge_qualification",
        "course_list",
        "course_get",
        "assessment_get",
        "learning_items",
        "learning_state",
        "learning_history",
        "capabilities_list",
        "machine_tasks_list",
        "machine_configuration",
        "model_configuration_get",
        "model_configuration_resolve",
        "machine_task_get",
        "machine_contexts_list",
        "ui_state_read",
        "ui_state_machine_status",
        "workspace_backups",
        "material_question_status",
        "conversation_history",
        "conversation_status",
    }
)


def readonly_bridge(bridge):
    def read(operation, payload=None):
        if operation not in READ_OPERATIONS:
            raise ValueError(f"Grouped probe forbids bridge mutation: {operation}")
        return bridge(operation, payload or {})

    return read


def xpath_literal(value: str) -> str:
    if "'" not in value:
        return "'" + value + "'"
    if '"' not in value:
        return '"' + value + '"'
    return "concat(" + ',"\'",'.join("'" + part + "'" for part in value.split("'")) + ")"


READER_SOURCE_TOOLS_OBSERVATION = r"""
return [...document.querySelectorAll('section[aria-label="阅读与编辑文档视图"] .reader-source-tools')]
 .filter(n=>!n.closest('[hidden],[aria-hidden="true"],[inert]')&&n.getClientRects().length>0)
 .map(n=>({open:n.open,summary:!!n.querySelector(':scope>summary')?.getClientRects().length}));
"""


TEXT_SELECTION_OBSERVATION = """const regions=document.querySelectorAll('[aria-label="并排原件正文"]');
const region=regions.length===1?regions[0]:null;
const node=region?.firstChild;
const selection=window.getSelection();
const range=selection?.rangeCount===1?selection.getRangeAt(0):null;
const proof={region_count:regions.length,focused:!!region&&document.activeElement===region,
focus_label:document.activeElement?.getAttribute('aria-label')??null,
source_text:region?.textContent??null,node_text:node?.textContent??null,
node_type:node?.nodeType??null,child_nodes:region?.childNodes.length??null,
node_length:node?.length??null,range_count:selection?.rangeCount??0,
start_same:!!node&&range?.startContainer===node,end_same:!!node&&range?.endContainer===node,
start_offset:range?.startOffset??null,end_offset:range?.endOffset??null,
range_text:range?.toString()??null,cloned_text:range?.cloneContents().textContent??null,
rendered_selection:selection?.toString()??null};
"""


def full_text_selection_wait_script(text):
    expected = json.dumps(text)
    return TEXT_SELECTION_OBSERVATION + (
        "return proof.region_count===1 && proof.focused && proof.node_type===3 && proof.child_nodes===1"
        " && proof.range_count===1 && proof.start_same && proof.end_same && proof.start_offset===0"
        " && proof.end_offset===proof.node_length && proof.source_text==="
        + expected
        + " && proof.node_text==="
        + expected
        + " && proof.range_text==="
        + expected
        + " && proof.cloned_text==="
        + expected
        + ";"
    )


def assert_full_text_selection(proof, text):
    # DOM Range covers source text exactly, including trailing LF. Selection.toString()
    # serializes rendered text and is retained for diagnosis, never used as byte truth.
    assert proof["region_count"] == 1 and proof["focused"] is True, (
        "Original region focus not confirmed"
    )
    assert proof["node_type"] == 3 and proof["child_nodes"] == 1
    assert proof["range_count"] == 1 and proof["start_same"] is True and proof["end_same"] is True
    assert (
        proof["start_offset"] == 0
        and proof["end_offset"] == proof["node_length"] == len(text.encode("utf-16-le")) // 2
    )
    assert (
        proof["source_text"]
        == proof["node_text"]
        == proof["range_text"]
        == proof["cloned_text"]
        == text
    ), "Full original range text differs"


QUOTE_SELECTION_OBSERVATION = """const labels=Array.from(document.querySelectorAll('label'))
.filter(label=>!label.closest('[hidden]')&&Array.from(label.childNodes)
.filter(node=>node.nodeType===3).map(node=>node.textContent).join('').trim()==='选择实际引文');
const input=labels.length===1?labels[0].querySelector('textarea[readonly]'):null;
const selected=input?.parentElement?.nextElementSibling;
const proof={focused:!!input&&document.activeElement===input,value:input?.value??null,
start:input?.selectionStart??null,end:input?.selectionEnd??null,
displayed:selected?.textContent??null};
"""


def assert_quote_selection(proof, text):
    assert proof["focused"] is True and proof["value"] == text
    assert proof["start"] == 0 and proof["end"] == len(text.encode("utf-16-le")) // 2
    assert proof["displayed"] == "已选引文：" + text


def select_full_quote(ui, js, wait, text, result):
    # Use a native Select All shortcut, then independently read both the browser
    # range and the React selection display. Never write DOM selection or events.
    ui.keys(label_selector("选择实际引文", "textarea"), "\ue009a\ue000")
    expected = json.dumps(text)
    result["quote_selection"] = {"status": "IN_PROGRESS"}
    try:
        wait(
            QUOTE_SELECTION_OBSERVATION
            + "return proof.focused && proof.value==="
            + expected
            + " && proof.start===0 && proof.end===proof.value.length"
            + " && proof.displayed==="
            + json.dumps("已选引文：" + text)
            + ";"
        )
        proof = js(QUOTE_SELECTION_OBSERVATION + "return proof;")
        assert_quote_selection(proof, text)
        result["quote_selection"].update(status="PASS", selection=proof)
    except BaseException:
        try:
            result["quote_selection"].update(
                status="FAIL", selection=js(QUOTE_SELECTION_OBSERVATION + "return proof;")
            )
        except BaseException:
            result["quote_selection"].update(
                status="FAIL", selection="UNVERIFIED_OBSERVATION_FAILED"
            )
        raise


def button_selector(label: str, scope: str = "") -> str:
    if scope == "//ul[@aria-label='复习队列']":
        return f"{scope}//button[@data-learning-item-key={xpath_literal(label)} and not(ancestor-or-self::*[@hidden])]"
    return f"{scope}//button[normalize-space(.)={xpath_literal(label)} and not(ancestor-or-self::*[@hidden])]"


def label_selector(label: str, tag: str = "input", scope: str = "") -> str:
    # AaosField associates sibling controls via htmlFor/id; native forms may
    # also wrap their controls. Resolve either actual HTML label association.
    labels = f"{scope}//label[normalize-space(text())={xpath_literal(label)} and not(ancestor-or-self::*[@hidden])]"
    associated = f"{scope}//{tag}[@id={labels}/@for and not(ancestor-or-self::*[@hidden])]"
    wrapped = f"{scope}//label[normalize-space(text())={xpath_literal(label)}]/{tag}[not(ancestor-or-self::*[@hidden])]"
    return associated + " | " + wrapped


def one(rows, predicate, description):
    matches = [row for row in rows if predicate(row)]
    if len(matches) != 1:
        raise AssertionError(f"{description}: expected one identity, got {len(matches)}")
    return matches[0]


def assert_assessment(value, pin):
    for field in (
        "item_key",
        "assessment_id",
        "knowledge_id",
        "knowledge_version",
        "source_id",
        "anchor_id",
    ):
        assert value.get(field) == pin[field], f"Assessment identity changed: {field}"


def assert_review_readback(before, after, learning, pin, answer):
    """Verify one persisted learner event, never mastery or scheduler effectiveness."""
    for history in (before, after):
        assert history["item_key"] == pin["item_key"]
        assert type(history["count"]) is int and history["count"] == len(history["events"])
    assert after["events"][:-1] == before["events"]
    assert after["count"] == before["count"] + 1
    ids = [event["event_id"] for event in after["events"]]
    assert all(type(value) is int for value in ids) and len(set(ids)) == len(ids)
    event = after["events"][-1]
    assert event["kind"] == "review" and isinstance(event["outcome"], str)
    outcome = json.loads(event["outcome"])
    assert outcome["answer"] == answer.strip()
    assert outcome["assessment_id"] == pin["assessment_id"] and outcome["outcome"] == "correct"
    assert outcome["review_evidence"]["knowledge_version"] == pin["knowledge_version"]
    assert learning["item_key"] == pin["item_key"]
    learner = learning["learner"]
    assert learner["event_count"] == after["count"]
    latest = learner["latest_review"]
    for field in ("event_id", "kind", "next_review"):
        assert latest[field] == event[field]
    assert latest["answer"] == outcome["answer"]
    assert latest["assessment_id"] == pin["assessment_id"]


def assert_reported_metering(answer):
    assert answer.get("cost_status") == "UNKNOWN" and answer.get("cost") is None
    assert "usage" in answer and answer.get("usage_status") in {"REPORTED", "UNKNOWN"}
    usage = answer["usage"]
    if answer["usage_status"] == "UNKNOWN":
        assert usage is None
    else:
        assert isinstance(usage, dict) and usage and set(usage) <= {"input_tokens", "output_tokens", "total_tokens"}
        assert all(type(value) is int and 0 <= value <= 2**53-1 for value in usage.values())
    return {"usage":usage,"usage_status":answer["usage_status"],"cost":None,"cost_status":"UNKNOWN"}


def task_conditions(task):
    """Core serializes MachineTaskDto.conditions as JSON text, not an object."""
    raw = task.get("conditions")
    if not isinstance(raw, str):
        raise AssertionError("Machine task conditions must be persisted JSON text")
    value = json.loads(raw)
    assert isinstance(value, dict), "Machine task conditions must decode to an object"
    return value


def _read_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ai_receipt_contract():
    """Read formal literals and declared lanes only; no model/service execution."""
    root = Path(__file__).resolve().parents[2]
    helper = _read_module("grouped_ai_receipt_binding", root / "scripts/probes/aaos01_ai_receipt_qualification.py")
    paths = _read_module("grouped_ai_tool_paths", root / "services/python-workers/tool_paths.py")
    source = (root / "services/python-workers/machine/worker_machine_answer.py").read_text(encoding="utf-8")
    return helper, helper.declared_identities(source, paths.local_runtime_lanes())


def receipt_binding(task, knowledge, question, grant, *, prior_failed_task=None, selected_model=None):
    helper, identities = ai_receipt_contract()
    try:
        return helper.validate(task, knowledge, question, grant, identities,
                               scope=task["scope"], prior_failed_task=prior_failed_task, selected_model=selected_model)
    except (helper.BindingError, ValueError, TypeError, KeyError) as exc:
        return {"status": "UNVERIFIED", "reason": type(exc).__name__ + ": " + str(exc),
                "actual_model_execution": "NOT_PROVEN_BY_RECEIPT_HELPER"}


def inference_status(task, selected_model=None):
    """A candidate worker result is execution evidence, never measured accuracy."""
    conditions = task_conditions(task)
    answer = conditions.get("answer", {})
    model = answer.get("model")
    if (
        task.get("scope") not in {"runtime.answer", "runtime.retest"}
        or task.get("outcome") != "unmeasured"
    ):
        return "NOT_EXECUTED"
    if (
        not isinstance(model, str)
        or not model.strip()
        or any(word in model.lower() for word in ("simulated", "synthetic", "fixture", "manual", "stub", "mock", "unknown"))
    ):
        return "UNVERIFIED"
    _, identities = ai_receipt_contract()
    if selected_model is not None and (model!=selected_model or answer.get('requested_model')!=selected_model or answer.get('observed_model')!=selected_model or conditions.get('request',{}).get('model')!=selected_model):
        return "UNVERIFIED"
    if not any(all(answer.get(key) == (selected_model if key=='model' and selected_model is not None else identity[key]) for key in
                   ("model", "endpoint", "protocol", "engine", "engine_version", "prompt_version"))
               for identity in identities):
        return "UNVERIFIED"
    return "EXECUTED_CANDIDATE_NOT_EVALUATED"


def assert_inference_task(task, knowledge_id, question, grant, scope="runtime.answer"):
    value = task_conditions(task)
    assert task["scope"] == scope and task["outcome"] == "unmeasured"
    assert value["schema"] == (
        "archeaxis.machine-answer/v1"
        if scope == "runtime.answer"
        else "archeaxis.machine-retest/v1"
    )
    assert value["answer_id"] == task["task_id"]
    assert value["knowledge_id"] == knowledge_id and value["question"] == question
    assert task["knowledge_version"] == knowledge_id + "@v1"
    assert value["authority"] == "candidate"
    assert task["model_version"] == value["answer"]["model"]
    assert isinstance(value["answer"]["answer"], str) and value["answer"]["answer"].strip()
    assert value["request"]["context_grant"] == grant
    if scope == "runtime.retest":
        assert value["retest_task_id"] == task["task_id"]
        assert task["retest_of"] == value["retest_of"]
    return value


def assert_correction_lineage(original, failed_task, candidate, authored):
    failed = task_conditions(failed_task)
    correction = failed["correction"]
    assert (
        failed_task["scope"] == "runtime.evaluation.failed" and failed_task["outcome"] == "failed"
    )
    assert failed_task["task_id"] == "evaluation_" + original["answer_id"]
    assert correction["answer_id"] == original["answer_id"]
    assert correction["failed_task_id"] == failed_task["task_id"]
    assert correction["corrects_knowledge_id"] == original["knowledge_id"]
    assert correction["question"] == original["question"]
    assert correction["machine_answer"] == original["answer"]["answer"]
    assert correction["corrected_answer"] == authored["body"]
    assert (
        correction["error_note"] == authored["note"] and correction["reviewer"] == authored["actor"]
    )
    assert correction["correction_candidate_id"] == candidate["knowledge_id"]
    assert candidate["body"] == authored["body"]
    assert candidate["source_id"] is None and candidate["anchor_id"] is None
    for field in ("answer_id", "knowledge_id", "question", "answer", "request"):
        assert failed[field] == original[field], "Correction replaced original " + field
    return correction


def grant_snapshot(document):
    grant = document["editor_json"]["attrs"]["archeaxis_context_grant"]
    return {
        "document_id": document["document_id"],
        "version": document["version"],
        "content_sha256": document["content_sha256"],
        "purpose": grant["purpose"],
    }


def read_grant(read, purpose, knowledge_id, operation):
    page = read("machine_contexts_list")
    assert page["next_cursor"] is None, "Owned fixture context list unexpectedly paginated"
    summary = one(page["items"], lambda item: item["title"] == purpose, "explicit grant document")
    document = read("document_get", {"document_id": summary["document_id"]})
    assert (
        document["version"] == summary["version"]
        and document["content_sha256"] == summary["content_sha256"]
    )
    grant = document["editor_json"]["attrs"]["archeaxis_context_grant"]
    assert grant["state"] == "granted" and grant["knowledge_id"] == knowledge_id
    assert grant["consumer"] == "local-machine" and grant["operations"] == [operation]
    return document


class GroupedUI:
    """DOM evaluation is observation only; all interaction uses WebDriver commands."""

    def __init__(self, js, wait, element, command, evidence, accept_navigation_alert=None):
        self.accept_navigation_alert=accept_navigation_alert
        self.js, self.wait, self.element, self.command, self.evidence = (
            js,
            wait,
            element,
            command,
            evidence,
        )

    def find(self, selector, using="xpath"):
        if using == "xpath":
            self.wait(
                "return !!document.evaluate("
                + json.dumps(selector)
                + ",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue"
            )
        else:
            self.wait("return !!document.querySelector(" + json.dumps(selector) + ")")
        return self.element(using, selector)

    def click(self, label, scope=""):
        if label == "读取项目":
            self.open_learning_disclosure("manual")
        elif scope == "//ul[@aria-label='复习队列']":
            self.open_learning_disclosure("queue")
        selector = button_selector(label, scope)
        self.click_selector(selector)

    def open_learning_disclosure(self, kind):
        label = {"manual": "按键定位学习项目", "queue": "学习队列工具"}[kind]
        script = "const label=" + json.dumps(label) + ";" + r"""
const visible=n=>!!n&&n.getClientRects().length>0&&!n.closest('[hidden],[aria-hidden="true"],[inert]')&&
 Array.from((function*(x){for(;x;x=x.parentElement)yield x;})(n)).every(x=>{
 const s=getComputedStyle(x);return s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse';});
const pages=[...document.querySelectorAll('[data-current-page-id]')];
const page=pages.length===1?pages[0].getAttribute('data-current-page-id'):null;
const nodes=[...document.querySelectorAll('details')].filter(n=>n.getAttribute('aria-label')===label&&visible(n));
const queues=[...document.querySelectorAll('ul[aria-label="复习队列"]')].filter(visible);
return {page,count:nodes.length,open:nodes.length===1?nodes[0].open:null,
 summary:nodes.length===1&&visible(nodes[0].querySelector(':scope>summary')),visible_queues:queues.length};"""
        observed = self.js(script)
        assert observed["page"] in ("06", "11", "12"), "Learning disclosure belongs to another/hidden page"
        if kind == "queue" and observed["count"] == 0:
            assert observed["visible_queues"] == 1, "No unambiguous visible learning queue"
            return
        assert observed["count"] == 1 and observed["summary"], "Missing/hidden/ambiguous learning disclosure"
        if not observed["open"]:
            self.click_revealed_selector("//details[@aria-label=" + xpath_literal(label) + " and not(ancestor-or-self::*[@hidden])]/summary")
            current = self.js(script)
            assert current["page"] == observed["page"] and current["count"] == 1 and current["summary"] and current["open"], "Learning disclosure did not open on the original page"

    def reveal_selector(self, selector):
        """Use real wheel input; observe every clipping ancestor before the final click."""
        if "@aria-label='复习队列'" in selector:
            self.open_learning_disclosure("queue")
        self.find(selector)
        script = "const n=document.evaluate(" + json.dumps(selector) + ",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue;" + r"""
if(!n)return {ready:false};
const r=n.getBoundingClientRect(), px=(r.left+r.right)/2, py=(r.top+r.bottom)/2;
let left=0,top=0,right=innerWidth,bottom=innerHeight;const scroll=[];
for(let a=n.parentElement;a;a=a.parentElement){const s=getComputedStyle(a),b=a.getBoundingClientRect();
 if(s.overflowX!=='visible'){left=Math.max(left,b.left+a.clientLeft);right=Math.min(right,b.left+a.clientLeft+a.clientWidth);}
 if(s.overflowY!=='visible'){top=Math.max(top,b.top+a.clientTop);bottom=Math.min(bottom,b.top+a.clientTop+a.clientHeight);}
 if((/auto|scroll/.test(s.overflowY)&&a.scrollHeight>a.clientHeight+1)||(/auto|scroll/.test(s.overflowX)&&a.scrollWidth>a.clientWidth+1))scroll.push(a);
}
const hit=document.elementFromPoint(px,py);
if(r.width>0&&r.height>0&&px>left&&px<right&&py>top&&py<bottom&&hit&&n.contains(hit))return {ready:true,point:{x:Math.floor(px),y:Math.floor(py)}};
for(const a of scroll){let b=a.getBoundingClientRect(),l=Math.max(0,b.left),t=Math.max(0,b.top),rr=Math.min(innerWidth,b.right),bb=Math.min(innerHeight,b.bottom);
 for(let p=a.parentElement;p;p=p.parentElement){const s=getComputedStyle(p),q=p.getBoundingClientRect();if(s.overflowX!=='visible'){l=Math.max(l,q.left+p.clientLeft);rr=Math.min(rr,q.left+p.clientLeft+p.clientWidth);}if(s.overflowY!=='visible'){t=Math.max(t,q.top+p.clientTop);bb=Math.min(bb,q.top+p.clientTop+p.clientHeight);}}
 const style=getComputedStyle(a);
 let dy=/auto|scroll/.test(style.overflowY)?(py>=bb?240:py<=t?-240:0):0;
 let dx=/auto|scroll/.test(style.overflowX)?(px>=rr?240:px<=l?-240:0):0;
 if((dy>0&&a.scrollTop+a.clientHeight>=a.scrollHeight-1)||(dy<0&&a.scrollTop<=0))dy=0;
 if((dx>0&&a.scrollLeft+a.clientWidth>=a.scrollWidth-1)||(dx<0&&a.scrollLeft<=0))dx=0;
 if((!dx&&!dy)||bb<=t||rr<=l)continue;
 const x=Math.floor((l+rr)/2),y=Math.floor((t+bb)/2),origin=document.elementFromPoint(x,y);
 if(origin&&a.contains(origin))return {ready:false,wheel:{x,y,deltaX:dx,deltaY:dy},scrollTop:a.scrollTop,scrollLeft:a.scrollLeft};
}
return {ready:false,reason:'No reachable scroll container',target:{x:px,y:py},clip:{left,top,right,bottom},hit:hit?.tagName};
"""
        unsettled = 0
        for _ in range(16):
            observed = self.js(script)
            if observed.get("ready"):
                self.evidence.append({"action":"target_visible_and_hit_tested", "selector":selector, **observed.get("point",{})})
                return observed
            if not observed.get("wheel"):
                # 刚激活的保留面板可能先有 DOM、后完成 Dock/ResizeObserver 布局。
                # 仅等有限次重新观察；永久遮挡仍失败，不绕过命中检查或强制点击。
                unsettled += 1
                assert unsettled < 6, observed
                self.evidence.append({"action": "wait_for_target_layout", "selector": selector, "observation": observed})
                time.sleep(.15)
                continue
            self.command(None, "wheel", observed["wheel"])
            self.evidence.append({"action":"trusted_wheel", **observed["wheel"]})
            time.sleep(.15)
        raise TimeoutError("Target remains clipped after bounded trusted scrolling")

    def click_revealed_selector(self, selector):
        for _ in range(3):
            observed = self.reveal_selector(selector)
            point = observed["point"]
            # A late async repaint can move the control after the first hit test.
            # Re-check the exact point against the same target immediately before
            # dispatching pointer input; never click a stale coordinate.
            still_there = self.js(
                "const n=document.evaluate(" + json.dumps(selector) + ",document,null,"
                "XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue;"
                "const hit=document.elementFromPoint(" + str(int(point["x"])) + "," + str(int(point["y"])) + ");"
                "return !!n&&!!hit&&n.contains(hit);"
            )
            if still_there:
                # Element-click may scroll the nested layout again. Pointer input uses
                # the already visible, unobscured target without changing that scroll.
                self.command(None, "pointer_click", point)
                self.evidence.append({"action":"trusted_visible_pointer_click", "selector":selector, **point})
                return
            time.sleep(0.15)
        raise TimeoutError("Target moved before the trusted pointer click")

    def click_revealed(self, label, scope=""):
        self.click_revealed_selector(button_selector(label, scope))

    def open_reader_source_tools(self):
        scope = "//section[@aria-label='阅读与编辑文档视图' and not(ancestor-or-self::*[@hidden])]"
        candidate = button_selector("整理此来源为知识候选", scope)
        self.find(candidate)
        disclosure = self.js(READER_SOURCE_TOOLS_OBSERVATION)
        assert len(disclosure) <= 1, "Ambiguous visible reader source tools"
        if disclosure:
            assert disclosure[0]["summary"], "Missing reader source tools disclosure"
            if not disclosure[0]["open"]:
                self.click_revealed_selector(scope + "//details[contains(@class,'reader-source-tools')]/summary")
                opened = self.js(READER_SOURCE_TOOLS_OBSERVATION)
                assert len(opened) == 1 and opened[0]["open"] and opened[0]["summary"], "Reader source tools did not open"
        self.click_revealed_selector(candidate)

    def click_native_option(self, selector):
        # Native option nodes need not have an independent visible rectangle.
        # WebDriver Element Click applies the browser's select/option semantics.
        self.reveal_selector("(" + selector + ")/ancestor::select[1]")
        element = self.find(selector)
        observation = (
            "const nodes=document.evaluate(" + json.dumps(selector) +
            ",document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null);"
            "const n=nodes.snapshotLength===1?nodes.snapshotItem(0):null,s=n?.closest('select');"
            "return {count:nodes.snapshotLength,valid:n?.tagName==='OPTION'&&!!s&&!s.multiple,"
            "disabled:!n||!s||n.matches(':disabled')||s.matches(':disabled')||!!n.closest('optgroup[disabled]'),"
            "hidden:!s||!!s.closest('[hidden],[aria-hidden=\"true\"],[inert]')||!s.getClientRects().length,"
            "value:n?.value,selected:n?.selected,parent_value:s?.value};"
        )
        before = self.js(observation)
        assert before["count"] == 1 and before["valid"] and not before["disabled"] and not before["hidden"], "Native option is ambiguous, disabled or unavailable"
        self.command(element, "click", {})
        after = self.js(observation)
        assert after["count"] == 1 and after["valid"] and not after["disabled"] and not after["hidden"], "Native option became unavailable"
        assert after["selected"] and after["value"] == after["parent_value"] == before["value"], "Native option selection was not retained"
        self.evidence.append({"action": "trusted_native_option_click", "using": "xpath", "selector": selector, "selected_value": after["value"]})

    def click_selector(self, selector, using="xpath"):
        if using == "xpath":
            if re.search(r"/option(?:\[.*\])?$", selector):
                return self.click_native_option(selector)
            return self.click_revealed_selector(selector)
        element = self.find(selector, using)
        node = (
            "document.evaluate("
            + json.dumps(selector)
            + ",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue"
            if using == "xpath"
            else "document.querySelector(" + json.dumps(selector) + ")"
        )
        self.wait("const n=" + node + ";return !!n && !n.disabled")
        self.command(element, "click", {})
        self.evidence.append({"action": "trusted_click", "using": using, "selector": selector})

    def type(self, label, value, tag="input", scope=""):
        if label == "学习项目键":
            self.open_learning_disclosure("manual")
        selector = label_selector(label, tag, scope)
        element = self.find(selector)
        # WebDriver clear 可能未同步 React 受控状态；可信全选后原位替换。
        self.command(element, "click", {})
        self.command(element, "value", {"text": "\ue009a\ue000"})
        self.command(element, "value", {"text": value if value else "\ue003"})
        node = "document.evaluate(" + json.dumps(selector) + ",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue"
        self.wait("const n=" + node + ";return !!n&&Object.is(n.value," + json.dumps(value) + ")")
        self.evidence.append({"action": "trusted_type", "selector": selector})

    def keys(self, selector, keys, using="xpath"):
        # The Stitch console keeps a fixed task strip over the panel's lower edge.
        # Native element-click scrolls the control under it and is refused as
        # non-interactable; use the trusted in-container wheel plus pointer focus.
        if using == "xpath":
            self.click_revealed_selector(selector)
        else:
            self.command(self.find(selector, using), "click", {})
        self.command(self.find(selector, using), "value", {"text": keys})
        self.evidence.append({"action": "trusted_keys", "using": using, "selector": selector})

    def upload_directory(self, folder):
        selector = 'input[type="file"][aria-label="选择文件夹"]'
        element = self.find(selector, "css selector")
        self.command(element, "value", {"text": str(folder.resolve())})
        self.evidence.append(
            {
                "action": "trusted_directory_upload",
                "selector": selector,
                "fixture_root": str(folder),
            }
        )

    def page(self, page_id, confirm_navigation=False):
        if self.js("return location.hash") == "#page=" + page_id:
            return
        assert re.fullmatch(r"\d{2}", page_id), "Invalid page identity"
        # Use the current Stitch application menu. The old navigation drawer
        # became the launchpad and must not remain an implicit probe contract.
        scope = f'.stitch-workspace-menu details:has(button[data-page-id="{page_id}"])'
        opened = self.js("const n=document.querySelector(" + json.dumps(scope) + ");return !!n&&n.open;")
        if not opened:
            self.click_selector(scope + " > summary", "css selector")
        selector = f'{scope} button[data-page-id="{page_id}"]'
        # Activate the exact focused navigation button using native WebDriver
        # keyboard input. Pointer activation remains separately qualified; do not
        # silently repeat a click that may have hit a moving layout neighbour.
        element = self.find(selector, "css selector")
        focus = self.js("const n=document.querySelector(" + json.dumps(scope) + ");"
            "return n?{summaryFocused:document.activeElement===n.querySelector('summary'),"
            "index:[...n.querySelectorAll('button')].findIndex(b=>b.dataset.pageId===" + json.dumps(page_id) + ")}:null;")
        assert focus and focus["summaryFocused"] and focus["index"] >= 0, "Navigation summary must own native focus"
        summary = self.find(scope + " > summary", "css selector")
        self.command(summary, "value", {"text": "\ue004" * (focus["index"] + 1)})
        focused = self.js("const n=document.querySelector(" + json.dumps(selector) + ");"
            "return !!n && document.activeElement===n && n.dataset.pageId===" + json.dumps(page_id) + ";")
        assert focused, "Native Tab did not focus the exact navigation target"
        self.evidence.append({"action": "native_tab_to_navigation", "page_id": page_id, "tabs": focus["index"] + 1})
        try:
            self.command(element, "value", {"text": "\ue007"})
        except Exception as error:
            if not confirm_navigation or getattr(error,'value',{}).get('error')!='unexpected alert open':
                raise
        if confirm_navigation:
            assert self.accept_navigation_alert is not None, 'Trusted navigation confirmation unavailable'
            self.accept_navigation_alert()
        self.evidence.append({"action": "trusted_navigation_enter", "selector": selector})
        try:
            observation = "return location.hash===" + json.dumps("#page=" + page_id)
            for attempt in range(3):
                try:
                    self.wait(observation)
                    break
                except Exception as error:
                    if not confirm_navigation or getattr(error, "value", {}).get("error") != "unexpected alert open" or attempt == 2:
                        raise
                    self.accept_navigation_alert()
        except TimeoutError:
            self.evidence.append({"action": "navigation_failure_observation", "observed": self.js("return {hash:location.hash,heading:document.querySelector('.ui-page-heading')?.innerText,focused:document.activeElement?.outerHTML}")})
            raise


    def pointer_page(self, page_id):
        selector = f'.stitch-workspace-dock button[data-page-id="{page_id}"]'
        self.find(selector, "css selector")
        self.js(r"""(() => {
const root=document.querySelector('.stitch-workspace-dock'), requested=document.querySelector(""" + json.dumps(selector) + r""");
const out={events:[],samples:[]}, id=n=>/^\d{2}$/.test(n?.dataset?.pageId??'')?n.dataset.pageId:null;
const rect=n=>{if(!n)return null;const r=n.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
const scroll=()=>['.stitch-workspace-dock'].map(scope=>({scope,top:document.querySelector(scope)?.scrollTop??null}));
const route=()=>({hashPage:location.hash.match(/^#page=(\d{2})$/)?.[1]??null,renderPage:(value=>/^\d{2}$/.test(value??'')?value:null)(document.querySelector('.ui-page-heading')?.dataset.currentPageId),currentPages:[...root.querySelectorAll('button[data-page-id][aria-current="page"]')].map(id)});
const sample=phase=>{if(out.samples.length<40)out.samples.push({phase,t:performance.now(),...route(),requestedRect:rect(requested),scroll:scroll()});};
const listeners=[];
for(const type of ['pointerdown','pointerup','pointercancel','mousedown','mouseup','click','focusin'])for(const capture of [true,false]){
 const fn=e=>{if(!(e.target instanceof Element)||!e.target.closest('.stitch-workspace-dock')||out.events.length>=64)return;
 const point='clientX' in e?{x:e.clientX,y:e.clientY}:null;
 out.events.push({type,phase:capture?'capture':'bubble',trusted:e.isTrusted,targetPage:id(e.target.closest('button[data-page-id]')),hitPage:point?id(document.elementFromPoint(point.x,point.y)?.closest('button[data-page-id]')):null,point,requestedRect:rect(requested),scroll:scroll(),...route()});
 if(type==='click'&&!capture){sample('click-bubble');queueMicrotask(()=>sample('click-microtask'));requestAnimationFrame(()=>sample('click-next-frame'));for(const ms of [100,250,1000])setTimeout(()=>sample('click+'+ms),ms);}};
 window.addEventListener(type,fn,capture);listeners.push([type,fn,capture]);
}
out.stop=()=>{for(const [type,fn,capture] of listeners)window.removeEventListener(type,fn,capture);};
window.__aaosNavPointerProbe=out;sample('before');return true;
})()""")
        trace = None
        try:
            # Exactly one trusted native click; no automatic replacement or retry.
            self.click_selector(selector, "css selector")
            self.wait("return location.hash===" + json.dumps("#page=" + page_id))
            self.wait("return window.__aaosNavPointerProbe.samples.some(s=>s.phase==='click+1000')")
        finally:
            trace = self.js("return {events:window.__aaosNavPointerProbe.events,samples:window.__aaosNavPointerProbe.samples}")
            self.evidence.append({"action":"native_pointer_navigation_observation", "requested_page":page_id, "trace":trace})
            self.js("window.__aaosNavPointerProbe.stop();delete window.__aaosNavPointerProbe;")
        assert_pointer_navigation(trace, page_id)
        return trace


def assert_pointer_navigation(trace, page_id):
    for event_type in ("pointerdown", "pointerup", "click"):
        events=[event for event in trace["events"] if event["type"]==event_type and event["phase"]=="capture"]
        assert len(events)==1 and events[0]["trusted"] is True and events[0]["targetPage"]==page_id, "Pointer activation target not proven"
    final=next(sample for sample in trace["samples"] if sample["phase"]=="click+1000")
    assert final["hashPage"]==final["renderPage"]==page_id and page_id in final["currentPages"], "Pointer route not stable"


def poll(read, operation, payload, predicate, seconds=30):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = read(operation, payload)
        if predicate(value):
            return value
        time.sleep(0.15)
    raise TimeoutError(f"Grouped readback deadline: {operation}")


def navigate_retained_review(ui, read, pin, answer):
    recovery = _read_module("grouped_review_draft_proof", Path(__file__).with_name("aaos01_learning_draft_recovery.py"))
    expected = recovery.expected_draft(pin, answer, revealed=True)
    before = poll(read, "ui_state_read", {}, lambda value: value["state"].get("learning_drafts", {}).get(pin["assessment_id"]) == expected)
    history = read("learning_history", {"item_key": pin["item_key"]})
    ui.page("12", confirm_navigation=True)
    after = read("ui_state_read")
    assert (after["workspace_id"], after["restore_epoch"]) == (before["workspace_id"], before["restore_epoch"])
    recovery.assert_unsubmitted(after, expected, history, read("learning_history", {"item_key": pin["item_key"]}), read("assessment_get", {"item_key": pin["item_key"]}), pin)
    return {"status": "PASS", "exact_unsubmitted_draft": True, "history_unchanged": True}


def review_ack_recovery(ui, read, js, wait, restart, key, before, report):
    """Real product submissions with synthetic ACK loss, never direct writes."""
    def install(mode):
        js("""const original=window.__TAURI__,invoke=original.core.invoke;
window.__aaosReviewOriginal=original;window.__aaosReviewProof={rows:[],faults:0};
const mode=""" + json.dumps(mode) + """, key=""" + json.dumps(key) + """;
const observed=async function(command,args,...rest){
 const op=args?.request?.operation, body=args?.request?.payload?.body;
 const value=await Reflect.apply(invoke,original.core,[command,args,...rest]);
 if(command==='core_command'&&['ui_state_write','learning_review'].includes(op)){
 const target=op==='learning_review'?body?.item_key===key:Object.values(value?.body?.state?.pending_reviews??{}).some(e=>e.item_key===key);
 if(target){window.__aaosReviewProof.rows.push({operation:op,status:value.status,body:op==='learning_review'?body:null,event_id:value.body?.event_id,duplicate:value.body?.duplicate});
 if(window.__aaosReviewProof.faults===0&&value.status>=200&&value.status<300&&((mode==='freeze'&&op==='ui_state_write')||(mode==='review'&&op==='learning_review'))){window.__aaosReviewProof.faults++;throw new Error('SYNTHETIC_REVIEW_ACK_LOST');}}
 }return value;
};window.__TAURI__={...original,core:{...original.core,invoke:observed}};
if(window.__TAURI__.core.invoke!==observed)throw new Error('Observer installation refused');""")
    def remove():
        proof=js("return window.__aaosReviewProof")
        js("window.__TAURI__=window.__aaosReviewOriginal;delete window.__aaosReviewOriginal;delete window.__aaosReviewProof;")
        return proof
    def journal():
        state=read('ui_state_read')
        entries=[e for e in state['state'].get('pending_reviews',{}).values() if e['item_key']==key]
        assert len(entries)==1, 'Frozen review absent or duplicated'
        return state,entries[0]
    def recover(expected, history):
        prior=read('ui_state_read')
        prior_backups={row['backup_id'] for row in read('workspace_backups')['backups']}
        ui.page('19',confirm_navigation=True);ui.click('创建一致备份')
        backups=poll(read,'workspace_backups',{},lambda value:len(value['backups'])==len(prior_backups)+1)['backups']
        saved=next(row for row in backups if row['backup_id'] not in prior_backups)
        restart()
        assert journal()[1]==expected and read('learning_history',{'item_key':key})==history
        # Resolve the current request through its actual receipt before restoring.
        # Restore protection must not be weakened merely to exercise a fixture.
        ui.page('12',confirm_navigation=True)
        wait("return [...document.querySelectorAll('label')].some(l=>l.textContent.startsWith('本次答案')&&l.querySelector('textarea')?.matches(':disabled'))")
        install('observe')
        try:
            ui.click('记录复习结果')
            wait("return document.body.innerText.includes('复习记录已保存')")
        finally:
            cleared=remove()
        rows=[row for row in cleared['rows'] if row['operation']=='learning_review']
        assert len(rows)==1 and rows[0]['body']==expected['body'] and rows[0]['status'] in (200,201)
        assert expected['client_event_id'] not in read('ui_state_read')['state'].get('pending_reviews',{})
        ui.page('19');ui.click('刷新备份产物')
        ui.click_selector('//li[strong[normalize-space(.)='+xpath_literal(saved['filename'])+']]//button[normalize-space(.)="预检此备份"]')
        ui.click('确认恢复整个工作区')
        wait("return document.body.innerText.includes('整个工作区已恢复，Core 已重启并读回')")
        wait("return [...document.querySelectorAll('button')].some(b=>b.textContent==='保留恢复候选')")
        candidate=read('ui_state_read')
        assert candidate['restore_epoch']!=prior['restore_epoch'] and candidate['recovery_candidates']['pending_reviews'][expected['client_event_id']]==expected
        assert js("return [...document.querySelectorAll('button')].find(b=>b.textContent==='丢弃恢复候选')?.disabled") is True
        ui.click('保留恢复候选')
        poll(read,'ui_state_read',{},lambda value:value['recovery_requires_confirmation'] is False)
        ui.page('12',confirm_navigation=True)
        report.setdefault('restore_preserve',[]).append({'status':'PASS','origin_retained':True,'discard_disabled':True,'epoch_changed':True})
        restart()
        state,entry=journal()
        assert entry==expected and read('learning_history',{'item_key':key})==history
        # The persisted scene must recover its pending review without a
        # navigation decision or changing the frozen learning identity.
        wait("return [...document.querySelectorAll('label')].some(l=>l.textContent.startsWith('本次答案')&&l.querySelector('textarea')?.matches(':disabled'))")
        answer=js("return [...document.querySelectorAll('label')].find(l=>l.textContent.startsWith('本次答案'))?.querySelector('textarea')?.value")
        assert answer==expected['body']['answer']
        return state
    report.update(status='IN_PROGRESS',evidence_level='INTEGRATED_WITH_SYNTHETIC_ACK_LOSS')
    install('freeze')
    try:
        ui.click('记录复习结果')
        wait("return window.__aaosReviewProof.faults===1&&document.body.innerText.includes('复习提交未确认')")
    finally:
        proof=remove(); report['freeze_ack']=proof
    assert proof['faults']==1 and not any(r['operation']=='learning_review' for r in proof['rows'])
    state,entry=journal()
    assert read('learning_history',{'item_key':key})==before
    recovered=recover(entry,before)
    assert recovered['workspace_id']==state['workspace_id'] and recovered['restore_epoch']!=state['restore_epoch']
    install('review')
    try:
        ui.click('记录复习结果')
        wait("return window.__aaosReviewProof.faults===1&&document.body.innerText.includes('复习提交未确认')")
    finally:
        proof=remove(); report['review_ack']=proof
    rows=[r for r in proof['rows'] if r['operation']=='learning_review']
    assert proof['faults']==1 and len(rows)==1 and rows[0]['status']==201 and rows[0]['duplicate'] is False and rows[0]['body']==entry['body']
    first=rows[0]; history=read('learning_history',{'item_key':key}); learning=read('learning_state',{'item_key':key})
    assert journal()[1]==entry and history!=before
    recover(entry,history)
    assert read('learning_state',{'item_key':key})==learning
    install('observe')
    try:
        ui.click('记录复习结果')
        wait("return document.body.innerText.includes('复习记录已保存')")
    finally:
        proof=remove(); report['explicit_retry']=proof
    rows=[r for r in proof['rows'] if r['operation']=='learning_review']
    assert proof['faults']==0 and len(rows)==1 and rows[0]['status']==200 and rows[0]['duplicate'] is True and rows[0]['body']==entry['body'] and rows[0]['event_id']==first['event_id']
    assert entry['client_event_id'] not in read('ui_state_read')['state'].get('pending_reviews',{})
    assert read('learning_history',{'item_key':key})==history and read('learning_state',{'item_key':key})==learning
    # Persist hashes only; test material bodies are not needed in the receipt.
    for phase in ['freeze_ack','review_ack','explicit_retry']:
        for row in report[phase]['rows']:
            body=row.pop('body',None)
            if body is not None:row['body_sha256']=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    report['status']='PASS'
    return learning,history


def multi_review_ack_recovery(ui, read, js, wait, restart, key, before, knowledge, nonce, answer, report):
    """Create both requests through native UI; never seed journal/database fixtures."""
    report.update(status='IN_PROGRESS', evidence_level='INTEGRATED_WITH_SYNTHETIC_ACK_LOSS')

    def install(target, lose=False):
        js("""const original=window.__TAURI__,invoke=original.core.invoke;
window.__aaosMultiOriginal=original;window.__aaosMultiProof={rows:[],faults:0};
const target="""+json.dumps(target)+""", lose="""+json.dumps(lose)+""";
const observed=async function(command,args,...rest){
 const op=args?.request?.operation,body=args?.request?.payload?.body;
 const attempted=command==='core_command'&&['machine_answer','machine_retest'].includes(op);
 if(attempted)window.__aaosMultiProof.rows.push({operation:op,completed:false});
 const value=await Reflect.apply(invoke,original.core,[command,args,...rest]);
 if(command==='core_command'&&['ui_state_write','learning_review','machine_answer','machine_retest'].includes(op)){
  window.__aaosMultiProof.rows.push({operation:op,status:value.status,body:op==='learning_review'?body:null,event_id:value.body?.event_id});
  const frozen=Object.values(value?.body?.state?.pending_reviews??{}).some(e=>e.item_key===target);
  if(lose&&op==='ui_state_write'&&frozen&&value.status>=200&&value.status<300&&window.__aaosMultiProof.faults===0){window.__aaosMultiProof.faults++;throw new Error('SYNTHETIC_MULTI_REVIEW_ACK_LOST');}
 }return value;
};window.__TAURI__={...original,core:{...original.core,invoke:observed}};
if(window.__TAURI__.core.invoke!==observed)throw new Error('Observer installation refused');""")

    def remove():
        proof=js('return window.__aaosMultiProof')
        js('window.__TAURI__=window.__aaosMultiOriginal;delete window.__aaosMultiOriginal;delete window.__aaosMultiProof;')
        return proof

    def freeze(target):
        install(target, True)
        try:
            ui.click('记录复习结果')
            wait("return window.__aaosMultiProof.faults===1&&document.body.innerText.includes('复习提交未确认')")
        finally:
            proof=remove()
        assert proof['faults']==1 and not any(r['operation'] in ('learning_review','machine_answer','machine_retest') for r in proof['rows'])
        entries=read('ui_state_read')['state']['pending_reviews']
        return one(list(entries.values()),lambda e:e['item_key']==target,'native frozen review')

    first=freeze(key)
    assert read('learning_history',{'item_key':key})==before
    # Reconcile the exact durable write through the product's reread action.
    # The same-source candidate overlay is retained until a cold restart.
    ui.click('核对工作状态')
    wait("return ![...document.querySelectorAll('button')].some(b=>b.textContent==='核对工作状态')")
    ui.page('19',confirm_navigation=True)
    ui.click('由当前知识建立学习问题',"//section[@aria-label='同源候选审核']")
    assert ui.accept_navigation_alert is not None, 'Trusted learning navigation confirmation unavailable'
    def trusted_wait(script):
        try:
            wait(script)
        except Exception as error:
            if 'unexpected alert open' not in str(error):
                raise
            ui.accept_navigation_alert()
            wait(script)
    trusted_wait("return location.hash==='#page=06'")
    trusted_wait("return [...document.querySelectorAll('label')].find(l=>l.textContent.startsWith('学习项目键'))?.querySelector('input')?.value?.startsWith('assessment_')&&!!document.querySelector('.stitch-learning-review article')")
    second_key=js("return [...document.querySelectorAll('label')].find(l=>l.textContent.startsWith('学习项目键'))?.querySelector('input')?.value")
    assert isinstance(second_key,str) and second_key.startswith('assessment_') and second_key!=key
    second_assessment=read('assessment_get',{'item_key':second_key})
    assert second_assessment['knowledge_id']==knowledge['knowledge_id']
    second_before=read('learning_history',{'item_key':second_key})
    ui.type('本次答案',answer,'textarea');ui.click('查看答案与核对内容')
    ui.click_selector(label_selector('回答正确'));ui.keys(label_selector('学习者自评','select'),'\ue015\ue015\ue015\ue007')
    second=freeze(second_key)
    frozen={first['client_event_id']:first,second['client_event_id']:second}
    assert read('ui_state_read')['state']['pending_reviews']==frozen
    restart();ui.page('06',confirm_navigation=True)
    assert read('ui_state_read')['state']['pending_reviews']==frozen
    install(None)
    try:
        for entry in (first,second,first):
            ui.click('恢复复习请求 '+entry['item_key'])
            trusted_wait("return !!document.querySelector('.stitch-learning-review article')&&[...document.querySelectorAll('label')].find(l=>l.textContent.startsWith('学习项目键'))?.querySelector('input')?.value==="+json.dumps(entry['item_key'])+"&&[...document.querySelectorAll('label')].find(l=>l.textContent.startsWith('本次答案'))?.querySelector('textarea')?.value==="+json.dumps(entry['body']['answer']))
            ui.accept_navigation_alert()
            assert js("return [...document.querySelectorAll('label')].find(l=>l.textContent.startsWith('本次答案'))?.querySelector('textarea')?.disabled") is True
            assert js("return [...document.querySelectorAll('label')].find(l=>l.textContent.startsWith('学习者自评'))?.querySelector('select')?.value") == str(entry['body']['rating'])
            assert js("return [...document.querySelectorAll('label')].find(l=>l.textContent.trim()==='回答正确')?.querySelector('input')?.checked") is entry['body']['correct']
            assert read('ui_state_read')['state']['pending_reviews']==frozen
        assert read('learning_history',{'item_key':key})==before
        assert read('learning_history',{'item_key':second_key})==second_before
    finally:
        selected=remove()
    assert not any(r['operation'] in ('learning_review','machine_answer','machine_retest') for r in selected['rows'])
    submissions=[]
    for entry,remaining in ((first,{second['client_event_id']:second}),(second,{})):
        if entry is second:
            # The single remaining request has a normal queue button, and still
            # retains its frozen body when explicitly selected.
            ui.click(second_key,"//ul[@aria-label='复习队列']")
            trusted_wait("return !!document.querySelector('.stitch-learning-review article')&&[...document.querySelectorAll('label')].find(l=>l.textContent.startsWith('学习项目键'))?.querySelector('input')?.value==="+json.dumps(second_key))
            ui.accept_navigation_alert()
        install(entry['item_key'])
        try:
            ui.click('记录复习结果')
            wait("return document.body.innerText.includes('复习记录已保存')")
        finally:
            proof=remove()
        rows=[r for r in proof['rows'] if r['operation']=='learning_review']
        assert len(rows)==1 and rows[0]['status']==201 and rows[0]['body']==entry['body']
        assert not any(r['operation'] in ('machine_answer','machine_retest') for r in proof['rows'])
        assert read('ui_state_read')['state'].get('pending_reviews',{})==remaining
        submissions.append({'item_key':entry['item_key'],'client_event_id':entry['client_event_id'],'event_id':rows[0]['event_id'],'body_sha256':hashlib.sha256(json.dumps(entry['body'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()})
    learning=read('learning_state',{'item_key':key});history=read('learning_history',{'item_key':key})
    assert history['count']==before['count']+1
    second_history=read('learning_history',{'item_key':second_key})
    assert second_history['count']==second_before['count']+1
    restart()
    assert read('ui_state_read')['state'].get('pending_reviews',{})=={}
    assert read('learning_history',{'item_key':key})==history
    assert read('learning_history',{'item_key':second_key})==second_history
    report.update(status='PASS',cold_restart=True,explicit_selection=True,selection_review_calls=0,recovery_inference_calls=0,submissions=submissions,other_request_retained=True)
    return learning,history


def run_grouped_loop(
    *,
    bridge,
    js,
    wait,
    element,
    command,
    work: Path,
    screenshot,
    restart,
    run_ai=False,
    authored_intervention=False,
    report=None,
    require_actual_ai_loop=False,
    pointer_navigation=False,
    review_ack_loss=False,
    multi_review_ack_loss=False,
    machine_ack_loss=False,
    machine_cancel=False,
    closure_features=False,
    download_control=None,
    selected_model=None,
    selected_max_tokens=None,
    save_deep_binding=False,
    material_companion_loop=False,
    material_companion_cancel=False,
    accept_navigation_alert=None,
):
    assert not material_companion_loop or (save_deep_binding and require_actual_ai_loop and run_ai), "Material/companion requires saved DEEP actual-model qualification"
    assert not material_companion_cancel or material_companion_loop, "Cancellation requires the explicit material/companion journey"
    teaching_only = os.environ.get("AAOS01_TEACHING_DRAFT_ONLY") == "1"
    learning_only = os.environ.get("AAOS01_LEARNING_DRAFT_ONLY") == "1"
    if teaching_only and learning_only:
        raise ValueError("Draft isolation modes are mutually exclusive")
    if teaching_only or learning_only:
        if any((run_ai, authored_intervention, require_actual_ai_loop, review_ack_loss, multi_review_ack_loss, machine_ack_loss, machine_cancel, closure_features)):
            raise ValueError("Learning draft isolation forbids model, ACK injection, and other journey modes")
        helper = _read_module("aaos_isolated_draft_recovery", Path(__file__).with_name("aaos01_teaching_draft_recovery.py" if teaching_only else "aaos01_learning_draft_recovery.py"))
        result = report if report is not None else {}
        ui = GroupedUI(js, wait, element, command, result.setdefault("actions", []), accept_navigation_alert)
        if teaching_only:
            navigation = _read_module("aaos_draft_navigation", Path(__file__).with_name("aaos01_learning_draft_recovery.py"))
            raw_wait = wait
            wait = lambda script: navigation.wait_with_navigation(ui, raw_wait, script)
        return helper.run(ui=ui, bridge=bridge, read=readonly_bridge(bridge), js=js, wait=wait, restart=restart, poll=poll, screenshot=screenshot, report=result)
    read = readonly_bridge(bridge)
    result = report if report is not None else {}
    result.update(
        {
            "engineering_status": "IN_PROGRESS",
            "schema": "archeaxis.grouped-owner-journey-probe/v1",
            "status": "PARTIAL",
            "human_signoff": False,
            "owner_acceptance": "NOT_EXECUTED",
            "closed_loop_verified": False,
            "execution_surface": "CURRENT_GROUPED_NATIVE_UI",
            "actions": [],
            "stages": [],
            "limitations": [
                "Authored project-local fixtures and SYNTHETIC review/learner actor, not Owner approval",
                "Directory upload/WebView2 support must be observed in the actual host",
                "No physical IME, installed-user-data, release or learning effectiveness claim",
            ],
        }
    )
    ui = GroupedUI(js, wait, element, command, result["actions"], accept_navigation_alert)
    nonce = uuid.uuid4().hex
    folder = work / "grouped-fixtures" / ("same-source-" + nonce)
    folder.mkdir(parents=True, exist_ok=False)
    text = f"Grouped native source {nonce}.\nArcheAxis stores original bytes separately from a versioned document.\n"
    fixtures = {
        "grouped-owner.txt": text.encode(),
        "grouped-owner.md": ("# Common Markdown\n\n" + text).encode(),
    }
    for name, content in fixtures.items():
        (folder / name).write_bytes(content)
    assert read("sources_list")["sources"] == [], (
        "Grouped branch requires a fresh owned product workspace"
    )
    assert read("documents_list")["snapshot_count"] == 0
    ui.page("16")
    ui.upload_directory(folder)
    wait(
        "return document.querySelector('[aria-label=\"批次真实统计\"]')?.textContent.includes('2')"
    )
    originals = poll(read, "sources_list", {}, lambda value: len(value["sources"]) == 2)["sources"]
    imported = {}
    for name, content in fixtures.items():
        sha = hashlib.sha256(content).hexdigest()
        source = one(
            originals,
            lambda row, name=name, sha=sha: row["original_name"] == name and row["sha256"] == sha,
            name,
        )
        original = read("source_original", {"source_id": source["source_id"]})
        assert original["sha256"] == sha and base64.b64decode(original["content_base64"]) == content
        imported[name] = source
    ui.click("执行本批次转换")
    jobs = {}
    for name, source in imported.items():
        listing = poll(
            read,
            "source_jobs",
            {"source_id": source["source_id"]},
            lambda v: any(
                row["state"] in {"succeeded", "failed", "cancelled"} for row in v["jobs"]
            ),
            100,
        )
        job = one(
            listing["jobs"],
            lambda row: row["kind"] == "text" and row["state"] == "succeeded",
            name + " text job",
        )
        state = read("jobs_get", {"job_id": job["job_id"]})
        assert state["input_ref"] == source["source_id"] and state["state"] == "succeeded"
        jobs[name] = state
    result["stages"].append({"id": "import", "status": "PASS", "sources": imported, "jobs": jobs})
    source, job = imported["grouped-owner.txt"], jobs["grouped-owner.txt"]
    pin = {
        "source_id": source["source_id"],
        "source_revision": source["source_revision"],
        "sha256": source["sha256"],
        "job_id": job["job_id"],
    }
    row_scope = "//section[@aria-label='文件夹导入']//tr[td[1][contains(.,'grouped-owner.txt')]]"
    ui.click("打开成功产物与来源", row_scope)
    ui.click("阅读此原件与整理知识候选")
    wait(
        "return location.hash==='#page=03' && !!document.querySelector('[aria-label=\"同源知识整理\"]')"
    )
    ui.click("建立版本化草稿")
    wait("return !!document.querySelector('[aria-label=\"版本化草稿编辑器\"] .tiptap')")
    documents = read("documents_list")["documents"]
    document = one(
        documents,
        lambda row: (
            row["source_id"] == pin["source_id"]
            and row["source_revision"] == pin["source_revision"]
        ),
        "same-source document",
    )
    document = read("document_get", {"document_id": document["document_id"]})
    ui.keys(
        '[aria-label="版本化草稿编辑器"] .tiptap',
        "\ue009\ue010\ue000Grouped document revision. ",
        "css selector",
    )
    ui.click("保存草稿")
    document = poll(
        read,
        "document_get",
        {"document_id": document["document_id"]},
        lambda d: d["version"] > document["version"],
    )
    assert (
        document["source_id"] == pin["source_id"]
        and document["source_revision"] == pin["source_revision"]
    )
    assert (
        "Grouped document revision" in document["text_projection"]
        and text.strip() in document["text_projection"]
    )
    result["stages"].append({"id": "read", "status": "PASS", "document": document})
    ui.click("引用当前页")
    wait("return !!document.querySelector('[data-evidence-reference=\"true\"]')")
    ui.click("保存草稿")
    document = poll(
        read,
        "document_get",
        {"document_id": document["document_id"]},
        lambda d: "evidenceReference" in json.dumps(d["editor_json"]),
    )
    anchors = read("anchors_list", {"source_id": pin["source_id"]})["anchors"]
    anchor = one(
        anchors, lambda a: a["source_revision"] == pin["source_revision"], "document anchor"
    )
    resolution = read(
        "anchor_resolve", {"source_id": pin["source_id"], "anchor_id": anchor["anchor_id"]}
    )
    assert resolution["status"] == "CURRENT" and resolution["position"] == anchor["position"]
    ui.click_selector('[data-evidence-reference="true"]', "css selector")
    result["anchor_navigation"] = {
        "status": "IN_PROGRESS",
        "anchor_id": anchor["anchor_id"],
        "expected_original_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }
    try:
        wait(full_text_selection_wait_script(text))
        observation = js(TEXT_SELECTION_OBSERVATION + "return proof;")
        assert_full_text_selection(observation, text)
        result["anchor_navigation"].update(status="PASS", selection=observation)
    except BaseException:
        try:
            result["anchor_navigation"].update(
                status="FAIL", selection=js(TEXT_SELECTION_OBSERVATION + "return proof;")
            )
        except BaseException:
            result["anchor_navigation"].update(
                status="FAIL", selection="UNVERIFIED_OBSERVATION_FAILED"
            )
        raise
    result["stages"].append(
        {"id": "anchor", "status": "PASS", "anchor": anchor, "resolution": resolution}
    )
    poll(
        read,
        "ui_state_read",
        {},
        lambda value: not value["state"]["drafts"] and not value["state"].get("pending_original"),
    )
    ui.click("整理此来源为知识候选")
    select_full_quote(ui, js, wait, text, result)
    candidate_body = text.strip()
    ui.type("知识候选正文", candidate_body, "textarea")
    ui.click("创建知识候选")
    ui.click("前往知识库审核")
    candidates = read("search", {"q": nonce, "active_only": False})["items"]
    candidate = one(
        candidates,
        lambda row: (
            read("knowledge_get", {"id": row["knowledge_id"]}).get("body") == candidate_body
        ),
        "created knowledge",
    )
    knowledge = read("knowledge_get", {"id": candidate["knowledge_id"]})
    assert knowledge["source_id"] == pin["source_id"] and knowledge["status"] == "candidate"
    review_scope = "//section[@aria-label='同源候选审核']"
    ui.type("审核者", "SYNTHETIC_GROUPED_NATIVE_ENGINEERING_ACTOR_NOT_OWNER", scope=review_scope)
    ui.type(
        "审核备注",
        "Authored fixture engineering decision, not human signoff",
        "textarea",
        review_scope,
    )
    ui.click("接受当前候选", review_scope)
    knowledge = poll(
        read,
        "knowledge_get",
        {"id": knowledge["knowledge_id"]},
        lambda value: value["status"] == "accepted",
    )
    pin.update(knowledge_id=knowledge["knowledge_id"], anchor_id=knowledge["anchor_id"])
    claim_anchor = read(
        "anchor_resolve", {"source_id": pin["source_id"], "anchor_id": pin["anchor_id"]}
    )
    assert (
        claim_anchor["status"] == "CURRENT"
        and claim_anchor["source_revision"] == pin["source_revision"]
        and claim_anchor["current_source_revision"] == pin["source_revision"]
    )
    result["stages"].append(
        {"id": "claim", "status": "PASS", "knowledge": knowledge, "human_signoff": False}
    )
    ui.click("从当前知识生成课程与课时", review_scope)
    ui.click("由课程课时建立学习问题", review_scope)
    wait("return location.hash==='#page=06'")
    item_input = (
        "document.evaluate("
        + json.dumps(label_selector("学习项目键"))
        + ",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue"
    )
    wait("return !!" + item_input + "?.value?.startsWith('course:')")
    key = js("return " + item_input + "?.value")
    assert isinstance(key, str) and re.fullmatch(
        r"course:[A-Za-z0-9_.-]+:artifact:[A-Za-z0-9_.-]+", key
    )
    assessment = read("assessment_get", {"item_key": key})
    pin.update(
        item_key=key,
        assessment_id=assessment["assessment_id"],
        knowledge_version=pin["knowledge_id"],
    )
    assert_assessment(assessment, pin)
    course = read("course_get", {"course_id": key.split(":")[1]})
    assert (
        course["bindings"][0]["knowledge_id"] == pin["knowledge_id"]
        and course["bindings"][0]["source_id"] == pin["source_id"]
    )
    result["stages"].append(
        {"id": "learn", "status": "PASS", "course": course, "assessment": assessment}
    )
    ui.click("练习此学习项目")
    wait("return location.hash==='#page=11'")
    assert assessment["question"] != assessment["content"] and candidate_body not in assessment["question"], "assessment question exposes bound answer"
    assert not js("return !!document.querySelector('section[aria-label=\"答案与核对内容\"]')"), "bound answer revealed before learner action"
    ui.type("本次答案", candidate_body, "textarea")
    ui.click("查看答案与核对内容")
    wait("return !!document.querySelector('section[aria-label=\"答案与核对内容\"] p')")
    assert js("return Array.from(document.querySelectorAll('label')).find(label=>label.textContent.startsWith('本次答案'))?.querySelector('textarea')?.value") == candidate_body
    assert js("return document.querySelector('section[aria-label=\"答案与核对内容\"] p')?.textContent") == assessment["content"]
    result["stages"].append(
        {"id": "practice", "status": "PASS", "item_key": key, "actual_mastery": "UNMEASURED"}
    )
    result["practice_to_review_navigation"] = navigate_retained_review(ui, read, pin, candidate_body)
    # Explicit authored learner fixture; no inference that this proves mastery.
    ui.click_selector(label_selector("回答正确"))
    ui.keys(label_selector("学习者自评", "select"), "\ue015\ue015\ue015\ue007")
    history_before = read("learning_history", {"item_key": key})
    if multi_review_ack_loss:
        learning, history = multi_review_ack_recovery(ui,read,js,wait,restart,key,history_before,knowledge,nonce,candidate_body,result.setdefault('multi_review_recovery',{}))
    elif review_ack_loss:
        learning, history = review_ack_recovery(ui,read,js,wait,restart,key,history_before,result.setdefault('review_recovery',{}))
    else:
        ui.click("记录复习结果")
        wait("return document.body.innerText.includes('复习记录已保存')")
        learning = read("learning_state", {"item_key": key})
    assert_assessment(learning["learner"]["assessment"], pin)
    history = read("learning_history", {"item_key": key})
    assert_review_readback(history_before, history, learning, pin, candidate_body)
    result["stages"].append(
        {"id": "review", "status": "PASS", "state": learning, "history": history}
    )
    title_row = next(item for item in read("learning_items")["items"] if item["item_key"] == key)
    title_selector = button_selector(key, "//ul[@aria-label='复习队列']")
    ui.reveal_selector(title_selector)
    title_layout = js("const b=document.evaluate(" + json.dumps(title_selector) + ",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue;return {label:b.textContent,width:b.getBoundingClientRect().width,scrollWidth:b.scrollWidth,clientWidth:b.clientWidth,queueWidth:b.closest('ul').clientWidth,queueScrollWidth:b.closest('ul').scrollWidth}")
    assert title_layout["label"] == title_row["display_title"] and title_layout["label"] != key
    assert 0 < len(title_layout["label"]) <= 80
    assert title_layout["width"] <= title_layout["queueWidth"] and title_layout["scrollWidth"] <= title_layout["clientWidth"]
    assert title_layout["queueScrollWidth"] <= title_layout["queueWidth"]
    result["review_title"] = {"status": "PASS", "item_key": key, "projection": title_row, "layout": title_layout}
    screenshot("grouped-learning-review.png")
    purposes = ("answer", "retest", "material", "companion") if material_companion_loop else ("answer", "retest")
    ai_stage = run_ai_stage(ui, read, js, wait, pin, result, run_ai, authored_intervention, selected_model, selected_max_tokens, machine_ack_loss, restart, machine_cancel, save_deep_binding, purposes)
    result["stages"].append(ai_stage)
    if machine_ack_loss:
        require_machine_ack_recovery(ai_stage)
    if require_actual_ai_loop and ai_stage.get("retest") != "EXECUTED_CANDIDATE_NOT_EVALUATED":
        raise AssertionError("Actual AI retest unverified; preserve frozen request and failure diagnostics before backup navigation")
    if material_companion_loop:
        mc = _read_module("aaos_material_companion", Path(__file__).with_name("aaos01_material_companion_loop.py"))
        result["material_companion"] = {}
        mc.run(ui, read, js, wait, screenshot, document, ai_stage["saved_deep_binding"], result["material_companion"])
        if selected_max_tokens is not None:
            for purpose in ("material", "companion"):
                record_output_budget(ai_stage, selected_max_tokens, purpose,
                                     result["material_companion"]["receipts"][purpose]["plan"]["request"])
    if save_deep_binding:
        tasks_before_reopen = machine_tasks(read)
        restart()
        read_saved_model_configuration(ui, read, wait, ai_stage, restored=False)
        assert machine_tasks(read) == tasks_before_reopen, "Configuration reopen dispatched inference"
        if material_companion_loop:
            mc.reopen(ui, read, js, wait, screenshot, document, result["material_companion"], "cold_reopen")
    ui.page("19")
    ui.click("工作区与恢复")
    backup_ids={row['backup_id'] for row in read('workspace_backups')['backups']}
    ui.click("创建一致备份")
    backups = poll(read, "workspace_backups", {}, lambda value: len(value["backups"]) == len(backup_ids)+1)["backups"]
    backup = next(row for row in backups if row['backup_id'] not in backup_ids)
    ui.click("预检此备份")
    ui.click("确认恢复整个工作区")
    wait("return document.body.innerText.includes('整个工作区已恢复，Core 已重启并读回')")
    wait("return [...document.querySelectorAll('button')].some(b=>b.textContent==='保留恢复候选')")
    before = read("ui_state_read")
    ui.click("保留恢复候选")
    after = poll(
        read, "ui_state_read", {}, lambda value: value["recovery_requires_confirmation"] is False
    )
    assert (
        before["restore_epoch"] == after["restore_epoch"]
        and after["state"] == before["recovery_candidates"]
    )
    restart()
    if save_deep_binding:
        read_saved_model_configuration(ui, read, wait, ai_stage, restored=True)
        if material_companion_loop:
            mc.reopen(ui, read, js, wait, screenshot, document, result["material_companion"], "backup_restore")
    assert read("document_get", {"document_id": document["document_id"]}) == document
    assert read("knowledge_get", {"id": pin["knowledge_id"]}) == knowledge
    assert read("learning_history", {"item_key": key}) == history
    restored_learning = read("learning_state", {"item_key": key})
    assert_assessment(restored_learning["learner"]["assessment"], pin)
    assert_review_readback(history_before, history, restored_learning, pin, candidate_body)
    assert read("course_get", {"course_id": key.split(":")[1]}) == course
    assert (
        base64.b64decode(read("source_original", {"source_id": pin["source_id"]})["content_base64"])
        == fixtures["grouped-owner.txt"]
    )
    for task_id, saved_task in result.get("actual_tasks", {}).items():
        assert read("machine_task_get", {"task_id": task_id}) == saved_task
    if ai_stage.get("accepted_correction"):
        assert (
            read("knowledge_get", {"id": ai_stage["accepted_correction"]["knowledge_id"]})
            == ai_stage["accepted_correction"]
        )
    ui.page("02")
    reopened_document_selector = (
        "//section[@aria-label='知识库文档视图' and not(ancestor-or-self::*[@hidden])]"
        "//nav[@aria-label='已保存文档']//button[@aria-label="
        + xpath_literal("打开文档 " + document["title"])
        + " and not(ancestor-or-self::*[@hidden])]"
    )
    ui.click_revealed_selector(reopened_document_selector)
    ui.page("20")
    wait("return document.body.innerText.includes('Grouped document revision')")
    if pointer_navigation:
        result["pointer_navigation"] = {"status":"IN_PROGRESS", "trace":ui.pointer_page("06")}
        assert poll(read,"ui_state_read",{},lambda value:value["state"]["page_id"]=="06")["state"]["page_id"]=="06"
        result["pointer_navigation"]["status"]="PASS"
    else:
        ui.page("06")
    ui.click(key, "//ul[@aria-label='复习队列']")
    result["restored_learning"] = restored_learning_view(ui, read, js, wait, key, assessment)
    result["stages"].append(
        {
            "id": "recover",
            "status": "PASS",
            "backup": backup,
            "working_state": after,
            "full_host_restart": True,
            "old_grant_refusal": "NOT_EXECUTED",
            "grant_qualification": "PARTIAL",
        }
    )
    result["capability_toggle"] = {}
    capability_refusal_recovery(
        ui, read, js, wait, restart, pin, document, text, result["capability_toggle"]
    )
    result["restored_grant_refusal"] = restored_grant_refusal(ui, read, wait, ai_stage)
    next(stage for stage in result["stages"] if stage["id"] == "recover")["old_grant_refusal"] = (
        result["restored_grant_refusal"]["status"]
    )
    result["pin"] = pin
    if require_actual_ai_loop:
        result["actual_ai_requirement"] = "IN_PROGRESS"
        assert_actual_ai_chain(result)
        result["actual_ai_requirement"] = "ENGINEERING_AUTHORED_ACTUAL_AI_CHAIN"
    if closure_features:
        helper = _read_module("aaos_closure_features",Path(__file__).with_name("aaos01_closure_features.py"))
        helper.run(ui=ui,read=read,bridge=bridge,js=js,wait=wait,restart=restart,work=work,report=result,download_control=download_control)
    if material_companion_cancel:
        result["material_companion_cancellation"] = {}
        mc.run_cancel(ui, read, js, wait, screenshot, document, result["material_companion_cancellation"], poll)
        restart()
        mc.reopen_cancel(ui, read, js, wait, screenshot, document, result["material_companion_cancellation"])
    result["engineering_status"] = "PASS"
    result["status"] = "PARTIAL"  # Missing Owner/model correction evidence remains explicit.
    return result


def assert_actual_ai_chain(result):
    """Fail closed on missing inference; never certify human or model accuracy."""
    stage = result["ai_progress"]
    assert stage.get("status") == "EXECUTED_CANDIDATE_NOT_EVALUATED"
    assert stage.get("retest") == "EXECUTED_CANDIDATE_NOT_EVALUATED"
    original = stage["original_answer"]
    failed = stage["failed_task"]
    accepted = stage["accepted_correction"]
    assert accepted["status"] == "accepted"
    assert_correction_lineage(original, failed, accepted, stage["authored_intervention"])
    assert stage["task"]["task_id"] != stage["retest_task"]["task_id"]
    assert stage["original_grant"]["document_id"] != stage["retest_grant"]["document_id"]
    for task, knowledge, document, scope, prior in (
        (stage["task"], stage["knowledge_before"], stage["original_grant"], "runtime.answer", None),
        (stage["retest_task"], accepted, stage["retest_grant"], "runtime.retest", failed),
    ):
        grant = grant_snapshot(document)
        value = assert_inference_task(task, knowledge["knowledge_id"], original["question"], grant, scope)
        selected=stage.get('explicit_model_selection',{}).get('model')
        assert inference_status(task,selected) == "EXECUTED_CANDIDATE_NOT_EVALUATED"
        assert receipt_binding(task, knowledge, original["question"], grant, prior_failed_task=prior,selected_model=selected)["status"] == "RECEIPT_BINDINGS_VALIDATED"
        assert value["answer"].get("truncated") is False
        assert value["answer"].get("finish_reason") == "stop"
        answer = value["answer"]
        assert answer.get("requested_model") == answer["model"]
        assert answer.get("observed_model") == answer["model"]
        assert answer.get("answer_source") == {"openai": "content", "ollama": "response"}[answer["protocol"]]
        assert result["actual_tasks"][task["task_id"]] == task
    assert result["actual_tasks"][failed["task_id"]] == failed
    assert result["restored_grant_refusal"]["status"] == "PASS"
    assert result["capability_toggle"]["status"] == "PASS"


def create_ui_grant(ui, read, wait, knowledge_id, operation, purpose):
    ui.click("读取指定知识并建立上下文候选")
    wait("return document.body.innerText.includes('固定知识：' + " + json.dumps(knowledge_id) + ")")
    ui.type("用途", purpose, "textarea")
    ui.type(
        "授权依据",
        "Explicit isolated-fixture engineering authorization, not Owner acceptance",
        "textarea",
    )
    ui.click_selector(label_selector("允许本地回答" if operation == "answer" else "允许本地复测"))
    ui.click("明确授权并保存")
    wait("return document.body.innerText.includes('授权版本已保存并读回')")
    document = read_grant(read, purpose, knowledge_id, operation)
    ui.click("使用已保存上下文进入纠正与评测")
    wait("return location.hash==='#page=14'")
    return document


def machine_tasks(read):
    page = read("machine_tasks_list", {"limit": 100})
    assert page["next_cursor"] is None, (
        "Owned task readback cannot claim complete absence from a partial page"
    )
    return [read("machine_task_get", {"task_id": row["task_id"]}) for row in page["items"]]


def selected_retest_binding(stage, selected_model):
    if not stage.get("retest_task"):
        return False
    retest = task_conditions(stage["retest_task"])
    assert retest["request"]["model"] == retest["answer"]["model"] == retest["answer"]["requested_model"] == selected_model
    return True


def request_owned_machine_cancellation(ui, wait, report):
    """Trusted UI opt-in; acceptance alone never qualifies worker/provider stop."""
    ui.click("请求取消当前本地 worker")
    wait("return document.body.innerText.includes('取消请求已接收；尚未确认停止') || document.body.innerText.includes('没有确认可取消的当前本地 worker')")
    text = ui.js("return document.body.innerText")
    accepted = "取消请求已接收；尚未确认停止" in text
    assert accepted or "没有确认可取消的当前本地 worker" in text
    report.update(cancel_requested=accepted, execution_state="UNKNOWN", provider_stop_state="UNKNOWN", terminal_verified=False)
    return report


def confirm_owned_machine_cancellation(ui, wait, report):
    """Invoke only after the original call finishes; observe the separate Core audit UI."""
    wait("return [...document.querySelectorAll('button')].some(b=>b.textContent==='核对冻结机器请求的失败状态' && !b.disabled)")
    ui.click("核对冻结机器请求的失败状态")
    wait("return document.body.innerText.includes('本地 worker 取消审计；可结束请求并保留草稿')")
    text = ui.js("return document.body.innerText")
    assert "本地 worker 取消审计；可结束请求并保留草稿" in text
    report.update(local_worker_terminal="CANCELLED_LOCAL_WORKER", terminal_verified=True, provider_stop_state="UNKNOWN", evidence_scope="TRUSTED_UI_DURABLE_LOCAL_WORKER_AUDIT")
    return report


def read_local_model_inventory(ui, wait, stage, phase):
    """Bounded explicit read-only retries; preserve every failed observation, never inference."""
    rows = stage.setdefault("inventory_observations", [])
    for attempt in range(1, 4):
        wait("return [...document.querySelectorAll('button')].some(n=>n.textContent==='探测本地模型清单'&&!n.disabled)")
        ui.click_revealed("探测本地模型清单")
        try:
            wait("const n=document.querySelector('[aria-label=\"本地模型清单探测结果\"]');return !!n && !n.textContent.includes('正在读取') && !n.textContent.includes('清单未探测或读取失败')", seconds=30)
            text = ui.js("return document.querySelector('[aria-label=\"本地模型清单探测结果\"]')?.textContent")
        except TimeoutError:
            text = ui.js("return document.querySelector('[aria-label=\"本地模型清单探测结果\"]')?.textContent")
        rows.append({"phase":phase,"attempt":attempt,"text":text,"inference_retried":False})
        if isinstance(text, str) and text.strip().startswith("清单已读取，共 "):
            return text
        if attempt < 3:
            time.sleep(1)
    raise AssertionError("Local inventory remains unverified after three explicit read-only observations")


MODEL_CONFIGURATION_SCOPE = "//div[h2[normalize-space(.)='产品模型与用途绑定'] and not(ancestor-or-self::*[@hidden or @aria-hidden='true' or @inert])]"


def model_configuration_status_observation(message):
    return (
        "const matches=document.evaluate(" + json.dumps(MODEL_CONFIGURATION_SCOPE) +
        ",document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null);"
        "const panels=Array.from({length:matches.snapshotLength},(_,i)=>matches.snapshotItem(i))"
        ".filter(n=>n.getClientRects().length>0&&getComputedStyle(n).visibility==='visible');"
        "return panels.length===1&&panels[0].textContent.includes(" + json.dumps(message) + ");"
    )


def save_deep_model_binding(ui, read, wait, stage, model, purposes=("answer", "retest"), *, budget=1024):
    """Explicit finite configuration on the harness's fresh synthetic workspace only."""
    assert type(budget) is int and budget in (1024, 2048, 4096), "Unsupported probe output budget"
    before = read("model_configuration_get")
    assert before["revision"] == 0 and before["profiles"] == {} and before["bindings"] == [], "Requires fresh isolated model configuration"
    assert isinstance(model, str) and re.fullmatch(r"[A-Za-z0-9_.:/@+-]{1,256}", model)
    tasks = machine_tasks(read)
    scope = MODEL_CONFIGURATION_SCOPE
    ui.page("19")
    ui.click_revealed("读取模型配置", scope)
    ui.type("本地服务地址", "http://127.0.0.1:1234/v1", scope=scope)
    ui.type("模型名称", model, scope=scope)
    ui.type("最大输出 token", str(budget), scope=scope)
    ui.type("超时秒数", "120", scope=scope)
    ui.click_revealed("测试连接", scope)
    wait(model_configuration_status_observation('目录读取成功，已找到所选模型'))
    assert set(purposes) <= {"answer", "retest", "material", "companion"} and len(set(purposes)) == len(purposes)
    for purpose in purposes:
        selector = scope + "/descendant::label[contains(.,'" + purpose + " / DEEP')]/select"
        ui.reveal_selector(selector)
        ui.click_selector(selector + "/option[@value='local']")
    ui.click_revealed("保存配置与用途绑定", scope)
    wait(model_configuration_status_observation('已保存版本 1'))
    saved = read("model_configuration_get")
    profile = {"endpoint":"http://127.0.0.1:1234/v1", "protocol":"openai", "model":model,
               "credential_ref":None, "max_tokens":budget, "timeout_s":120}
    assert saved["revision"] == 1 and saved["profiles"] == {"local": profile}
    assert sorted(saved["bindings"], key=lambda row: row["purpose"]) == [
        {"purpose":purpose, "lane":"deep", "profile_id":"local"} for purpose in sorted(purposes)]
    assert saved["workspace_id"] == before["workspace_id"] and saved["restore_epoch"] == before["restore_epoch"]
    resolved = {purpose: read("model_configuration_resolve", {"body":{"purpose":purpose,"lane":"deep"}}) for purpose in purposes}
    for purpose, value in resolved.items():
        assert value["purpose"] == purpose and value["lane"] == "deep" and value["profile_id"] == "local"
        assert value["profile"] == profile and value["configuration_revision"] == saved["revision"]
        assert value["workspace_id"] == saved["workspace_id"] and value["restore_epoch"] == saved["restore_epoch"]
    assert machine_tasks(read) == tasks, "Configuration save or directory diagnosis dispatched inference"
    stage["saved_deep_binding"] = {"status":"SAVED_NOT_YET_EXECUTED", "configuration":saved, "resolved":resolved,
                                   "configuration_inference_calls":0, "compatibility_model_selection":"NOT_USED"}


def assert_saved_model_request(value, saved, purpose):
    expected = saved["resolved"][purpose]
    request = value["request"]
    assert request["model_configuration"] == expected, "Frozen saved model binding mismatch"
    execution = value["execution_request"] if purpose == "retest" else request
    assert execution["resolved_model"] == expected, "Resolved model receipt mismatch"
    assert request["model"] == expected["profile"]["model"]
    assert type(expected["profile"]["max_tokens"]) is int and expected["profile"]["max_tokens"] in (1024, 2048, 4096)
    assert request["max_tokens"] == expected["profile"]["max_tokens"]
    assert request["timeout_s"] == expected["profile"]["timeout_s"] == 120


def select_saved_deep_lane(ui, wait):
    selector = "//label[contains(.,'用途执行通道')]/select"
    ui.reveal_selector(selector)
    ui.click_selector(selector + "/option[@value='deep']")
    wait("return [...document.querySelectorAll('label')].find(n=>n.textContent.includes('用途执行通道'))?.querySelector('select')?.value==='deep'")


def read_saved_model_configuration(ui, read, wait, stage, *, restored):
    saved = stage["saved_deep_binding"]["configuration"]
    ui.page("19")
    ui.click_revealed("读取模型配置", MODEL_CONFIGURATION_SCOPE)
    wait(model_configuration_status_observation('已读取版本 1'))
    current = read("model_configuration_get")
    if not restored:
        assert current == saved, "Saved configuration changed across cold reopen"
    else:
        for key in ("schema", "revision", "profiles", "bindings", "workspace_id"):
            assert current[key] == saved[key], "Restored configuration mismatch: " + key
        assert current["restore_epoch"] == read("ui_state_read")["restore_epoch"]
        assert current["restore_epoch"] != saved["restore_epoch"], "Restore epoch did not advance"
    stage["saved_deep_binding"]["restore_readback" if restored else "cold_reopen"] = {"status":"PASS", "configuration":current}


def run_ai_stage(ui, read, js, wait, pin, result, run_ai, authored_intervention=False, selected_model=None, selected_max_tokens=None, machine_ack_loss=False, restart=None, machine_cancel=False, save_deep_binding=False, purposes=("answer", "retest")):
    stage = {
        "id": "distill",
        "status": "NOT_EXECUTED",
        "correction": "NOT_EXECUTED",
        "retest": "NOT_EXECUTED",
    }
    result["ai_progress"] = stage
    assert not authored_intervention or run_ai, (
        "Authored intervention requires explicit actual-model opt-in"
    )
    if not run_ai:
        stage["reason"] = (
            "Actual inference requires explicit --actual-model; no model/provider changes"
        )
        return stage
    rows = read("capabilities_list").get("capabilities", [])
    route = [
        row
        for row in rows
        if row.get("capability") == "machine.answer"
        and row.get("enabled") is True
        and row.get("registered") is True
        and row.get("provider", {}).get("worker_present") is True
        and row.get("provider", {}).get("interpreter_present") is True
    ]
    if len(route) != 1:
        stage["reason"] = (
            "Current machine.answer enabled registered worker/interpreter route not confirmed; no inference dispatched"
        )
        return stage
    stage["preflight"] = {
        "route": route[0],
        "model_availability": "UNKNOWN",
        "explicit_actual_model_attempt": True,
    }
    knowledge = read("knowledge_get", {"id": pin["knowledge_id"]})
    assert knowledge["knowledge_id"] == pin["knowledge_id"] and knowledge["status"] == "accepted"
    if save_deep_binding:
        assert run_ai and selected_model and not machine_ack_loss and not machine_cancel
        save_deep_model_binding(ui, read, wait, stage, selected_model, purposes,
                                budget=1024 if selected_max_tokens is None else selected_max_tokens)
    ui.page("13")
    purpose = "Grouped native original " + pin["knowledge_id"]
    document = create_ui_grant(ui, read, wait, pin["knowledge_id"], "answer", purpose)
    grant = grant_snapshot(document)
    stage["original_grant"] = document
    before_tasks = machine_tasks(read)
    ui.click("读取模型配置状态")
    wait("return document.body.innerText.includes('模型是否已加载和能否回答仍需实际验证')")
    configuration = read("machine_configuration")
    assert configuration["schema"] == "archeaxis.machine-configuration/v1"
    assert configuration["availability"] == "CONFIGURED_UNVERIFIED"
    assert configuration["network_performed"] is False
    assert configuration["inference_status"] == "NOT_EXECUTED" and configuration["loaded_status"] == "UNKNOWN"
    assert all(configuration[key] is None for key in ["model_identity", "usage", "cost"])
    assert machine_tasks(read) == before_tasks
    stage["configuration_read"] = {"status":"PASS", "configuration":configuration, "machine_tasks_unchanged":True}
    inventory_text = read_local_model_inventory(ui, wait, stage, "initial")
    assert isinstance(inventory_text, str)
    inventory_match = re.fullmatch(r"清单已读取，共 (\d+) 项；声明模型(已列出|未列出)。加载状态未知，推理尚未验证。", inventory_text.strip())
    assert inventory_match and 0 <= int(inventory_match[1]) <= 256
    assert machine_tasks(read) == before_tasks
    stage["inventory_read"] = {"status":"PASS", "evidence_scope":"FORMAL_UI_LOCAL_INVENTORY_ONLY", "listed_model_count":int(inventory_match[1]), "selected_model_listed":inventory_match[2] == "已列出", "loaded_status":"UNKNOWN", "inference_status":"NOT_EXECUTED", "machine_tasks_unchanged":True}
    if save_deep_binding:
        select_saved_deep_lane(ui, wait)
    elif selected_model is not None:
        assert isinstance(selected_model,str) and selected_model.strip() == selected_model and 0 < len(selected_model.encode()) <= 256
        ui.click_selector("descendant::label[contains(.,'兼容模式本地回答模型')]/select/option[@value=" + xpath_literal(selected_model) + "]")
        wait("return Array.from(document.querySelectorAll('label')).find(n=>n.textContent.includes('兼容模式本地回答模型'))?.querySelector('select')?.value === " + json.dumps(selected_model))
    question = "Explain why original bytes and a versioned document are distinct."
    if selected_max_tokens is not None:
        assert selected_max_tokens in (2048,4096)
        ui.click_selector("descendant::label[contains(.,'本次输出预算')]/select/option[@value=" + xpath_literal(str(selected_max_tokens)) + "]")
    ui.type("实际问题", question, "textarea")
    if machine_ack_loss:
        assert restart is not None
        install_machine_observer(js, lose_ack=True, knowledge_id=pin['knowledge_id'], question=question)
    ui.click("执行本地机器回答")
    if machine_cancel:
        assert restart is not None and run_ai and not machine_ack_loss
        cancellation = stage["owned_worker_cancellation"] = {"status":"IN_PROGRESS","provider_stop_state":"UNKNOWN"}
        # This is the existing actual model route, not a synthetic worker or SDK substitute.
        time.sleep(2)
        frozen_state = read("ui_state_read")
        frozen = one(frozen_state["state"].get("pending_machine",{}).values(),
            lambda row: row["operation"]=="answer" and row["owner_knowledge_id"]==pin["knowledge_id"] and row["body"]["question"]==question,
            "actual machine cancellation journal")
        request_owned_machine_cancellation(ui,wait,cancellation)
        assert cancellation["cancel_requested"], "No actual current owned worker accepted cancellation; no stop claim"
        confirm_owned_machine_cancellation(ui,wait,cancellation)
        current = read("ui_state_read")
        query = {key:current[key] for key in ("workspace_id","restore_epoch","state_revision")}
        query["journal_id"] = frozen["journal_id"]
        terminal = read("ui_state_machine_status",{"body":query})
        assert terminal["status"]=="CANCELLED_LOCAL_WORKER" and terminal["can_clear"] is True
        assert terminal["provider_stop_state"]=="UNKNOWN" and 1<=terminal["attempt"]<=3
        audit = read("machine_task_get",{"task_id":terminal["task_id"]})
        audit_body = task_conditions(audit)
        assert audit["scope"]=="runtime.execution.failed" and audit_body["reason_code"]=="machine worker cancelled"
        assert audit_body["client_request_id"]==frozen["body"]["client_request_id"] and audit_body["answer_published"] is False
        assert audit_body["usage"] is None and audit_body["cost"] is None
        assert not any(row["scope"]=="runtime.answer" and task_conditions(row).get("client_request_id")==frozen["body"]["client_request_id"] for row in machine_tasks(read))
        ui.click("结束失败请求，保留草稿")
        cleared = poll(read,"ui_state_read",{},lambda row: frozen["journal_id"] not in row["state"].get("pending_machine",{}))
        retained = js("return [...document.querySelectorAll('label')].find(n=>n.textContent.startsWith('实际问题'))?.querySelector('textarea')?.value")
        assert retained==question,"Cancellation clear erased the user's question draft"
        shutdown = restart()
        assert read("machine_task_get",{"task_id":terminal["task_id"]})==audit
        assert frozen["journal_id"] not in read("ui_state_read")["state"].get("pending_machine",{})
        cancellation.update(status="LOCAL_CANCEL_AUDIT_CONFIRMED",evidence_level="REAL_LOCAL_WORKER_CANCEL_WITH_SYNTHETIC_MATERIAL",model_execution_state="UNKNOWN",frozen_journal=frozen,
            terminal=terminal,audit=audit,clear_revision=cleared["state_revision"],retained_question=retained,restart=shutdown,
            normal_answer_after_restart="IN_PROGRESS")
        ui.page("14");ui.click("刷新上下文列表");ui.click("选择原知识授权 "+document["title"])
        wait("return [...document.querySelectorAll('label')].some(n=>n.textContent.startsWith('实际问题'))")
        if selected_model is not None:
            read_local_model_inventory(ui, wait, stage, "after_cancel_restart")
            ui.click_selector("descendant::label[contains(.,'兼容模式本地回答模型')]/select/option[@value="+xpath_literal(selected_model)+"]")
        if selected_max_tokens is not None:
            ui.click_selector("descendant::label[contains(.,'本次输出预算')]/select/option[@value="+xpath_literal(str(selected_max_tokens))+ "]")
        ui.type("实际问题",question,"textarea")
        before_tasks=machine_tasks(read)
        ui.click("执行本地机器回答")
    wait(
        "return !!document.querySelector('[aria-label=\"真实机器回答\"]') || document.body.innerText.includes('回答未完成') || document.body.innerText.includes('本地知识库明确拒绝此回答请求') || document.body.innerText.includes('推理已执行，答案未发布')",
        seconds=150,
    )
    tasks = machine_tasks(read)
    matches = [
        row
        for row in tasks
        if row["scope"] == "runtime.answer"
        and task_conditions(row).get("knowledge_id") == pin["knowledge_id"]
    ]
    if not matches:
        stage["status"] = "UNVERIFIED"
        stage["reason"] = (
            "UI request dispatched but no confirmed answer task; refusal/unknown/withheld preserved, not a successful inference"
        )
        stage["task_inventory"] = tasks
        stage["ui_text"] = js(
            "return document.querySelector('[aria-label=\"知识到机器回答\"]')?.innerText ?? 'No confirmed machine answer'"
        )
        return stage
    task = one(matches, lambda _: True, "actual machine answer task")
    if machine_ack_loss:
        recover_machine_ack(ui, read, js, wait, restart, document, task, stage)
    original = assert_inference_task(task, pin["knowledge_id"], question, grant)
    if selected_max_tokens is not None:
        record_output_budget(stage, selected_max_tokens, "answer", original["request"])
    if save_deep_binding:
        assert_saved_model_request(original, stage["saved_deep_binding"], "answer")
    if selected_model is not None:
        assert original["request"]["model"] == original["answer"]["requested_model"] == original["answer"]["observed_model"] == original["answer"]["model"] == selected_model
        stage["explicit_model_selection"] = {"status":"PASS", "model":selected_model,"surface":"TRUSTED_NATIVE_UI"}
    assert (
        original["request"]["context_sha256"]
        == hashlib.sha256(knowledge["body"].encode()).hexdigest()
    )
    assert read("knowledge_get", {"id": pin["knowledge_id"]}) == knowledge, (
        "Answer knowledge changed during inference"
    )
    binding = receipt_binding(task, knowledge, question, grant,selected_model=selected_model)
    if machine_cancel:
        assert original["client_request_id"] != stage["owned_worker_cancellation"]["frozen_journal"]["body"]["client_request_id"]
        stage["owned_worker_cancellation"]["normal_answer_after_restart"]="PERSISTED_CANDIDATE"
        stage["owned_worker_cancellation"]["status"]="PASS" if binding["status"]=="RECEIPT_BINDINGS_VALIDATED" else "UNVERIFIED"
        stage["owned_worker_cancellation"]["normal_answer_task_id"]=task["task_id"]
    stage.update(
        receipt_binding=binding,
        status=(inference_status(task,selected_model) if binding["status"] == "RECEIPT_BINDINGS_VALIDATED" else "UNVERIFIED"),
        task=task,
        original_answer=original,
        original_metering=assert_reported_metering(original["answer"]),
        original_answer_sha256=hashlib.sha256(original["answer"]["answer"].encode()).hexdigest(),
        knowledge_before=knowledge,
    )
    result["actual_tasks"] = {task["task_id"]: task}
    result["actual_task_id"] = task["task_id"]
    if stage["status"] != "EXECUTED_CANDIDATE_NOT_EVALUATED":
        stage["reason"] = (
            "Actual configured-model identity not confirmed; no authored intervention or qualification claim"
        )
        return stage
    if machine_ack_loss:
        stage['machine_ack_recovery'].update(status='PASS',evidence_level='REAL_MODEL_WITH_SYNTHETIC_BRIDGE_ACK_LOSS')
    if authored_intervention:
        run_authored_intervention(ui, read, wait, stage, result)
        if selected_model is not None:
            bound = selected_retest_binding(stage, selected_model)
            stage["explicit_model_selection"]["retest_bound"] = bound
            if not bound:
                return stage
    else:
        stage["reason"] = (
            "Actual answer retained. No explicitly authorized authored intervention; no invented model error."
        )
    ui.click("查看本次运行详细记录")
    wait(
        "return location.hash==='#page=22' && !!document.querySelector('[aria-label=\"历史机器回答\"]')"
    )
    return stage


def install_machine_observer(js, *, lose_ack, knowledge_id=None, question=None):
    """Observe trusted bridge; discard one successful answer ACK after Core persistence."""
    js("""const original=window.__TAURI__,invoke=original.core.invoke;
window.__aaosMachineOriginal=original;window.__aaosMachineProof={rows:[],faults:0};
const lose=""" + json.dumps(lose_ack) + """, expectedKnowledge=""" + json.dumps(knowledge_id) + """, expectedQuestion=""" + json.dumps(question) + """;
const observed=async function(command,args,...rest){
 const op=args?.request?.operation;
 const row=command==='core_command'&&['machine_answer','machine_retest','ui_state_clear_machine'].includes(op)?{operation:op,status:null,completed:false}:null;
 if(row)window.__aaosMachineProof.rows.push(row);
 let value;try{value=await Reflect.apply(invoke,original.core,[command,args,...rest]);}catch(error){if(row)row.error='BRIDGE_REJECTED';throw error;}
 if(row){Object.assign(row,{status:value.status,task_id:value.body?.answer_id,completed:true});
 if(lose&&op==='machine_answer'&&value.status>=200&&value.status<300&&value.body?.schema==='archeaxis.machine-answer/v1'&&value.body?.knowledge_id===expectedKnowledge&&value.body?.question===expectedQuestion&&value.body?.client_request_id===args?.request?.payload?.body?.client_request_id&&window.__aaosMachineProof.faults===0){window.__aaosMachineProof.faults++;throw new Error('SYNTHETIC_MACHINE_ACK_LOST');}
 }return value;
};window.__TAURI__={...original,core:{...original.core,invoke:observed}};
if(window.__TAURI__.core.invoke!==observed)throw new Error('Machine observer installation refused');""")


def remove_machine_observer(js):
    proof=js("return window.__aaosMachineProof")
    js("window.__TAURI__=window.__aaosMachineOriginal;delete window.__aaosMachineOriginal;delete window.__aaosMachineProof;")
    return proof


def recover_machine_ack(ui, read, js, wait, restart, document, task, stage):
    proof=remove_machine_observer(js)
    assert proof['faults']==1 and len(proof['rows'])==1
    assert proof['rows'][0]['operation']=='machine_answer' and proof['rows'][0]['status']==200
    conditions=task_conditions(task)
    before=read('ui_state_read')
    entries=[e for e in before['state'].get('pending_machine',{}).values() if e['owner_knowledge_id']==conditions['knowledge_id']]
    assert len(entries)==1
    frozen=entries[0]
    assert frozen['body']['client_request_id']==conditions['client_request_id'] and frozen['body']['question']==conditions['question']
    tasks=machine_tasks(read)
    old_backups={row['backup_id'] for row in read('workspace_backups')['backups']}
    ui.page('19',confirm_navigation=True);ui.click('创建一致备份')
    backups=poll(read,'workspace_backups',{},lambda value:len(value['backups'])==len(old_backups)+1)['backups']
    saved=next(row for row in backups if row['backup_id'] not in old_backups)
    restart()
    assert read('ui_state_read')['state'].get('pending_machine',{}).get(frozen['journal_id'])==frozen
    assert machine_tasks(read)==tasks
    install_machine_observer(js,lose_ack=False)
    try:
        ui.page('14',confirm_navigation=True);ui.click('刷新上下文列表');ui.click('选择原知识授权 '+document['title'])
        wait("return document.body.innerText.includes('已恢复未确认的机器请求')")
        ui.click('读取机器学习历史')
        ui.click_selector("//ul[@aria-label='既有机器学习任务']/li[@data-task-id="+xpath_literal(task['task_id'])+"]//button[normalize-space(.)='查看这次任务']")
        wait("return document.body.innerText.includes('已从 Core 恢复固定回答与既有回执')")
    finally:
        recovery=remove_machine_observer(js)
    assert recovery['faults']==0 and not any(row['operation'] in ('machine_answer','machine_retest') for row in recovery['rows'])
    assert len(recovery['rows'])==1 and recovery['rows'][0]['operation']=='ui_state_clear_machine' and 200<=recovery['rows'][0]['status']<300
    assert frozen['journal_id'] not in read('ui_state_read')['state'].get('pending_machine',{})
    assert machine_tasks(read)==tasks and read('machine_task_get',{'task_id':task['task_id']})==task
    ui.page('19');ui.click('刷新备份产物')
    ui.click_selector('//li[strong[normalize-space(.)='+xpath_literal(saved['filename'])+']]//button[normalize-space(.)="预检此备份"]')
    ui.click('确认恢复整个工作区')
    wait("return document.body.innerText.includes('整个工作区已恢复，Core 已重启并读回')")
    candidate=read('ui_state_read')
    assert candidate['restore_epoch']!=before['restore_epoch'] and candidate['recovery_candidates']['pending_machine'][frozen['journal_id']]==frozen
    wait("return [...document.querySelectorAll('button')].some(b=>b.textContent==='保留恢复候选')")
    assert js("return [...document.querySelectorAll('button')].find(b=>b.textContent==='丢弃恢复候选')?.disabled") is True
    ui.click('保留恢复候选')
    poll(read,'ui_state_read',{},lambda value:value['recovery_requires_confirmation'] is False)
    restart()
    assert read('ui_state_read')['state']['pending_machine'][frozen['journal_id']]==frozen and machine_tasks(read)==tasks
    install_machine_observer(js,lose_ack=False)
    try:
        ui.page('14',confirm_navigation=True);ui.click('刷新上下文列表');ui.click('选择原知识授权 '+document['title'])
        wait("return document.body.innerText.includes('已恢复未确认的机器请求')")
        ui.click('读取机器学习历史');ui.click_selector("//ul[@aria-label='既有机器学习任务']/li[@data-task-id="+xpath_literal(task['task_id'])+"]//button[normalize-space(.)='查看这次任务']")
        wait("return document.body.innerText.includes('已从 Core 恢复固定回答与既有回执')")
    finally:
        restored=remove_machine_observer(js)
    assert restored['faults']==0 and len(restored['rows'])==1 and restored['rows'][0]['operation']=='ui_state_clear_machine' and 200<=restored['rows'][0]['status']<300
    assert frozen['journal_id'] not in read('ui_state_read')['state'].get('pending_machine',{})
    assert machine_tasks(read)==tasks and read('machine_task_get',{'task_id':task['task_id']})==task
    stage['machine_restore_recovery']={'status':'JOURNAL_RECOVERY_VERIFIED','discard_disabled':True,'origin_retained':True,'task_unchanged':True,'recovery':restored,'recovery_inference_calls':0}
    stage['machine_ack_recovery']={'status':'JOURNAL_RECOVERY_VERIFIED','evidence_level':'INTEGRATED_WITH_SYNTHETIC_BRIDGE_ACK_LOSS','initial':proof,'recovery':recovery,'cold_restart':True,'task_unchanged':True,'recovery_inference_calls':0,'journal_id':frozen['journal_id']}


def require_machine_ack_recovery(stage):
    recovery=stage.get('machine_ack_recovery',{})
    assert stage.get('status')=='EXECUTED_CANDIDATE_NOT_EVALUATED' and recovery.get('status')=='PASS', 'Required actual machine ACK recovery absent or unverified'
    assert recovery.get('cold_restart') is True and recovery.get('task_unchanged') is True
    assert recovery.get('recovery_inference_calls')==0
    assert not any(row['operation'] in ('machine_answer','machine_retest') for row in recovery['recovery']['rows']), 'Recovery attempted inference'
    assert len(recovery['initial']['rows'])==1 and recovery['initial']['rows'][0].get('completed') is True and recovery['initial']['faults']==1


def retryable_retest_failure(observation):
    return (observation.get("status") == "OBSERVED"
            and observation.get("retest_incomplete") is True
            and observation.get("same_request_retry") is True
            and observation.get("unknown") is False
            and observation.get("retest_withheld") is False
            and observation.get("retest_refused") is False
            and {key: observation.get("failure", {}).get(key) for key in ("phase", "status", "code")}
                == {"phase": "invoke", "status": 503, "code": "unavailable"})


def machine_ui_diagnostic(ui):
    """Bounded observations only: never copy questions, answers or error bodies."""
    observe = getattr(ui, "js", None)
    if not callable(observe):
        return {"status": "NO_OBSERVER"}
    try:
        value = observe("""const root=document.querySelector('[aria-label="知识到机器回答"]');
const text=root?.innerText??'';
return {panel_present:!!root,answer_visible:!!root?.querySelector('[aria-label="真实机器回答"]'),
retest_visible:!!root?.querySelector('[aria-label="独立复测机器回答"]'),
unknown:text.includes('执行状态尚未确认'),retest_incomplete:text.includes('复测未完成'),
retest_refused:text.includes('本地知识库明确拒绝复测请求'),
retest_withheld:text.includes('复测推理已执行，答案未发布'),
same_request_retry:[...(root?.querySelectorAll('button')??[])].some(b=>b.textContent?.includes('重试同一冻结复测请求'))};""")
        keys = ("panel_present", "answer_visible", "retest_visible", "unknown",
                "retest_incomplete", "retest_refused", "retest_withheld", "same_request_retry")
        if not isinstance(value, dict) or any(type(value.get(key)) is not bool for key in keys):
            return {"status": "INVALID_OBSERVATION"}
        result = {"status": "OBSERVED", **{key: value[key] for key in keys}}
        failure = observe("return document.querySelector('[aria-label=\"知识到机器回答\"]')?.dataset.retestFailure??null;")
        if isinstance(failure, str):
            data = json.loads(failure)
            if (isinstance(data, dict) and data.get("phase") in ("invoke", "receipt_validation", "task_readback")
                    and data.get("code") in ("offline", "backend_starting", "migrating", "incompatible", "unauthorized", "unavailable", "unverified")
                    and (data.get("status") is None or type(data.get("status")) is int and 0 <= data["status"] <= 599)):
                result["failure"] = {key: data[key] for key in ("phase", "status", "code")}
                if data.get("reason_code") in {"MODEL_CALL_FAILED", "MODEL_CALL_TIMEOUT", "NO_FINAL_ANSWER", "EMPTY_ANSWER", "WORKER_TIMEOUT", "OUTPUT_LIMIT", "INVALID_OUTPUT", "PIPE_DRAIN_FAILED", "WORKER_FAILED"}:
                    result["failure"]["reason_code"] = data["reason_code"]
        return result
    except Exception:
        return {"status": "OBSERVATION_FAILED"}


def run_authored_intervention(ui, read, wait, stage, result):
    original = stage["original_answer"]
    actor = "ENGINEERING_AUTHORED_INTERVENTION_NOT_OWNER"
    authored = {
        "actor": actor,
        "body": stage["knowledge_before"]["body"]
        + "\nEngineering clarification: original source bytes are preserved independently; document revisions are editable derived content.",
        "note": "ENGINEERING_AUTHORED_INTERVENTION_NOT_INDEPENDENT_MODEL_ERROR; original_answer_id="
        + original["answer_id"]
        + "; original_answer_sha256="
        + stage["original_answer_sha256"]
        + "; selected clarification exercises lineage/adoption, not factual proof that the actual model answer is wrong.",
    }
    stage["authored_intervention"] = {
        **authored,
        "owner_acceptance": False,
        "independent_error_adjudication": False,
    }
    stage["semantic_limitation"] = (
        "Core machine_correction records runtime.evaluation.failed for every intervention. That stored label is not independent model-failure evidence in this engineering probe."
    )
    ui.type("正确答案", authored["body"], "textarea")
    ui.type("具体错误依据", authored["note"], "textarea")
    ui.type("纠正提交者", actor)
    ui.click("记录使用者纠正候选")
    wait("return !!document.querySelector('[aria-label=\"纠正候选审核\"]')")
    failed = read("machine_task_get", {"task_id": "evaluation_" + original["answer_id"]})
    correction = task_conditions(failed)["correction"]
    candidate = read("knowledge_get", {"id": correction["correction_candidate_id"]})
    assert candidate["status"] == "candidate"
    assert_correction_lineage(original, failed, candidate, authored)
    stage.update(
        correction="EXECUTED_AUTHORED_INTERVENTION_NOT_INDEPENDENT_ERROR",
        failed_task=failed,
        correction_candidate=candidate,
    )
    scope = "//section[@aria-label='纠正候选审核']"
    ui.type("审核者", actor, scope=scope)
    ui.type(
        "审核依据",
        "Explicit authored engineering adoption, not Owner acceptance or model qualification; "
        + authored["note"],
        "textarea",
        scope,
    )
    ui.click("接受纠正知识", scope)
    wait("return document.body.innerText.includes('本地知识库已接受此纠正知识')")
    accepted = read("knowledge_get", {"id": candidate["knowledge_id"]})
    assert (
        accepted["knowledge_id"] == candidate["knowledge_id"] and accepted["status"] == "accepted"
    )
    assert_correction_lineage(original, failed, accepted, authored)
    assert read("knowledge_get", {"id": original["knowledge_id"]}) == stage["knowledge_before"], (
        "Adoption changed original knowledge"
    )
    stage["accepted_correction"] = accepted
    ui.click("为此纠正知识建立独立复测授权")
    wait("return location.hash==='#page=13'")
    purpose = "Grouped native corrected " + candidate["knowledge_id"]
    document = create_ui_grant(ui, read, wait, candidate["knowledge_id"], "retest", purpose)
    grant = grant_snapshot(document)
    assert grant["document_id"] != stage["original_grant"]["document_id"], (
        "Retest reused original grant"
    )
    stage["retest_grant"] = document
    if stage.get("saved_deep_binding"):
        select_saved_deep_lane(ui, wait)
    ui.click("以已接受纠正知识运行独立复测", scope)
    wait(
        "return !!document.querySelector('[aria-label=\"独立复测机器回答\"]') || document.body.innerText.includes('复测未完成') || document.body.innerText.includes('本地知识库明确拒绝复测请求') || document.body.innerText.includes('复测推理已执行，答案未发布')",
        seconds=150,
    )
    stage["retest_ui_diagnostic"] = machine_ui_diagnostic(ui)
    inventory = machine_tasks(read)
    stage["retest_task_inventory"] = [
        {key: task.get(key) for key in ("task_id", "scope", "outcome", "retest_of")}
        for task in inventory
    ]
    matches = [
        task
        for task in inventory
        if task["scope"] == "runtime.retest" and task["retest_of"] == failed["task_id"]
    ]
    if not matches and retryable_retest_failure(stage["retest_ui_diagnostic"]):
        # One explicit UI retry of the same frozen payload; never generate a new
        # request, replace its grant, or turn an unknown response into success.
        stage["retest_retry"] = {"limit": 1, "first_failure": stage["retest_ui_diagnostic"], "first_inventory": stage["retest_task_inventory"]}
        ui.click("重试同一冻结复测请求", scope)
        wait("return !!document.querySelector('[aria-label=\"独立复测机器回答\"]') || document.body.innerText.includes('复测未完成') || document.body.innerText.includes('本地知识库明确拒绝复测请求') || document.body.innerText.includes('复测推理已执行，答案未发布')", seconds=150)
        stage["retest_retry"]["final_observation"] = machine_ui_diagnostic(ui)
        inventory = machine_tasks(read)
        matches = [task for task in inventory if task["scope"] == "runtime.retest" and task["retest_of"] == failed["task_id"]]
    if not matches:
        stage["retest"] = "UNVERIFIED"
        stage["reason"] = (
            "Actual retest request dispatched, response/receipt not confirmed; preserve unknown/refusal, no qualification claim"
        )
        return
    retest = one(matches, lambda _: True, "independent actual retest task")
    value = assert_inference_task(
        retest, accepted["knowledge_id"], original["question"], grant, "runtime.retest"
    )
    if stage.get("saved_deep_binding"):
        assert_saved_model_request(value, stage["saved_deep_binding"], "retest")
        stage["saved_deep_binding"]["status"] = "ANSWER_RETEST_FROZEN_BINDINGS_VERIFIED"
    if stage.get("explicit_output_budget"):
        record_output_budget(stage, stage["explicit_output_budget"]["requested_cli_max_tokens"], "retest", value["request"])
    assert read("knowledge_get", {"id": accepted["knowledge_id"]}) == accepted, (
        "Retest knowledge changed during inference"
    )
    assert value["retest_of"] == failed["task_id"] and value["prior"][
        "conditions"
    ] == task_conditions(failed)
    assert read("machine_task_get", {"task_id": stage["task"]["task_id"]}) == stage["task"], (
        "Retest replaced original answer"
    )
    selected=stage.get('explicit_model_selection',{}).get('model')
    binding = receipt_binding(retest, accepted, original["question"], grant, prior_failed_task=failed,selected_model=selected)
    stage.update(
        retest_receipt_binding=binding,
        retest=(inference_status(retest,selected) if binding["status"] == "RECEIPT_BINDINGS_VALIDATED" else "UNVERIFIED"),
        retest_task=retest,
        retest_metering=assert_reported_metering(task_conditions(retest)["answer"]),
        reason="Actual answer and retest preserved; authored adoption is not independent error evidence or proof of improvement.",
    )
    result["actual_tasks"].update({failed["task_id"]: failed, retest["task_id"]: retest})
    result["actual_task_id"] = retest["task_id"]


def restored_admission_receipt(receipt, document, knowledge_id, question, model_configuration=None):
    """Validate a Core-bound redacted receipt actually observed on the trusted UI."""
    assert isinstance(receipt, dict), "Missing typed restore admission receipt"
    expected = {
        "schema": "archeaxis.context-admission-refusal/v1",
        "reason_code": "RESTORED_GRANT_FENCED",
        "execution_state": "NOT_EXECUTED",
        "execution_scope": "CURRENT_INVOCATION",
        "prior_request_execution": "UNVERIFIED",
        "answer_published": False,
        "operation": "answer",
        "knowledge_id": knowledge_id,
        "retest_of": None,
        "grant": {key: document[key] for key in ("document_id", "version", "content_sha256")},
    }
    for key, value in expected.items():
        assert receipt.get(key) == value, "Restore admission binding mismatch: " + key
    client = receipt.get("client_request_id")
    assert isinstance(client, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", client), "Invalid frozen client identity"
    request = {"operation": "answer", "request": {
        "knowledge_id": knowledge_id, "question": question, "max_tokens": 2048, "timeout_s": 120,
        "context_grant": grant_snapshot(document), "asset_context_grant": None,
        "client_request_id": client, "retest_of": None,
    }}
    if model_configuration is not None:
        request["request"].update(model=model_configuration["profile"]["model"],
                                  model_configuration=model_configuration,
                                  max_tokens=min(2048, model_configuration["profile"]["max_tokens"]),
                                  timeout_s=model_configuration["profile"]["timeout_s"])
    digest = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert receipt.get("request_sha256") == digest, "Restore admission frozen request digest mismatch"
    assert set(receipt) == set(expected) | {"client_request_id", "request_sha256"}, "Unbounded restore receipt"
    return receipt


def assert_restored_original_selection(selection, document, knowledge):
    assert isinstance(selection, dict), "Missing rendered original selection diagnostic"
    assert selection["document"] == document, "Rendered original grant document mismatch"
    assert selection["grant"] == document["editor_json"]["attrs"]["archeaxis_context_grant"], "Rendered original grant mismatch"
    assert selection["snapshot"] == grant_snapshot(document), "Rendered original consumption snapshot mismatch"
    assert selection["knowledge"] == knowledge, "Rendered original knowledge identity/body mismatch"
    assert selection["grant"]["knowledge_id"] == knowledge["knowledge_id"]
    assert selection["current"] is True, "Rendered original knowledge is not current"


def select_restored_original(ui, wait, stage):
    document, knowledge = stage["original_grant"], stage["knowledge_before"]
    scope = "//section[@aria-label='纠正、评测与复测内容' and not(ancestor-or-self::*[@hidden])]"
    selector = button_selector("选择原知识授权 " + document["title"], scope)
    # Refresh is asynchronous; do not select from the retained list while it is loading.
    wait("const roots=[...document.querySelectorAll('[aria-label=\"纠正、评测与复测内容\"]')].filter(n=>!n.closest('[hidden],[aria-hidden=\"true\"],[inert]'));"
         "const buttons=document.evaluate(" + json.dumps(selector) + ",document,null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null);"
         "return roots.length===1&&!roots[0].textContent.includes('正在读取实际上下文')&&buttons.snapshotLength===1&&!buttons.snapshotItem(0).disabled;")
    ui.click_revealed_selector(selector)
    try:
        wait("const rows=[...document.querySelectorAll('[aria-label=\"原知识授权快照\"] [aria-label=\"原知识当前正文\"]')].filter(n=>!n.closest('[hidden],[aria-hidden=\"true\"],[inert]'));return rows.length===1&&rows[0].textContent===" + json.dumps(knowledge["body"]) + ";")
    except BaseException:
        stage["restore_selection_failure"] = ui.js("const roots=[...document.querySelectorAll('[aria-label=\"纠正、评测与复测内容\"]')].filter(n=>!n.closest('[hidden]'));return roots.map(n=>({alerts:[...n.querySelectorAll('[role=alert]')].map(x=>x.textContent),status:[...n.querySelectorAll('[role=status]')].map(x=>x.textContent),original:n.querySelector('[aria-label=\"原知识授权快照\"]')?.textContent}));")
        raise
    ui.click_revealed_selector(scope + "//section[@aria-label='原知识授权快照']//button[@data-diagnostic-label='原知识授权详细信息']")
    try:
        wait("return [...document.querySelectorAll('[aria-label=\"诊断控制台\"] details[open]')].some(n=>n.getClientRects().length>0&&n.querySelector('summary')?.textContent.startsWith('原知识授权详细信息 ·'))")
        selection = ui.js("const rows=[...document.querySelectorAll('[aria-label=\"诊断控制台\"] details[open]')].filter(n=>n.getClientRects().length>0&&!n.closest('[hidden],[aria-hidden=\"true\"],[inert]')&&n.querySelector('summary')?.textContent.startsWith('原知识授权详细信息 ·'));return rows.length===1?JSON.parse(rows[0].querySelector('pre').textContent):null")
        assert_restored_original_selection(selection, document, knowledge)
        stage["restore_selected_original"] = {"status":"PASS", "selection":selection}
    finally:
        ui.click_revealed("关闭运行诊断", "//*[@role='dialog']")


def restored_grant_refusal(ui, read, wait, stage):
    if not stage.get("original_grant") or stage.get("status") != "EXECUTED_CANDIDATE_NOT_EVALUATED":
        return {
            "status": "NOT_EXECUTED",
            "reason": "No confirmed actual answer and old explicit grant to challenge",
        }
    document = stage["original_grant"]
    before = machine_tasks(read)
    assert read("document_get", {"document_id": document["document_id"]}) == document
    assert (
        read("knowledge_get", {"id": stage["original_answer"]["knowledge_id"]})
        == stage["knowledge_before"]
    )
    capability = one(
        read("capabilities_list")["capabilities"],
        lambda row: row["capability"] == "machine.answer",
        "restored machine route",
    )
    assert capability["enabled"] is True and capability["registered"] is True
    ui.page("14")
    ui.click("刷新上下文列表")
    select_restored_original(ui, wait, stage)
    current_binding = None
    if stage.get("saved_deep_binding"):
        select_saved_deep_lane(ui, wait)
        current_binding = read("model_configuration_resolve", {"body":{"purpose":"answer","lane":"deep"}})
        assert current_binding["restore_epoch"] == read("ui_state_read")["restore_epoch"]
        assert current_binding["profile"] == stage["saved_deep_binding"]["configuration"]["profiles"]["local"]
    ui.type("实际问题", stage["original_answer"]["question"], "textarea")
    # New UI client request; it cannot succeed through cached old-answer replay.
    ui.click("执行本地机器回答")
    wait("return document.body.innerText.includes('本地知识库明确拒绝此回答请求')", seconds=150)
    receipt = restored_admission_receipt(ui.js("""const n=document.querySelector('[aria-label="恢复授权拒绝"]');
      return n?JSON.parse(n.dataset.contextAdmissionRefusal):null;"""), document,
      stage["original_answer"]["knowledge_id"], stage["original_answer"]["question"], current_binding)
    after = machine_tasks(read)
    assert after == before, "Restored grant refusal created/changed a machine task"
    assert read("document_get", {"document_id": document["document_id"]}) == document
    return {
        "status": "PASS",
        "old_grant": grant_snapshot(document),
        "tasks_unchanged": True,
        "authority": "CORE_UI_REFUSAL_OBSERVATION",
        "exact_core_reason": receipt["reason_code"],
        "execution_scope": receipt["execution_scope"],
        "prior_request_execution": receipt["prior_request_execution"],
        "admission_receipt": receipt,
        "reason": "Core request-bound RESTORED_GRANT_FENCED receipt observed on trusted UI. Only this invocation is NOT_EXECUTED; prior request execution remains UNVERIFIED. Frozen input is preserved.",
    }


def capability_permission(read, enabled):
    value = read("capabilities_list")
    row = one(
        value["capabilities"], lambda item: item["capability"] == "text.extract", "text capability"
    )
    assert row["enabled"] is enabled, "Text capability enable/readback mismatch"
    return value


def frozen_conversion_view(js):
    return js("""const root=document.querySelector('[aria-label="真实转换产物"]');
      if(!root)return null;
      return {page:location.hash,
        frozen:[...root.querySelectorAll('p')].find(p=>p.textContent.startsWith('执行请求已冻结：'))?.textContent??null,
        latest:[...root.querySelectorAll('p')].find(p=>p.textContent.startsWith('最新任务 '))?.textContent??null,
        recovery:root.querySelector('[aria-label="冻结请求的能力恢复"]')?.textContent??null};""")


def assert_unadmitted(status, job_id, source_id):
    assert (
        status["job_id"] == job_id and status["input_ref"] == source_id and status["kind"] == "text"
    )
    assert status["state"] in {"queued", "pending"}
    assert status["attempt"] is None and status["request_id"] is None
    assert status["attempts"] == [] and status["attempts_capped"] is False


def frozen_job_journal(readback, frozen, source_id, source_revision, kind):
    assert readback["schema"] == "archeaxis.ui-working-state/v1"
    assert readback["recovery_requires_confirmation"] is False
    entry = readback["state"]["pending_jobs"][frozen["request_id"]]
    assert entry["job_id"] == frozen["job_id"] and entry["request_id"] == frozen["request_id"]
    assert entry["source_id"] == source_id and entry["source_revision"] == source_revision
    assert entry["kind"] == kind and entry["body"] == frozen["body"]
    assert entry["origin_restore_epoch"] == readback["restore_epoch"], "Old restore intent cannot be replayed"
    assert entry["surface"] == "manual" and entry["mode"] == "single" and entry["relative"] is None
    return entry


def assert_single_attempt(status, frozen, source_id):
    assert (
        status["job_id"] == frozen["job_id"]
        and status["input_ref"] == source_id
        and status["kind"] == "text"
    )
    assert status["state"] == "succeeded" and status["attempt"] == 1
    assert status["request_id"] == frozen["request_id"] and status["attempts_capped"] is False
    assert len(status["attempts"]) == 1, "Retry created more than one durable attempt"
    attempt = status["attempts"][0]
    assert (
        attempt["attempt"] == 1
        and attempt["request_id"] == frozen["request_id"]
        and attempt["state"] == "succeeded"
    )
    assert attempt["budget"] == {**frozen["body"], "capability": "text.extract"}
    assert attempt["steps"] == {
        "durable_claim": "RECORDED",
        "worker_response_commit": "RECORDED",
        "terminal_write": "RECORDED",
    }
    assert attempt["checkpoint"]["status"] == "CORE_COMMITTED"


def assert_text_output(output, text):
    assert output["content"] == text, "Actual conversion body differs from original authored text"
    metadata = output["metadata"]
    assert metadata["kind"] == "text" and metadata["byte_length"] == len(text.encode())
    assert metadata["sha256"] == hashlib.sha256(text.encode()).hexdigest()


LEARNING_RESTORE_OBSERVATION = """const visible=n=>!!n&&n.getClientRects().length>0&&
 !n.closest('[hidden],[aria-hidden="true"],[inert]')&&
 Array.from((function*(x){for(;x;x=x.parentElement)yield x;})(n)).every(x=>{
  const s=getComputedStyle(x);return s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse';});
const pages=[...document.querySelectorAll('[data-current-page-id]')];
const articles=[...document.querySelectorAll('.stitch-learning-review article')].filter(n=>visible(n)&&
 [...n.children].some(c=>c.tagName==='H3'&&c.textContent==='复习题'&&visible(c)));
return {page:pages.length===1?pages[0].getAttribute('data-current-page-id'):null,
 count:articles.length,paragraphs:articles.length===1?[...articles[0].children].filter(c=>c.tagName==='P'&&visible(c)).map(c=>c.innerText):[]};"""


def restored_learning_view(ui, read, js, wait, key, assessment):
    """Recover business question + its current diagnostic identity and full Core snapshot."""
    wait("const v=(function(){" + LEARNING_RESTORE_OBSERVATION + "})();return v.page==='06'&&v.count===1&&v.paragraphs.includes(" + json.dumps(assessment["question"]) + ")")
    view = js(LEARNING_RESTORE_OBSERVATION)
    assert view["page"] == "06" and view["count"] == 1 and assessment["question"] in view["paragraphs"], "Restored learning question mismatch"
    ui.click_revealed_selector("//article[h3[.='复习题'] and not(ancestor-or-self::*[@hidden])]//button[@aria-label='查看诊断详情：学习项目与题目版本']")
    try:
        wait("return [...document.querySelectorAll('[aria-label=\"诊断控制台\"] details[open]')].some(n=>n.getClientRects().length>0&&n.querySelector('summary')?.textContent.startsWith('学习项目与题目版本 ·'))")
        identity = js("const rows=[...document.querySelectorAll('[aria-label=\"诊断控制台\"] details[open]')].filter(n=>n.getClientRects().length>0&&!n.closest('[hidden],[aria-hidden=\"true\"],[inert]')&&n.querySelector('summary')?.textContent.startsWith('学习项目与题目版本 ·'));return rows.length===1?JSON.parse(rows[0].querySelector('pre').textContent):null")
        expected = {"item_key":key, **{k:assessment[k] for k in ("assessment_id", "question_version", "knowledge_id", "knowledge_version", "source_id", "anchor_id") if k in assessment}}
        assert identity == expected, "Rendered learning identity mismatch (including same-question items)"
        assert read("assessment_get", {"item_key":key}) == assessment, "Restored Core assessment changed"
    finally:
        ui.click_revealed("关闭运行诊断", "//*[@role='dialog']")
    assert js(LEARNING_RESTORE_OBSERVATION) == view, "Learning view changed during identity verification"
    return {"status":"PASS", "view":view, "identity":identity, "core_assessment_equal":True}


def record_output_budget(stage, requested, purpose, request):
    """Report CLI intent separately from the purpose-bound persisted request."""
    saved = stage.get("saved_deep_binding")
    expected = saved["resolved"][purpose] if saved else None
    if expected:
        assert request["model_configuration"] == expected, "Budget configuration binding mismatch"
    effective = request["max_tokens"]
    assert effective == (min(requested, expected["profile"]["max_tokens"]) if expected else requested), "Effective output budget mismatch"
    report = stage.setdefault("explicit_output_budget", {
        "requested_cli_max_tokens": requested,
        "requested_surface": "CLI_VIA_PER_TASK_UI",
        "effective_by_purpose": {},
    })
    assert report["requested_cli_max_tokens"] == requested
    report["effective_by_purpose"][purpose] = {
        "max_tokens": effective,
        "source": "SAVED_DEEP_BINDING" if expected else "COMPATIBILITY_PER_TASK_UI",
        "evidence": "PERSISTED_REQUEST",
    }


READER_RESTORE_OBSERVATION = """const visible=n=>!!n&&n.getClientRects().length>0&&
 !n.closest('[hidden],[aria-hidden="true"],[inert]')&&
 Array.from((function*(x){for(;x;x=x.parentElement)yield x;})(n)).every(x=>{
  const s=getComputedStyle(x);return s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse';});
const pages=[...document.querySelectorAll('[data-current-page-id]')];
const readers=[...document.querySelectorAll('[aria-label="阅读与编辑文档视图"]')].filter(visible);
const reader=readers.length===1?readers[0]:null;
const titles=reader?[...reader.querySelectorAll('.stitch-reader-heading h2')].filter(visible):[];
const bodies=reader?[...reader.querySelectorAll('[aria-label="版本化草稿编辑器"] .ProseMirror,[aria-label="共享文档当前内容"]')].filter(visible):[];
const metas=reader?[...reader.querySelectorAll('.stitch-document-version')].filter(visible):[];
const meta=metas.length===1?metas[0]:null;
return {page:pages.length===1?pages[0].getAttribute('data-current-page-id'):null,
 reader_count:readers.length,title:titles.length===1?titles[0].innerText:null,
 text:bodies.length===1?bodies[0].innerText:null,
 version:visible(meta)?Number(meta.textContent.match(/^v(\\d+)(?:$| ·)/)?.[1]??NaN):null};"""


def restored_reader_expected_text(document):
    """Check the fixture's exact visible reference labels as well as Core prose.

    Core's search projection excludes evidenceReference atoms. The editor and
    snapshot show their labels. Reject unsupported reference-bearing structures
    rather than silently dropping content from this bounded journey oracle.
    """
    def has_reference(node):
        return node.get("type") == "evidenceReference" or any(has_reference(child) for child in node.get("content", []))

    editor = document["editor_json"]
    if not has_reference(editor):
        return document["text_projection"]

    def render(node, references):
        kind = node.get("type")
        if kind == "text":
            assert isinstance(node.get("text"), str)
            assert not any(mark.get("type") == "strike" for mark in node.get("marks", [])), "Reference fixture strike rendering requires an explicit oracle"
            return node["text"]
        if kind == "hardBreak":
            return "\n"
        if kind == "evidenceReference":
            excerpt = node.get("attrs", {}).get("excerpt")
            assert isinstance(excerpt, str) and excerpt, "Reference fixture needs its exact visible excerpt"
            return "引用：" + excerpt if references else ""
        assert kind in ("paragraph", "heading", "codeBlock"), "Unsupported reference fixture block"
        return "".join(render(child, references) for child in node.get("content", []))

    assert editor.get("type") == "doc"
    blocks = editor.get("content", [])
    canonical = "\n".join(text for block in blocks if (text := render(block, False)))
    assert canonical == document["text_projection"], "Reference fixture canonical projection mismatch"
    return "\n".join(render(block, True) for block in blocks)


def restored_reader(ui, read, js, wait, document):
    """Bind the rendered business view to its user-opened diagnostic and Core identity."""
    wait("const v=(function(){" + READER_RESTORE_OBSERVATION + "})();return v.page==='03'&&v.reader_count===1&&v.title!==null&&v.text!==null")
    view = js(READER_RESTORE_OBSERVATION)
    assert view["page"] == "03" and view["reader_count"] == 1
    assert view["title"] == document["title"], "Restored reader title mismatch"
    normalize = lambda value: value.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    assert isinstance(view["text"], str) and normalize(view["text"]) == normalize(restored_reader_expected_text(document)), "Restored reader content mismatch"
    assert view["version"] == document["version"], "Restored reader version mismatch"
    scope = "//section[@aria-label='阅读与编辑文档视图' and not(ancestor-or-self::*[@hidden])]"
    ui.click_revealed_selector(scope + "//button[@aria-label='文档与来源详细信息：文档与来源详细信息']")
    try:
        wait("return [...document.querySelectorAll('[aria-label=\"诊断控制台\"] details[open]')].some(n=>n.getClientRects().length>0&&n.querySelector('summary')?.textContent.startsWith('文档与来源详细信息 ·'))")
        identity = js("const rows=[...document.querySelectorAll('[aria-label=\"诊断控制台\"] details[open]')].filter(n=>n.getClientRects().length>0&&!n.closest('[hidden],[aria-hidden=\"true\"],[inert]')&&n.querySelector('summary')?.textContent.startsWith('文档与来源详细信息 ·'));return rows.length===1?JSON.parse(rows[0].querySelector('pre').textContent):null")
        expected = {key: document[key] for key in ("document_id", "source_id", "source_revision", "content_sha256")}
        assert identity == expected, "Rendered reader identity mismatch (including same-title documents)"
        assert read("document_get", {"document_id": document["document_id"]}) == document, "Restored Core document changed"
    finally:
        ui.click_revealed("关闭运行诊断", "//*[@role='dialog']")
    # Closing the owned diagnostic must return to the same rendered document.
    assert js(READER_RESTORE_OBSERVATION) == view, "Reader changed during identity verification"
    return {"status": "PASS", "view": view, "identity": identity, "core_document_equal": True}


def capability_refusal_recovery(
    ui, read, js, wait, restart, pin, document, expected_text, report=None
):
    result = report if report is not None else {}
    result.update(
        status="IN_PROGRESS",
        execution_refusal="IN_PROGRESS",
        execution_surface="CURRENT_GROUPED_NATIVE_UI",
    )
    ui.page("15")
    ui.click("重新读取当前宿主能力")
    capability_permission(read, True)
    ui.click_selector("//button[@aria-label='禁用 text.extract']")
    result["disabled"] = poll(
        read,
        "capabilities_list",
        {},
        lambda value: any(
            row["capability"] == "text.extract" and row["enabled"] is False
            for row in value["capabilities"]
        ),
    )
    restart()
    capability_permission(read, False)
    result["disable_restart_readback"] = "PASS"
    before = read("source_jobs", {"source_id": pin["source_id"]})
    assert before["source_id"] == pin["source_id"] and before["jobs_capped"] is False
    previous_jobs = {row["job_id"] for row in before["jobs"]}
    ui.page("02")
    ui.click_revealed_selector(
        "//section[@aria-label='知识库文档视图' and not(ancestor-or-self::*[@hidden])]"
        "//nav[@aria-label='已保存文档']//button[@aria-label="
        + xpath_literal("打开文档 " + document["title"])
        + " and not(ancestor-or-self::*[@hidden])]"
    )
    wait("return location.hash==='#page=03'")
    ui.open_reader_source_tools()
    wait(
        'return !!document.querySelector(\'[aria-label="真实转换产物"] [aria-label="Core 提取正文"]\')'
    )
    ui.click_revealed("执行真实内容转换", "//section[@aria-label='真实转换产物']")
    wait("return !!document.querySelector('[aria-label=\"冻结请求的能力恢复\"]')")
    view = frozen_conversion_view(js)
    assert view["page"] == "#page=03" and "Core 已证明原请求未受理" in view["recovery"]
    match = re.fullmatch(
        r"执行请求已冻结：(read_run_[A-Za-z0-9-]+)；单次预算 60s。未知结果不会产生新作业。",
        view["frozen"],
    )
    assert match, "Native frozen request/budget not observed"
    assert view["latest"].startswith("最新任务 read_")
    job_id = view["latest"].removeprefix("最新任务 ")
    frozen = {
        "job_id": job_id,
        "request_id": match.group(1),
        "body": {"deadline_ms": 60000, "split": False, "words": False},
    }
    listing = read("source_jobs", {"source_id": pin["source_id"]})
    assert listing["source_id"] == pin["source_id"] and listing["jobs_capped"] is False
    new_jobs = {row["job_id"] for row in listing["jobs"]} - previous_jobs
    assert new_jobs == {job_id}, "Refused action created a different/multiple job identity"
    refused = read("job_execution_status", {"job_id": job_id})
    assert_unadmitted(refused, job_id, pin["source_id"])
    capability_permission(read, False)
    journal_entry = frozen_job_journal(read("ui_state_read"), frozen, pin["source_id"], document["source_revision"], "text")
    # Restart at the unadmitted/UNKNOWN scene, not only after a completed output.
    restart()
    frozen_job_journal(read("ui_state_read"), frozen, pin["source_id"], document["source_revision"], "text")
    capability_permission(read, False)
    result["restored_reader"] = restored_reader(ui, read, js, wait, document)
    # Hydration restores the scene, while a fresh host URL has no hash. Use the
    # actual same-page control to normalize it without changing the frozen intent.
    ui.page("03")
    wait("return location.hash==='#page=03'")
    ui.open_reader_source_tools()
    ui.click_revealed_selector("//*[@data-recovery-request=" + xpath_literal(frozen["request_id"]) + "]//button[@data-recovery-action='restore']")
    recovered_view = frozen_conversion_view(js)
    assert recovered_view["frozen"] == view["frozen"] and recovered_view["latest"] == view["latest"]
    assert read("job_execution_status", {"job_id": job_id}) == refused, "Restart silently executed frozen intent"
    assert read("source_jobs", {"source_id": pin["source_id"]}) == listing, "Restart created a replacement job"
    # Explicitly retry the original identity while still disabled to obtain a fresh admission proof.
    ui.click_revealed("同请求重试转换", "//section[@aria-label='真实转换产物']")
    wait("return !!document.querySelector('[aria-label=\"冻结请求的能力恢复\"]')")
    assert read("job_execution_status", {"job_id": job_id}) == refused
    result.update(
        execution_refusal="PASS",
        frozen_intent_restart="PASS",
        core_journal_entry=journal_entry,
        frozen=frozen,
        refused_status=refused,
        refused_ui=view,
        body_evidence="Rendered bound NOT_ADMITTED proof + canonical single-text 60s/split:false/words:false contract; retry durable budget checked independently",
    )
    scope = "//section[@aria-label='冻结请求的能力恢复']"
    ui.click_revealed("启用 text.extract", scope)
    wait(
        "return document.body.innerText.includes('该能力已启用，工作区设置已读回。原冻结请求保留；请另点同请求重试。')"
    )
    result["enabled"] = capability_permission(read, True)
    after_enable = frozen_conversion_view(js)
    assert (
        after_enable["page"] == view["page"]
        and after_enable["frozen"] == view["frozen"]
        and after_enable["latest"] == view["latest"]
    )
    assert read("job_execution_status", {"job_id": job_id}) == refused, (
        "Capability enable automatically admitted/executed the frozen request"
    )
    time.sleep(1.1)
    assert read("job_execution_status", {"job_id": job_id}) == refused, (
        "Delayed automatic execution after enable"
    )
    assert read("source_jobs", {"source_id": pin["source_id"]}) == listing, (
        "Capability enable enqueued another job"
    )
    result["enable_without_execution"] = "PASS"
    ui.click_revealed("同请求重试转换", "//section[@aria-label='真实转换产物']")
    succeeded = poll(
        read,
        "job_execution_status",
        {"job_id": job_id},
        lambda value: value["state"] in {"succeeded", "failed", "cancelled", "rejected"},
        seconds=75,
    )
    assert_single_attempt(succeeded, frozen, pin["source_id"])
    output = read("job_output", {"job_id": job_id, "kind": "text"})
    assert_text_output(output, expected_text)
    quality = read("job_quality", {"job_id": job_id})
    assert (
        quality["job_id"] == job_id
        and quality["state"] == "succeeded"
        and isinstance(quality["engine"], str)
        and quality["engine"]
    )
    transform = read("source_job_transform", {"source_id": pin["source_id"], "job_id": job_id})
    assert transform["source_id"] == pin["source_id"] and transform["job_id"] == job_id
    assert (
        transform["raw_sha256"] == document["source_revision"]
        and transform["content"] == expected_text
    )
    wait(
        "return ![...document.querySelectorAll('[aria-label=\"真实转换产物\"] p')].some(p=>p.textContent.startsWith('执行请求已冻结：')) && !!document.querySelector('[aria-label=\"Core 提取正文\"]')"
    )
    assert (
        js("return document.querySelector('[aria-label=\"Core 提取正文\"]')?.textContent")
        == expected_text
    )
    result.update(
        same_request_retry="PASS",
        succeeded_status=succeeded,
        output=output,
        quality=quality,
        source_transform=transform,
    )
    restart()
    capability_permission(read, True)
    assert read("job_execution_status", {"job_id": job_id}) == succeeded
    assert read("job_output", {"job_id": job_id, "kind": "text"}) == output
    assert read("job_quality", {"job_id": job_id}) == quality
    assert (
        read("source_job_transform", {"source_id": pin["source_id"], "job_id": job_id}) == transform
    )
    assert read("document_get", {"document_id": document["document_id"]}) == document
    result.update(
        status="PASS",
        host_restart_result="PASS",
        qualification="Actual bound Core refusal/recovery and authored text conversion; not professional quality or Owner signoff",
    )
    return result
