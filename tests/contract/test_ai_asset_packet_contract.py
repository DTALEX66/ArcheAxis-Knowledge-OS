"""AI context packets must validate the reference states emitted by Core."""

import json
import os
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def validator_for(name):
    schema = json.loads((ROOT / "packages/contracts/v2/ai-asset.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator({"$defs": schema["$defs"], "$ref": f"#/$defs/{name}"})


def test_packet_items_accept_reference_states_and_legacy_shape():
    validator = validator_for("AssetPacketItem")
    item = {"snapshot": {"document_id": "asset_1", "version": 1, "content_sha256": "a" * 64},
        "kind": "rule", "content": "synthetic", "purpose": "synthetic", "scope": [], "provenance": [],
        "engine_execution": "NOT_EXECUTED", "grants_professional_truth": False,
        "grants_human_mastery": False, "grants_machine_qualification": False}
    document = {"reference": {"kind": "document", "document_id": "doc_1", "version": 1},
        "readable": True, "currentness": "not_applicable"}
    knowledge = {"reference": {"kind": "knowledge", "knowledge_id": "k_1"}, "readable": True,
        "status": "accepted", "currentness": "superseded", "active": False,
        "superseded_by": "k_2", "successor_count": 1, "valid_to": None}
    unknown = {"reference": {"kind": "knowledge", "knowledge_id": "k_missing"},
        "readable": False, "status": "missing", "currentness": "unavailable"}
    source = {"reference": {"kind": "source", "source_id": "src_1", "sha256": "b" * 64},
        "readable": True, "currentness": "not_applicable"}
    assert not list(validator.iter_errors(item))  # old packets remain readable
    assert not list(validator.iter_errors({**item, "reference_states": [document, knowledge, unknown, source]}))
    assert list(validator.iter_errors({**item, "reference_states": [{**document, "currentness": "verified"}]}))
    assert list(validator.iter_errors({**item, "reference_states": [{**knowledge, "extra": "invalid"}]}))
    assert list(validator.iter_errors({**item, "reference_states": [{**unknown, "readable": True}]}))
    assert list(validator.iter_errors({**item, "reference_states": [{**knowledge, "reference": document["reference"]}]}))
    assert list(validator.iter_errors({**item, "reference_states": [{**document, "reference": knowledge["reference"]}]}))
    assert list(validator.iter_errors({**item, "reference_states": [document] * 65}))


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_real_core_packet_schema_and_historical_reference_state(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    def snapshot(value):
        return {key: value[key] for key in ("document_id", "version", "content_sha256")}

    validator = validator_for("AssetPacketResponse")
    core = Core(Path(os.environ["AAOS_TEST_CORE_EXE"]), tmp_path, Path(sys.executable))
    try:
        core.start()
        status, document = core.request("POST", "/api/v1/documents", {
            "title": "Synthetic provenance", "editor_json": {"type": "doc", "content": []}})
        assert status == 201
        doc_ref = {"kind": "document", "document_id": document["document_id"], "version": 1, "block_id": None}
        status, knowledge = core.request("POST", "/api/v1/knowledge-items", {
            "knowledge_type": "FACTUAL_CLAIM", "body": "Synthetic provenance fact",
            "status": "accepted", "created_by": "synthetic owner"})
        assert status == 201
        knowledge_ref = {"kind": "knowledge", "knowledge_id": knowledge["knowledge_id"]}
        asset = {"schema": "archeaxis.ai-asset/v1", "kind": "rule", "content": "synthetic rule",
            "purpose": "synthetic purpose", "scope": [doc_ref], "provenance": [knowledge_ref],
            "expires_at": None, "state": "candidate", "members": [], "conflicts": [],
            "revises": None, "review": None, "source_payload": None}
        status, candidate = core.request("POST", "/api/v1/documents", {
            "title": "Synthetic asset", "editor_json": {"type": "doc", "content": [],
                "attrs": {"archeaxis_ai_asset": asset}}})
        assert status == 201
        status, rubric = core.request("POST", "/api/v1/machine/rubrics", {
            "schema": "archeaxis.machine-rubric/v1", "request_id": "synthetic_rubric",
            "title": "Synthetic rubric", "purpose": "synthetic purpose", "sources": [],
            "criteria": [{"criterion_id": "fit", "label": "fit", "expectation": "synthetic observation"}]})
        assert status == 201
        editor = candidate["editor_json"]
        editor["attrs"]["archeaxis_ai_asset"]["state"] = "adopted"
        editor["attrs"]["archeaxis_ai_asset"]["review"] = {
            "asset": snapshot(candidate), "rubric": snapshot(rubric), "reviewer": "synthetic owner",
            "basis": "synthetic observation", "judgments": [{"criterion_id": "fit", "outcome": "passed",
                "basis": "synthetic observation"}], "outcome": "passed"}
        status, adopted = core.request("PUT", f"/api/v1/documents/{candidate['document_id']}/draft", {
            "expected_version": 1, "editor_json": editor})
        assert status == 200
        grant = {"schema": "archeaxis.asset-context-grant/v1", "asset": snapshot(adopted),
            "purpose": "synthetic purpose", "consumer": "manual-context-packet", "operations": ["read_packet"],
            "authorization_basis": "synthetic explicit grant", "expires_at": None, "state": "granted"}
        status, granted = core.request("POST", "/api/v1/documents", {
            "title": "Synthetic grant", "editor_json": {"type": "doc", "content": [],
                "attrs": {"archeaxis_asset_context_grant": grant}}})
        assert status == 201
        request = {"request_id": "synthetic_packet", "asset": snapshot(adopted), "grant": snapshot(granted),
            "purpose": "synthetic purpose", "consumer": "manual-context-packet", "operation": "read_packet"}
        status, first = core.request("POST", "/api/v1/ai/context-packets", request)
        assert status == 200
        assert not list(validator.iter_errors(first))
        states = first["packet"]["items"][0]["reference_states"]
        assert states[0]["reference"] == doc_ref and states[0]["currentness"] == "not_applicable"
        assert states[1]["reference"] == knowledge_ref and states[1]["currentness"] == "current"
        core.stop()
        core.start()
        status, replay = core.request("POST", "/api/v1/ai/context-packets", request)
        assert status == 200 and replay["duplicate"] is True
        assert replay["packet_sha256"] == first["packet_sha256"]
        assert not list(validator.iter_errors(replay))
        status, updated = core.request("PUT", f"/api/v1/documents/{document['document_id']}/draft", {
            "expected_version": 1, "editor_json": {"type": "doc", "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "new synthetic version"}]}]}})
        assert status == 200 and updated["version"] == 2
        status, after_document_change = core.request("POST", "/api/v1/ai/context-packets", request)
        assert status == 200 and after_document_change["duplicate"] is True
        assert after_document_change["packet_sha256"] == first["packet_sha256"]
        status, revised = core.request("POST", f"/api/v1/knowledge-items/{knowledge['knowledge_id']}/review-decisions", {
            "action": "modified", "reviewer": "synthetic owner", "new_body": "Synthetic corrected fact"})
        assert status == 200
        status, _ = core.request("POST", "/api/v1/ai/context-packets", request)
        assert status == 409  # changed knowledge state cannot reuse an earlier frozen packet identity
        status, fresh = core.request("POST", "/api/v1/ai/context-packets", {**request, "request_id": "synthetic_packet_after"})
        assert status == 200 and not list(validator.iter_errors(fresh))
        state = fresh["packet"]["items"][0]["reference_states"][1]
        assert state["reference"] == knowledge_ref and state["currentness"] == "superseded"
        assert state["superseded_by"] == revised["knowledge_id"]
        if output := os.environ.get("AAOS_TEST_PACKET_OUTPUT"):
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump({"initial": first, "replay": replay, "after_document_change": after_document_change,
                           "revised": fresh}, stream)
    finally:
        core.stop()
