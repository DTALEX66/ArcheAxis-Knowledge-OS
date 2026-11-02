"""Test-only synthetic composition; not an application pipeline or model integration."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKERS = ROOT / "services/learning-providers/openmaic"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
pytestmark = pytest.mark.skipif(not NODE, reason="explicit ARCHEAXIS_TEST_NODE is required; PATH is not searched")

SCRIPTS = {"outline": "outline-replay-worker.mjs", "quiz": "quiz-replay-worker.mjs",
           "actions": "quiz-actions-replay-worker.mjs", "build": "scene-build-worker.mjs"}
SCHEMAS = {"outline": "archeaxis.openmaic-outline-replay-result/v1",
           "quiz": "archeaxis.openmaic-quiz-replay-result/v1",
           "actions": "archeaxis.openmaic-quiz-actions-replay-result/v1",
           "build": "archeaxis.openmaic-scene-build-result/v1"}
SOURCE_TEXT = "用于联测的合成材料"
SOURCE = {"document_id": "synthetic_document_1", "version": 1,
          "content_sha256": hashlib.sha256(SOURCE_TEXT.encode("utf-8")).hexdigest()}


def run_worker(stage: str, frame: dict) -> tuple[int, dict]:
    assert NODE and Path(NODE).is_absolute(), "ARCHEAXIS_TEST_NODE must be an absolute path"
    raw = json.dumps(frame, ensure_ascii=False).encode("utf-8")
    process = subprocess.run([NODE, str(WORKERS / SCRIPTS[stage])], input=raw, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=20, check=False)
    try:
        body = json.loads(process.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise AssertionError(f"{stage} worker missing JSON: exit={process.returncode}, stderr={process.stderr.decode('utf-8', 'replace')}") from error
    return process.returncode, body


def synthetic_outline(**extra) -> dict:
    outline = {"id": "outline_1", "type": "quiz", "title": "合成知识检查", "description": "仅作联测",
               "keyPoints": ["区分合成材料"], "order": 7,
               "quizConfig": {"questionCount": 1, "difficulty": "easy", "questionTypes": ["single"]}}
    outline.update(extra)
    return {"languageDirective": "中文", "courseTitle": "合成课程", "outlines": [outline]}


def synthetic_question(**extra) -> dict:
    question = {"id": "question_1", "type": "single", "question": "哪项是合成材料？",
                "options": ["材料甲", "材料乙"], "correctAnswer": "材料乙", "analysis": "合成参考"}
    question.update(extra)
    return question


def reply(value) -> dict:
    return {"kind": "synthetic_response", "value": json.dumps(value, ensure_ascii=False)}


def run_synthetic_chain(*, outline_reply=None, quiz_reply=None, source=None, actions=None,
                        generate_actions=False, action_reply=None, invoke=run_worker) -> dict:
    """Compose offline workers only for this test and retain each request/result.

    The quiz worker's strict contract excludes outline ``order``. This helper
    passes the remaining original fields to that worker and preserves the full
    outline for the builder and trace. Unknown fields stop the chain. This is
    not a production adapter or proof of a Core model/task lifecycle.
    """
    trace = []

    def step(name, frame):
        code, result = invoke(name, frame)
        trace.append({"stage": name, "request": deepcopy(frame), "exit": code, "result": result})
        return code == 0 and isinstance(result, dict) and result.get("schema") == SCHEMAS[name] and result.get("status") == "CANDIDATE", result

    def reject(stage, reason):
        return {"status": "REJECTED", "failed_stage": stage, "reason": reason, "trace": trace, "candidate": None}

    outline_frame = {"schema": "archeaxis.openmaic-outline-replay/v1", "request_id": "outline_request_1",
                     "requirement": "从合成材料制作知识检查", "source_text": SOURCE_TEXT,
                     "reply": outline_reply if outline_reply is not None else reply(synthetic_outline())}
    ok, outline_result = step("outline", outline_frame)
    if not ok or outline_result.get("model_call") != "NOT_INVOKED" or outline_result.get("input") != outline_frame:
        return reject("outline", "worker failure, unexpected status or model boundary")
    transformations = outline_result.get("transformations")
    allowed_outline_changes = {"DEFAULT_LANGUAGE_DIRECTIVE", "UNSTABLE_GENERATED_OUTLINE_IDS",
                               "OUTLINE_ORDER_ASSIGNED", "COURSE_TITLE_NORMALIZED"}
    if not isinstance(transformations, list) or any(not isinstance(item, str) or item not in allowed_outline_changes for item in transformations):
        return reject("outline", "upstream reported a dropped or unknown transformation")
    data = outline_result.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("outlines"), list) or len(data["outlines"]) != 1:
        return reject("outline", "exactly one supported quiz outline required")
    outline = data["outlines"][0]
    allowed = {"id", "type", "title", "description", "keyPoints", "order", "quizConfig"}
    required = {"id", "type", "title", "description", "keyPoints", "order"}
    if not isinstance(outline, dict) or not required <= outline.keys() or not outline.keys() <= allowed or outline["type"] != "quiz":
        return reject("outline", "unknown outline type or fields")
    if not isinstance(data.get("languageDirective"), str):
        return reject("outline", "missing language directive")
    quiz_outline = deepcopy(outline)
    quiz_outline.pop("order")
    quiz_frame = {"schema": "archeaxis.openmaic-quiz-replay/v1", "request_id": "quiz_request_1",
                  "outline": quiz_outline, "language_directive": data["languageDirective"],
                  "reply": quiz_reply if quiz_reply is not None else reply([synthetic_question()])}
    ok, quiz_result = step("quiz", quiz_frame)
    if (not ok or quiz_result.get("model_call") != "NOT_INVOKED"
            or quiz_result.get("full_generate_scene_content") is not False or quiz_result.get("input") != quiz_frame):
        return reject("quiz", "worker failure, unexpected status or generation boundary")
    quiz_changes = quiz_result.get("transformations")
    allowed_quiz_changes = {"UNSTABLE_GENERATED_QUESTION_IDS", "PLAIN_OPTIONS_NORMALIZED", "ANSWER_REFERENCE_NORMALIZED",
                            "SHORT_ANSWER_NOT_GRADED", "QUESTION_COUNT_DIFFERS_FROM_REQUEST", "QUESTION_TYPE_DIFFERS_FROM_REQUEST"}
    if not isinstance(quiz_changes, list) or any(not isinstance(item, str) or item not in allowed_quiz_changes for item in quiz_changes):
        return reject("quiz", "upstream reported an unknown transformation")
    content = quiz_result.get("data")
    if not isinstance(content, dict) or set(content) != {"questions"} or not isinstance(content["questions"], list) or not content["questions"]:
        return reject("quiz", "unknown content result")
    selected_actions = deepcopy(actions) if actions is not None else []
    actions_origin = "caller_supplied" if actions is not None else "explicit_empty"
    if generate_actions:
        if actions is not None:
            return reject("actions", "generated and caller-supplied actions cannot be combined")
        action_frame = {"schema": "archeaxis.openmaic-quiz-actions-replay/v1", "request_id": "actions_request_1",
                        "outline": deepcopy(outline), "content": deepcopy(content),
                        "language_directive": data["languageDirective"],
                        "reply": action_reply if action_reply is not None else reply([
                            {"type": "text", "content": " 先独立完成合成练习。 "}])}
        ok, action_result = step("actions", action_frame)
        if (not ok or action_result.get("model_call") != "NOT_INVOKED"
                or action_result.get("action_execution") != "NOT_PERFORMED"
                or action_result.get("rendering_authorized") is not False
                or action_result.get("full_generate_scene_actions") is not False
                or action_result.get("canonical_bindings_verified") is not False
                or action_result.get("answer_non_disclosure_verified") is not False
                or action_result.get("input") != action_frame):
            return reject("actions", "worker failure, unexpected status or action boundary")
        action_changes = action_result.get("transformations")
        observation = action_result.get("observation")
        if (not isinstance(action_changes, list)
                or any(not isinstance(item, str) or item not in {"UNSTABLE_GENERATED_ACTION_IDS", "SPEECH_TRIMMED"} for item in action_changes)
                or not isinstance(observation, dict) or observation.get("fallback") is not False
                or observation.get("dropped_item_count") != 0):
            return reject("actions", "unknown, dropped or fallback action transformation")
        action_data = action_result.get("data")
        if (not isinstance(action_data, dict) or set(action_data) != {"actions"}
                or not isinstance(action_data["actions"], list) or not 1 <= len(action_data["actions"]) <= 2
                or any(not isinstance(item, dict) or set(item) != {"id", "type", "text"}
                       or item["type"] != "speech" or not isinstance(item["id"], str)
                       or not isinstance(item["text"], str) or not item["text"].strip()
                       for item in action_data["actions"])):
            return reject("actions", "unknown or active action result")
        selected_actions = deepcopy(action_data["actions"])
        actions_origin = "synthetic_upstream_quiz_branch"
    elif action_reply is not None:
        return reject("actions", "action reply provided without requesting replay")
    declared_source = deepcopy(source) if source is not None else deepcopy(SOURCE)
    build_frame = {"schema": "archeaxis.openmaic-scene-build/v1", "request_id": "build_request_1", "attempt": 1,
                   "source": declared_source, "stage_id": "stage_1", "scene_id": "scene_1",
                   "outline": deepcopy(outline), "content": deepcopy(content), "actions": selected_actions}
    ok, build_result = step("build", build_frame)
    if not ok or build_result.get("model_call") != "NOT_INVOKED":
        return reject("build", "worker failure, unexpected status or model boundary")
    scene = build_result.get("scene")
    if (not isinstance(scene, dict) or scene.get("id") != "scene_1" or scene.get("stageId") != "stage_1"
            or scene.get("outlineId") != outline["id"] or scene.get("type") != "quiz"
            or scene.get("order") != outline["order"] or scene.get("actions") != selected_actions
            or not isinstance(scene.get("content"), dict) or scene["content"].get("type") != "quiz"
            or scene["content"].get("questions") != content["questions"]
            or build_result.get("source") != declared_source
            or build_result.get("source_binding") != "client_declared_unverified"
            or build_result.get("canonical_bindings_verified") is not False
            or build_result.get("active_content_executed") is not False):
        return reject("build", "unknown or mismatched builder result")
    return {"status": "CANDIDATE", "candidate": build_result, "trace": trace,
            "actions_origin": actions_origin,
            "model_call": "NOT_INVOKED", "core_task": "NOT_CONNECTED", "full_generation_chain": False}


@pytest.mark.parametrize("actions", [None, [{"id": "caller_action_1", "type": "speech", "text": "合成说明"}]])
def test_actual_workers_compose_one_inert_quiz_scene_and_preserve_bindings(actions):
    result = run_synthetic_chain(actions=actions)
    assert result["status"] == "CANDIDATE", result
    assert [entry["stage"] for entry in result["trace"]] == ["outline", "quiz", "build"]
    outline_stage, quiz_stage, build_stage = result["trace"]
    outline = outline_stage["result"]["data"]["outlines"][0]
    assert outline["id"] == "outline_1" and outline["order"] == 1
    assert "OUTLINE_ORDER_ASSIGNED" in outline_stage["result"]["transformations"]
    assert quiz_stage["request"]["outline"] == {key: value for key, value in outline.items() if key != "order"}
    assert build_stage["request"]["outline"] == outline
    assert outline_stage["request"]["source_text"] == SOURCE_TEXT
    assert outline_stage["result"]["input"] == outline_stage["request"]
    assert quiz_stage["result"]["input"] == quiz_stage["request"]
    assert quiz_stage["request"]["language_directive"] == outline_stage["result"]["data"]["languageDirective"]
    candidate, scene = result["candidate"], result["candidate"]["scene"]
    assert scene["id"] == "scene_1" and scene["stageId"] == "stage_1" and scene["outlineId"] == outline["id"]
    assert scene["title"] == outline["title"] and scene["type"] == "quiz"
    question = scene["content"]["questions"][0]
    assert question["id"] == "question_1" and question["question"] == "哪项是合成材料？"
    assert question["options"] == [{"value": "A", "label": "材料甲"}, {"value": "B", "label": "材料乙"}]
    assert question["answer"] == ["B"] and question["analysis"] == "合成参考"
    assert scene["actions"] == (actions or [])
    assert result["actions_origin"] == ("caller_supplied" if actions is not None else "explicit_empty")
    assert candidate["source"] == SOURCE and candidate["source_binding"] == "client_declared_unverified"
    build_bytes = json.dumps(build_stage["request"], ensure_ascii=False).encode("utf-8")
    assert candidate["input_sha256"] == hashlib.sha256(build_bytes).hexdigest()
    assert candidate["canonical_bindings_verified"] is False and candidate["active_content_executed"] is False
    assert candidate["rendering_authorized"] is False and candidate["retry_bytes_stable"] is False
    assert result["model_call"] == "NOT_INVOKED" and result["core_task"] == "NOT_CONNECTED"
    assert result["full_generation_chain"] is False


@pytest.mark.parametrize("overrides,failed,stages", [
    ({"outline_reply": {"kind": "synthetic_error"}}, "outline", ["outline"]),
    ({"outline_reply": reply(synthetic_outline(type="future"))}, "outline", ["outline"]),
    ({"outline_reply": reply(synthetic_outline(mediaGenerations=[{"id": "m1"}]))}, "outline", ["outline"]),
    ({"outline_reply": reply(synthetic_outline(mediaGenerations="invalid metadata"))}, "outline", ["outline"]),
    ({"outline_reply": reply(synthetic_outline(actions=[{"type": "run"}]))}, "outline", ["outline"]),
    ({"quiz_reply": {"kind": "synthetic_error"}}, "quiz", ["outline", "quiz"]),
    ({"quiz_reply": reply([synthetic_question(type="future")])}, "quiz", ["outline", "quiz"]),
    ({"quiz_reply": reply([synthetic_question(actions=[{"type": "run"}])])}, "quiz", ["outline", "quiz"]),
    ({"quiz_reply": reply([synthetic_question(correctAnswer="unknown")])}, "quiz", ["outline", "quiz"]),
    ({"source": {"document_id": "doc_1", "version": 1, "content_sha256": "bad"}}, "build", ["outline", "quiz", "build"]),
])
def test_real_worker_failure_or_unsupported_output_stops_before_candidate(overrides, failed, stages):
    result = run_synthetic_chain(**overrides)
    assert result["status"] == "REJECTED" and result["candidate"] is None
    assert result["failed_stage"] == failed
    assert [entry["stage"] for entry in result["trace"]] == stages
    assert all(entry["result"].get("scene") is None for entry in result["trace"])


@pytest.mark.parametrize("injected_stage,stages", [
    ("outline", ["outline"]), ("quiz", ["outline", "quiz"]), ("build", ["outline", "quiz", "build"]),
])
def test_test_only_composition_rejects_a_simulated_future_worker_status(injected_stage, stages):
    def simulate_unknown(name, frame):
        if name == injected_stage:
            return 0, {"schema": SCHEMAS[name], "status": "FUTURE_STATUS", "model_call": "NOT_INVOKED"}
        return run_worker(name, frame)

    result = run_synthetic_chain(invoke=simulate_unknown)
    assert result["status"] == "REJECTED" and result["candidate"] is None
    assert result["failed_stage"] == injected_stage
    assert [entry["stage"] for entry in result["trace"]] == stages


@pytest.mark.parametrize("change", ["outline_id", "source"])
def test_test_only_composition_rejects_simulated_mismatched_builder_binding(change):
    def simulate_mismatch(name, frame):
        code, body = run_worker(name, frame)
        if name == "build" and code == 0:
            body = deepcopy(body)
            if change == "outline_id":
                body["scene"]["outlineId"] = "different_outline"
            else:
                body["source"]["version"] = 2
        return code, body

    result = run_synthetic_chain(invoke=simulate_mismatch)
    assert result["status"] == "REJECTED" and result["candidate"] is None
    assert result["failed_stage"] == "build"


def test_actual_actions_branch_joins_the_synthetic_chain_as_unexecuted_scene_data():
    result = run_synthetic_chain(generate_actions=True)
    assert result["status"] == "CANDIDATE", result
    assert [entry["stage"] for entry in result["trace"]] == ["outline", "quiz", "actions", "build"]
    outline_stage, quiz_stage, action_stage, build_stage = result["trace"]
    action_result = action_stage["result"]
    outline = outline_stage["result"]["data"]["outlines"][0]
    assert action_stage["request"]["outline"] == outline
    assert action_stage["request"]["content"] == quiz_stage["result"]["data"]
    assert action_result["input"] == action_stage["request"]
    assert action_result["response_origin"] == "SYNTHETIC_REPLAY"
    assert action_result["action_execution"] == "NOT_PERFORMED" and action_result["rendering_authorized"] is False
    assert action_result["answer_non_disclosure_verified"] is False
    assert action_result["prompt_projection"]["outline_fields_not_interpolated"] == ["id", "order", "quizConfig", "type"]
    assert action_result["prompt_projection"]["question_fields_not_interpolated"] == ["analysis", "answer", "correctAnswer", "hasAnswer", "id"]
    assert set(action_result["transformations"]) == {"SPEECH_TRIMMED", "UNSTABLE_GENERATED_ACTION_IDS"}
    generated = action_result["data"]["actions"]
    assert len(generated) == 1 and generated[0]["type"] == "speech"
    assert generated[0]["text"] == "先独立完成合成练习。"
    assert generated[0]["id"].startswith("action_")
    assert build_stage["request"]["actions"] == generated
    scene = result["candidate"]["scene"]
    assert scene["actions"] == generated and scene["outlineId"] == outline["id"]
    assert scene["content"]["questions"] == quiz_stage["result"]["data"]["questions"]
    assert result["candidate"]["source"] == SOURCE
    assert result["candidate"]["source_binding"] == "client_declared_unverified"
    assert result["candidate"]["active_content_executed"] is False
    assert result["actions_origin"] == "synthetic_upstream_quiz_branch"
    assert result["full_generation_chain"] is False and result["core_task"] == "NOT_CONNECTED"


@pytest.mark.parametrize("overrides,failed,stages", [
    ({"outline_reply": {"kind": "synthetic_error"}}, "outline", ["outline"]),
    ({"quiz_reply": reply([synthetic_question(type="future")])}, "quiz", ["outline", "quiz"]),
    ({"action_reply": {"kind": "synthetic_error"}}, "actions", ["outline", "quiz", "actions"]),
    ({"action_reply": reply([])}, "actions", ["outline", "quiz", "actions"]),
    ({"action_reply": reply([{"type": "action", "name": "spotlight", "params": {"elementId": "x"}}])},
     "actions", ["outline", "quiz", "actions"]),
    ({"action_reply": reply([{"type": "text", "content": "前"},
                              {"type": "action", "name": "discussion", "params": {}},
                              {"type": "text", "content": "不应被丢弃"}])},
     "actions", ["outline", "quiz", "actions"]),
    ({"action_reply": {"kind": "synthetic_response", "value": '[{"type":"text","content":"x",}]'}},
     "actions", ["outline", "quiz", "actions"]),
    ({"action_reply": {"kind": "synthetic_response", "value": r'[{"type":"text","content":"safe\u12X'}},
     "actions", ["outline", "quiz", "actions"]),
    ({"source": {"document_id": "doc_1", "version": 1, "content_sha256": "bad"}},
     "build", ["outline", "quiz", "actions", "build"]),
])
def test_synthetic_chain_refuses_any_failure_unknown_action_or_recovered_output(overrides, failed, stages):
    result = run_synthetic_chain(generate_actions=True, **overrides)
    assert result["status"] == "REJECTED" and result["candidate"] is None
    assert result["failed_stage"] == failed
    assert [entry["stage"] for entry in result["trace"]] == stages
    assert all(entry["result"].get("scene") is None for entry in result["trace"])


def test_test_only_composition_rejects_simulated_unknown_action_status():
    def simulate_unknown(name, frame):
        if name == "actions":
            return 0, {"schema": SCHEMAS[name], "status": "FUTURE_STATUS", "model_call": "NOT_INVOKED"}
        return run_worker(name, frame)

    result = run_synthetic_chain(generate_actions=True, invoke=simulate_unknown)
    assert result["status"] == "REJECTED" and result["candidate"] is None
    assert result["failed_stage"] == "actions"
    assert [entry["stage"] for entry in result["trace"]] == ["outline", "quiz", "actions"]


@pytest.mark.parametrize("injected_stage,stages", [
    ("outline", ["outline"]), ("quiz", ["outline", "quiz"]), ("actions", ["outline", "quiz", "actions"]),
])
def test_test_only_composition_rejects_simulated_unknown_transformation(injected_stage, stages):
    def simulate_unknown(name, frame):
        code, body = run_worker(name, frame)
        if name == injected_stage and code == 0:
            body = deepcopy(body)
            body["transformations"].append("FUTURE_TRANSFORMATION")
        return code, body

    result = run_synthetic_chain(generate_actions=True, invoke=simulate_unknown)
    assert result["status"] == "REJECTED" and result["candidate"] is None
    assert result["failed_stage"] == injected_stage
    assert [entry["stage"] for entry in result["trace"]] == stages
