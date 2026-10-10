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


def inference_status(task):
    """A candidate worker result is execution evidence, never measured accuracy."""
    conditions = task.get("conditions", {})
    answer = conditions.get("answer", {})
    model = answer.get("model")
    if task.get("scope") != "runtime.answer" or task.get("outcome") != "unmeasured":
        return "NOT_EXECUTED"
    if (
        not isinstance(model, str)
        or not model.strip()
        or any(word in model.lower() for word in ("simulated", "synthetic", "fixture", "manual"))
    ):
        return "UNVERIFIED"
    return "EXECUTED_CANDIDATE_NOT_EVALUATED"


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
        "document.evaluate(" + json.dumps(label_selector("学习项目键"))
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
    result["stages"].append(run_ai_stage(ui, read, js, wait, pin, result, run_ai))
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
    if result.get("actual_task_id"):
        assert read("machine_task_get", {"task_id": result["actual_task_id"]}) == next(
            stage["task"] for stage in result["stages"] if stage["id"] == "distill"
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
    result["pin"] = pin
    result["engineering_status"] = "PASS"
    result["status"] = "PARTIAL"  # Missing Owner/model correction evidence remains explicit.
    return result


def run_ai_stage(ui, read, js, wait, pin, result, run_ai):
    stage = {
        "id": "distill",
        "status": "NOT_EXECUTED",
        "correction": "NOT_EXECUTED",
        "retest": "NOT_EXECUTED",
    }
    if not run_ai:
        stage["reason"] = (
            "Actual inference requires explicit --grouped-run-ai; no model/provider changes"
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
    ui.page("13")
    ui.click("读取指定知识并建立上下文候选")
    wait(
        "return document.body.innerText.includes('固定知识：' + "
        + json.dumps(pin["knowledge_id"])
        + ")"
    )
    ui.type("用途", "Authored native grouped engineering answer", "textarea")
    ui.type(
        "授权依据",
        "Explicit isolated-fixture engineering authorization, not Owner acceptance",
        "textarea",
    )
    ui.click_selector(label_selector("允许本地回答"))
    ui.click("明确授权并保存")
    ui.click("使用已保存上下文进入纠正与评测")
    wait("return location.hash==='#page=14'")
    ui.type("实际问题", "Explain why original bytes and a versioned document are distinct.")
    ui.click("执行本地机器回答")
    wait(
        "return !!document.querySelector('[aria-label=\"真实机器回答\"]') || document.body.innerText.includes('回答未完成') || document.body.innerText.includes('Core 明确拒绝此回答请求') || document.body.innerText.includes('推理已执行，答案未发布')",
        seconds=150,
    )
    tasks = read("machine_tasks_list", {}).get("items", [])
    actual = [
        read("machine_task_get", {"task_id": row["task_id"]})
        for row in tasks
        if row.get("scope") == "runtime.answer"
    ]
    matches = [
        row
        for row in actual
        if row.get("conditions", {}).get("knowledge_id") == pin["knowledge_id"]
    ]
    if not matches:
        stage["reason"] = (
            "UI inference not confirmed; refusal/unknown outcome retained, no fabricated answer"
        )
        stage["ui_text"] = js(
            "return document.querySelector('[aria-label=\"机器回答与纠正\"]')?.innerText ?? 'No confirmed machine answer'"
        )
        return stage
    selected = one(matches, lambda _: True, "actual machine answer task")
    task = read("machine_task_get", {"task_id": selected["task_id"]})
    assert task["conditions"]["knowledge_id"] == pin["knowledge_id"]
    stage.update(status=inference_status(task), task=task)
    stage["reason"] = (
        "Actual answer retained for human error adjudication. Correct answers are never fabricated failures; independent correction grant/retest require a genuine reviewed error."
    )
    ui.click("读取此机器旅程的持久化回执")
    wait(
        "return location.hash==='#page=22' && !!document.querySelector('[aria-label=\"历史机器回答\"]')"
    )
    result["actual_task_id"] = task["task_id"]
    return stage


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
