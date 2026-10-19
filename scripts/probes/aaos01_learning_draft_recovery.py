"""Unsubmitted learner draft proof using real UI and read-only recovery checks.

The explicit isolated mode seeds synthetic fixtures through canonical Core APIs.
The caller supplies normal product exit/relaunch. No direct database writes,
injected ACK loss, model calls, or submitted review counts stand in for recovery.
"""

from __future__ import annotations

import base64
import json
import uuid


def expected_draft(pin, answer, *, revealed=False, correct=None, rating=None):
    return {
        "item_key": pin["item_key"],
        "assessment_id": pin["assessment_id"],
        "knowledge_version": pin["knowledge_version"],
        "answer": answer,
        "answer_revealed": revealed,
        "checked_correct": correct,
        "rating": rating,
    }


def assert_unsubmitted(state, expected, history_before, history_after, assessment, pin):
    assert state["recovery_requires_confirmation"] is False
    assert state["state"].get("pending_reviews", {}) == {}, "Already frozen submission is not a raw draft"
    draft = state["state"].get("learning_drafts", {}).get(expected["assessment_id"])
    assert draft == expected, "Unsubmitted draft fields or identity changed"
    assert history_after == history_before, "Draft recovery must not submit a learner event"
    for field in ("item_key", "assessment_id", "knowledge_version", "knowledge_id", "source_id", "anchor_id"):
        assert assessment[field] == pin[field], f"Recovered assessment crossed binding: {field}"


def assert_cleared(before, after, assessment_id):
    expected = dict(before["state"].get("learning_drafts", {}))
    assert assessment_id in expected, "No pre-submit draft proof"
    del expected[assessment_id]
    assert after["state"].get("learning_drafts", {}) == expected, "Submission cleared the wrong draft"
    assert after["state"].get("pending_reviews", {}) == {}, "Frozen review was not acknowledged"
    assert (after["workspace_id"], after["restore_epoch"]) == (before["workspace_id"], before["restore_epoch"])


OBSERVE = """const labels=[...document.querySelectorAll('label')].filter(n=>n.getClientRects().length);
const own=n=>[...n.childNodes].filter(x=>x.nodeType===3).map(x=>x.textContent).join('').trim();
const answer=labels.find(n=>own(n)==='本次答案')?.querySelector('textarea');
const article=answer?.closest('article');
const correct=labels.find(n=>own(n)==='回答正确')?.querySelector('input');
const incorrect=labels.find(n=>own(n)==='回答不正确')?.querySelector('input');
const rating=labels.find(n=>own(n)==='学习者自评')?.querySelector('select');
const observed={answer:answer?.value,editable:!!answer&&!answer.disabled,
answer_revealed:!!article?.querySelector('section[aria-label="答案与核对内容"]'),
checked_correct:correct?.checked?true:incorrect?.checked?false:null,
rating:rating?.value?Number(rating.value):null,
question:article?.querySelector('h3 + p')?.textContent,
knowledge:article?.querySelector('small')?.textContent};
"""


def assert_visible(observed, expected, assessment):
    for field in ("answer", "answer_revealed", "checked_correct", "rating"):
        assert observed[field] == expected[field], f"Visible recovered field differs: {field}"
    assert observed["editable"] is True, "Unsubmitted draft was frozen"
    assert observed["question"] == assessment["question"]
    assert observed["knowledge"] == "知识修订：" + expected["knowledge_version"]


def click_with_navigation(ui, label):
    ui.click(label)
    if ui.accept_navigation_alert:
        ui.accept_navigation_alert()


def wait_with_navigation(ui, wait, script):
    # Selection can finish its Core read after the click ACK. Accept only the
    # harness-validated product prompt, then retry observation, never the click.
    for attempt in range(3):
        try:
            return wait(script)
        except Exception as error:
            if getattr(error, "value", {}).get("error") != "unexpected alert open" or not ui.accept_navigation_alert or attempt == 2:
                raise
            ui.accept_navigation_alert()


def cold_recover(*, ui, read, js, wait, restart, poll, pin, expected, page, report):
    """Read persisted draft, exit normally, reopen by public draft selection."""
    key = pin["item_key"]
    assessment = read("assessment_get", {"item_key": key})
    history = read("learning_history", {"item_key": key})
    before = poll(read, "ui_state_read", {}, lambda value: value["state"].get("learning_drafts", {}).get(pin["assessment_id"]) == expected)
    assert_unsubmitted(before, expected, history, history, assessment, pin)
    report.update(status="IN_PROGRESS", expected=expected, history_before=history)
    restart()
    after = read("ui_state_read")
    assert (after["workspace_id"], after["restore_epoch"]) == (before["workspace_id"], before["restore_epoch"])
    assert after["state"].get("learning_drafts", {}) == before["state"].get("learning_drafts", {})
    assert_unsubmitted(after, expected, history, read("learning_history", {"item_key": key}), read("assessment_get", {"item_key": key}), pin)
    ui.page("06", confirm_navigation=True)
    summary = json.dumps("学习草稿 " + key + " · " + pin["knowledge_version"], ensure_ascii=False)
    ui.click_selector("//section[@aria-label='未提交学习草稿']//summary[normalize-space(.)=" + summary + " and not(ancestor-or-self::*[@hidden])]")
    click_with_navigation(ui, "打开草稿题目 " + key)
    wait(OBSERVE + "return observed.editable && observed.answer===" + json.dumps(expected["answer"]) + ";")
    click_with_navigation(ui, "练习此学习项目" if page == "11" else "复习此学习项目")
    wait("return location.hash===" + json.dumps("#page=" + page))
    wait(OBSERVE + "return observed.editable && observed.answer===" + json.dumps(expected["answer"]) + ";")
    observed = js(OBSERVE + "return observed;")
    assert_visible(observed, expected, assessment)
    assert_unsubmitted(read("ui_state_read"), expected, history, read("learning_history", {"item_key": key}), read("assessment_get", {"item_key": key}), pin)
    report.update(status="PASS", cold_restart=True, visible=observed, pending_reviews=0, new_review_events=0, source_binding="EXACT_ASSESSMENT_SOURCE_AND_KNOWLEDGE")
    return after


def seed_fixture(bridge, poll, label):
    """Isolated synthetic fixture via canonical APIs; not UI or Owner acceptance."""
    text = "SYNTHETIC learning draft source " + label + " " + uuid.uuid4().hex + ".\n"
    source = bridge("source_import", {"body": {"name": "draft-" + label + ".txt", "content_base64": base64.b64encode(text.encode()).decode()}})
    job = "draft_probe_" + uuid.uuid4().hex
    bridge("job_enqueue", {"body": {"job_id": job, "kind": "text", "input_ref": source["source_id"]}})
    bridge("job_execute", {"job_id": job, "body": {"deadline_ms": 30000}})
    execution = poll(bridge, "jobs_get", {"job_id": job}, lambda value: value["state"] not in {"queued", "running"}, 40)
    assert execution["state"] == "succeeded"
    transform = bridge("source_job_transform", {"source_id": source["source_id"], "job_id": job})
    content = transform["content"]
    knowledge = bridge("knowledge_from_transform", {"body": {"knowledge_type": "NOTE", "body": content, "source_id": source["source_id"], "job_id": job, "transform_id": transform["transform_id"], "selection_start_utf16": 0, "selection_end_utf16": len(content.encode("utf-16-le")) // 2, "quote": content}})
    detail = bridge("knowledge_get", {"id": knowledge["knowledge_id"]})
    bridge("knowledge_review", {"id": detail["knowledge_id"], "body": {"action": "accepted", "reviewer": "SYNTHETIC_DRAFT_PROBE_NOT_OWNER", "note": "Isolated authored fixture; not human acceptance", "expected_version": detail["version"]}})
    key = "assessment_" + uuid.uuid4().hex
    bridge("learning_reference", {"item_key": key, "body": {"knowledge_id": detail["knowledge_id"]}})
    assessment = bridge("assessment_create", {"item_key": key, "body": {"knowledge_id": detail["knowledge_id"]}})
    pin = {field: assessment[field] for field in ("item_key", "assessment_id", "knowledge_id", "knowledge_version", "source_id", "anchor_id")}
    assert pin["source_id"] == source["source_id"] and pin["knowledge_id"] == detail["knowledge_id"]
    return pin, assessment


def run(*, ui, bridge, read, js, wait, restart, poll, screenshot, report):
    raw_wait = wait
    wait = lambda script: wait_with_navigation(ui, raw_wait, script)
    report.update(engineering_status="IN_PROGRESS", status="PARTIAL", mode="LEARNING_DRAFT_ONLY", evidence_level="REAL_NATIVE_SYNTHETIC_MATERIAL", model_calls="NOT_EXECUTED", fixture_setup="CANONICAL_CORE_API_SYNTHETIC_NOT_UI_ACCEPTANCE", owner_acceptance="NOT_EXECUTED", teach_back_and_summary_drafts="NOT_IMPLEMENTED_NOT_QUALIFIED")
    assert read("sources_list")["sources"] == [], "Draft probe needs a new owned workspace"
    assert read("ui_state_read")["state"].get("learning_drafts", {}) == {}
    pin, assessment = seed_fixture(bridge, poll, "A")
    other_pin, other_assessment = seed_fixture(bridge, poll, "B")
    assert pin["source_id"] != other_pin["source_id"] and pin["knowledge_id"] != other_pin["knowledge_id"]
    report["bindings"] = [pin, other_pin]
    initial_history = read("learning_history", {"item_key": pin["item_key"]})
    other_history = read("learning_history", {"item_key": other_pin["item_key"]})
    other_answer = "  来源 B 的未提交答案\n不要覆盖\n\n"
    ui.page("06")
    ui.type("学习项目键", other_pin["item_key"])
    click_with_navigation(ui, "读取项目")
    wait(OBSERVE + "return observed.editable;")
    ui.type("本次答案", other_answer, "textarea")
    other_expected = expected_draft(other_pin, other_answer)
    poll(read, "ui_state_read", {}, lambda value: value["state"].get("learning_drafts", {}).get(other_pin["assessment_id"]) == other_expected)
    ui.type("学习项目键", pin["item_key"])
    click_with_navigation(ui, "读取项目")
    wait(OBSERVE + "return observed.editable && observed.question===" + json.dumps(assessment["question"]) + ";")
    click_with_navigation(ui, "练习此学习项目")
    wait("return location.hash==='#page=11'")
    answer = "  来源 A 的原始练习答案\n第二行独立内容\n\n"
    ui.type("本次答案", answer, "textarea")
    cold_recover(ui=ui, read=read, js=js, wait=wait, restart=restart, poll=poll, pin=pin, expected=expected_draft(pin, answer), page="11", report=report.setdefault("practice", {}))
    ui.click("查看答案与核对内容")
    ui.page("12", confirm_navigation=True)
    wait(OBSERVE + "return observed.answer_revealed && observed.editable;")
    ui.click_selector("//label[normalize-space(.)='回答正确']/input[not(ancestor-or-self::*[@hidden])]")
    ui.keys("//label[normalize-space(text())='学习者自评']/select[not(ancestor-or-self::*[@hidden])]", "\ue015\ue015\ue015\ue007")
    expected = expected_draft(pin, answer, revealed=True, correct=True, rating=3)
    before_submit = cold_recover(ui=ui, read=read, js=js, wait=wait, restart=restart, poll=poll, pin=pin, expected=expected, page="12", report=report.setdefault("review", {}))
    assert read("learning_history", {"item_key": pin["item_key"]}) == initial_history
    assert read("learning_history", {"item_key": other_pin["item_key"]}) == other_history
    screenshot("learning-draft-restored.png")
    ui.click("记录复习结果")
    wait("return document.body.innerText.includes('复习记录已保存')")
    after = poll(read, "ui_state_read", {}, lambda value: pin["assessment_id"] not in value["state"].get("learning_drafts", {}))
    assert_cleared(before_submit, after, pin["assessment_id"])
    history = read("learning_history", {"item_key": pin["item_key"]})
    assert history["count"] == initial_history["count"] + 1 and history["events"][:-1] == initial_history["events"]
    outcome = json.loads(history["events"][-1]["outcome"])
    assert outcome["answer"] == answer.strip() and outcome["assessment_id"] == pin["assessment_id"] and outcome["outcome"] == "correct"
    assert outcome["review_evidence"]["knowledge_version"] == pin["knowledge_version"]
    report["submission_cleanup"] = {"status": "PASS", "one_review_event": True, "normalized_answer": answer.strip(), "other_source_draft_retained": True}
    cold_recover(ui=ui, read=read, js=js, wait=wait, restart=restart, poll=poll, pin=other_pin, expected=other_expected, page="11", report=report.setdefault("other_source_after_submission", {}))
    assert_cleared(before_submit, read("ui_state_read"), pin["assessment_id"])
    assert read("learning_history", {"item_key": pin["item_key"]}) == history
    assert read("learning_history", {"item_key": other_pin["item_key"]}) == other_history
    assert read("assessment_get", {"item_key": pin["item_key"]}) == assessment
    assert read("assessment_get", {"item_key": other_pin["item_key"]}) == other_assessment
    screenshot("learning-draft-other-source-preserved.png")
    report.update(engineering_status="PASS", status="PASS_IMPLEMENTED_LEARNER_FIELDS_ONLY", exact_cleanup_survives_restart=True, different_source_draft_pair="PASS", closed_loop_verified=False)
    return report
