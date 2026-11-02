"""Synthetic caller-supplied practice readbacks; no Core or model is started."""
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import threading
import uuid

from openpyxl import Workbook
import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services/learning-providers/deeptutor"
MATERIAL = {"document_id": "synthetic_material", "version": 3, "content_sha256": "1" * 64}


@pytest.fixture
def adapter():
    name = "practice_readback_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, PROVIDER / "practice_candidate_readback.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def raw_source(format):
    if format == "json":
        return wire([{"question": "Synthetic question?", "question_type": "single_choice",
                      "options": {"A": "one", "B": "two"}, "correct_answer": "B",
                      "user_answer": "SYNTHETIC_PRIVATE_USER", "extra": "SYNTHETIC_PRIVATE_EXTRA"}]), 1
    if format == "xlsx":
        book = Workbook()
        sheet = book.active
        sheet.append(["question", "question_type", "A", "B", "answer", "extra"])
        sheet.append(["Synthetic question?", "single_choice", "one", "two", "B", "SYNTHETIC_PRIVATE_EXTRA"])
        output = io.BytesIO()
        book.save(output)
        book.close()
        return output.getvalue(), 2
    delimiter = "," if format == "csv" else "\t"
    lines = [["question", "question_type", "A", "B", "answer", "extra"],
             ["Synthetic question?", "single_choice", "one", "two", "B", "SYNTHETIC_PRIVATE_EXTRA"]]
    return ("\n".join(delimiter.join(line) for line in lines) + "\n").encode("utf-8"), 2


def fixture(adapter, format="json", raw=None):
    default_raw, row = raw_source(format)
    raw = default_raw if raw is None else raw
    title, question_id, create_id = "SYNTHETIC_PRIVATE_TITLE", "q_1", "synthetic_create"
    material = copy.deepcopy(MATERIAL)
    prepared = adapter.prepare_practice_row(raw, format, row, material, question_id, create_id, title)
    digest = hashlib.sha256(raw).hexdigest()
    # These are explicitly synthetic Core-shaped claims, not real receipts.
    claimed = {"source_id": "synthetic_previous_source", "sha256": digest, "duplicate": True}
    expected = prepared.document_create_request(claimed)
    original = {"source_id": claimed["source_id"], "name": "old-duplicate-name.json",
                "media_type": "application/json", "sha256": digest,
                "content_base64": base64.b64encode(raw).decode("ascii")}
    editor = copy.deepcopy(expected["editor_json"])
    blocks, texts = [], []
    for index, node in enumerate(editor["content"]):
        block_id = f"blk_{index + 1:024x}"
        node["attrs"] = {"block_id": block_id}
        text = node["content"][0]["text"]
        texts.append(text)
        blocks.append({"block_id": block_id, "kind": "paragraph", "ordinal": index,
                       "node_json": copy.deepcopy(node), "text_projection": text, "codec_status": "known"})
    document_id = "doc_req_" + hashlib.sha256(create_id.encode("ascii")).hexdigest()
    document = {"document_id": document_id, "source_id": claimed["source_id"], "source_revision": digest,
                "title": title, "version": 1, "editor_json": editor, "text_projection": "\n".join(texts),
                "content_sha256": "2" * 64, "blocks": blocks, "revision_basis": None}
    snapshot = {"document_id": document_id, "version": 1, "content_sha256": document["content_sha256"]}
    question = editor["attrs"]["archeaxis_deeptutor_question"]["question"]
    view = {"schema": "archeaxis.deeptutor-question-view/v1", "question_document": snapshot,
            "question_status": "current", "source_material": copy.deepcopy(material), "source_snapshot_status": "current",
            "source_reference": "declared_unverified", "question_document_origin": "unverified",
            "authorization_effect": "none", "question_version": "sha256:" + "3" * 64, "visible_sha256": "4" * 64,
            "question": {key: copy.deepcopy(question[key]) for key in ("question_id", "question", "question_type", "options")},
            "origin": "user_import_unverified", "provider_identity": "unverified", "provider_executed": False,
            "independent_mastery": "not_established"}
    return {"prepared": prepared, "raw": raw, "format": format, "row": row, "material": material,
            "question_id": question_id, "create_id": create_id, "title": title, "import": claimed,
            "original": original, "create": copy.deepcopy(document), "document": document, "view": view}


def run(adapter, data, replacements=None):
    replacements = replacements or {}

    def response(name, status):
        return replacements.get(name, (status, wire(data[name])))

    return adapter.reconcile(data["prepared"], data["raw"], data["format"], data["row"], data["material"],
        data["question_id"], data["create_id"], data["title"], response("import", 202), response("original", 200),
        response("create", 201), response("document", 200), response("view", 200))


def rejected(adapter, data, reason, replacements=None):
    with pytest.raises(adapter.PracticeReadbackError) as failure:
        run(adapter, data, replacements)
    assert str(failure.value) == reason


@pytest.mark.parametrize("format", ["csv", "tsv", "json", "xlsx"])
def test_caller_supplied_readbacks_match_same_prepared_candidate_without_reparse(adapter, format, monkeypatch, capsys):
    data = fixture(adapter, format)
    importer = adapter._practice._practice_module

    def forbidden(*_args, **_kwargs):
        raise AssertionError("readback must not reparse or start an XLSX child")

    monkeypatch.setattr(importer, "_private_preview", forbidden)
    monkeypatch.setattr(adapter._practice, "prepare_practice_row", forbidden)
    result = run(adapter, data)
    assert result["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_PREPARED_CANDIDATE"
    assert result["reparse_during_readback"] == "NOT_INVOKED"
    assert result["prepared_identity"] == "LATEST_SAME_INSTANCE_FINGERPRINT_NOT_AUTHENTICATION"
    assert result["core_authentication"] == result["core_authorization"] == "NOT_ESTABLISHED"
    assert result["source_link"] == ("XLSX_CHILD_SOURCE_LINK_UNVERIFIED" if format == "xlsx"
                                    else "PINNED_PARSER_OF_CALLER_BYTES_NOT_AUTHENTICATED")
    assert result["question_status"] == result["source_snapshot_status"] == "current"
    assert result["restart_durability"] == result["independent_mastery"] == "NOT_ESTABLISHED"
    assert result["readback_atomicity"] == result["cross_instance_process_fence"] == "NOT_ESTABLISHED"
    assert result["source_and_document_calls"] == "SEPARATE_DOCUMENT_FAILURE_MAY_LEAVE_SOURCE"
    rendered = json.dumps(result)
    for private in ("Synthetic question", "SYNTHETIC_PRIVATE", data["import"]["sha256"], "3" * 64):
        assert private not in rendered
    # Identical sources may be deduplicated under an older name and MIME.
    assert data["original"]["name"] == "old-duplicate-name.json"
    assert capsys.readouterr() == ("", "")


def test_first_source_identity_and_duplicate_id_have_distinct_rules(adapter):
    data = fixture(adapter)
    assert run(adapter, data)["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_PREPARED_CANDIDATE"
    digest = data["import"]["sha256"]
    new_id = "src_" + hashlib.sha256(digest.encode("ascii")).hexdigest()[:24]
    data["import"].update(duplicate=False, source_id=new_id)
    data["original"]["source_id"] = new_id
    data["create"]["source_id"] = data["document"]["source_id"] = new_id
    assert run(adapter, data)["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_PREPARED_CANDIDATE"
    data["import"]["source_id"] = data["original"]["source_id"] = "wrong"
    data["create"]["source_id"] = data["document"]["source_id"] = "wrong"
    rejected(adapter, data, "SOURCE_MISMATCH")


@pytest.mark.parametrize("case,reason", [
    ("source_bytes", "SOURCE_MISMATCH"), ("source_sha", "SOURCE_MISMATCH"),
    ("source_id", "SOURCE_MISMATCH"), ("row", "PREPARED_MISMATCH"),
    ("material", "PREPARED_MISMATCH"), ("question_id", "PREPARED_MISMATCH"),
    ("create_id", "PREPARED_MISMATCH"), ("title", "PREPARED_MISMATCH"),
    ("document_answer", "DOCUMENT_MISMATCH"), ("document_body", "DOCUMENT_MISMATCH"),
    ("document_id", "DOCUMENT_MISMATCH"), ("view_question", "VIEW_MISMATCH"),
    ("view_material", "VIEW_MISMATCH"), ("view_snapshot", "VIEW_MISMATCH"),
])
def test_tampered_claims_or_receipts_fail_closed(adapter, case, reason, capsys):
    data = fixture(adapter)
    if case == "source_bytes":
        data["original"]["content_base64"] = base64.b64encode(b"different").decode("ascii")
    elif case == "source_sha":
        data["import"]["sha256"] = "0" * 64
    elif case == "source_id":
        data["original"]["source_id"] = "different"
    elif case == "row":
        data["row"] += 1
    elif case == "material":
        data["material"]["version"] += 1
    elif case == "question_id":
        data["question_id"] = "different"
    elif case == "create_id":
        data["create_id"] = "different"
    elif case == "title":
        data["title"] = "different"
    elif case == "document_answer":
        for name in ("create", "document"):
            data[name]["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["correct_answer"] = "A"
    elif case == "document_body":
        data["document"]["editor_json"]["content"][0]["content"][0]["text"] = "different"
    elif case == "document_id":
        data["document"]["document_id"] = "doc_req_" + "0" * 64
    elif case == "view_question":
        data["view"]["question"]["question"] = "different"
    elif case == "view_material":
        data["view"]["source_material"]["version"] = True
    else:
        data["view"]["question_document"]["content_sha256"] = "0" * 64
    rejected(adapter, data, reason)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("private_part", ["row_receipt", "document_question"])
def test_changed_original_input_and_private_candidate_are_rejected(adapter, private_part):
    data = fixture(adapter)
    data["raw"] += b" "
    rejected(adapter, data, "PREPARED_MISMATCH")
    data["raw"] = data["raw"][:-1]
    if private_part == "row_receipt":
        private = data["prepared"].private_import_receipt()
        private["source_row"] += 1
        object.__setattr__(data["prepared"], "_receipt_json", json.dumps(private))
    else:
        inner = data["prepared"]._candidate
        question = json.loads(inner._candidate_json)
        question["correct_answer"] = "A"
        object.__setattr__(inner, "_candidate_json", json.dumps(question))
    rejected(adapter, data, "PREPARED_MISMATCH")


def test_mutating_returned_document_request_does_not_change_expected_candidate(adapter):
    data = fixture(adapter)
    returned = data["prepared"].document_create_request(data["import"])
    returned["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["correct_answer"] = "A"
    for name in ("create", "document"):
        data[name]["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["correct_answer"] = "A"
    rejected(adapter, data, "DOCUMENT_MISMATCH")


@pytest.mark.parametrize("case", ["title_characters", "title_utf8", "receipt_characters"])
def test_tampered_private_strings_are_bounded_before_and_after_encoding(adapter, monkeypatch, case):
    data = fixture(adapter)
    if case == "title_characters":
        object.__setattr__(data["prepared"]._candidate, "_title", "x" * 1025)
    elif case == "title_utf8":
        # Character count fits, but the actual UTF-8 bytes do not.
        object.__setattr__(data["prepared"]._candidate, "_title", "中" * 342)
    else:
        assert adapter._MAX_PRIVATE_RECEIPT == 16 * 1024 * 1024
        # Exercise the same pre-encoding boundary with a small synthetic cap;
        # neither an oversized file nor a 16 MiB test allocation is needed.
        monkeypatch.setattr(adapter, "_MAX_PRIVATE_RECEIPT", 64)
        object.__setattr__(data["prepared"], "_receipt_json", "x" * 65)
    rejected(adapter, data, "PREPARED_UNAVAILABLE")


def test_valid_multibyte_title_within_existing_limit_remains_preparable(adapter):
    raw, row = raw_source("json")
    title = "中" * 341
    assert len(title.encode("utf-8")) == 1023
    prepared = adapter.prepare_practice_row(raw, "json", row, MATERIAL, "q", "create", title)
    assert adapter._prepared_fingerprint(prepared, adapter._practice) == adapter._latest_fingerprint


@pytest.mark.parametrize("name,status,reason", [
    ("import", 403, "IMPORT_UNAVAILABLE"), ("original", 404, "SOURCE_UNAVAILABLE"),
    ("create", 409, "DOCUMENT_CREATE_UNAVAILABLE"), ("document", 404, "DOCUMENT_READ_UNAVAILABLE"),
    ("view", 422, "VIEW_UNAVAILABLE"),
])
def test_non_success_status_never_reflects_body(adapter, name, status, reason, capsys):
    data = fixture(adapter)
    rejected(adapter, data, reason, {name: (status, b'{"private":"SYNTHETIC_PRIVATE"}')})
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("name,status", [("import", 202), ("original", 200), ("create", 201),
                                          ("document", 200), ("view", 200)])
def test_duplicate_json_members_are_rejected_at_each_response(adapter, name, status):
    data = fixture(adapter)
    duplicated = wire(data[name])[:-1] + b',"duplicate":1,"duplicate":2}'
    rejected(adapter, data, "INVALID_RESPONSE_JSON", {name: (status, duplicated)})


@pytest.mark.parametrize("constant", [b"NaN", b"Infinity", b"1e999"])
def test_nonfinite_response_metadata_is_rejected(adapter, constant):
    data = fixture(adapter)
    altered = wire(data["document"])[:-1] + b',"extra":' + constant + b'}'
    rejected(adapter, data, "INVALID_RESPONSE_JSON", {"document": (200, altered)})


def test_5_mib_original_and_base64_readback_are_bounded_in_memory(adapter):
    small, _ = raw_source("json")
    raw = small + b" " * (adapter._MAX_SOURCE - len(small))
    assert len(raw) == 5 * 1024 * 1024
    data = fixture(adapter, raw=raw)
    source_wire = wire(data["original"])
    assert len(source_wire) > 6_990_508 and len(source_wire) <= adapter._MAX_SOURCE_JSON
    assert run(adapter, data)["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_PREPARED_CANDIDATE"
    data["raw"] += b" "
    rejected(adapter, data, "INVALID_INPUT")
    data["raw"] = data["raw"][:-1]
    rejected(adapter, data, "INVALID_RESPONSE_ENVELOPE", {"original": (200, b" " * (adapter._MAX_SOURCE_JSON + 1))})


def test_new_selection_invalidates_old_candidate_even_if_new_prepare_fails(adapter):
    old = fixture(adapter)
    newer = fixture(adapter)
    rejected(adapter, old, "PREPARED_STALE")
    assert run(adapter, newer)["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_PREPARED_CANDIDATE"
    with pytest.raises(adapter.PracticeReadbackError, match="^CANDIDATE_UNAVAILABLE$"):
        adapter.prepare_practice_row(b"invalid", "json", 1, MATERIAL, "q", "create", "private")
    rejected(adapter, newer, "PREPARATION_REQUIRED")
    assert adapter._latest is None and adapter._latest_fingerprint is None


def test_a_prepared_object_from_another_module_instance_is_not_accepted(adapter):
    data = fixture(adapter)
    name = "practice_readback_other_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, PROVIDER / "practice_candidate_readback.py")
    assert spec is not None and spec.loader is not None
    other = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(other)
    fixture(other)
    with pytest.raises(other.PracticeReadbackError, match="^PREPARED_STALE$"):
        run(other, data)


def test_concurrent_prepare_and_readback_are_nonblocking(adapter, monkeypatch):
    old = fixture(adapter)
    entered, release = threading.Event(), threading.Event()
    prepare = adapter._practice.prepare_practice_row

    def blocked(*args):
        entered.set()
        assert release.wait(10)
        return prepare(*args)

    monkeypatch.setattr(adapter._practice, "prepare_practice_row", blocked)
    raw, row = raw_source("json")
    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(adapter.prepare_practice_row, raw, "json", row, MATERIAL, "q_2", "create_2", "private")
        assert entered.wait(10)
        rejected(adapter, old, "BUSY")
        release.set()
        assert future.result(timeout=15).report()["status"] == "PRIVATE_CANDIDATE_PREPARED"
    rejected(adapter, old, "PREPARED_STALE")


def test_xlsx_unknown_never_recreates_module_or_retries_from_readback(adapter, monkeypatch):
    old = fixture(adapter)
    practice = adapter._practice
    importer = practice._practice_module
    calls = []

    def unknown(_data, cleanup_confirmed):
        calls.append(1)
        cleanup_confirmed[0] = False
        raise importer.UpstreamUnavailable("synthetic unknown")

    monkeypatch.setattr(importer, "_isolated_xlsx_preview_owned", unknown)
    for _ in range(2):
        with pytest.raises(adapter.PracticeReadbackError, match="^CANDIDATE_UNAVAILABLE$"):
            adapter.prepare_practice_row(b"synthetic", "xlsx", 2, MATERIAL, "q", "create", "private")
    assert calls == [1]
    assert adapter._practice is practice and practice._practice_module is importer
    rejected(adapter, old, "PREPARATION_REQUIRED")


@pytest.mark.parametrize("which", ["practice", "comparison"])
@pytest.mark.parametrize("missing", [True, False])
def test_pinned_dependency_missing_or_same_length_tamper_fails_closed(adapter, tmp_path, monkeypatch, which, missing):
    filename = adapter._PINS[which][0]
    if not missing:
        source = (PROVIDER / filename).read_bytes()
        (tmp_path / filename).write_bytes(bytes([source[0] ^ 1]) + source[1:])
    monkeypatch.setattr(adapter, "_ROOT", tmp_path)
    with pytest.raises(adapter.PracticeReadbackError, match="^ADAPTER_UNAVAILABLE$"):
        adapter._read_pinned(which)
