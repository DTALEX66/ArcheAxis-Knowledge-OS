"""Synthetic private candidate preparation, without a Core or model process."""
import asyncio
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services/learning-providers/deeptutor"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, PROVIDER / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load("deeptutor_candidate_document_test", "candidate_document.py")
turn = load("deeptutor_candidate_turn_test", "question_turn_worker.py")
MATERIAL = {"document_id": "selected_material", "version": 3, "content_sha256": "1" * 64}


def capture(kind="choice", language="en"):
    request = {"schema": turn.SCHEMA, "request_id": "synthetic_turn_1", "mode": "capture", "language": language,
               "plan": {"analysis": "Synthetic plan", "templates": [{"question_id": "q_1", "topic": "Synthetic topic",
                   "question_type": kind, "difficulty": "easy", "source": "custom",
                   "reference_question": "", "reference_answer": ""}]},
               "question_number": 1, "exploration_trace": "Synthetic context", "previous_questions": []}
    observed = turn.process(request)
    assert observed["status"] == "CAPTURED"
    request["mode"] = "replay"
    request["expected_prompt_sha256"] = observed["prompt_sha256"]
    return request


def choice(answer="B"):
    return {"question_type": "choice", "question": "  Synthetic question?  ",
            "options": {"A": "one", "B": "  two  ", "C": "three", "D": "four"},
            "correct_answer": answer, "explanation": "  Synthetic explanation  "}


def arguments(payload=None, *, kind="choice", language="en"):
    raw = json.dumps(payload if payload is not None else choice(), ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    request = capture(kind, language)
    request["response_body"] = raw.decode("utf-8")
    return request, raw, copy.deepcopy(MATERIAL), "document_request_1", "Synthetic candidate"


def import_receipt(raw):
    return {"source_id": "caller_declared_source", "sha256": hashlib.sha256(raw).hexdigest(), "duplicate": False}


def document(prepared, raw):
    return prepared.document_create_request(import_receipt(raw))


def body_text(editor):
    assert all(node["type"] == "paragraph" and len(node["content"]) == 1
               and node["content"][0]["type"] == "text" for node in editor["content"])
    return [node["content"][0]["text"] for node in editor["content"]]


def assert_reason(code, function, *args):
    with pytest.raises(adapter.CandidateError) as failure:
        function(*args)
    assert str(failure.value) == code


def test_private_candidate_binds_original_pair_and_builds_existing_core_request(capsys):
    args = arguments()
    prepared = adapter.prepare_candidate(*args)
    raw = args[1]
    assert prepared.original_response_bytes() == raw
    assert base64.b64decode(prepared.raw_import_request()["content_base64"], validate=True) == raw
    request = document(prepared, raw)
    assert set(request) == {"create_request_id", "source_id", "source_revision", "title", "editor_json"}
    assert request["create_request_id"] == "document_request_1"
    assert request["source_id"] == "caller_declared_source"
    assert request["source_revision"] == hashlib.sha256(raw).hexdigest()
    candidate = request["editor_json"]["attrs"]["archeaxis_deeptutor_question"]
    assert candidate["schema"] == "archeaxis.deeptutor-question/v1"
    assert candidate["source_material"] == MATERIAL
    assert candidate["origin"] == "user_import_unverified"
    assert candidate["question"] == {"question_id": "q_1", "question": "Synthetic question?",
        "question_type": "choice", "options": {"A": "one", "B": "two", "C": "three", "D": "four"},
        "correct_answer": "B", "explanation": "Synthetic explanation"}
    assert body_text(request["editor_json"]) == ["Synthetic question?", "A. one", "B. two", "C. three", "D. four"]
    report = prepared.report()
    assert report["original_response_bytes"] == "IN_MEMORY_ONLY"
    assert report["original_replay_envelope_bytes"] == "NOT_SUPPLIED"
    assert report["core_source_import"] == report["core_document_write"] == "NOT_EXECUTED"
    assert report["material_snapshot"] == "CALLER_DECLARED_UNVERIFIED"
    assert report["provider_generation"] == report["core_authorization"] == "NOT_ESTABLISHED"
    assert report["unmapped_response_fields"] == []
    assert report["replay_context_in_document"] == "NOT_PRESERVED"
    assert report["body_attrs_consistency"] == "NOT_CONTINUOUSLY_ENFORCED_BY_CORE"
    assert report["source_and_document_calls"] == "SEPARATE_DOCUMENT_FAILURE_MAY_LEAVE_SOURCE"
    assert {entry["field"] for entry in report["changes"]} == {"question", "options.B", "explanation"}
    assert report["grading"] == "NOT_ASSESSED"
    assert "Synthetic question" not in repr(prepared)
    assert "Synthetic explanation" not in json.dumps(report)
    assert capsys.readouterr() == ("", "")


def test_mutating_caller_inputs_or_returned_requests_does_not_change_prepared_candidate():
    args = arguments()
    prepared = adapter.prepare_candidate(*args)
    raw = args[1]
    args[0]["response_body"] = "changed"
    args[2]["document_id"] = "changed"
    first = document(prepared, raw)
    first["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["correct_answer"] = "changed"
    second = document(prepared, raw)
    assert second["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["source_material"] == MATERIAL
    assert second["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["correct_answer"] == "B"
    with pytest.raises(AttributeError):
        prepared._candidate_json = "{}"
    assert_reason("CANDIDATE_NOT_PREPARED", adapter.PrivateCandidate, b"{}", {}, {}, "id", "title", {})


def test_mutated_returned_body_is_not_evidence_of_a_verified_core_binding():
    args = arguments()
    prepared = adapter.prepare_candidate(*args)
    request = document(prepared, args[1])
    initial_source_revision = request["source_revision"]
    request["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["correct_answer"] = "C"
    request["editor_json"]["content"][0]["content"][0]["text"] = "Changed synthetic question"
    assert request["source_revision"] == initial_source_revision
    assert request != document(prepared, args[1])
    assert prepared.report()["request_binding"] == "AT_CONSTRUCTION_ONLY_MUTABLE_AFTER_RETURN_NOT_VERIFIED_BY_CORE"
    assert prepared.report()["core_document_write"] == "NOT_EXECUTED"


def test_answer_only_changed_bytes_cannot_be_spliced_into_same_visible_turn(capsys):
    args = arguments(choice("B"))
    changed = json.dumps(choice("C"), ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    assert_reason("RESPONSE_BYTES_MISMATCH", adapter.prepare_candidate, args[0], changed, *args[2:])
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("field", ["question", "options", "correct_answer", "explanation", "question_type"])
def test_full_upstream_pair_and_independently_normalized_fields_must_match(field, monkeypatch):
    original = adapter._normalizer

    def mismatching(turn_namespace):
        namespace = original(turn_namespace)
        selected = namespace["_candidate"]

        def change(value):
            result = selected(value)
            candidate = result["candidate"]
            if field == "options":
                candidate[field]["B"] = "different"
            else:
                candidate[field] = "different"
            return result

        namespace["_candidate"] = change
        return namespace

    monkeypatch.setattr(adapter, "_normalizer", mismatching)
    assert_reason("NORMALIZATION_MISMATCH", adapter.prepare_candidate, *arguments())


@pytest.mark.parametrize("kind,question,answer", [
    ("concept", "Synthetic proposition?", "true"),
    ("fill_in_blank", "Synthetic answer is ____.", "two"),
    ("short_answer", "Explain the synthetic example.", "A synthetic reference"),
    ("written", "Discuss the synthetic example.", "A longer synthetic reference"),
    ("coding", "Write a synthetic function.", "return 2"),
])
@pytest.mark.parametrize("include_null", [False, True])
def test_nonchoice_null_to_empty_is_reported_and_not_claimed_as_graded(kind, question, answer, include_null):
    payload = {"question_type": kind, "question": question, "correct_answer": answer, "explanation": "Synthetic explanation"}
    if include_null:
        payload["options"] = None
    args = arguments(payload, kind=kind)
    prepared = adapter.prepare_candidate(*args)
    candidate = document(prepared, args[1])["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]
    assert candidate["options"] == {}
    assert body_text(document(prepared, args[1])["editor_json"]) == [candidate["question"]]
    changes = prepared.report()["changes"]
    assert {"field": "options", "change": "null_to_empty_object_for_core"} in changes
    assert ({"field": "options", "change": "absent_to_null"} in changes) is (not include_null)
    assert prepared.report()["grading"] == "UNASSESSED_EMPTY_OPTIONS_UNGRADED"


@pytest.mark.parametrize("language", ["en", "zh"])
def test_body_projection_uses_same_multilingual_question_and_key_order(language):
    payload = {"question_type": "choice", "question": "  合成题 😀?  ",
               "options": {"D": "四", "B": "二", "A": "一", "C": "三"},
               "correct_answer": "B", "explanation": "合成解释"}
    args = arguments(payload, language=language)
    prepared = adapter.prepare_candidate(*args)
    request = document(prepared, args[1])
    candidate = request["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]
    assert candidate["question"] == "合成题 😀?"
    assert body_text(request["editor_json"]) == [candidate["question"], *[
        f"{key}. {candidate['options'][key]}" for key in ("A", "B", "C", "D")]]
    assert {"field": "options", "change": "body_projection_sorted_by_key"} in prepared.report()["changes"]
    assert "合成解释" not in json.dumps(request["editor_json"]["content"], ensure_ascii=False)


def test_actual_original_grader_returns_null_for_synthetic_nonchoice_candidate(tmp_path):
    payload = {"question_type": "concept", "question": "Synthetic proposition?", "correct_answer": "true",
               "explanation": "Synthetic explanation"}
    args = arguments(payload, kind="concept")
    candidate = document(adapter.prepare_candidate(*args), args[1])["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]
    data = {"schema": "archeaxis.deeptutor-practice-grade/v1", "request_id": "synthetic_grade_1",
            "question": {key: candidate[key] for key in ("question_type", "options", "correct_answer")},
            "answer": "true"}
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8") + b"\n"
    # No user data or inherited application credentials are supplied to the child.
    env = {key: str(tmp_path) for key in ("HOME", "USERPROFILE", "TEMP", "TMP", "TMPDIR", "APPDATA", "LOCALAPPDATA")}
    if sys.platform == "win32":
        env["SystemRoot"] = os.environ["SystemRoot"]
    result = subprocess.run([sys.executable, "-I", "-B", "-S", str(PROVIDER / "grade_worker.py")],
                            input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, timeout=20, check=False)
    assert result.returncode == 0 and result.stderr == b""
    receipt = json.loads(result.stdout)
    assert receipt["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["provider_correct"] is None
    assert receipt["question_binding"] == "caller_declared_unverified"


def test_supplied_import_receipt_is_only_a_claim_and_sha_mismatch_is_rejected():
    args = arguments()
    prepared = adapter.prepare_candidate(*args)
    claimed = import_receipt(args[1])
    claimed["source_id"] = "synthetic_nonexistent_id"
    request = prepared.document_create_request(claimed)
    assert request["source_id"] == "synthetic_nonexistent_id"
    assert prepared.report()["core_source_import"] == "NOT_EXECUTED"
    claimed["sha256"] = "0" * 64
    assert_reason("INVALID_IMPORT_RECEIPT", prepared.document_create_request, claimed)
    claimed = import_receipt(args[1])
    claimed["source_id"] = "\ud800"
    assert_reason("INVALID_IMPORT_RECEIPT", prepared.document_create_request, claimed)


@pytest.mark.parametrize("raw", [
    b'{"question_type":"choice","question":"Q","question":"Q2","correct_answer":"A","explanation":"E","options":{"A":"a","B":"b","C":"c","D":"d"}}',
    b'{"question_type":"choice","question":"Q","correct_answer":"A","explanation":"E","options":{"A":"a","B":"b","C":"c","D":"d"},"extra":"SYNTHETIC_PRIVATE_MARKER"}',
    b'{"question_type":"choice","question":"Q","correct_answer":"A","explanation":"E","options":{"A":"a","B":"b","C":"c","D":NaN}}',
])
def test_strict_turn_rejects_duplicate_unknown_and_nonfinite_response_without_echo(raw, capsys):
    request = capture()
    request["response_body"] = raw.decode("utf-8")
    assert_reason("TURN_UNAVAILABLE_OR_REJECTED", adapter.prepare_candidate, request, raw, MATERIAL,
                  "document_request_1", "Synthetic candidate")
    assert capsys.readouterr() == ("", "")


def test_invalid_snapshot_prompt_and_identity_fail_closed():
    args = arguments()
    for invalid in [0, -1, 9_007_199_254_740_992, True]:
        material = {**MATERIAL, "version": invalid}
        assert_reason("INVALID_MATERIAL_SNAPSHOT", adapter.prepare_candidate, args[0], args[1], material, *args[3:])
    altered = copy.deepcopy(args[0])
    altered["plan"]["templates"][0]["topic"] = "Different synthetic topic"
    assert_reason("TURN_UNAVAILABLE_OR_REJECTED", adapter.prepare_candidate, altered, *args[1:])
    assert_reason("INVALID_INPUT", adapter.prepare_candidate, args[0], args[1], args[2], "invalid id", args[4])


def test_running_event_loop_is_rejected_without_constructing_coroutine():
    args = arguments()

    async def inside_running_loop():
        assert_reason("ACTIVE_EVENT_LOOP_UNSUPPORTED", adapter.prepare_candidate, *args)

    asyncio.run(inside_running_loop())


def test_tampered_pinned_turn_is_rejected_before_execution(tmp_path, monkeypatch):
    source = (PROVIDER / "question_turn_worker.py").read_bytes()
    altered = bytes([source[0] ^ 1]) + source[1:]
    target = tmp_path / "question_turn_worker.py"
    target.write_bytes(altered)
    monkeypatch.setattr(adapter, "_ROOT", tmp_path)
    assert_reason("SOURCE_UNAVAILABLE", adapter._read_turn)


def test_each_concurrent_preparation_owns_its_capture_namespace():
    first = arguments(choice("A"))
    second = arguments(choice("B"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(adapter.prepare_candidate, *args) for args in (first, second)]
        prepared = [future.result(timeout=20) for future in futures]
    questions = [document(item, args[1])["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]
                 for item, args in zip(prepared, (first, second))]
    assert questions[0]["correct_answer"] == "A"
    assert questions[1]["correct_answer"] == "B"
    assert questions[0]["question"] == questions[1]["question"]


def recovered_arguments(payload=None, *, kind="choice", language="en"):
    request, body, material, create_id, title = arguments(payload, kind=kind, language=language)
    return request, b"``FINISH\n" + body, material, create_id, title


def prepare_recovered(args, **overrides):
    declaration = {"completed": True, "finish_reason": "stop", "tool_calls": [],
                   "function_call": None, "allow_recovery": True}
    declaration.update(overrides)
    return adapter.prepare_recovered_candidate(*args, **declaration)


def test_recovered_candidate_imports_complete_labeled_bytes_using_real_receipt_shape(capsys):
    args = recovered_arguments()
    prepared = prepare_recovered(args)
    raw = args[1]
    body = args[0]["response_body"].encode("utf-8")
    imported = prepared.raw_import_request()
    assert imported["name"] == "deeptutor-question-response.txt"
    assert base64.b64decode(imported["content_base64"], validate=True) == raw
    assert prepared.original_response_bytes() == raw
    # The test receipt is synthetic; production passes the response actually
    # received from Core. The labeled source digest must not be replaced by the
    # digest of the body used by the independent replay.
    receipt = import_receipt(raw)
    created = prepared.document_create_request(receipt)
    assert created["source_revision"] == hashlib.sha256(raw).hexdigest()
    assert created["source_revision"] != hashlib.sha256(body).hexdigest()
    assert_reason("INVALID_IMPORT_RECEIPT", prepared.document_create_request, import_receipt(body))
    plain = adapter.prepare_candidate(args[0], body, *args[2:])
    assert plain.raw_import_request()["name"] == "deeptutor-question-response.json"
    assert plain.private_recovery_receipt() is None
    assert created["editor_json"] == document(plain, body)["editor_json"]
    private = prepared.private_recovery_receipt()
    assert base64.b64decode(private["content_base64"], validate=True) == raw
    assert base64.b64decode(private["removed_prefix_base64"], validate=True) == raw[:-len(body)]
    assert private["body_byte_offset"] == len(raw) - len(body)
    assert private["body_sha256"] == hashlib.sha256(body).hexdigest()
    private["private_candidate"]["correct_answer"] = "changed"
    assert prepared.private_recovery_receipt()["private_candidate"]["correct_answer"] == "B"
    report = prepared.report()
    assert report["label_recovery"] == "OPT_IN_UPSTREAM_RESEARCH_HELPER_SUBSET"
    assert report["parser_path"] == "ORIGINAL_MODEL_TEXT_PARSER"
    assert report["completion_and_tools"] == "CALLER_DECLARED_UNVERIFIED"
    assert report["recovery_receipt_persistence"] == "NOT_ESTABLISHED_BY_ADAPTER_OR_CORE"
    assert report["core_source_import"] == report["core_document_write"] == "NOT_EXECUTED"
    assert "Synthetic question" not in repr(prepared) + json.dumps(report)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("override,reason", [
    ({"allow_recovery": False}, "RECOVERY_NOT_ENABLED"),
    ({"allow_recovery": 1}, "RECOVERY_NOT_ENABLED"),
    ({"completed": False}, "INVALID_TERMINAL_DECLARATION"),
    ({"finish_reason": "length"}, "INVALID_TERMINAL_DECLARATION"),
    ({"tool_calls": [{"name": "synthetic"}]}, "INVALID_TERMINAL_DECLARATION"),
    ({"tool_calls": False}, "INVALID_TERMINAL_DECLARATION"),
    ({"function_call": {"name": "synthetic"}}, "INVALID_TERMINAL_DECLARATION"),
])
def test_recovery_requires_opt_in_and_caller_declared_finished_no_tools(override, reason, capsys):
    with pytest.raises(adapter.CandidateError) as failure:
        prepare_recovered(recovered_arguments(), **override)
    assert str(failure.value) == reason
    assert capsys.readouterr() == ("", "")


def test_recovered_path_rejects_strict_label_multiple_labels_and_original_parser_fallback(capsys):
    args = list(recovered_arguments())
    body = args[0]["response_body"].encode("utf-8")
    args[1] = b"``FINISH``\n" + body
    with pytest.raises(adapter.CandidateError, match="^RECOVERY_PATH_UNSUPPORTED$"):
        prepare_recovered(args)
    args[1] = b"``FINISH\n``TOOL``\n" + body
    with pytest.raises(adapter.CandidateError, match="^RECOVERY_UNAVAILABLE_OR_REJECTED$"):
        prepare_recovered(args)
    fenced = choice()
    fenced["question"] = "Synthetic code ```true```?"
    args = recovered_arguments(fenced)
    with pytest.raises(adapter.CandidateError, match="^RECOVERY_UNAVAILABLE_OR_REJECTED$"):
        prepare_recovered(args)
    assert capsys.readouterr() == ("", "")


def test_recovered_body_and_replay_prompt_cannot_be_spliced(capsys):
    args = list(recovered_arguments())
    args[1] = b"``FINISH\n" + json.dumps(choice("C"), ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    with pytest.raises(adapter.CandidateError, match="^RESPONSE_BYTES_MISMATCH$"):
        prepare_recovered(args)
    args = list(recovered_arguments())
    args[0]["plan"]["templates"][0]["topic"] = "Different synthetic topic"
    with pytest.raises(adapter.CandidateError, match="^TURN_UNAVAILABLE_OR_REJECTED$"):
        prepare_recovered(args)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("field", ["question_type", "question", "options", "correct_answer", "explanation"])
def test_recovery_private_candidate_is_independently_compared_with_full_replay(field, monkeypatch):
    load_adapter = adapter._load_adapter

    def altered_adapter(source, name, path):
        namespace = load_adapter(source, name, path)
        if name != "deeptutor_candidate_recovery":
            return namespace
        prepare = namespace["prepare_response"]

        def altered_prepare(*args, **kwargs):
            assert kwargs["allow_parser_fallback"] is False
            real = prepare(*args, **kwargs)

            class AlteredReceipt:
                def __getattr__(self, key):
                    return getattr(real, key)

                def private_receipt(self):
                    receipt = real.private_receipt()
                    receipt["private_candidate"][field] = {"A": "different"} if field == "options" else "different"
                    return receipt

            return AlteredReceipt()

        namespace["prepare_response"] = altered_prepare
        return namespace

    monkeypatch.setattr(adapter, "_load_adapter", altered_adapter)
    with pytest.raises(adapter.CandidateError, match="^RECOVERY_RESULT_MISMATCH$"):
        prepare_recovered(recovered_arguments())


def test_recovered_nonchoice_null_options_are_explicitly_ungraded():
    payload = {"question_type": "concept", "question": "合成命题 😀?", "correct_answer": "true",
               "explanation": "合成解释", "options": None}
    args = recovered_arguments(payload, kind="concept", language="zh")
    prepared = prepare_recovered(args)
    question = document(prepared, args[1])["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]
    assert question["options"] == {}
    assert prepared.private_recovery_receipt()["private_candidate"]["options"] is None
    assert {change["change"] for change in prepared.report()["changes"]} >= {"null_to_empty_object_for_core"}
    assert prepared.report()["grading"] == "UNASSESSED_EMPTY_OPTIONS_UNGRADED"


@pytest.mark.parametrize("missing", [True, False])
def test_recovery_source_missing_or_same_length_tamper_is_rejected(tmp_path, monkeypatch, missing):
    if not missing:
        source = (PROVIDER / "response_recovery.py").read_bytes()
        (tmp_path / "response_recovery.py").write_bytes(bytes([source[0] ^ 1]) + source[1:])
    monkeypatch.setattr(adapter, "_ROOT", tmp_path)
    assert_reason("SOURCE_UNAVAILABLE", adapter._read_pinned, "recovery")

