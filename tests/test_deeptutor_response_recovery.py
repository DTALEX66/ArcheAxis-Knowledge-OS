"""Synthetic, offline controls for the unregistered response-recovery slice.

The fixtures below are caller-authored and do not include either stored model
response.  They do not run a model, access Core, or authenticate a provider.
"""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services/learning-providers/deeptutor"
PATH = PROVIDER / "response_recovery.py"
ARCHIVE = ROOT / ".project-local/archives/owner-inputs/20261101-learning-platform-sources/DeepTutor-1.7.1.zip"
spec = importlib.util.spec_from_file_location("deeptutor_response_recovery_test", PATH)
assert spec is not None and spec.loader is not None
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def question(kind="choice"):
    value = {"question_type": kind, "question": "  Synthetic question?  ",
             "correct_answer": "sample", "explanation": "  Synthetic explanation.  "}
    if kind == "choice":
        value.update(options={"A": " first ", "B": " second ", "C": " third ", "D": " fourth "},
                     correct_answer="B")
    elif kind == "concept":
        value["correct_answer"] = "true"
        value["options"] = None
    elif kind == "fill_in_blank":
        value["question"] = "Complete the synthetic ____ here."
    return value


def body(value=None):
    return json.dumps(value if value is not None else question(), ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def prepare(raw, kind="choice", **overrides):
    args = {"completed": True, "finish_reason": "stop", "tool_calls": [], "function_call": None}
    args.update(overrides)
    return recovery.prepare_response(raw, kind, **args)


def test_owner_archive_source_is_preserved_byte_for_byte():
    archive_digest = hashlib.sha256()
    with ARCHIVE.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            archive_digest.update(chunk)
    assert archive_digest.hexdigest() == "9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262"
    with zipfile.ZipFile(ARCHIVE) as archive:
        original = archive.read("DeepTutor-1.7.1/deeptutor/runtime/agentic/labels.py")
    preserved = (PROVIDER / "upstream/agentic_labels.py").read_bytes()
    assert len(original) == 7_559
    assert hashlib.sha256(original).hexdigest() == recovery.PINS["agentic_labels.py"][2]
    assert preserved == original


def test_default_refuses_recovery_but_strict_final_is_not_rewritten(monkeypatch):
    namespace = recovery._labels()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("recovery helper was called")

    namespace["recover_finished_label"] = forbidden
    monkeypatch.setattr(recovery, "_labels", lambda: namespace)
    raw = b"``FINISH``\n" + body()
    result = prepare(raw)
    assert result.original_bytes() == raw
    assert result.report()["recovery"] == "NOT_NEEDED_STRICT_RAW_UNCHANGED"
    assert result.report()["parser_path"] == "ORIGINAL_MODEL_TEXT_PARSER"
    with pytest.raises(recovery.RecoveryError, match="RECOVERY_DISABLED"):
        prepare(b"``FINISH\n" + body())


@pytest.mark.parametrize("opener,closer,newline", [
    (b"`", b"", b"\n"), (b"``", b"", b"\n"), (b"```", b"", b"\r\n"),
    (b"`", b"``", b"\n"), (b"``", b"`", b"\n"), (b"```", b"``", b"\n"),
])
def test_opt_in_recovery_preserves_exact_private_source_and_delta(opener, closer, newline):
    raw_body = body()
    prefix = opener + b"FINISH" + closer + newline + b"  \t"
    raw = prefix + raw_body
    result = prepare(raw, allow_recovery=True)
    assert result.report()["recovery"] == "OPT_IN_UPSTREAM_RESEARCH_HELPER_SUBSET"
    assert result.report()["strict_label"] == "NONE"
    assert result.original_bytes() == raw
    assert result.removed_prefix_bytes() == prefix
    assert result.body_bytes() == raw_body
    receipt = result.private_receipt()
    assert base64.b64decode(receipt["content_base64"], validate=True) == raw
    assert base64.b64decode(receipt["removed_prefix_base64"], validate=True) == prefix
    assert receipt["body_byte_offset"] == len(prefix)
    assert receipt["content_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["body_sha256"] == hashlib.sha256(raw_body).hexdigest()
    assert receipt["private_candidate"]["question"] == "Synthetic question?"
    assert receipt["private_candidate"]["options"]["B"] == "second"
    assert receipt["private_candidate"]["correct_answer"] == "B"
    assert {item["field"] for item in receipt["normalization_changes"]} >= {"question", "options.B", "explanation"}
    assert receipt["completion_and_tools"] == "CALLER_DECLARED_UNVERIFIED"
    assert receipt["answer_correctness"] == "NOT_VERIFIED"
    assert receipt["original_content"] == "THIS_ADAPTER_DOES_NOT_PERSIST"
    assert receipt["caller_persistence"] == "NOT_ESTABLISHED"
    assert receipt["parser_path"] == "ORIGINAL_MODEL_TEXT_PARSER"
    assert receipt["provider_envelope"] == "NOT_SUPPLIED"


@pytest.mark.parametrize("kind", sorted(recovery.QUESTION_TYPES))
def test_all_existing_question_types_are_validated_without_grading(kind):
    raw = b"``FINISH\n" + body(question(kind))
    result = prepare(raw, kind=kind, allow_recovery=True)
    receipt = result.private_receipt()
    assert receipt["private_candidate"]["question_type"] == kind
    assert receipt["answer_correctness"] == "NOT_VERIFIED"
    assert receipt["independent_mastery"] == "NOT_ESTABLISHED"
    if kind != "choice":
        assert receipt["private_candidate"]["options"] is None


def test_result_and_error_reporting_do_not_expose_private_values():
    marker = "SYNTHETIC_PRIVATE_MARKER"
    q = question()
    q["question"] = marker
    raw = b"``FINISH\n" + body(q)
    result = prepare(raw, allow_recovery=True)
    assert marker not in repr(result)
    assert marker not in json.dumps(result.report())
    assert "content_sha256" not in result.report()
    copy = result.private_receipt()
    copy["private_candidate"]["question"] = "changed"
    assert result.private_receipt()["private_candidate"]["question"] == marker
    with pytest.raises(AttributeError):
        result._raw = b"changed"
    with pytest.raises(recovery.RecoveryError) as error:
        prepare(b"unlabelled " + marker.encode("utf-8"), allow_recovery=True)
    assert marker not in str(error.value)


@pytest.mark.parametrize("fields", [
    {"completed": False}, {"completed": 1}, {"finish_reason": "length"}, {"finish_reason": None},
    {"tool_calls": [{"name": "synthetic"}]}, {"tool_calls": False},
    {"function_call": {"name": "synthetic"}}, {"allow_recovery": 1}, {"allow_parser_fallback": 1},
])
def test_terminal_or_tool_declarations_must_be_explicit_and_valid(fields):
    args = {"allow_recovery": True}
    args.update(fields)
    with pytest.raises(recovery.RecoveryError, match="INVALID_INPUT_OR_TERMINAL"):
        prepare(b"``FINISH\n" + body(), **args)


def test_terminal_and_tool_arguments_cannot_be_silently_omitted():
    raw = b"``FINISH\n" + body()
    with pytest.raises(TypeError):
        recovery.prepare_response(raw, "choice", completed=True, finish_reason="stop", allow_recovery=True)


@pytest.mark.parametrize("prefix", [
    b"preamble\n``FINISH\n", b"``\nFINISH\n", b"``FINISH: \n", b"````FINISH\n",
    b"``FINISH````\n", b"``THINK\n", b"``TOOL\n", b"``FINISH\n- ", b"``FINISH\n: ",
])
def test_unsupported_or_ambiguous_recovery_forms_are_rejected(prefix):
    with pytest.raises(recovery.RecoveryError, match="RECOVERY_FORMAT_UNSUPPORTED"):
        prepare(prefix + body(), allow_recovery=True)


@pytest.mark.parametrize("label", [b"``THINK``\n", b"``TOOL``\n"])
def test_strict_nonfinal_label_is_rejected(label):
    with pytest.raises(recovery.RecoveryError, match="NON_FINAL_LABEL"):
        prepare(label + body(), allow_recovery=True)


def test_multiple_labels_rejected_before_json():
    with pytest.raises(recovery.RecoveryError, match="MULTIPLE_LABELS"):
        prepare(b"``FINISH\n" + body() + b"\n``TOOL``\n", allow_recovery=True)


@pytest.mark.parametrize("invalid", [
    b'{"question_type":"choice","question_type":"choice"}',
    b'{"question_type":NaN}', b'{"question_type":1e999}', b'{"question_type":Infinity}',
    b"{} trailing", b"```json\n{}\n```", b"[]",
])
@pytest.mark.parametrize("allow_parser_fallback", [False, True])
def test_recovered_body_requires_strict_json(invalid, allow_parser_fallback):
    with pytest.raises(recovery.RecoveryError, match="INVALID_JSON"):
        prepare(b"``FINISH\n" + invalid, allow_recovery=True, allow_parser_fallback=allow_parser_fallback)


@pytest.mark.parametrize("alteration", ["missing_answer", "unknown_field", "wrong_type", "ambiguous_options", "placeholder"])
def test_incomplete_or_ambiguous_question_is_rejected(alteration):
    value = question()
    if alteration == "missing_answer":
        value.pop("correct_answer")
    elif alteration == "unknown_field":
        value["tool_calls"] = []
    elif alteration == "wrong_type":
        value["question_type"] = "coding"
    elif alteration == "ambiguous_options":
        value["options"]["B"] = value["options"]["A"].strip()
    else:
        value["explanation"] = "N/A"
    with pytest.raises(recovery.RecoveryError):
        prepare(b"``FINISH\n" + body(value), allow_recovery=True)


@pytest.mark.parametrize("kind", ["choice", "coding"])
def test_original_parser_fenced_text_inside_json_can_reject_valid_question(kind):
    value = question(kind)
    value["question"] = "Synthetic text containing ```true``` inside JSON."
    with pytest.raises(recovery.RecoveryError, match="ORIGINAL_PARSER_MISMATCH"):
        prepare(b"``FINISH\n" + body(value), kind=kind, allow_recovery=True)


@pytest.mark.parametrize("field", ["question", "explanation", "options"])
def test_separate_opt_in_object_fallback_retains_same_content_and_fields(field):
    value = question("choice")
    if field == "options":
        value[field]["B"] = "  Synthetic ```true``` option  "
    else:
        value[field] = "  Synthetic ```true``` text  "
    raw_body = body(value)
    raw = b"``FINISH\n \t" + raw_body
    result = prepare(raw, allow_recovery=True, allow_parser_fallback=True)
    receipt = result.private_receipt()
    assert result.report()["parser_path"] == "OPT_IN_STRICT_OBJECT_NORMALIZATION"
    assert receipt["parser_path"] == "OPT_IN_STRICT_OBJECT_NORMALIZATION"
    assert result.original_bytes() == raw
    assert result.removed_prefix_bytes() + result.body_bytes() == raw
    assert result.body_bytes() == raw_body
    candidate = receipt["private_candidate"]
    assert candidate["question"] == value["question"].strip()
    assert candidate["correct_answer"] == value["correct_answer"].strip()
    assert candidate["explanation"] == value["explanation"].strip()
    assert candidate["options"] == {key: value["options"][key].strip() for key in "ABCD"}


def test_object_fallback_keeps_nonchoice_answer_and_does_not_grade_it():
    value = question("short_answer")
    value["correct_answer"] = "  Synthetic ```true``` answer  "
    result = prepare(b"``FINISH\n" + body(value), kind="short_answer", allow_recovery=True,
                     allow_parser_fallback=True)
    receipt = result.private_receipt()
    assert receipt["parser_path"] == "OPT_IN_STRICT_OBJECT_NORMALIZATION"
    assert receipt["private_candidate"]["correct_answer"] == value["correct_answer"].strip()
    assert receipt["private_candidate"]["options"] is None
    assert receipt["answer_correctness"] == "NOT_VERIFIED"


def test_label_and_object_parser_opt_ins_are_independent():
    value = question()
    value["question"] = "Synthetic ```true``` question."
    raw_body = body(value)
    with pytest.raises(recovery.RecoveryError, match="RECOVERY_DISABLED"):
        prepare(b"``FINISH\n" + raw_body, allow_parser_fallback=True)
    with pytest.raises(recovery.RecoveryError, match="ORIGINAL_PARSER_MISMATCH"):
        prepare(b"``FINISH\n" + raw_body, allow_recovery=True)
    with pytest.raises(recovery.RecoveryError, match="ORIGINAL_PARSER_MISMATCH"):
        prepare(b"``FINISH``\n" + raw_body)
    strict = prepare(b"``FINISH``\n" + raw_body, allow_parser_fallback=True)
    assert strict.report()["recovery"] == "NOT_NEEDED_STRICT_RAW_UNCHANGED"
    assert strict.report()["parser_path"] == "OPT_IN_STRICT_OBJECT_NORMALIZATION"
    ordinary = prepare(b"``FINISH\n" + body(), allow_recovery=True, allow_parser_fallback=True)
    assert ordinary.report()["parser_path"] == "ORIGINAL_MODEL_TEXT_PARSER"


@pytest.mark.parametrize("text", [
    'Before "quoted" and ```true``` after.',
    "Unicode emoji 😊 before ```true``` after.",
    'Backslashes \\\\ and escaped "quote" before ```true``` after.',
    'One backslash \\ and escaped "quote" before ```true``` after.',
    'Three backslashes \\\\\\ and escaped "quote" before ```true``` after.',
    "Multiple ```true``` then ```false``` fences.",
    "Uppercase ```JSON true``` is still the original regex's first fence.",
])
def test_fallback_lexing_stays_inside_one_original_json_string(text):
    value = question()
    value["question"] = text
    raw_body = body(value)
    raw = b"``FINISH\n" + raw_body
    result = prepare(raw, allow_recovery=True, allow_parser_fallback=True)
    receipt = result.private_receipt()
    assert receipt["parser_path"] == "OPT_IN_STRICT_OBJECT_NORMALIZATION"
    assert receipt["body_byte_offset"] == len(b"``FINISH\n")
    assert receipt["private_candidate"]["question"] == text
    assert result.original_bytes() == raw


def test_uppercase_json_is_not_treated_as_the_original_lowercase_language_marker():
    lower = re.search(recovery._UPSTREAM_FENCE_PATTERN, "```json true```", re.DOTALL)
    upper = re.search(recovery._UPSTREAM_FENCE_PATTERN, "```JSON true```", re.DOTALL)
    assert lower is not None and lower.group(1) == "true"
    assert upper is not None and upper.group(1) == "JSON true"


@pytest.mark.parametrize("backslashes", [0, 1, 2, 3])
@pytest.mark.parametrize("second_fence", ["closing ```", "closing ``` then another ```true```"])
def test_original_first_fence_crossing_json_string_tokens_never_enables_fallback(second_fence, backslashes):
    value = question()
    value["question"] = "Synthetic open ```true" + "\\" * backslashes
    value["explanation"] = second_fence
    with pytest.raises(recovery.RecoveryError, match="PARSER_MISMATCH_UNSUPPORTED"):
        prepare(b"``FINISH\n" + body(value), allow_recovery=True, allow_parser_fallback=True)


def test_escaped_unicode_backticks_and_unclosed_fence_use_original_parser():
    value = question()
    value["question"] = "MARKER"
    encoded = body(value).replace(b"MARKER", b"\\u0060\\u0060\\u0060true\\u0060\\u0060\\u0060")
    escaped = prepare(b"``FINISH\n" + encoded, allow_recovery=True, allow_parser_fallback=True)
    assert escaped.report()["parser_path"] == "ORIGINAL_MODEL_TEXT_PARSER"
    assert escaped.private_receipt()["private_candidate"]["question"] == "```true```"
    value["question"] = "Synthetic unclosed ``` marker."
    unclosed = prepare(b"``FINISH\n" + body(value), allow_recovery=True, allow_parser_fallback=True)
    assert unclosed.report()["parser_path"] == "ORIGINAL_MODEL_TEXT_PARSER"


def test_original_parser_forged_valid_second_question_never_replaces_input(monkeypatch):
    value = question()
    value["question"] = "Original synthetic ```true``` question."
    forged = question()
    forged["question"] = "Different synthetic question."
    normalizer = recovery._normalizer()
    original = normalizer["_selected_functions"]()

    def forged_parser(_body):
        # Retain the pinned regex constant while simulating an incorrect parser
        # object; this test does not claim the fixed source actually forged it.
        assert len(r"```(?:json)?\s*(.*?)```") > 0
        return forged

    class ForgedFunctions:
        _parse_quiz_payload = staticmethod(forged_parser)
        _normalize_quiz_payload = staticmethod(original._normalize_quiz_payload)
        _collect_quiz_issues = staticmethod(original._collect_quiz_issues)

    normalizer["_selected_functions"] = lambda: ForgedFunctions
    monkeypatch.setattr(recovery, "_normalizer", lambda: normalizer)
    raw = b"``FINISH\n" + body(value)
    with pytest.raises(recovery.RecoveryError, match="ORIGINAL_PARSER_MISMATCH"):
        prepare(raw, allow_recovery=True)
    result = prepare(raw, allow_recovery=True, allow_parser_fallback=True)
    receipt = result.private_receipt()
    assert receipt["parser_path"] == "OPT_IN_STRICT_OBJECT_NORMALIZATION"
    assert receipt["private_candidate"]["question"] == value["question"]
    assert receipt["private_candidate"]["question"] != forged["question"]


def test_unknown_parser_mismatch_without_proven_fence_never_enables_fallback(monkeypatch):
    value = question()
    forged = question()
    forged["question"] = "Different synthetic question."
    normalizer = recovery._normalizer()
    original = normalizer["_selected_functions"]()

    def forged_parser(_body):
        assert len(r"```(?:json)?\s*(.*?)```") > 0
        return forged

    class ForgedFunctions:
        _parse_quiz_payload = staticmethod(forged_parser)
        _normalize_quiz_payload = staticmethod(original._normalize_quiz_payload)
        _collect_quiz_issues = staticmethod(original._collect_quiz_issues)

    normalizer["_selected_functions"] = lambda: ForgedFunctions
    monkeypatch.setattr(recovery, "_normalizer", lambda: normalizer)
    with pytest.raises(recovery.RecoveryError, match="PARSER_MISMATCH_UNSUPPORTED"):
        prepare(b"``FINISH\n" + body(value), allow_recovery=True, allow_parser_fallback=True)


def test_fallback_never_hides_unknown_parser_failure_or_issues(monkeypatch):
    value = question()
    value["question"] = "Synthetic ```true``` question."
    raw = b"``FINISH\n" + body(value)
    normalizer = recovery._normalizer()
    original = normalizer["_selected_functions"]()

    class BrokenParser:
        @staticmethod
        def _parse_quiz_payload(_body):
            raise RuntimeError("synthetic failure")

    normalizer["_selected_functions"] = lambda: BrokenParser
    monkeypatch.setattr(recovery, "_normalizer", lambda: normalizer)
    with pytest.raises(recovery.RecoveryError, match="QUESTION_REJECTED_OR_UNAVAILABLE"):
        prepare(raw, allow_recovery=True, allow_parser_fallback=True)

    class ReportedIssues:
        _parse_quiz_payload = staticmethod(original._parse_quiz_payload)
        _normalize_quiz_payload = staticmethod(original._normalize_quiz_payload)

        @staticmethod
        def _collect_quiz_issues(_template, _candidate):
            return ["synthetic_issue"]

    normalizer["_selected_functions"] = lambda: ReportedIssues
    with pytest.raises(recovery.RecoveryError, match="QUESTION_REJECTED"):
        prepare(raw, allow_recovery=True, allow_parser_fallback=True)


@pytest.mark.parametrize("field", ["question_type", "question", "correct_answer", "explanation", "options"])
def test_object_fallback_rejects_normalized_field_mismatch(monkeypatch, field):
    value = question()
    value["question"] = "Synthetic ```true``` question."
    normalizer = recovery._normalizer()
    original = normalizer["_selected_functions"]()

    class IncorrectNormalization:
        _parse_quiz_payload = staticmethod(original._parse_quiz_payload)
        _collect_quiz_issues = staticmethod(original._collect_quiz_issues)

        @staticmethod
        def _normalize_quiz_payload(template, parsed):
            result = original._normalize_quiz_payload(template, parsed)
            if field == "options":
                result["options"]["B"] = "different synthetic option"
            elif field == "question_type":
                result[field] = "coding"
            elif field == "correct_answer":
                result[field] = "C"
            else:
                result[field] = "different synthetic value"
            return result

    normalizer["_selected_functions"] = lambda: IncorrectNormalization
    monkeypatch.setattr(recovery, "_normalizer", lambda: normalizer)
    with pytest.raises(recovery.RecoveryError, match="VALIDATION_MISMATCH"):
        prepare(b"``FINISH\n" + body(value), allow_recovery=True, allow_parser_fallback=True)


@pytest.mark.parametrize("alteration", ["missing_answer", "unknown_field", "wrong_type", "ambiguous_options", "placeholder"])
def test_object_fallback_never_bypasses_strict_validation(alteration):
    value = question()
    value["question"] = "Synthetic ```true``` question."
    if alteration == "missing_answer":
        value.pop("correct_answer")
    elif alteration == "unknown_field":
        value["tool_calls"] = []
    elif alteration == "wrong_type":
        value["question_type"] = "coding"
    elif alteration == "ambiguous_options":
        value["options"]["B"] = value["options"]["A"].strip()
    else:
        value["explanation"] = "N/A"
    with pytest.raises(recovery.RecoveryError):
        prepare(b"``FINISH\n" + body(value), allow_recovery=True, allow_parser_fallback=True)


def test_object_fallback_never_accepts_declared_tool_calls():
    value = question()
    value["question"] = "Synthetic ```true``` question."
    with pytest.raises(recovery.RecoveryError, match="INVALID_INPUT_OR_TERMINAL"):
        prepare(b"``FINISH\n" + body(value), allow_recovery=True, allow_parser_fallback=True,
                tool_calls=[{"name": "synthetic"}])


def test_input_unicode_and_private_output_bounds(monkeypatch):
    for raw in (b"", b"\xff", b"``FINISH\n\x00", b"x" * (recovery.MAX_CONTENT_BYTES + 1)):
        with pytest.raises(recovery.RecoveryError, match="INVALID_INPUT_OR_TERMINAL"):
            prepare(raw, allow_recovery=True)
    deep = b'{"x":' + b"[" * 33 + b"0" + b"]" * 33 + b"}"
    with pytest.raises(recovery.RecoveryError, match="INVALID_JSON"):
        prepare(b"``FINISH\n" + deep, allow_recovery=True)
    monkeypatch.setattr(recovery, "MAX_PRIVATE_RECEIPT_BYTES", 10)
    with pytest.raises(recovery.RecoveryError, match="PRIVATE_RECEIPT_LIMIT"):
        prepare(b"``FINISH\n" + body(), allow_recovery=True)


def test_missing_or_changed_original_source_fails_closed(monkeypatch):
    original = recovery.PINS["agentic_labels.py"]
    monkeypatch.setitem(recovery.PINS, "agentic_labels.py", (original[0], original[1], "0" * 64))
    with pytest.raises(recovery.RecoveryError, match="SOURCE_UNAVAILABLE"):
        prepare(b"``FINISH\n" + body(), allow_recovery=True)


def test_missing_original_source_fails_closed(monkeypatch, tmp_path):
    original = recovery.PINS["agentic_labels.py"]
    missing = tmp_path / "missing_agentic_labels.py"
    monkeypatch.setitem(recovery.PINS, "agentic_labels.py", (missing, original[1], original[2]))
    with pytest.raises(recovery.RecoveryError, match="SOURCE_UNAVAILABLE"):
        prepare(b"``FINISH\n" + body(), allow_recovery=True)


def test_same_size_tampered_original_source_fails_closed(monkeypatch, tmp_path):
    original = recovery.PINS["agentic_labels.py"]
    data = original[0].read_bytes()
    tampered = data[:-1] + bytes([data[-1] ^ 1])
    path = tmp_path / "tampered_agentic_labels.py"
    path.write_bytes(tampered)
    assert len(tampered) == original[1]
    monkeypatch.setitem(recovery.PINS, "agentic_labels.py", (path, original[1], original[2]))
    with pytest.raises(recovery.RecoveryError, match="SOURCE_UNAVAILABLE"):
        prepare(b"``FINISH\n" + body(), allow_recovery=True)


@pytest.mark.parametrize("name", ["question_turn_worker.py", "question_normalizer.py"])
@pytest.mark.parametrize("variant", ["missing", "same_size_tampered"])
def test_other_fixed_adapters_missing_or_tampered_fail_closed(monkeypatch, tmp_path, name, variant):
    original = recovery.PINS[name]
    target = tmp_path / name
    if variant == "same_size_tampered":
        data = original[0].read_bytes()
        tampered = data[:-1] + bytes([data[-1] ^ 1])
        assert len(tampered) == original[1]
        target.write_bytes(tampered)
    monkeypatch.setitem(recovery.PINS, name, (target, original[1], original[2]))
    with pytest.raises(recovery.RecoveryError, match="SOURCE_UNAVAILABLE"):
        prepare(b"``FINISH\n" + body(), allow_recovery=True, allow_parser_fallback=True)


@pytest.mark.parametrize("allow_parser_fallback", [False, True])
@pytest.mark.parametrize("variant", ["missing", "same_size_tampered"])
def test_original_pipeline_missing_or_tampered_cannot_be_bypassed(
        monkeypatch, tmp_path, variant, allow_parser_fallback):
    normalizer = recovery._normalizer()
    temporary_upstream = tmp_path / "upstream"
    temporary_upstream.mkdir()
    target = temporary_upstream / "question_pipeline.py"
    if variant == "same_size_tampered":
        data = normalizer["UPSTREAM"].read_bytes()
        tampered = data[:-1] + bytes([data[-1] ^ 1])
        assert len(tampered) == normalizer["UPSTREAM_SIZE"]
        target.write_bytes(tampered)
    normalizer["UPSTREAM_ROOT"] = temporary_upstream
    normalizer["UPSTREAM"] = target
    monkeypatch.setattr(recovery, "_normalizer", lambda: normalizer)
    value = question()
    value["question"] = "Synthetic ```true``` question."
    with pytest.raises(recovery.RecoveryError, match="QUESTION_REJECTED_OR_UNAVAILABLE"):
        prepare(b"``FINISH\n" + body(value), allow_recovery=True,
                allow_parser_fallback=allow_parser_fallback)


def test_recovery_interface_is_not_directly_constructible():
    with pytest.raises(recovery.RecoveryError, match="RESULT_NOT_PREPARED"):
        recovery.PrivateRecovery(b"raw", 0, {}, "{}")
