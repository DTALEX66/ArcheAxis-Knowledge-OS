"""Synthetic caller-supplied readbacks; no Core, network or model is started."""
import asyncio
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services/learning-providers/deeptutor"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, PROVIDER / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


readback = load("deeptutor_candidate_readback_test", "candidate_readback.py")
candidate = load("deeptutor_candidate_for_readback_test", "candidate_document.py")
turn = load("deeptutor_turn_for_readback_test", "question_turn_worker.py")


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def fixture(kind="choice", language="en", payload=None):
    material = {"document_id": "synthetic_material", "version": 1, "content_sha256": "1" * 64}
    request = {"schema": turn.SCHEMA, "request_id": "synthetic_turn", "mode": "capture", "language": language,
               "plan": {"analysis": "Synthetic plan", "templates": [{"question_id": "q_1", "topic": "Synthetic topic",
                   "question_type": kind, "difficulty": "easy", "source": "custom",
                   "reference_question": "", "reference_answer": ""}]},
               "question_number": 1, "exploration_trace": "Synthetic context", "previous_questions": []}
    prompt = turn.process(request)
    assert prompt["status"] == "CAPTURED"
    if payload is None:
        payload = {"question_type": "choice", "question": "Synthetic question?",
                   "options": {"A": "one", "B": "two", "C": "three", "D": "four"},
                   "correct_answer": "B", "explanation": "Synthetic explanation"}
    raw = wire(payload)
    request.update(mode="replay", expected_prompt_sha256=prompt["prompt_sha256"], response_body=raw.decode("utf-8"))
    title = "Synthetic candidate"
    create_id = "synthetic_create"
    prepared = candidate.prepare_candidate(request, raw, material, create_id, title)
    claimed = {"source_id": "synthetic_source", "sha256": hashlib.sha256(raw).hexdigest(), "duplicate": True}
    expected = prepared.document_create_request(claimed)
    original = {"source_id": claimed["source_id"], "name": "existing-duplicate-name.json",
                "media_type": "application/json", "sha256": claimed["sha256"],
                "content_base64": base64.b64encode(raw).decode("ascii")}
    # Construct synthetic Core-shaped data; IDs and digests are intentionally
    # artificial and do not assert that a Core process or storage was accessed.
    editor = copy.deepcopy(expected["editor_json"])
    blocks = []
    texts = []
    for index, node in enumerate(editor["content"]):
        block_id = f"blk_{index + 1:024x}"
        node["attrs"] = {"block_id": block_id}
        text = node["content"][0]["text"]
        texts.append(text)
        blocks.append({"block_id": block_id, "kind": "paragraph", "ordinal": index,
                       "node_json": copy.deepcopy(node), "text_projection": text, "codec_status": "known"})
    document_id = "doc_req_" + hashlib.sha256(create_id.encode("ascii")).hexdigest()
    document = {"document_id": document_id, "source_id": claimed["source_id"],
                "source_revision": claimed["sha256"], "title": title, "version": 1,
                "editor_json": editor, "text_projection": "\n".join(texts),
                "content_sha256": "2" * 64, "blocks": blocks, "revision_basis": None,
                "tags": [], "properties": {}, "metadata_status": "COMPLETE", "metadata_issues": []}
    snapshot = {"document_id": document["document_id"], "version": 1, "content_sha256": document["content_sha256"]}
    question = editor["attrs"]["archeaxis_deeptutor_question"]["question"]
    view = {"schema": "archeaxis.deeptutor-question-view/v1", "question_document": snapshot,
            "question_status": "current", "source_material": copy.deepcopy(material), "source_snapshot_status": "current",
            "source_reference": "declared_unverified", "question_document_origin": "unverified",
            "authorization_effect": "none", "question_version": "sha256:" + "3" * 64, "visible_sha256": "4" * 64,
            "question": {key: copy.deepcopy(question[key]) for key in ("question_id", "question", "question_type", "options")},
            "origin": "user_import_unverified", "provider_identity": "unverified", "provider_executed": False,
            "independent_mastery": "not_established"}
    return {"request": request, "raw": raw, "material": material, "create_id": create_id, "title": title,
            "import": claimed, "original": original, "create": copy.deepcopy(document),
            "document": document, "view": view}


def run(data, replacements=None):
    replacements = replacements or {}
    def response(name, code):
        return replacements.get(name, (code, wire(data[name])))
    return readback.reconcile(data["request"], data["raw"], data["material"], data["create_id"], data["title"],
        response("import", 202), response("original", 200), response("create", 201),
        response("document", 200), response("view", 200))


def rejected(data, reason, replacements=None):
    with pytest.raises(readback.ReadbackError) as failure:
        run(data, replacements)
    assert str(failure.value) == reason


def test_consistent_but_entirely_synthetic_receipts_are_only_conditionally_matched(capsys):
    data = fixture()
    result = run(data)
    assert result["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_LOCAL_EXPECTATIONS"
    assert result["response_identity"] == "CALLER_SUPPLIED_UNAUTHENTICATED"
    assert result["core_authentication"] == result["core_authorization"] == "NOT_ESTABLISHED"
    assert result["provider_generation"] == result["independent_mastery"] == "NOT_ESTABLISHED"
    assert result["document_content_sha256"] == "FORMAT_AND_REFERENCE_ONLY_NOT_RECOMPUTED"
    assert result["view_digests"] == result["block_id"] == "FORMAT_ONLY_NOT_RECOMPUTED"
    assert result["restart_durability"] == "NOT_ESTABLISHED"
    assert result["question_status"] == result["source_snapshot_status"] == "current"
    for private in ("Synthetic question", "Synthetic explanation", data["import"]["sha256"], "2" * 64, "3" * 64):
        assert private not in json.dumps(result)
    assert capsys.readouterr() == ("", "")


def test_multilingual_nonchoice_readback_keeps_empty_options_and_does_not_imply_grading():
    payload = {"question_type": "concept", "question": "合成命题 😀?", "correct_answer": "true", "explanation": "合成解释"}
    data = fixture(kind="concept", language="zh", payload=payload)
    assert len(data["document"]["editor_json"]["content"]) == 1
    assert data["view"]["question"]["options"] == {}
    result = run(data)
    assert result["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_LOCAL_EXPECTATIONS"
    assert result["independent_mastery"] == "NOT_ESTABLISHED"
    assert result["new_provider_execution"] == "NOT_AUTHORIZED"


def test_first_import_uses_core_source_identity_but_duplicate_may_keep_an_older_id():
    data = fixture()
    # A duplicate may report a source row with an existing non-derived ID.
    assert data["import"]["duplicate"] is True
    assert data["import"]["source_id"] == "synthetic_source"
    assert run(data)["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_LOCAL_EXPECTATIONS"
    # New Core rows derive the ID from the ASCII hex digest, not the raw bytes.
    digest = data["import"]["sha256"]
    identity = "src_" + hashlib.sha256(digest.encode("ascii")).hexdigest()[:24]
    data["import"].update(duplicate=False, source_id=identity)
    data["original"]["source_id"] = identity
    data["create"]["source_id"] = identity
    data["document"]["source_id"] = identity
    assert run(data)["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_LOCAL_EXPECTATIONS"


def test_first_import_rejects_coherent_but_incorrect_source_id():
    data = fixture()
    # Every response agrees on this ID, but it is not the Core new-row formula.
    data["import"]["duplicate"] = False
    rejected(data, "SOURCE_MISMATCH")
    wrong = "src_" + hashlib.sha256(data["raw"]).hexdigest()[:24]
    data["import"]["source_id"] = wrong
    data["original"]["source_id"] = wrong
    data["create"]["source_id"] = wrong
    data["document"]["source_id"] = wrong
    rejected(data, "SOURCE_MISMATCH")


@pytest.mark.parametrize("question_status", ["current", "historical"])
@pytest.mark.parametrize("source_status", ["current", "historical", "unavailable"])
def test_current_historical_and_unavailable_status_are_not_conflated(question_status, source_status):
    data = fixture()
    data["view"]["question_status"] = question_status
    data["view"]["source_snapshot_status"] = source_status
    result = run(data)
    assert result["question_status"] == question_status
    assert result["source_snapshot_status"] == source_status
    assert result["new_provider_execution"] == "NOT_AUTHORIZED"


@pytest.mark.parametrize("case", ["source_id", "source_sha", "source_bytes", "source_base64", "import_sha"])
def test_source_identity_and_exact_original_bytes_are_rechecked(case, capsys):
    data = fixture()
    data["original"]["name"] = "SYNTHETIC_PRIVATE_MARKER"
    if case == "source_id":
        data["original"]["source_id"] = "other"
    elif case == "source_sha":
        data["original"]["sha256"] = "0" * 64
    elif case == "source_bytes":
        data["original"]["content_base64"] = base64.b64encode(data["raw"] + b" ").decode("ascii")
    elif case == "source_base64":
        data["original"]["content_base64"] = "bad?"
    else:
        data["import"]["sha256"] = "0" * 64
    rejected(data, "SOURCE_MISMATCH")
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("case", ["answer", "explanation", "material", "body", "projection", "block_order", "block_id", "bool_ordinal", "bool_version", "missing_basis"])
def test_private_candidate_and_core_body_mismatches_fail_closed(case, capsys):
    data = fixture()
    document = data["document"]
    if case in {"answer", "explanation", "material"}:
        target = document["editor_json"]["attrs"]["archeaxis_deeptutor_question"]
        if case == "answer":
            target["question"]["correct_answer"] = "C"
        elif case == "explanation":
            target["question"]["explanation"] = "changed"
        else:
            target["source_material"]["version"] = True
    elif case == "body":
        document["editor_json"]["content"][0]["content"][0]["text"] = "changed"
    elif case == "projection":
        document["text_projection"] = "changed"
    elif case == "block_order":
        document["blocks"][0], document["blocks"][1] = document["blocks"][1], document["blocks"][0]
    elif case == "block_id":
        document["editor_json"]["content"][1]["attrs"]["block_id"] = document["editor_json"]["content"][0]["attrs"]["block_id"]
        document["blocks"][1]["block_id"] = document["blocks"][0]["block_id"]
        document["blocks"][1]["node_json"]["attrs"]["block_id"] = document["blocks"][0]["block_id"]
    elif case == "bool_ordinal":
        document["blocks"][1]["ordinal"] = True
    elif case == "bool_version":
        document["version"] = True
    else:
        del document["revision_basis"]
    rejected(data, "DOCUMENT_MISMATCH")
    assert capsys.readouterr() == ("", "")


def test_same_content_under_a_different_create_request_id_cannot_be_relabelled():
    data = fixture()
    # Core would produce a different document ID for this other request ID,
    # despite identical source and candidate content.
    data["create_id"] = "other_synthetic_create"
    rejected(data, "DOCUMENT_MISMATCH")


def test_swapping_even_all_reported_document_ids_does_not_match_the_create_id():
    data = fixture()
    other = "doc_req_" + hashlib.sha256(b"other_synthetic_create").hexdigest()
    data["create"]["document_id"] = other
    data["document"]["document_id"] = other
    data["view"]["question_document"]["document_id"] = other
    rejected(data, "DOCUMENT_MISMATCH")


def test_swapping_one_reported_document_id_is_rejected():
    data = fixture()
    data["document"]["document_id"] = "doc_req_" + "0" * 64
    rejected(data, "DOCUMENT_MISMATCH")


@pytest.mark.parametrize("case", ["identity", "version_bool", "content_hash", "material_bool", "visible", "option", "status", "digest", "answer_field"])
def test_question_view_snapshot_visible_fields_and_status_are_cross_checked(case):
    data = fixture()
    view = data["view"]
    if case == "identity":
        view["question_document"]["document_id"] = "different"
    elif case == "version_bool":
        view["question_document"]["version"] = True
    elif case == "content_hash":
        view["question_document"]["content_sha256"] = "0" * 64
    elif case == "material_bool":
        view["source_material"]["version"] = True
    elif case == "visible":
        view["question"]["question"] = "changed"
    elif case == "option":
        view["question"]["options"]["B"] = "changed"
    elif case == "status":
        view["question_status"] = []
    elif case == "digest":
        view["question_version"] = "sha256:not-a-digest"
    else:
        view["question"]["correct_answer"] = "B"
    rejected(data, "VIEW_MISMATCH")


@pytest.mark.parametrize("name,code", [("import", 202), ("original", 200), ("create", 201), ("document", 200), ("view", 200)])
def test_duplicate_json_members_are_rejected_at_every_wire_entry(name, code):
    data = fixture()
    encoded = wire(data[name])
    duplicated = encoded[:-1] + b',"__duplicate":1,"__duplicate":2}'
    rejected(data, "INVALID_RESPONSE_JSON", {name: (code, duplicated)})


@pytest.mark.parametrize("constant", [b"NaN", b"Infinity", b"1e999"])
def test_nonfinite_json_values_are_rejected_even_in_unmapped_fields(constant):
    data = fixture()
    raw = wire(data["document"])
    raw = raw[:-1] + b',"extra_number":' + constant + b'}'
    rejected(data, "INVALID_RESPONSE_JSON", {"document": (200, raw)})


@pytest.mark.parametrize("name,status,reason", [
    ("import", 403, "IMPORT_UNAVAILABLE"), ("original", 404, "SOURCE_UNAVAILABLE"),
    ("create", 409, "DOCUMENT_CREATE_UNAVAILABLE"), ("document", 404, "DOCUMENT_READ_UNAVAILABLE"),
    ("view", 422, "VIEW_UNAVAILABLE"),
])
def test_unavailable_http_claim_is_reported_by_stage_without_response_echo(name, status, reason):
    data = fixture()
    rejected(data, reason, {name: (status, b'{"private":"SYNTHETIC_PRIVATE_MARKER"}')})


def test_response_size_and_status_types_are_bounded():
    data = fixture()
    rejected(data, "INVALID_RESPONSE_ENVELOPE", {"original": (200, b" " * (readback._MAX_SOURCE_JSON + 1))})
    rejected(data, "INVALID_RESPONSE_ENVELOPE", {"document": (True, b"{}")})


def test_json_structure_budget_respects_quoted_delimiters_and_rejects_excess():
    data = fixture()
    document = wire(data["document"])
    safe = document[:-1] + b',"ignored":"[{\\\"}]:,"}'
    assert run(data, {"document": (200, safe)})["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_LOCAL_EXPECTATIONS"
    too_deep = b'{"extra":' + b"[" * 65 + b"0" + b"]" * 65 + b"}"
    rejected(data, "INVALID_RESPONSE_JSON", {"document": (200, too_deep)})
    too_many = b'{"extra":[' + b"0," * 20_001 + b"0]}"
    rejected(data, "INVALID_RESPONSE_JSON", {"document": (200, too_many)})


def test_unpaired_unicode_surrogate_is_rejected_even_in_unchecked_metadata():
    data = fixture()
    raw = wire(data["document"])
    raw = raw[:-1] + b',"extra":"\\ud800"}'
    rejected(data, "INVALID_RESPONSE_JSON", {"document": (200, raw)})


def test_active_event_loop_fails_closed_with_a_fixed_reason():
    data = fixture()

    async def inside_loop():
        rejected(data, "ACTIVE_EVENT_LOOP_UNSUPPORTED")

    asyncio.run(inside_loop())


def test_changing_answer_in_source_and_replay_does_not_validate_a_different_saved_candidate():
    data = fixture()
    changed = data["raw"].replace(b'"correct_answer":"B"', b'"correct_answer":"C"')
    data["raw"] = changed
    data["request"]["response_body"] = changed.decode("utf-8")
    data["import"]["sha256"] = hashlib.sha256(changed).hexdigest()
    data["original"]["sha256"] = data["import"]["sha256"]
    data["original"]["content_base64"] = base64.b64encode(changed).decode("ascii")
    data["document"]["source_revision"] = data["import"]["sha256"]
    data["create"]["source_revision"] = data["import"]["sha256"]
    rejected(data, "DOCUMENT_MISMATCH")


def test_changed_pinned_candidate_adapter_is_rejected(tmp_path, monkeypatch):
    source = (PROVIDER / "candidate_document.py").read_bytes()
    (tmp_path / "candidate_document.py").write_bytes(bytes([source[0] ^ 1]) + source[1:])
    monkeypatch.setattr(readback, "_ROOT", tmp_path)
    with pytest.raises(readback.ReadbackError) as failure:
        readback._read_candidate_source()
    assert str(failure.value) == "ADAPTER_UNAVAILABLE"


def recovered_fixture():
    data = fixture()
    data["raw"] = b"``FINISH\n" + data["raw"]
    digest = hashlib.sha256(data["raw"]).hexdigest()
    data["import"]["sha256"] = digest
    data["original"]["sha256"] = digest
    data["original"]["content_base64"] = base64.b64encode(data["raw"]).decode("ascii")
    data["create"]["source_revision"] = digest
    data["document"]["source_revision"] = digest
    return data


def run_recovered(data, replacements=None, **overrides):
    replacements = replacements or {}
    declaration = {"completed": True, "finish_reason": "stop", "tool_calls": [],
                   "function_call": None, "allow_recovery": True}
    declaration.update(overrides)

    def response(name, code):
        return replacements.get(name, (code, wire(data[name])))

    return readback.reconcile_recovered(data["request"], data["raw"], data["material"], data["create_id"], data["title"],
        response("import", 202), response("original", 200), response("create", 201),
        response("document", 200), response("view", 200), **declaration)


def test_recovered_readback_compares_complete_labeled_source_with_replayed_body(capsys):
    data = recovered_fixture()
    result = run_recovered(data)
    assert result["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_LOCAL_EXPECTATIONS"
    assert result["label_recovery"] == "OPT_IN_UPSTREAM_RESEARCH_HELPER_SUBSET"
    assert result["parser_path"] == "ORIGINAL_MODEL_TEXT_PARSER"
    assert result["completion_and_tools"] == "CALLER_DECLARED_UNVERIFIED"
    assert result["recovery_policy_persistence"] == "NOT_ESTABLISHED_BY_COMPARISON"
    assert result["core_authentication"] == result["core_authorization"] == "NOT_ESTABLISHED"
    assert result["restart_durability"] == result["independent_mastery"] == "NOT_ESTABLISHED"
    # A duplicate row may retain its former name and MIME, even though the
    # request that would be constructed for these bytes now uses a .txt name.
    assert data["import"]["duplicate"] is True
    assert data["original"]["name"] == "existing-duplicate-name.json"
    assert data["original"]["media_type"] == "application/json"
    for private in ("Synthetic question", "Synthetic explanation", data["import"]["sha256"]):
        assert private not in json.dumps(result)
    assert capsys.readouterr() == ("", "")


def test_recovered_readback_accepts_new_source_identity_with_text_name():
    data = recovered_fixture()
    digest = data["import"]["sha256"]
    identity = "src_" + hashlib.sha256(digest.encode("ascii")).hexdigest()[:24]
    data["import"].update(source_id=identity, duplicate=False)
    data["original"].update(source_id=identity, name="deeptutor-question-response.txt", media_type="text/plain")
    data["create"]["source_id"] = data["document"]["source_id"] = identity
    assert run_recovered(data)["status"] == "CALLER_SUPPLIED_READBACKS_MATCH_LOCAL_EXPECTATIONS"


@pytest.mark.parametrize("case,reason", [
    ("source_body", "SOURCE_MISMATCH"), ("source_id", "SOURCE_MISMATCH"),
    ("import_sha", "SOURCE_MISMATCH"), ("document_sha", "DOCUMENT_MISMATCH"),
    ("answer", "DOCUMENT_MISMATCH"), ("view", "VIEW_MISMATCH"),
])
def test_recovered_readback_rejects_spliced_sources_or_unmatched_documents(case, reason, capsys):
    data = recovered_fixture()
    if case == "source_body":
        body = data["request"]["response_body"].encode("utf-8")
        data["original"]["content_base64"] = base64.b64encode(body).decode("ascii")
    elif case == "source_id":
        data["original"]["source_id"] = "different"
    elif case == "import_sha":
        data["import"]["sha256"] = hashlib.sha256(data["request"]["response_body"].encode("utf-8")).hexdigest()
    elif case == "document_sha":
        data["document"]["source_revision"] = hashlib.sha256(data["request"]["response_body"].encode("utf-8")).hexdigest()
    elif case == "answer":
        for key in ("create", "document"):
            data[key]["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["correct_answer"] = "C"
    else:
        data["view"]["question"]["question"] = "different"
    with pytest.raises(readback.ReadbackError) as failure:
        run_recovered(data)
    assert str(failure.value) == reason
    assert capsys.readouterr() == ("", "")


def test_matching_body_only_receipts_do_not_stand_in_for_labeled_source():
    data = recovered_fixture()
    body = data["request"]["response_body"].encode("utf-8")
    data["raw"] = body
    digest = hashlib.sha256(body).hexdigest()
    data["import"]["sha256"] = data["original"]["sha256"] = digest
    data["original"]["content_base64"] = base64.b64encode(body).decode("ascii")
    data["create"]["source_revision"] = data["document"]["source_revision"] = digest
    with pytest.raises(readback.ReadbackError, match="^CANDIDATE_UNAVAILABLE$"):
        run_recovered(data)


def test_recovered_readback_reconstructs_answer_from_same_raw_even_when_receipts_are_consistent():
    data = recovered_fixture()
    data["raw"] = data["raw"].replace(b'"correct_answer":"B"', b'"correct_answer":"C"')
    digest = hashlib.sha256(data["raw"]).hexdigest()
    data["import"]["sha256"] = data["original"]["sha256"] = digest
    data["original"]["content_base64"] = base64.b64encode(data["raw"]).decode("ascii")
    data["create"]["source_revision"] = data["document"]["source_revision"] = digest
    # Replay still specifies B: the full labeled source cannot be spliced in.
    with pytest.raises(readback.ReadbackError, match="^CANDIDATE_UNAVAILABLE$"):
        run_recovered(data)
    # If replay is also changed to C, readback still cannot validate a document
    # whose stored private answer remains B.
    data["request"]["response_body"] = data["raw"].split(b"\n", 1)[1].decode("utf-8")
    with pytest.raises(readback.ReadbackError, match="^DOCUMENT_MISMATCH$"):
        run_recovered(data)


@pytest.mark.parametrize("declaration", [
    {"allow_recovery": False}, {"completed": False}, {"finish_reason": "length"},
    {"tool_calls": [{"name": "synthetic"}]}, {"function_call": {"name": "synthetic"}},
])
def test_recovered_readback_requires_same_opt_in_and_terminal_declaration(declaration):
    with pytest.raises(readback.ReadbackError, match="^CANDIDATE_UNAVAILABLE$"):
        run_recovered(recovered_fixture(), **declaration)

