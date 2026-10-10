"""Current grouped UI engineering journey. No bridge mutations or human signoff.

This helper only runs when the native harness explicitly selects the grouped
branch. Pure contract tests must not launch a host or model.
"""

from __future__ import annotations

import base64
import hashlib
import json
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
        "machine_task_get",
        "machine_contexts_list",
        "ui_state_read",
        "workspace_backups",
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


def button_selector(label: str, scope: str = "") -> str:
    return f"{scope}//button[normalize-space(.)={xpath_literal(label)} and not(ancestor-or-self::*[@hidden])]"


def label_selector(label: str, tag: str = "input", scope: str = "") -> str:
    return f"{scope}//label[normalize-space(text())={xpath_literal(label)}]/{tag}[not(ancestor-or-self::*[@hidden])]"


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


def task_conditions(task):
    """Core serializes MachineTaskDto.conditions as JSON text, not an object."""
    raw = task.get("conditions")
    if not isinstance(raw, str):
        raise AssertionError("Machine task conditions must be persisted JSON text")
    value = json.loads(raw)
    assert isinstance(value, dict), "Machine task conditions must decode to an object"
    return value


def inference_status(task):
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
        or any(word in model.lower() for word in ("simulated", "synthetic", "fixture", "manual"))
    ):
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
    assert task["knowledge_version"].startswith(knowledge_id + "@")
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

    def __init__(self, js, wait, element, command, evidence):
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
        selector = button_selector(label, scope)
        self.click_selector(selector)

    def click_selector(self, selector, using="xpath"):
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
        selector = label_selector(label, tag, scope)
        element = self.find(selector)
        self.command(element, "clear", {})
        self.command(element, "value", {"text": value})
        self.evidence.append({"action": "trusted_type", "selector": selector})

    def keys(self, selector, keys, using="xpath"):
        element = self.find(selector, using)
        self.command(element, "click", {})
        self.command(element, "value", {"text": keys})
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

    def page(self, page_id):
        if self.js("return location.hash") == "#page=" + page_id:
            return
        parents = {
            "16": "15",
            "03": "02",
            "11": "06",
            "12": "06",
            "14": "13",
            "22": "13",
            "20": "19",
        }
        selector = f'.navigation-sidebar button[data-page-id="{page_id}"]'
        if not self.js("return !!document.querySelector(" + json.dumps(selector) + ")"):
            parent = parents[page_id]
            self.click_selector(
                f'.navigation-sidebar button[data-page-id="{parent}"]', "css selector"
            )
        self.click_selector(selector, "css selector")
        self.wait("return location.hash===" + json.dumps("#page=" + page_id))


def poll(read, operation, payload, predicate, seconds=30):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = read(operation, payload)
        if predicate(value):
            return value
        time.sleep(0.15)
    raise TimeoutError(f"Grouped readback deadline: {operation}")


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
):
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
    ui = GroupedUI(js, wait, element, command, result["actions"])
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
    wait(
        "return document.activeElement?.getAttribute('aria-label')==='并排原件正文' && window.getSelection()?.toString()==="
        + json.dumps(text)
    )
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
    quote = label_selector("选择实际引文", "textarea")
    ui.keys(quote, "\ue009\ue011\ue000\ue009\ue008\ue010\ue000")
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
    ui.type("本次答案", candidate_body, "textarea")
    ui.click("查看答案与核对内容")
    result["stages"].append(
        {"id": "practice", "status": "PASS", "item_key": key, "actual_mastery": "UNMEASURED"}
    )
    ui.page("12")
    # Explicit authored learner fixture; no inference that this proves mastery.
    ui.click_selector(label_selector("回答正确"))
    ui.keys(label_selector("学习者自评", "select"), "\ue015\ue015\ue015\ue007")
    ui.click("记录复习结果")
    wait("return document.body.innerText.includes('Core 已确认复习记录')")
    learning = read("learning_state", {"item_key": key})
    assert_assessment(learning["learner"]["assessment"], pin)
    history = read("learning_history", {"item_key": key})
    result["stages"].append(
        {"id": "review", "status": "PASS", "state": learning, "history": history}
    )
    screenshot("grouped-learning-review.png")
    ai_stage = run_ai_stage(ui, read, js, wait, pin, result, run_ai, authored_intervention)
    result["stages"].append(ai_stage)
    ui.page("19")
    ui.click("创建一致备份")
    backups = poll(read, "workspace_backups", {}, lambda value: len(value["backups"]) == 1)[
        "backups"
    ]
    backup = backups[0]
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
    assert read("document_get", {"document_id": document["document_id"]}) == document
    assert read("knowledge_get", {"id": pin["knowledge_id"]}) == knowledge
    assert read("learning_history", {"item_key": key}) == history
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
    ui.page("20")
    ui.click_selector(
        "//nav[@aria-label='已保存文档']//button[@aria-label="
        + xpath_literal("打开文档 " + document["title"])
        + "]"
    )
    ui.page("20")
    wait("return document.body.innerText.includes('Grouped document revision')")
    ui.page("06")
    ui.click(key, "//ul[@aria-label='复习队列']")
    wait(
        "return document.body.innerText.includes('知识修订：' + "
        + json.dumps(pin["knowledge_id"])
        + ")"
    )
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
    result["capability_toggle"] = capability_toggle(ui, read, restart)
    result["restored_grant_refusal"] = restored_grant_refusal(ui, read, wait, ai_stage)
    next(stage for stage in result["stages"] if stage["id"] == "recover")["old_grant_refusal"] = (
        result["restored_grant_refusal"]["status"]
    )
    result["pin"] = pin
    result["engineering_status"] = "PASS"
    result["status"] = "PARTIAL"  # Missing Owner/model correction evidence remains explicit.
    return result


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


def run_ai_stage(ui, read, js, wait, pin, result, run_ai, authored_intervention=False):
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
    ui.page("13")
    purpose = "Grouped native original " + pin["knowledge_id"]
    document = create_ui_grant(ui, read, wait, pin["knowledge_id"], "answer", purpose)
    grant = grant_snapshot(document)
    stage["original_grant"] = document
    question = "Explain why original bytes and a versioned document are distinct."
    ui.type("实际问题", question, "textarea")
    ui.click("执行本地机器回答")
    wait(
        "return !!document.querySelector('[aria-label=\"真实机器回答\"]') || document.body.innerText.includes('回答未完成') || document.body.innerText.includes('Core 明确拒绝此回答请求') || document.body.innerText.includes('推理已执行，答案未发布')",
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
    original = assert_inference_task(task, pin["knowledge_id"], question, grant)
    assert (
        original["request"]["context_sha256"]
        == hashlib.sha256(knowledge["body"].encode()).hexdigest()
    )
    assert read("knowledge_get", {"id": pin["knowledge_id"]}) == knowledge, (
        "Answer knowledge changed during inference"
    )
    stage.update(
        status=inference_status(task),
        task=task,
        original_answer=original,
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
    if authored_intervention:
        run_authored_intervention(ui, read, wait, stage, result)
    else:
        stage["reason"] = (
            "Actual answer retained. No explicitly authorized authored intervention; no invented model error."
        )
    ui.click("读取此机器旅程的持久化回执")
    wait(
        "return location.hash==='#page=22' && !!document.querySelector('[aria-label=\"历史机器回答\"]')"
    )
    return stage


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
    wait("return document.body.innerText.includes('Core 已接受此纠正知识')")
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
    ui.click("以已接受纠正知识运行独立复测", scope)
    wait(
        "return !!document.querySelector('[aria-label=\"独立复测机器回答\"]') || document.body.innerText.includes('复测未完成') || document.body.innerText.includes('Core 明确拒绝复测请求') || document.body.innerText.includes('复测推理已执行，答案未发布')",
        seconds=150,
    )
    matches = [
        task
        for task in machine_tasks(read)
        if task["scope"] == "runtime.retest" and task["retest_of"] == failed["task_id"]
    ]
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
    assert read("knowledge_get", {"id": accepted["knowledge_id"]}) == accepted, (
        "Retest knowledge changed during inference"
    )
    assert value["retest_of"] == failed["task_id"] and value["prior"][
        "conditions"
    ] == task_conditions(failed)
    assert read("machine_task_get", {"task_id": stage["task"]["task_id"]}) == stage["task"], (
        "Retest replaced original answer"
    )
    stage.update(
        retest=inference_status(retest),
        retest_task=retest,
        reason="Actual answer and retest preserved; authored adoption is not independent error evidence or proof of improvement.",
    )
    result["actual_tasks"].update({failed["task_id"]: failed, retest["task_id"]: retest})
    result["actual_task_id"] = retest["task_id"]


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
    ui.click("选择原知识授权 " + document["title"])
    wait("return !!document.querySelector('[aria-label=\"原知识当前正文\"]')")
    ui.type("实际问题", stage["original_answer"]["question"], "textarea")
    # New UI client request; it cannot succeed through cached old-answer replay.
    ui.click("执行本地机器回答")
    wait("return document.body.innerText.includes('Core 明确拒绝此回答请求')", seconds=150)
    after = machine_tasks(read)
    assert after == before, "Restored grant refusal created/changed a machine task"
    assert read("document_get", {"document_id": document["document_id"]}) == document
    return {
        "status": "PASS",
        "old_grant": grant_snapshot(document),
        "tasks_unchanged": True,
        "authority": "CORE_UI_REFUSAL_OBSERVATION",
        "exact_core_reason": "UNVERIFIED_UI_GENERIC_REFUSAL",
        "reason": "Old preserved grant displayed then explicitly refused by Core after restore, with unchanged active knowledge/enabled route. UI does not expose the specific refusal reason; input remains dirty and is not discarded.",
    }


def capability_toggle(ui, read, restart):
    ui.page("15")
    ui.click("重新读取当前宿主能力")
    initial = one(
        read("capabilities_list")["capabilities"],
        lambda row: row["capability"] == "text.extract",
        "text capability",
    )
    assert initial["enabled"] is True, "Owned fresh workspace text capability unexpectedly disabled"
    ui.click_selector("//button[@aria-label='禁用 text.extract']")
    disabled = poll(
        read,
        "capabilities_list",
        {},
        lambda value: any(
            row["capability"] == "text.extract" and row["enabled"] is False
            for row in value["capabilities"]
        ),
    )
    restart()
    assert (
        one(
            read("capabilities_list")["capabilities"],
            lambda row: row["capability"] == "text.extract",
            "restart text capability",
        )["enabled"]
        is False
    )
    ui.page("15")
    ui.click_selector("//button[@aria-label='启用 text.extract']")
    enabled = poll(
        read,
        "capabilities_list",
        {},
        lambda value: any(
            row["capability"] == "text.extract" and row["enabled"] is True
            for row in value["capabilities"]
        ),
    )
    restart()
    assert (
        one(
            read("capabilities_list")["capabilities"],
            lambda row: row["capability"] == "text.extract",
            "enabled restart text capability",
        )["enabled"]
        is True
    )
    return {
        "toggle": "PASS",
        "disable_restart_readback": disabled,
        "enable_readback": enabled,
        "execution_refusal": "NOT_EXECUTED",
        "status": "PARTIAL",
        "reason": "Refusal leaves a frozen queued request without a rendered release action; probe does not discard it or bypass dirty guards",
    }
