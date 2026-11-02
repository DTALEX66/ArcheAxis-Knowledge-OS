"""Synthetic, offline controls for the unregistered practice-row adapter."""
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
from types import SimpleNamespace
import uuid

from openpyxl import Workbook
import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services/learning-providers/deeptutor"


@pytest.fixture
def adapter():
    # Each test owns one adapter instance. Production hosts must not treat a
    # fresh module or a different process as inheriting this instance's fence.
    name = "practice_candidate_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, PROVIDER / "practice_candidate_document.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MATERIAL = {"document_id": "selected_material", "version": 3, "content_sha256": "1" * 64}


def json_source(rows):
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def choice_row():
    return {"question": "Synthetic question?", "question_type": "single_choice",
            "options": {"A": "first", "B": "second"}, "correct_answer": "B",
            "explanation": "SYNTHETIC_PRIVATE_EXPLANATION", "user_answer": "SYNTHETIC_PRIVATE_USER",
            "difficulty": "SYNTHETIC_PRIVATE_DIFFICULTY", "tags": ["SYNTHETIC_PRIVATE_TAG"],
            "extra": "SYNTHETIC_PRIVATE_UNMAPPED"}


def workbook_source():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["question", "question_type", "A", "B", "answer", "extra"])
    sheet.append(["Synthetic question?", "single_choice", "first", "second", "B", "SYNTHETIC_PRIVATE_UNMAPPED"])
    stream = io.BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def source_for(format):
    if format == "json":
        return json_source([choice_row()]), 1
    if format == "xlsx":
        return workbook_source(), 2
    delimiter = "," if format == "csv" else "\t"
    rows = [["question", "question_type", "A", "B", "answer", "extra"],
            ["Synthetic question?", "single_choice", "first", "second", "B", "SYNTHETIC_PRIVATE_UNMAPPED"]]
    return ("\n".join(delimiter.join(row) for row in rows) + "\n").encode("utf-8"), 2


def prepare(adapter, data, format="json", row=1, *, question_id="question_1", create_id="create_1"):
    return adapter.prepare_practice_row(data, format, row, copy.deepcopy(MATERIAL), question_id, create_id,
                                        "SYNTHETIC_PRIVATE_TITLE")


def synthetic_receipt(raw, *, duplicate=False):
    digest = hashlib.sha256(raw).hexdigest()
    return {"source_id": "src_" + hashlib.sha256(digest.encode("ascii")).hexdigest()[:24],
            "sha256": digest, "duplicate": duplicate}


@pytest.mark.parametrize("format", ["csv", "tsv", "json", "xlsx"])
def test_one_row_uses_original_bytes_and_existing_document_builder(adapter, format, capsys):
    raw, row = source_for(format)
    prepared = prepare(adapter, raw, format, row)
    imported = prepared.raw_import_request()
    assert imported["name"] == "deeptutor-practice-import." + format
    assert base64.b64decode(imported["content_base64"], validate=True) == raw
    assert prepared.original_source_bytes() == raw
    # Synthetic shape only: no Core process or storage was used by this test.
    actual_argument = synthetic_receipt(raw)
    document = prepared.document_create_request(actual_argument)
    assert document["source_id"] == actual_argument["source_id"]
    assert document["source_revision"] == hashlib.sha256(raw).hexdigest()
    question = document["editor_json"]["attrs"]["archeaxis_deeptutor_question"]
    assert question["origin"] == "user_import_unverified"
    assert question["source_material"] == MATERIAL
    assert question["question"]["question_id"] == "question_1"
    assert question["question"]["question_type"] == "single_choice"
    assert question["question"]["correct_answer"] == "B"
    assert "user_answer" not in question["question"]
    assert [node["content"][0]["text"] for node in document["editor_json"]["content"]] == [
        "Synthetic question?", "A. first", "B. second"]
    private = prepared.private_import_receipt()
    assert private["source_row"] == row and private["source_format"] == format
    assert private["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert private["normalized_candidate"]["question_id"].startswith("import:")
    assert private["raw_row"]["extra"] == "SYNTHETIC_PRIVATE_UNMAPPED"
    assert private["unmapped"][0]["value"] == "SYNTHETIC_PRIVATE_UNMAPPED"
    if format == "json":
        assert private["normalized_candidate"]["user_answer"] == "SYNTHETIC_PRIVATE_USER"
        assert private["normalized_candidate"]["tags"] == ["SYNTHETIC_PRIVATE_TAG"]
    report = prepared.report()
    assert report["question_replay"] == report["provider_execution"] == report["grading"] == "NOT_INVOKED"
    assert report["core_authorization"] == report["independent_mastery"] == "NOT_ESTABLISHED"
    assert report["source_import"] == report["core_document_write"] == "NOT_EXECUTED"
    assert report["private_row_receipt_persistence"] == "NOT_ESTABLISHED"
    assert report["source_link"] == ("XLSX_CHILD_SOURCE_LINK_UNVERIFIED" if format == "xlsx"
                                    else "PINNED_PARSER_OF_CALLER_BYTES_NOT_AUTHENTICATED")
    serialized_report = json.dumps(report, ensure_ascii=False) + repr(prepared)
    for secret in ("Synthetic question", "SYNTHETIC_PRIVATE", private["normalized_candidate"]["question_id"],
                   hashlib.sha256(raw).hexdigest()):
        assert secret not in serialized_report
    private["raw_row"]["extra"] = "changed"
    assert prepared.private_import_receipt()["raw_row"]["extra"] == "SYNTHETIC_PRIVATE_UNMAPPED"
    assert capsys.readouterr() == ("", "")


def test_duplicate_rows_keep_independent_caller_ids_and_one_source_receipt(adapter):
    raw = json_source([choice_row(), choice_row()])
    first = prepare(adapter, raw, row=1, question_id="q_first", create_id="create_first")
    second = prepare(adapter, raw, row=2, question_id="q_second", create_id="create_second")
    receipt = synthetic_receipt(raw, duplicate=True)
    first_doc, second_doc = first.document_create_request(receipt), second.document_create_request(receipt)
    assert first_doc["source_revision"] == second_doc["source_revision"] == receipt["sha256"]
    assert first_doc["create_request_id"] != second_doc["create_request_id"]
    assert first_doc["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["question_id"] == "q_first"
    assert second_doc["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["question_id"] == "q_second"
    assert (first.private_import_receipt()["normalized_candidate"]["question_id"]
            == second.private_import_receipt()["normalized_candidate"]["question_id"])
    again = prepare(adapter, raw, row=1, question_id="q_first", create_id="create_first")
    assert again.document_create_request(receipt) == first_doc


def test_gb18030_and_logical_csv_record_number_are_preserved(adapter):
    text = '题目,题型,选项A,选项B,答案,备注\n"跨行\n问题",单选,甲,乙,乙,私有备注\n'
    raw = text.encode("gb18030")
    prepared = prepare(adapter, raw, "csv", 2)
    receipt = prepared.private_import_receipt()
    assert receipt["source_row"] == 2
    assert receipt["source_row_scope"] == "tabular_record_index_one_based_including_header"
    assert receipt["raw_row"]["题目"] == "跨行\n问题"
    assert receipt["normalized_candidate"]["correct_answer"] == "B"


@pytest.mark.parametrize("case", ["option_key", "option_value", "answer"])
def test_core_utf8_byte_limits_are_stricter_than_upstream_character_limits(adapter, case):
    row = choice_row()
    if case == "option_key":
        row["options"] = {"A": "first", "K" * 257: "second"}
        row["correct_answer"] = "A"
    elif case == "option_value":
        # Each JSON leaf is below the preview's 20,000-byte limit, but the
        # original _cell stringifies the list into a larger UTF-8 value.
        row["options"]["B"] = ["中" * 3_334, "中" * 3_334]
    else:
        row.update(question_type="short_answer", options={}, correct_answer=["中" * 3_334, "中" * 3_334])
    raw = json_source([row])
    _, practice = adapter._modules()
    functions = practice._selected_functions()
    parsed = functions["parse_rows"](raw, "synthetic.json")
    normalized = functions["normalize_question"](parsed[0][1])
    preview = practice._private_preview(raw, "json")
    assert preview.rows[0]["candidate"] == normalized
    if case == "option_key":
        assert any(len(key.encode("utf-8")) == 257 for key in normalized["options"])
    else:
        value = normalized["options"]["B"] if case == "option_value" else normalized["correct_answer"]
        assert len(value) < 20_000 and len(value.encode("utf-8")) > 20_000
    with pytest.raises(adapter.PracticeCandidateError, match="^QUESTION_OUTSIDE_CORE_BOUNDS$"):
        prepare(adapter, raw)


@pytest.mark.parametrize("case", ["option_value", "answer"])
def test_single_oversized_utf8_leaf_is_rejected_by_earlier_import_preflight(adapter, case):
    row = choice_row()
    if case == "option_value":
        row["options"]["B"] = "中" * 6_667
    else:
        row.update(question_type="short_answer", options={}, correct_answer="中" * 6_667)
    with pytest.raises(adapter.PracticeCandidateError, match="^IMPORT_UNAVAILABLE_OR_REJECTED$"):
        prepare(adapter, json_source([row]))


@pytest.mark.parametrize("options,answer,kind", [
    ({"A": "same", "B": "same"}, "same", "single_choice"),
    ({"A": "first", "B": " A "}, "A", "single_choice"),
    ({"A": "first", "B": "second", "C": "A,B"}, "A,B", "multi_choice"),
    ({"A": "alpha", "B": "beta", "C": "AB"}, "A,B", "multi_choice"),
    ({"A": "alpha", "B": "beta", "C": "AA"}, "A", "multi_choice"),
    ({"AB": "combined", "A": "alpha", "B": "beta"}, "AB", "multi_choice"),
    ({"S": "sigma", "T": "tau", "C": "ß"}, "S", "multi_choice"),
    ({"A": "alpha", "B": "beta", "C": " A，B "}, "A,B", "multi_choice"),
    ({"A": "alpha", "B": "beta", "C": "A\tB"}, "A,B", "multi_choice"),
])
def test_ambiguous_grader_aliases_are_narrower_than_original_import(adapter, options, answer, kind):
    row = {"question": "Synthetic?", "question_type": kind, "options": options, "correct_answer": answer}
    with pytest.raises(adapter.PracticeCandidateError, match="^AMBIGUOUS_OPTIONS$"):
        prepare(adapter, json_source([row]))


@pytest.mark.parametrize("options,alias,expected", [
    ({"A": "alpha", "B": "beta", "C": "AB"}, "AB", "A,B"),
    ({"A": "alpha", "B": "beta", "C": "AA"}, "AA", "A"),
    ({"S": "sigma", "T": "tau", "C": "ß"}, "ß", "S"),
    ({"A": "alpha", "B": "beta", "C": " A，B "}, " A，B ", "A,B"),
    ({"A": "alpha", "B": "beta", "C": "A\tB"}, "A\tB", "A,B"),
])
def test_multiselect_alias_conflicts_with_real_original_grader(adapter, options, alias, expected):
    spec = importlib.util.spec_from_file_location("practice_grade_for_alias_test", PROVIDER / "grade_worker.py")
    assert spec is not None and spec.loader is not None
    grader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader)
    question = {"question_type": "multi_choice", "options": options, "correct_answer": expected}
    request = {"schema": grader.SCHEMA, "request_id": "synthetic_grade", "question": question, "answer": expected}
    original = grader._upstream_grader()
    assert original(question, expected) is True
    # Keep the original's behavior visible: the alias can also be read as
    # selection keys, but the upstream grader assigns it to C first.
    assert original(question, alias) is False
    with pytest.raises(grader.InvalidRequest):
        grader.process(request)
    request["answer"] = alias
    with pytest.raises(grader.InvalidRequest):
        grader.process(request)
    row = {"question": "Synthetic?", **question}
    with pytest.raises(adapter.PracticeCandidateError, match="^AMBIGUOUS_OPTIONS$"):
        prepare(adapter, json_source([row]))


def test_unambiguous_continuous_multiselect_remains_a_candidate(adapter):
    row = {"question": "Synthetic?", "question_type": "multi_choice",
           "options": {"A": "alpha", "B": "beta", "C": "gamma"}, "correct_answer": "AB"}
    prepared = prepare(adapter, json_source([row]))
    normalized = prepared.private_import_receipt()["normalized_candidate"]
    assert normalized["correct_answer"] == "A,B"
    assert prepared.report()["grading"] == "NOT_INVOKED"


def test_multicharacter_key_without_component_keys_remains_a_candidate(adapter):
    row = {"question": "Synthetic?", "question_type": "multi_choice",
           "options": {"AB": "group", "C": "gamma"}, "correct_answer": "AB"}
    prepared = prepare(adapter, json_source([row]))
    assert prepared.private_import_receipt()["normalized_candidate"]["correct_answer"] == "AB"


def test_invalid_row_ids_material_and_receipts_fail_without_private_echo(adapter, capsys):
    raw = json_source([choice_row(), {"question": "SYNTHETIC_PRIVATE_BAD", "answer": ""}])
    with pytest.raises(adapter.PracticeCandidateError, match="^IMPORTED_ROW_UNAVAILABLE$"):
        prepare(adapter, raw, row=2)
    with pytest.raises(adapter.PracticeCandidateError, match="^IMPORTED_ROW_UNAVAILABLE$"):
        prepare(adapter, raw, row=3)
    with pytest.raises(adapter.PracticeCandidateError, match="^INVALID_INPUT$"):
        prepare(adapter, raw, question_id="import:unsafe")
    with pytest.raises(adapter.PracticeCandidateError, match="^INVALID_INPUT$"):
        prepare(adapter, raw, row=True)
    material = {**MATERIAL, "version": True}
    with pytest.raises(adapter.PracticeCandidateError, match="^INVALID_MATERIAL_SNAPSHOT$"):
        adapter.prepare_practice_row(raw, "json", 1, material, "q", "create", "private")
    self_id = "doc_req_" + hashlib.sha256(b"create").hexdigest()
    with pytest.raises(adapter.PracticeCandidateError, match="^INVALID_MATERIAL_SNAPSHOT$"):
        adapter.prepare_practice_row(raw, "json", 1, {**MATERIAL, "document_id": self_id}, "q", "create", "private")
    prepared = prepare(adapter, raw)
    wrong = synthetic_receipt(raw)
    wrong["sha256"] = hashlib.sha256(b"wrong").hexdigest()
    with pytest.raises(adapter.PracticeCandidateError, match="^INVALID_IMPORT_RECEIPT$"):
        prepared.document_create_request(wrong)
    assert capsys.readouterr() == ("", "")


def test_single_instance_caches_modules_removes_registration_and_serializes_calls(adapter, monkeypatch):
    raw, row = source_for("json")
    before = {name for name in sys.modules if name.startswith("_deeptutor_practice_candidate_")}
    prepare(adapter, raw, row=row)
    practice = adapter._practice_module
    assert practice is not None
    after = {name for name in sys.modules if name.startswith("_deeptutor_practice_candidate_")}
    assert after == before
    entered, release = threading.Event(), threading.Event()
    original = practice._private_preview

    def blocked(data, format):
        entered.set()
        assert release.wait(10)
        return original(data, format)

    monkeypatch.setattr(practice, "_private_preview", blocked)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(prepare, adapter, raw, "json", row)
        assert entered.wait(10)
        with pytest.raises(adapter.PracticeCandidateError, match="^BUSY$"):
            prepare(adapter, raw, "json", row)
        release.set()
        assert future.result(timeout=15).report()["status"] == "PRIVATE_CANDIDATE_PREPARED"
    assert adapter._practice_module is practice


def test_xlsx_unknown_keeps_same_instance_and_slot_poisoned(adapter, monkeypatch):
    json_raw, row = source_for("json")
    prepare(adapter, json_raw, row=row)
    practice = adapter._practice_module
    calls = []

    def unknown(_data, cleanup_confirmed):
        calls.append(1)
        cleanup_confirmed[0] = False
        raise practice.UpstreamUnavailable("synthetic unknown")

    monkeypatch.setattr(practice, "_isolated_xlsx_preview_owned", unknown)
    for _ in range(2):
        with pytest.raises(adapter.PracticeCandidateError, match="^IMPORT_UNAVAILABLE_OR_REJECTED$"):
            prepare(adapter, b"synthetic xlsx", "xlsx", 2)
    assert calls == [1]
    assert adapter._practice_module is practice
    assert prepare(adapter, json_raw, row=row).report()["status"] == "PRIVATE_CANDIDATE_PREPARED"


def test_xlsx_forged_consistent_child_is_never_claimed_as_source_proof(adapter, monkeypatch, capsys):
    json_raw, row = source_for("json")
    prepare(adapter, json_raw, row=row)
    practice = adapter._practice_module
    raw = workbook_source()
    row_value = {"question": "SYNTHETIC_FORGED_ROW", "answer": "SYNTHETIC_PRIVATE_ANSWER"}
    functions = practice._selected_functions()
    normalized = functions["normalize_question"](row_value)
    reply = {"schema": practice._XLSX_CHILD_SCHEMA, "status": "OK", "source_sha256": hashlib.sha256(raw).hexdigest(),
             "rows": [{"row": 2, "raw": row_value, "unmapped": [], "candidate": normalized,
                       "option_changes": []}], "skipped_rows": []}
    wire = (json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8")
    program = "import sys;sys.stdin.buffer.readline();sys.stdout.buffer.write(" + repr(wire) + ")"

    def spawn_stub(_command, **kwargs):
        return subprocess.Popen([sys.executable, "-I", "-B", "-c", program], **kwargs)

    local_subprocess = SimpleNamespace(Popen=spawn_stub, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired)
    monkeypatch.setattr(practice, "subprocess", local_subprocess)
    prepared = prepare(adapter, raw, "xlsx", 2)
    assert prepared.private_import_receipt()["raw_row"]["question"] == "SYNTHETIC_FORGED_ROW"
    assert prepared.report()["source_link"] == "XLSX_CHILD_SOURCE_LINK_UNVERIFIED"
    assert prepared.original_source_bytes() == raw
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("which", ["candidate", "practice"])
@pytest.mark.parametrize("missing", [True, False])
def test_pinned_sources_missing_or_same_length_tamper_fail_closed(adapter, tmp_path, monkeypatch, which, missing):
    filename = adapter._PINS[which][0]
    if not missing:
        source = (PROVIDER / filename).read_bytes()
        (tmp_path / filename).write_bytes(bytes([source[0] ^ 1]) + source[1:])
    monkeypatch.setattr(adapter, "_ROOT", tmp_path)
    with pytest.raises(adapter.PracticeCandidateError, match="^SOURCE_UNAVAILABLE$"):
        adapter._read_pinned(which)
