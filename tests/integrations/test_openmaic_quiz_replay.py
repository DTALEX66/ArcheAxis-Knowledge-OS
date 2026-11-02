"""Synthetic replay of a retained upstream quiz excerpt, without Core or a model."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/learning-providers/openmaic/quiz-replay-worker.mjs"
QUIZ = WORKER.parent / "vendor/generation-0.3.28-quiz"
OUTLINE = WORKER.parent / "vendor/generation-0.3.28-outline"
ARCHIVE = ROOT / ".project-local/archives/owner-inputs/20261101-learning-platform-sources/OpenMAIC-1.3.0.zip"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit ARCHEAXIS_TEST_NODE is required; PATH is not searched")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def child_env() -> dict[str, str]:
    # The fixed Node worker needs only non-secret operating-system bootstrap
    # values. Do not inherit proxy, credentials or Node injection settings.
    return {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}


def invoke(frame: dict | bytes) -> tuple[int, dict]:
    assert NODE and Path(NODE).is_absolute(), "ARCHEAXIS_TEST_NODE must be an absolute path"
    raw = frame if isinstance(frame, bytes) else json.dumps(frame, ensure_ascii=False).encode("utf-8")
    process = subprocess.run([NODE, str(WORKER)], input=raw, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=20, check=False, env=child_env())
    try:
        body = json.loads(process.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise AssertionError(f"missing JSON result: exit={process.returncode}, stderr={process.stderr.decode('utf-8', 'replace')}") from error
    return process.returncode, body


def frame(reply: dict | None = None) -> dict:
    questions = [
        {"type": "single", "question": "选择一个", "options": ["零", "一"], "correctAnswer": "一"},
        {"id": "q2", "type": "multiple", "question": "选择两个", "options": [
            {"value": "A", "label": "甲"}, {"value": "B", "label": "乙"}, {"value": "C", "label": "丙"}],
         "answer": ["A", "C"], "analysis": "合成参考", "points": 5},
    ]
    return {"schema": "archeaxis.openmaic-quiz-replay/v1", "request_id": "request_1",
            "outline": {"id": "quiz_1", "type": "quiz", "title": "示例",
                        "description": "离线合成", "keyPoints": ["核对"],
                        "quizConfig": {"questionCount": 2, "difficulty": "medium",
                                       "questionTypes": ["single", "multiple"]}},
            "language_directive": "中文", "reply": reply or {
                "kind": "synthetic_response", "value": json.dumps(questions, ensure_ascii=False)}}


def capture_frame() -> dict:
    sample = frame()
    return {"schema": "archeaxis.openmaic-quiz-prompt/v1", "stage": "capture",
            "request_id": "quiz_prompt_1", "outline": sample["outline"],
            "language_directive": sample["language_directive"]}


def replay_frame(capture: dict, binding: dict, value: str | None = None) -> dict:
    if value is None:
        value = frame()["reply"]["value"]
    return {**capture, "stage": "replay", "binding": binding,
            "reply": {"kind": "caller_supplied", "value": value}}


def capture_prompt() -> tuple[dict, dict]:
    request = capture_frame()
    code, result = invoke(request)
    assert code == 0 and result["status"] == "PROMPT_CAPTURED", result
    return request, result["binding"]


def test_vendored_quiz_and_loaded_donor_files_match_exact_owner_archive_paths():
    if not ARCHIVE.is_file():
        pytest.skip("local-only original absent in a Git clone/CI (Git-ignored .project-local input); "
                    "this skip is NOT evidence of byte identity")
    assert sha(ARCHIVE.read_bytes()) == "7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40"
    with zipfile.ZipFile(ARCHIVE) as archive:
        for root, expected_count in [(QUIZ, 6), (OUTLINE, 18)]:
            manifest = json.loads((root / "ORIGINALS.json").read_text(encoding="utf-8"))
            assert manifest["generation_version"] == "0.3.28"
            assert manifest["license"] == "MIT"
            assert len(manifest["originals"]) == expected_count
            for relative, expected in manifest["originals"].items():
                original = archive.read(manifest["source_prefix"] + relative)
                assert sha(original) == expected
                assert (root / relative).read_bytes() == original


def test_adapter_retains_exact_contiguous_upstream_function_bytes():
    manifest_bytes = (QUIZ / "ORIGINALS.json").read_bytes()
    assert sha(manifest_bytes) == "54499d6b7840d2968a3b02d11a27ee70ceed92d865efe702882015044b597de8"
    excerpt = json.loads(manifest_bytes)["excerpt"]
    assert excerpt["source"] == "src/scene-generator.ts"
    assert (excerpt["start_line"], excerpt["end_line"]) == (914, 1108)
    source = (QUIZ / excerpt["source"]).read_bytes()
    original = b"".join(source.splitlines(keepends=True)[913:1108])
    assert sha(original) == excerpt["sha256"]
    assert original.startswith(b"async function generateQuizContent(")
    assert b"export function normalizeQuizAnswer(" in original
    adapter = (QUIZ / excerpt["adapted_file"]).read_bytes()
    assert sha(adapter) == excerpt["adapted_sha256"]
    assert adapter.count(original) == 1
    assert adapter.endswith(b"export { generateQuizContent };\n")


def test_locked_npm_dependency_members_and_licenses_are_identified():
    packages = {
        "jsonrepair-3.13.3": ("ISC", "sha512-BTznj0owIt2CBAH/LTo7+1I5pMvl1e1033LRl/HUowlZmJOIhzC0zbX5bxMngLkfT4WnzPP26QnW5wMr2g9tsQ=="),
        "nanoid-5.1.14": ("MIT", "sha512-5c8l8kVzqpnDPaicbEop/fV0Q1w16FmbWtVhMqugTozAwYdlIQojWH5a/M7UfziFmGdQRrUdV+EPzc9Xng3VAQ=="),
    }
    for package, (license_name, sri) in packages.items():
        root = WORKER.parent / "vendor/npm" / package
        record = json.loads((root / "SOURCE.json").read_text(encoding="utf-8"))
        assert record["license"] == license_name and record["archive_sri"] == sri
        assert record["scripts_executed"] is False
        for relative, identity in record["files"].items():
            data = (root / relative).read_bytes()
            assert (len(data), sha(data)) == (identity["bytes"], identity["sha256"])


@requires_node
def test_real_excerpt_normalizes_synthetic_choice_data_and_reports_limits():
    data = frame()
    code, result = invoke(data)
    assert code == 0, result
    assert result["status"] == "CANDIDATE" and result["input"] == data
    first, second = result["data"]["questions"]
    assert first["id"].startswith("q_") and len(first["id"]) == 10
    assert first["options"] == [{"value": "A", "label": "零"}, {"value": "B", "label": "一"}]
    assert first["answer"] == ["B"] and second["answer"] == ["A", "C"]
    assert set(result["transformations"]) >= {"UNSTABLE_GENERATED_QUESTION_IDS", "PLAIN_OPTIONS_NORMALIZED", "ANSWER_REFERENCE_NORMALIZED"}
    assert len(result["calls"]) == 1 and len(result["calls"][0]["system_sha256"]) == 64
    assert result["model_call"] == "NOT_INVOKED" and result["response_origin"] == "SYNTHETIC_REPLAY"
    assert result["network_performed"] is False and result["core_task"] == "NOT_CONNECTED"
    assert result["full_generate_scene_content"] is False and result["full_generation_chain"] is False
    assert result["independent_mastery"] == "not_established"
    assert result["provider_result_verification"] == "not_established" and result["retry_bytes_stable"] is False
    observed = subprocess.run([NODE, "-p", "process.versions.node"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=10, check=False)
    assert observed.returncode == 0
    assert result["runtime"]["node_version"] == observed.stdout.decode("utf-8").strip()
    assert int(result["runtime"]["node_version"].split(".")[0]) >= 24
    assert result["runtime"]["upstream_excerpt_imported"] is True
    assert result["runtime"]["register_hooks_available"] is True
    assert result["runtime"]["upstream_members_checked"] is True
    assert result["runtime"]["locked_npm_members_checked"] is True


@requires_node
@pytest.mark.parametrize("question,answer_index", [
    ({"id": "q1", "type": "single", "question": "Q", "options": ["B", "A"], "answer": "A"}, 0),
    ({"id": "q1", "type": "multiple", "question": "Q", "options": ["B", "A", "C"], "answer": ["A", "C"]}, 0),
])
def test_ambiguous_answer_is_quarantined_with_upstream_observation(question, answer_index):
    data = frame({"kind": "synthetic_response", "value": json.dumps([question])})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UPSTREAM_RESULT_NOT_ADMITTED"
    assert result["data"] is None and result["input"] == data
    observed = result["observed_upstream"]["questions"][0]
    assert observed["answer"][answer_index] == "A"
    assert observed["options"][:2] == [{"value": "A", "label": "B"}, {"value": "B", "label": "A"}]
    assert result["differences"] == [{"kind": "ANSWER_NOT_UNIQUE", "question_index": 0,
        "answer_index": answer_index, "original_answer": "A", "candidate_values": ["A", "B"],
        "upstream_answer": "A"}]


@requires_node
@pytest.mark.parametrize("option,observed_label", [
    ({"value": "A", "label": "Blue", "text": "Red"}, "Blue"),
    ({"value": "A", "text": "Red"}, "A"),
    ({"label": "Blue", "text": "Red"}, "Blue"),
])
def test_discarded_option_text_is_quarantined_with_upstream_observation(option, observed_label):
    question = {"id": "q1", "type": "single", "question": "Q", "options": [option, "Green"], "answer": "A"}
    data = frame({"kind": "synthetic_response", "value": json.dumps([question])})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UPSTREAM_RESULT_NOT_ADMITTED"
    assert result["data"] is None and result["input"] == data
    assert result["observed_upstream"]["questions"][0]["options"][0] == {"value": "A", "label": observed_label}
    assert result["differences"] == [{"kind": "OPTION_TEXT_DISCARDED", "question_index": 0,
        "option_index": 0, "original_text": "Red"}]


@requires_node
@pytest.mark.parametrize("answer,expected", [("A", "A"), ("乙", "B")])
def test_unique_value_or_label_match_is_admitted(answer, expected):
    question = {"id": "q1", "type": "single", "question": "Q", "options": ["甲", "乙"], "answer": answer}
    data = frame({"kind": "synthetic_response", "value": json.dumps([question], ensure_ascii=False)})
    code, result = invoke(data)
    assert code == 0 and result["status"] == "CANDIDATE" and result["input"] == data
    assert result["data"]["questions"][0]["answer"] == [expected]


@requires_node
def test_option_text_only_is_retained_and_its_conversion_is_reported():
    question = {"id": "q1", "type": "single", "question": "Q",
                "options": [{"text": "甲"}, "乙"], "answer": "甲"}
    data = frame({"kind": "synthetic_response", "value": json.dumps([question], ensure_ascii=False)})
    code, result = invoke(data)
    assert code == 0 and result["status"] == "CANDIDATE" and result["input"] == data
    assert result["data"]["questions"][0]["options"][0] == {"value": "A", "label": "甲"}
    assert "OPTION_TEXT_NORMALIZED_TO_LABEL" in result["transformations"]


@requires_node
def test_short_answer_is_not_graded_and_preserves_reference_text():
    question = {"id": "q3", "type": "short_answer", "question": "说明", "analysis": "合成参考",
                "commentPrompt": "合成规则"}
    data = frame({"kind": "synthetic_response", "value": json.dumps([question], ensure_ascii=False)})
    data["outline"]["quizConfig"] = {"questionCount": 1, "difficulty": "easy", "questionTypes": ["short_answer"]}
    code, result = invoke(data)
    assert code == 0, result
    item = result["data"]["questions"][0]
    assert item["hasAnswer"] is False and "answer" not in item and "options" not in item
    assert item["analysis"] == "合成参考" and "SHORT_ANSWER_NOT_GRADED" in result["transformations"]
    assert result["input"] == data


@requires_node
@pytest.mark.parametrize("question", [
    {"type": "single", "question": "Q", "options": ["A", "B"]},
    {"type": "single", "question": "Q", "options": ["A", "B"], "answer": "Z"},
    {"type": "single", "question": "Q", "options": [{"value": "A", "label": "x"}, {"value": "A", "label": "y"}], "answer": "A"},
])
def test_upstream_choice_contract_failure_returns_null_without_candidate(question):
    data = frame({"kind": "synthetic_response", "value": json.dumps([question])})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UPSTREAM_FAILURE"
    assert result["failures"] == ["invalid-model-output"] and result["data"] is None
    assert result["input"] == data


@requires_node
def test_synthetic_error_and_invalid_json_are_failures():
    data = frame({"kind": "synthetic_error"})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UPSTREAM_FAILURE"
    assert len(result["calls"]) == 1 and result["input"] == data
    invalid = frame({"kind": "synthetic_response", "value": "no JSON present"})
    code, result = invoke(invalid)
    assert code == 2 and result["status"] == "UPSTREAM_FAILURE"
    assert result["failures"] == ["invalid-model-output"] and result["input"] == invalid


@requires_node
def test_upstream_jsonrepair_recovery_is_quarantined_with_original_reply():
    malformed = '[{"id":"q1","type":"single","question":"Q","options":["a","b"],"answer":"A",}]'
    data = frame({"kind": "synthetic_response", "value": malformed})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UPSTREAM_RECOVERY_NOT_ADMITTED"
    assert result["upstream_reported_success"] is True and result["data"] is None
    assert result["input"] == data


@requires_node
@pytest.mark.parametrize("question", [
    {"type": "future", "question": "Q", "options": ["A"], "answer": "A"},
    {"type": "single", "question": "Q", "options": ["A"], "answer": "A", "media": {"url": "file://x"}},
    {"type": "single", "question": "Q", "options": ["A"], "answer": "A", "actions": [{"type": "run"}]},
    {"type": "single", "question": "Q", "options": ["A"], "answer": "A", "correctAnswer": "B"},
    {"type": "short_answer", "question": "Q", "answer": "do not discard"},
])
def test_unknown_media_actions_or_lossy_fields_are_refused(question):
    data = frame({"kind": "synthetic_response", "value": json.dumps([question])})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "UNSUPPORTED_OUTPUT"
    assert result["data"] is None and result["input"] == data


@requires_node
def test_ambiguous_duplicate_keys_invalid_outline_and_oversize_are_refused():
    duplicate = '[{"type":"single","question":"Q","quest\\u0069on":"other","options":["A"],"answer":"A"}]'
    data = frame({"kind": "synthetic_response", "value": duplicate})
    code, result = invoke(data)
    assert code == 2 and result["status"] == "INVALID_RESPONSE" and result["input"] == data
    invalid = frame()
    invalid["outline"]["actions"] = [{"type": "run"}]
    assert invoke(invalid)[1]["status"] == "INVALID_REQUEST"
    assert invoke(b" " * 256_001)[1]["status"] == "INVALID_REQUEST"
    duplicated = json.dumps(frame()).replace('"request_id": "request_1"', '"request_id": "request_1", "request_\\u0069d": "other"').encode()
    assert invoke(duplicated)[1]["status"] == "INVALID_REQUEST"


@requires_node
@pytest.mark.parametrize("relative,reason", [
    ("vendor/generation-0.3.28-quiz/ORIGINALS.json", b"QUIZ_MANIFEST_IDENTITY_MISMATCH"),
    ("vendor/generation-0.3.28-quiz/quiz-functions.ts", b"QUIZ_ADAPTER_IDENTITY_MISMATCH"),
    ("vendor/generation-0.3.28-quiz/src/scene-generator.ts", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("vendor/generation-0.3.28-quiz/templates/quiz-content/system.md", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("vendor/generation-0.3.28-quiz/snippets/json-output-rules.md", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("vendor/generation-0.3.28-outline/src/prompts/loader.ts", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("vendor/npm/nanoid-5.1.14/index.js", b"LOCKED_NPM_MEMBER_IDENTITY_MISMATCH"),
    ("vendor/npm/jsonrepair-3.13.3/lib/esm/regular/jsonrepair.js", b"LOCKED_NPM_MEMBER_IDENTITY_MISMATCH"),
])
def test_changed_dependency_is_rejected_before_replay(tmp_path, relative, reason):
    assert NODE and Path(NODE).is_absolute()
    copy = tmp_path / "worker-copy"
    copy.mkdir()
    shutil.copy2(WORKER, copy / WORKER.name)
    for member in ["generation-0.3.28-quiz", "generation-0.3.28-outline", "npm"]:
        shutil.copytree(WORKER.parent / "vendor" / member, copy / "vendor" / member)
    changed = copy / relative
    changed.write_bytes(changed.read_bytes() + b"\n// changed\n")
    process = subprocess.run([NODE, str(copy / WORKER.name), "--hello"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=10, check=False)
    assert process.returncode != 0 and process.stdout == b""
    assert reason in process.stderr


@requires_node
def test_prompt_capture_and_exact_replay_use_actual_upstream_excerpt():
    request, binding = capture_prompt()
    assert binding["schema"] == "archeaxis.openmaic-quiz-prompt-binding/v1"
    assert binding["request_id"] == request["request_id"]
    assert binding["outline_manifest_sha256"] == sha((OUTLINE / "ORIGINALS.json").read_bytes())
    assert binding["quiz_manifest_sha256"] == sha((QUIZ / "ORIGINALS.json").read_bytes())
    assert binding["quiz_excerpt_sha256"] == sha((QUIZ / "quiz-functions.ts").read_bytes())
    assert binding["worker_sha256"] == sha(WORKER.read_bytes())
    assert binding["guard_sha256"] == sha((WORKER.parent / "outline-prompt-guard.mjs").read_bytes())
    assert request["outline"]["title"] in binding["user"]
    assert binding["system_sha256"] == sha(binding["system"].encode())
    assert binding["user_sha256"] == sha(binding["user"].encode())
    code, result = invoke(replay_frame(request, binding))
    assert code == 0 and result["status"] == "CANDIDATE" and result["callback_count"] == 1, result
    assert "input" not in result and result["request_id"] == request["request_id"]
    assert result["data"]["questions"][0]["answer"] == ["B"]
    assert result["model_call"] == "NOT_INVOKED" and result["network_performed"] is False
    assert result["response_origin"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert result["core_task"] == "NOT_CONNECTED" and result["core_authorization"] == "NOT_ESTABLISHED"
    assert result["canonical_bindings_verified"] is False and result["persisted"] is False
    assert result["binding_authentication"] == "NOT_PROVIDED" and result["identity_scope"] == "UNKEYED_COMPARISON_ONLY"
    assert result["source_snapshot_authority"] == "CALLER_DECLARED_ONLY"
    assert result["output_privacy_filter"] == "NOT_APPLIED" and result["logging_safety"] == "NOT_ESTABLISHED"
    assert result["file_identity_scope"] == "CHECKED_NOT_HELD_TOCTOU_UNRESOLVED"


@requires_node
@pytest.mark.parametrize("field", ["input_sha256", "outline_manifest_sha256", "quiz_manifest_sha256",
                                   "quiz_excerpt_sha256", "npm_members_sha256", "worker_sha256", "guard_sha256"])
def test_changed_prompt_input_or_member_binding_is_rejected_without_reflection(field):
    request, binding = capture_prompt()
    binding[field] = "0" * 64
    binding["system"] += "SYN_PROMPT_SENTINEL"
    replay = replay_frame(request, binding, "SYN_REPLY_SENTINEL")
    code, result = invoke(replay)
    assert code == 2 and result["status"] == "BINDING_MISMATCH"
    assert "input" not in result
    serialized = json.dumps(result, ensure_ascii=False)
    assert "SYN_PROMPT_SENTINEL" not in serialized and "SYN_REPLY_SENTINEL" not in serialized


@requires_node
@pytest.mark.parametrize("field", ["system", "user"])
def test_changed_prompt_with_recomputed_digest_fails_upstream_comparison(field):
    request, binding = capture_prompt()
    binding[field] += "tampered"
    binding[field + "_sha256"] = sha(binding[field].encode())
    code, result = invoke(replay_frame(request, binding))
    assert code == 2 and result["status"] == "CALLBACK_REJECTED"
    assert result["reason"] == "PROMPT_MISMATCH" and result["data"] is None


@requires_node
@pytest.mark.parametrize("change", ["request_id", "language_directive", "outline_title", "outline_points"])
def test_different_input_cannot_use_unchanged_binding(change):
    request, binding = capture_prompt()
    request = json.loads(json.dumps(request, ensure_ascii=False))
    if change == "request_id":
        request["request_id"] += "_other"
    elif change == "language_directive":
        request["language_directive"] += "other"
    elif change == "outline_title":
        request["outline"]["title"] += "other"
    else:
        request["outline"]["keyPoints"].append("other")
    code, result = invoke(replay_frame(request, binding))
    assert code == 2 and result["status"] == "BINDING_MISMATCH" and result["data"] is None


@requires_node
def test_distinct_outline_points_can_produce_same_prompt_unkeyed_hash_is_not_authentication():
    request = capture_frame()
    request["outline"]["keyPoints"] = ["first\n2. second"]
    code, captured = invoke(request)
    assert code == 0 and captured["status"] == "PROMPT_CAPTURED"
    altered = json.loads(json.dumps(request, ensure_ascii=False))
    altered["outline"]["keyPoints"] = ["first", "second"]
    binding = captured["binding"]
    identity = json.dumps({"request_id": altered["request_id"], "outline": altered["outline"],
                           "language_directive": altered["language_directive"]},
                          ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    binding["input_sha256"] = sha(identity.encode())
    code, result = invoke(replay_frame(altered, binding))
    assert code == 0 and result["status"] == "CANDIDATE"
    assert result["binding_authentication"] == "NOT_PROVIDED"
    assert result["source_snapshot_authority"] == "CALLER_DECLARED_ONLY"
    assert result["core_task"] == "NOT_CONNECTED" and result["core_authorization"] == "NOT_ESTABLISHED"


@requires_node
@pytest.mark.parametrize("stage", ["capture", "replay"])
def test_invalid_prompt_request_does_not_reflect_unknown_or_nested_sentinels(stage):
    request, binding = capture_prompt()
    sentinels = ["SYN_ID_93", "SYN_TITLE_93", "SYN_UNKNOWN_93", "SYN_PROMPT_93", "SYN_REPLY_93"]
    request["request_id"] = sentinels[0]
    request["outline"]["title"] = sentinels[1]
    request["unknown"] = {"nested": sentinels[2]}
    if stage == "replay":
        binding["system"] = sentinels[3]
        request = replay_frame(request, binding, sentinels[4])
    code, result = invoke(request)
    assert code == 2 and result["status"] == "INVALID_REQUEST"
    assert "input" not in result and result["request_id"] is None and result["stage"] is None
    serialized = json.dumps(result, ensure_ascii=False)
    assert all(sentinel not in serialized for sentinel in sentinels)


@requires_node
def test_duplicate_frame_invalid_reply_and_extra_images_fail_without_request_echo():
    request, binding = capture_prompt()
    duplicate_frame = json.dumps(request).replace('"request_id": "quiz_prompt_1"',
        '"request_id": "SYN_DUPLICATE", "request_\\u0069d": "other"').encode()
    code, invalid = invoke(duplicate_frame)
    assert code == 2 and invalid["status"] == "INVALID_REQUEST"
    assert "input_raw_base64" not in invalid and "SYN_DUPLICATE" not in json.dumps(invalid)
    with_images = {**request, "images": [{"id": "SYN_IMAGE"}]}
    assert invoke(with_images)[1]["status"] == "INVALID_REQUEST"
    duplicate_reply = '[{"type":"single","question":"Q","quest\\u0069on":"other","options":["a","b"],"answer":"A"}]'
    code, invalid = invoke(replay_frame(request, binding, duplicate_reply))
    assert code == 2 and invalid["status"] == "INVALID_RESPONSE" and invalid["data"] is None
    nonfinite = '[{"type":"single","question":"Q","options":["a","b"],"answer":"A","points":1e9999}]'
    assert invoke(replay_frame(request, binding, nonfinite))[1]["status"] == "INVALID_RESPONSE"


@requires_node
def test_guard_rejects_multiple_callbacks_and_nonempty_images():
    guard = (WORKER.parent / "outline-prompt-guard.mjs").as_uri()
    source = '''
const {createPromptGuard}=await import(process.argv[1]);
const a=createPromptGuard(null,()=>"ok"); await a.callback("system","user",undefined);
try { await a.callback("system","user",undefined); } catch {}
const b=createPromptGuard(null,()=>"ok");
try { await b.callback("system","user",[{id:"image"}]); } catch {}
process.stdout.write(JSON.stringify({extra:a.state,images:b.state}));
'''
    process = subprocess.run([NODE, "--input-type=module", "-e", source, guard], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=10, check=False, env=child_env())
    assert process.returncode == 0, process.stderr.decode("utf-8", "replace")
    states = json.loads(process.stdout.decode("utf-8"))
    assert states["extra"]["calls"] == 2 and states["extra"]["failure"] == "MULTIPLE_CALLBACKS"
    assert states["images"]["calls"] == 1 and states["images"]["failure"] == "IMAGES_UNSUPPORTED"


@requires_node
def test_changed_prompt_guard_is_rejected_before_any_prompt(tmp_path):
    assert NODE and Path(NODE).is_absolute()
    copy = tmp_path / "worker-copy"
    copy.mkdir()
    shutil.copy2(WORKER, copy / WORKER.name)
    shutil.copy2(WORKER.parent / "outline-prompt-guard.mjs", copy / "outline-prompt-guard.mjs")
    for member in ["generation-0.3.28-quiz", "generation-0.3.28-outline", "npm"]:
        shutil.copytree(WORKER.parent / "vendor" / member, copy / "vendor" / member)
    guard = copy / "outline-prompt-guard.mjs"
    guard.write_bytes(guard.read_bytes() + b"\n// changed\n")
    process = subprocess.run([NODE, str(copy / WORKER.name), "--hello"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=20, check=False, env=child_env())
    assert process.returncode != 0 and process.stdout == b""
    assert b"QUIZ_GUARD_IDENTITY_MISMATCH" in process.stderr


@requires_node
def test_repaired_response_is_quarantined_with_original_and_upstream_observation():
    request, binding = capture_prompt()
    malformed = '[{"id":"q1","type":"single","question":"Q","options":["a","b"],"answer":"A",}]'
    code, result = invoke(replay_frame(request, binding, malformed))
    assert code == 2 and result["status"] == "UPSTREAM_RECOVERY_NOT_ADMITTED" and result["data"] is None
    assert result["original_reply"] == malformed and result["observed_upstream"]["questions"][0]["id"] == "q1"
    assert result["differences"] == [{"kind": "JSON_REPAIR_NOT_ADMITTED"}]
    assert result["output_privacy_filter"] == "NOT_APPLIED"


@requires_node
@pytest.mark.parametrize("question,kind", [
    ({"id": "q1", "type": "single", "question": "Q", "options": ["B", "A"], "answer": "A"}, "ANSWER_NOT_UNIQUE"),
    ({"id": "q1", "type": "single", "question": "Q", "options": [
        {"value": "A", "label": "Blue", "text": "Red"}, "Green"], "answer": "A"}, "OPTION_TEXT_DISCARDED"),
])
def test_prompt_replay_quarantines_answer_ambiguity_and_discarded_option_text(question, kind):
    request, binding = capture_prompt()
    original = json.dumps([question], ensure_ascii=False)
    code, result = invoke(replay_frame(request, binding, original))
    assert code == 2 and result["status"] == "UPSTREAM_RESULT_NOT_ADMITTED" and result["data"] is None
    assert result["original_reply"] == original and result["observed_upstream"]["questions"][0]["id"] == "q1"
    assert kind in {item["kind"] for item in result["differences"]}


@requires_node
def test_unknown_question_field_and_duplicate_question_ids_are_not_candidates():
    request, binding = capture_prompt()
    question = {"id": "q1", "type": "single", "question": "Q", "options": ["a", "b"], "answer": "A"}
    unknown = json.dumps([{**question, "unknown": "SYN_UNKNOWN_REPLY"}])
    code, rejected = invoke(replay_frame(request, binding, unknown))
    assert code == 2 and rejected["status"] == "UNSUPPORTED_OUTPUT"
    assert "SYN_UNKNOWN_REPLY" not in json.dumps(rejected)
    duplicates = json.dumps([question, {**question, "question": "Second"}])
    code, result = invoke(replay_frame(request, binding, duplicates))
    assert code == 2 and result["status"] == "UPSTREAM_RESULT_NOT_ADMITTED"
    assert "DUPLICATE_QUESTION_ID" in {item["kind"] for item in result["differences"]}
    assert result["original_reply"] == duplicates


@requires_node
def test_legacy_replay_duplicate_question_ids_are_quarantined_and_unique_ids_remain_candidates():
    first = {"id": "q1", "type": "single", "question": "First", "options": ["a", "b"], "answer": "A"}
    second = {"id": "q1", "type": "single", "question": "Second", "options": ["c", "d"], "answer": "B"}
    duplicate_request = frame({"kind": "synthetic_response", "value": json.dumps([first, second])})
    code, duplicate = invoke(duplicate_request)
    assert code == 2 and duplicate["status"] == "UPSTREAM_RESULT_NOT_ADMITTED" and duplicate["data"] is None
    assert duplicate["input"] == duplicate_request
    assert [q["id"] for q in duplicate["observed_upstream"]["questions"]] == ["q1", "q1"]
    assert {"kind": "DUPLICATE_QUESTION_ID", "question_index": 1,
            "first_question_index": 0, "id": "q1"} in duplicate["differences"]
    assert duplicate["response_origin_verification"] == "CALLER_DECLARED_UNVERIFIED"
    assert duplicate["returned_content_may_include_material_or_answers"] is True
    assert duplicate["output_privacy_filter"] == "NOT_APPLIED" and duplicate["logging_safety"] == "NOT_ESTABLISHED"

    unique_request = frame({"kind": "synthetic_response", "value": json.dumps([first, {**second, "id": "q2"}])})
    code, unique = invoke(unique_request)
    assert code == 0 and unique["status"] == "CANDIDATE" and unique["input"] == unique_request
    assert [q["id"] for q in unique["data"]["questions"]] == ["q1", "q2"]
    assert [q["answer"] for q in unique["data"]["questions"]] == [["A"], ["B"]]
    assert unique["response_origin_verification"] == "CALLER_DECLARED_UNVERIFIED"
    assert unique["returned_content_may_include_material_or_answers"] is True
    assert unique["output_privacy_filter"] == "NOT_APPLIED" and unique["logging_safety"] == "NOT_ESTABLISHED"


@requires_node
@pytest.mark.parametrize("question,alias,answer", [
    ({"id": "q1", "type": "single", "question": "One?", "options": ["red", "blue"],
      "correctAnswer": ["B"]}, "correctAnswer", ["B"]),
    ({"id": "q2", "type": "multiple", "question": "Two?", "options": ["red", "blue", "green"],
      "correct_answer": ["A", "C"]}, "correct_answer", ["A", "C"]),
])
def test_prompt_replay_preserves_equivalent_array_answer_aliases_by_value(question, alias, answer):
    request, binding = capture_prompt()
    code, result = invoke(replay_frame(request, binding, json.dumps([question])))
    assert code == 0 and result["status"] == "CANDIDATE", result
    actual = result["data"]["questions"][0]
    assert actual[alias] == answer and actual["answer"] == answer
    assert "QUESTION_FIELD_CHANGED" not in {item.get("kind") for item in result.get("differences", [])}


@requires_node
def test_legacy_success_keeps_input_identity_but_unparseable_frames_do_not_echo_bytes():
    request = frame()
    original = json.dumps(request, ensure_ascii=False).encode("utf-8")
    code, valid = invoke(original)
    assert code == 0 and valid["schema"] == "archeaxis.openmaic-quiz-replay-result/v1"
    assert valid["status"] == "CANDIDATE" and valid["input"] == request
    assert valid["input_sha256"] == sha(original)

    malformed = b'{"schema":"archeaxis.openmaic-quiz-replay/v1","unknown":"SYN_PRIVATE_BYTES"'
    duplicate = (b'{"schema":"archeaxis.openmaic-quiz-replay/v1",'
                 b'"schema":"SYN_DUPLICATE_BYTES"}')
    for caller_owned_input in (malformed, duplicate):
        saved_by_caller = bytes(caller_owned_input)
        code, rejected = invoke(caller_owned_input)
        assert code == 2 and rejected["status"] == "INVALID_REQUEST"
        assert rejected["input"] is None and "input_raw_base64" not in rejected and "input_sha256" not in rejected
        serialized = json.dumps(rejected, ensure_ascii=False)
        assert "SYN_PRIVATE_BYTES" not in serialized and "SYN_DUPLICATE_BYTES" not in serialized
        assert caller_owned_input == saved_by_caller  # only this caller's in-memory copy is retained
