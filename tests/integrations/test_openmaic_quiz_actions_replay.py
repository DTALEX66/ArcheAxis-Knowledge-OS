"""Original quiz action branch with synthetic replies; no action execution or model."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/learning-providers/openmaic/quiz-actions-replay-worker.mjs"
VENDOR = WORKER.parent / "vendor"
ARCHIVE = ROOT / ".project-local/archives/owner-inputs/20261101-learning-platform-sources/OpenMAIC-1.3.0.zip"
NPM_AUDIT = ROOT / ".project-local/cache/npm/openmaic-owner-4660cd2b97ac2a3862cd238fc28b54195a622c8beabb87c9185d87f626f47a29/backend-verify-npm-partial-fetch-0f3e8682f8"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit ARCHEAXIS_TEST_NODE is required; PATH is not searched")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def invoke(frame: dict | bytes) -> tuple[int, dict]:
    assert NODE and Path(NODE).is_absolute(), "ARCHEAXIS_TEST_NODE must be an absolute path"
    raw = frame if isinstance(frame, bytes) else json.dumps(frame, ensure_ascii=False).encode("utf-8")
    process = subprocess.run([NODE, str(WORKER)], input=raw, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=20, check=False)
    try:
        body = json.loads(process.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise AssertionError(f"missing JSON result: exit={process.returncode}, stderr={process.stderr.decode('utf-8', 'replace')}") from error
    return process.returncode, body


def frame(reply: dict | None = None) -> dict:
    return {"schema": "archeaxis.openmaic-quiz-actions-replay/v1", "request_id": "request_1",
            "outline": {"id": "outline_1", "type": "quiz", "title": "合成练习", "description": "测试",
                        "keyPoints": ["练习"], "order": 1,
                        "quizConfig": {"questionCount": 1, "difficulty": "easy", "questionTypes": ["single"]}},
            "content": {"questions": [{"id": "q_1", "type": "single", "question": "选择一项？",
                        "options": [{"value": "A", "label": "甲"}, {"value": "B", "label": "乙"}],
                        "answer": ["B"], "correctAnswer": "乙", "hasAnswer": True}]},
            "language_directive": "中文", "reply": reply or {"kind": "synthetic_response", "value": json.dumps([
                {"type": "text", "content": " 开始合成练习 "}, {"type": "text", "content": "提交后讨论。"}], ensure_ascii=False)}}


def prompt_frame() -> dict:
    return {"schema": "archeaxis.openmaic-quiz-actions-prompt/v1", "stage": "capture",
            "request_id": "prompt_1",
            "outline": {"id": "outline_1", "type": "quiz", "title": "合成练习", "description": "测试",
                        "keyPoints": ["练习"], "order": 1,
                        "quizConfig": {"questionCount": 1, "difficulty": "easy", "questionTypes": ["single"]}},
            "content": {"questions": [{"id": "q_1", "type": "single", "question": "选择一项？",
                        "options": [{"value": "A", "label": "甲"}, {"value": "B", "label": "乙"}],
                        "answer": ["B"], "correctAnswer": "乙", "hasAnswer": True}]},
            "language_directive": "中文"}


def capture() -> dict:
    code, result = invoke(prompt_frame())
    assert code == 0 and result["status"] == "PROMPT_CAPTURED", result
    return result


def replay(reply: str, binding: dict) -> tuple[int, dict]:
    data = prompt_frame()
    data["stage"] = "replay"
    data["binding"] = binding
    data["reply"] = {"kind": "caller_supplied", "value": reply}
    return invoke(data)


@requires_node
def test_prompt_capture_binds_the_original_quiz_action_prompt():
    result = capture()
    binding = result["binding"]
    assert result["schema"] == "archeaxis.openmaic-quiz-actions-prompt-result/v1"
    assert result["stage"] == "capture" and result["request_id"] == "prompt_1"
    assert result["callback_count"] == 1 and len(result["calls"]) == 1
    assert binding["schema"] == "archeaxis.openmaic-quiz-actions-prompt-binding/v1"
    assert binding["system"].startswith("# Quiz Action Generator")
    assert "Q1 (single): 选择一项？" in binding["user"]
    assert "answer" not in binding["user"].lower(), "the prompt carries no answer field"
    assert len(binding["system_sha256"]) == 64 and len(binding["user_sha256"]) == 64
    assert binding["system_sha256"] == sha(binding["system"].encode("utf-8"))
    assert binding["user_sha256"] == sha(binding["user"].encode("utf-8"))
    assert binding["worker_sha256"] == sha(WORKER.read_bytes())
    assert binding["actions_manifest_sha256"] == "8e4b62a07c4daf3085fadd126396e467084a7dd35c9c5e9159f863fb527e655a"
    assert binding["dsl_manifest_sha256"] == "ef4102ca18abefcf0c5956a8caa356236d60d248416b1b666cfc6daa99066dc0"
    assert result["model_call"] == "NOT_INVOKED" and result["action_execution"] == "NOT_PERFORMED"
    assert "human_review_required" not in result and result["data"] is None


@requires_node
def test_prompt_replay_admits_only_inert_text_speech():
    binding = capture()["binding"]
    code, result = replay('[{"type":"text","content":" 开始合成练习 "}]', binding)
    assert code == 0 and result["status"] == "CANDIDATE", result
    assert result["stage"] == "replay" and result["exact_json_output"] is True
    assert [item["type"] for item in result["data"]["actions"]] == ["speech"]
    assert result["data"]["actions"][0]["text"] == "开始合成练习"
    assert set(result["transformations"]) == {"UNSTABLE_GENERATED_ACTION_IDS", "SPEECH_TRIMMED"}
    assert result["observation"]["parser_action_count"] == 1 and result["observation"]["fallback"] is False
    assert result["action_execution"] == "NOT_PERFORMED" and result["rendering_authorized"] is False
    assert result["answer_non_disclosure_verified"] is False and result["human_review_required"] is True


@requires_node
def test_prompt_replay_refuses_a_changed_binding_before_running_the_branch():
    binding = dict(capture()["binding"])
    binding["worker_sha256"] = "0" * 64
    code, result = replay('[{"type":"text","content":"x"}]', binding)
    assert code == 2 and result["status"] == "BINDING_MISMATCH"
    assert result["data"] is None and result.get("calls") is None


@requires_node
def test_prompt_replay_quarantines_named_actions_and_fallback():
    binding = capture()["binding"]
    code, result = replay('[{"type":"action","name":"discussion","params":{}}]', binding)
    assert code == 2 and result["status"] == "UNSUPPORTED_OUTPUT" and result["data"] is None
    # An exact empty array is refused before the branch; the donor is only
    # allowed to repair the text, and its repaired fallback is still not admitted.
    code, result = replay("[]", binding)
    assert code == 2 and result["status"] == "UNSUPPORTED_OUTPUT"
    code, result = replay("```json\n[]\n```", binding)
    assert code == 2 and result["status"] == "UPSTREAM_FALLBACK_NOT_ADMITTED"
    assert result["observation"]["fallback"] is True


@requires_node
def test_prompt_replay_admits_a_donor_repaired_reply_as_non_exact():
    binding = capture()["binding"]
    code, result = replay('```json\n[{"type":"text","content":"围栏开场"}]\n```', binding)
    assert code == 0 and result["status"] == "CANDIDATE", result
    assert result["exact_json_output"] is False
    assert "UPSTREAM_JSON_REPAIRED" in result["transformations"]
    assert "UPSTREAM_NORMALIZATIONS_UNRECONSTRUCTED" in result["transformations"]
    assert result["data"]["actions"][0]["text"] == "围栏开场"


@requires_node
def test_prompt_frame_rejects_unknown_or_missing_fields():
    data = prompt_frame()
    data["reply"] = {"kind": "caller_supplied", "value": "[]"}
    code, result = invoke(data)
    assert code == 2 and result["status"] == "INVALID_REQUEST"
    data = prompt_frame()
    data["language_directive"] = "中文\0"
    assert invoke(data)[1]["status"] == "INVALID_REQUEST"


def test_all_loaded_openmaic_members_match_exact_owner_zip_bytes():
    if not ARCHIVE.is_file():
        pytest.skip("local-only original absent in a Git clone/CI (Git-ignored .project-local input); "
                    "this skip is NOT evidence of byte identity")
    assert sha(ARCHIVE.read_bytes()) == "7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40"
    groups = [("generation-0.3.28-outline", 18), ("generation-0.3.28-quiz", 6),
              ("generation-0.3.28-quiz-actions", 7), ("dsl-0.12.0-actions", 3)]
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name, count in groups:
            root = VENDOR / name
            record = json.loads((root / "ORIGINALS.json").read_text(encoding="utf-8"))
            assert record["license"] == "MIT" and len(record["originals"]) == count
            for relative, expected in record["originals"].items():
                original = archive.read(record["source_prefix"] + relative)
                assert sha(original) == expected
                assert (root / relative).read_bytes() == original


def test_quiz_branch_and_complete_helpers_are_exact_original_excerpts():
    root = VENDOR / "generation-0.3.28-quiz-actions"
    manifest_bytes = (root / "ORIGINALS.json").read_bytes()
    assert sha(manifest_bytes) == "8e4b62a07c4daf3085fadd126396e467084a7dd35c9c5e9159f863fb527e655a"
    record = json.loads(manifest_bytes)
    source = (root / record["source_file"]).read_bytes()
    assert sha(source) == record["source_sha256"]
    adapter = (root / record["adapted_file"]).read_bytes()
    assert sha(adapter) == record["adapted_sha256"]
    assert [(e["start_line"], e["end_line"]) for e in record["excerpts"]] == [
        (1781, 1783), (1823, 1849), (1970, 1979), (1984, 2035), (2071, 2080)]
    lines = source.splitlines(keepends=True)
    for excerpt in record["excerpts"]:
        original = b"".join(lines[excerpt["start_line"] - 1:excerpt["end_line"]])
        assert sha(original) == excerpt["sha256"] and adapter.count(original) == 1
    assert b"export async function replayQuizActionsBranch(" in adapter


def test_locked_partial_json_archive_and_runtime_members_are_exact():
    if not (NPM_AUDIT / "partial-json-0.1.7.tgz").is_file():
        pytest.skip("local-only original absent in a Git clone/CI (Git-ignored .project-local input); "
                    "this skip is NOT evidence of byte identity")
    archive_bytes = (NPM_AUDIT / "partial-json-0.1.7.tgz").read_bytes()
    sri = "sha512-" + base64.b64encode(hashlib.sha512(archive_bytes).digest()).decode("ascii")
    assert sri == "sha512-Njv/59hHaokb/hRUjce3Hdv12wd60MtM9Z5Olmn+nehe0QDAsRtRbJPvJ0Z91TusF0SuZRIvnM+S4l6EIP8leA=="
    root = VENDOR / "npm/partial-json-0.1.7"
    record = json.loads((root / "SOURCE.json").read_text(encoding="utf-8"))
    assert record["name"] == "partial-json" and record["version"] == "0.1.7"
    assert record["license"] == "MIT" and record["archive_sri"] == sri and record["scripts_executed"] is False
    assert set(record["files"]) == {"LICENSE", "package.json", "dist/index.js", "dist/options.js"}
    with tarfile.open(NPM_AUDIT / "partial-json-0.1.7.tgz", "r:gz") as archive:
        members = archive.getmembers()
        assert len(members) == 9 and all(member.isfile() and member.name.startswith("package/") for member in members)
        for member in members:
            relative = member.name.removeprefix("package/")
            stream = archive.extractfile(member)
            assert stream is not None
            original = stream.read()
            assert (NPM_AUDIT / "partial-json-0.1.7" / relative).read_bytes() == original
            if relative in record["files"]:
                identity = record["files"][relative]
                assert (root / relative).read_bytes() == original
                assert (len(original), sha(original)) == (identity["bytes"], identity["sha256"])


@requires_node
def test_original_branch_returns_inert_synthetic_speech_with_visible_transformations():
    data = frame()
    code, result = invoke(data)
    assert code == 0 and result["status"] == "CANDIDATE", result
    assert result["input"] == data and len(result["calls"]) == 1
    assert len(result["calls"][0]["system_sha256"]) == 64
    produced = result["data"]["actions"]
    assert [item["type"] for item in produced] == ["speech", "speech"]
    assert [item["text"] for item in produced] == ["开始合成练习", "提交后讨论。"]
    assert all(item["id"].startswith("action_") and len(item["id"]) == 15 for item in produced)
    assert set(result["transformations"]) == {"UNSTABLE_GENERATED_ACTION_IDS", "SPEECH_TRIMMED"}
    assert result["observation"]["parser_action_count"] == 2 and result["observation"]["fallback"] is False
    assert result["prompt_projection"]["outline_fields_not_interpolated"] == ["id", "order", "quizConfig", "type"]
    assert result["prompt_projection"]["question_fields_not_interpolated"] == ["answer", "correctAnswer", "hasAnswer", "id"]
    assert result["model_call"] == "NOT_INVOKED" and result["core_task"] == "NOT_CONNECTED"
    assert result["full_generate_scene_actions"] is False and result["full_generation_chain"] is False
    assert result["action_execution"] == "NOT_PERFORMED" and result["rendering_authorized"] is False
    assert result["answer_non_disclosure_verified"] is False and result["human_review_required"] is True
    assert result["retry_bytes_stable"] is False and result["independent_mastery"] == "not_established"
    observed = subprocess.run([NODE, "-p", "process.versions.node"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=10, check=False)
    assert observed.returncode == 0
    assert result["runtime"]["node_version"] == observed.stdout.decode("utf-8").strip()
    assert result["runtime"]["register_hooks_available"] is True
    assert result["runtime"]["upstream_quiz_branch_imported"] is True
    assert result["runtime"]["upstream_members_checked"] is True
    assert result["runtime"]["locked_npm_members_checked"] is True


@requires_node
@pytest.mark.parametrize("value,slide_filtered", [
    ([], False), ([{"type": "action", "name": "spotlight", "params": {"elementId": "x"}}], True),
])
def test_actual_upstream_default_speech_is_reported_as_fallback_not_model_output(value, slide_filtered):
    data = frame({"kind": "synthetic_response", "value": json.dumps(value)})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UPSTREAM_FALLBACK_NOT_ADMITTED"
    assert result["data"] is None and result["input"] == data
    assert result["fallback_origin"] == "UPSTREAM_DEFAULT"
    assert result["fallback_speech"] == "现在让我们来做一个小测验，检验一下学习成果。"
    assert result["observation"]["parser_action_count"] == 0 and result["observation"]["fallback"] is True
    assert ("SLIDE_ACTIONS_FILTERED" in result["notices"]) is slide_filtered
    assert result["observation"]["dropped_item_count"] == len(value)


@requires_node
def test_upstream_discussion_truncation_and_unknown_action_are_quarantined():
    value = [{"type": "text", "content": "前"}, {"type": "action", "name": "discussion", "params": {}},
             {"type": "text", "content": "保留原始输入中的后段"}]
    data = frame({"kind": "synthetic_response", "value": json.dumps(value, ensure_ascii=False)})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UNSUPPORTED_OR_FILTERED_NOT_ADMITTED"
    assert result["data"] is None and result["input"] == data
    assert result["observation"]["input_item_count"] == 3
    assert result["observation"]["parser_action_count"] == 2
    assert result["observation"]["dropped_item_count"] == 1
    assert result["observation"]["discussion_may_truncate"] is True
    assert result["action_execution"] == "NOT_PERFORMED"


@requires_node
def test_jsonrepair_recovery_is_quarantined_and_original_reply_retained():
    malformed = '[{"type":"text","content":"合成开场",}]'
    data = frame({"kind": "synthetic_response", "value": malformed})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UPSTREAM_RECOVERY_NOT_ADMITTED"
    assert result["data"] is None and result["input"] == data
    assert result["observation"]["parser_action_count"] == 1
    assert result["observation"]["recovery_path"] == "jsonrepair" and "JSONREPAIR_USED" in result["notices"]


@requires_node
def test_partial_json_fallback_on_truncated_unicode_is_observed_and_quarantined():
    assert NODE and Path(NODE).is_absolute()
    malformed = r'[{"type":"text","content":"safe\u12X'
    # Demonstrate on the same exact input that locked jsonrepair rejects and the
    # locked partial-json parser returns one text item. The original action
    # parser tries these in that order; neither result is admitted as a scene.
    script = r'''const jr=await import(process.argv[1]); const pj=await import(process.argv[2]);
let repairRejected=false; try {jr.jsonrepair(process.argv[3])} catch {repairRejected=true}
process.stdout.write(JSON.stringify({repairRejected,parsed:pj.default.parse(process.argv[3])}));'''
    jr = (VENDOR / "npm/jsonrepair-3.13.3/lib/esm/index.js").as_uri()
    pj = (VENDOR / "npm/partial-json-0.1.7/dist/index.js").as_uri()
    process = subprocess.run([NODE, "--input-type=module", "-e", script, jr, pj, malformed],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
    assert process.returncode == 0, process.stderr.decode("utf-8", "replace")
    direct = json.loads(process.stdout.decode("utf-8"))
    assert direct == {"repairRejected": True, "parsed": [{"type": "text", "content": "safe"}]}
    data = frame({"kind": "synthetic_response", "value": malformed})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UPSTREAM_RECOVERY_NOT_ADMITTED"
    assert result["input"] == data and result["data"] is None
    assert result["observation"]["parser_action_count"] == 1
    assert result["observation"]["recovery_path"] == "unverified" and "JSONREPAIR_USED" not in result["notices"]


@requires_node
def test_callback_failure_duplicate_keys_bad_input_and_oversize_are_refused():
    data = frame({"kind": "synthetic_error"})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UPSTREAM_FAILURE" and result["input"] == data
    duplicate = '[{"type":"text","content":"x","cont\\u0065nt":"y"}]'
    data = frame({"kind": "synthetic_response", "value": duplicate})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "INVALID_RESPONSE" and result["input"] == data
    invalid = frame()
    invalid["content"]["questions"][0]["media"] = {"url": "file://x"}
    assert invoke(invalid)[1]["status"] == "INVALID_REQUEST"
    assert invoke(b" " * 256_001)[1]["status"] == "INVALID_REQUEST"


@requires_node
@pytest.mark.parametrize("relative,reason", [
    ("generation-0.3.28-quiz-actions/ORIGINALS.json", b"ACTIONS_MANIFEST_IDENTITY_MISMATCH"),
    ("generation-0.3.28-quiz-actions/quiz-actions-functions.ts", b"ACTIONS_ADAPTER_IDENTITY_MISMATCH"),
    ("generation-0.3.28-quiz-actions/src/action-parser.ts", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("generation-0.3.28-quiz-actions/templates/quiz-actions/system.md", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("dsl-0.12.0-actions/src/action.ts", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("generation-0.3.28-quiz/src/scene-generator.ts", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("npm/partial-json-0.1.7/dist/index.js", b"LOCKED_NPM_MEMBER_IDENTITY_MISMATCH"),
    ("npm/partial-json-0.1.7/dist/options.js", b"LOCKED_NPM_MEMBER_IDENTITY_MISMATCH"),
])
def test_changed_dependency_is_rejected_before_replay(tmp_path, relative, reason):
    assert NODE and Path(NODE).is_absolute()
    copy = tmp_path / "worker-copy"
    copy.mkdir()
    shutil.copy2(WORKER, copy / WORKER.name)
    for member in ["generation-0.3.28-outline", "generation-0.3.28-quiz", "generation-0.3.28-quiz-actions",
                   "dsl-0.12.0-actions", "npm"]:
        shutil.copytree(VENDOR / member, copy / "vendor" / member)
    changed = copy / "vendor" / relative
    changed.write_bytes(changed.read_bytes() + b"\n// changed\n")
    process = subprocess.run([NODE, str(copy / WORKER.name), "--hello"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=10, check=False)
    assert process.returncode != 0 and process.stdout == b""
    assert reason in process.stderr
