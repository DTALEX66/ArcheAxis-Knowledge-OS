"""The relation-node schema accepts current Core observations without widening input."""

import json
import os
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def test_relation_node_supports_legacy_and_explicit_use_states():
    schema = json.loads((ROOT / "packages/contracts/v1/core-document.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/RelationNodeDto"})
    document = {"key": "document", "reference": {"kind": "document", "document_id": "doc_1", "version": 1},
                "status": "resolved", "object": {"current_version": 2, "version_relation": "historical"}}
    knowledge = {"key": "knowledge", "reference": {"kind": "knowledge", "knowledge_id": "k_1"},
                 "status": "resolved", "object": {}, "currentness": "superseded"}
    assert not list(validator.iter_errors(document))  # legacy node remains valid
    assert not list(validator.iter_errors(knowledge))
    assert not list(validator.iter_errors({**document, "version_relation": "historical"}))
    assert list(validator.iter_errors({**document, "version_relation": "verified"}))
    assert list(validator.iter_errors({**knowledge, "currentness": "verified"}))
    assert list(validator.iter_errors({**document, "transport_url": "http://invalid"}))


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_real_core_relation_projection_matches_schema_across_revision_and_restart(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    schema = json.loads((ROOT / "packages/contracts/v1/core-document.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/RelationProjectionDto"})
    core = Core(Path(os.environ["AAOS_TEST_CORE_EXE"]), tmp_path, Path(sys.executable))
    try:
        core.start()
        status, material = core.request("POST", "/api/v1/documents", {
            "title": "Synthetic material", "editor_json": {"type": "doc", "content": []}})
        assert status == 201
        reference = {"kind": "document", "document_id": material["document_id"], "version": 1, "block_id": None}
        status, knowledge = core.request("POST", "/api/v1/knowledge-items", {
            "knowledge_type": "FACTUAL_CLAIM", "body": "Synthetic fact",
            "status": "accepted", "created_by": "synthetic owner"})
        assert status == 201
        knowledge_reference = {"kind": "knowledge", "knowledge_id": knowledge["knowledge_id"]}
        status, research = core.request("POST", "/api/v1/documents", {
            "title": "Synthetic relation", "editor_json": {"type": "doc", "content": [], "attrs": {
                "archeaxis_relations": {"schema": "archeaxis.relations/v1", "relations": [
                    {"id": "source", "kind": "supports", "label": "source", "target": reference},
                    {"id": "fact", "kind": "supports", "label": "fact", "target": knowledge_reference}]}}}})
        assert status == 201
        path = f"/api/v1/documents/{research['document_id']}/relations?version=1"
        status, before = core.request("GET", path)
        assert status == 200
        assert not list(validator.iter_errors(before))
        def target(graph):
            return next(node for node in graph["nodes"] if node["reference"] == reference)
        assert target(before)["version_relation"] == "current"
        knowledge_node = next(node for node in before["nodes"] if node["reference"] == knowledge_reference)
        assert knowledge_node["currentness"] == "current"
        status, updated = core.request("PUT", f"/api/v1/documents/{material['document_id']}/draft", {
            "expected_version": 1, "editor_json": {"type": "doc", "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "updated"}]}]}})
        assert status == 200 and updated["version"] == 2
        status, after = core.request("GET", path)
        assert status == 200
        assert not list(validator.iter_errors(after))
        assert target(after)["version_relation"] == "historical"
        assert target(after)["object"]["current_version"] == 2
        assert target(after)["object"]["content_sha256"] == material["content_sha256"]
        core.stop()
        core.start()
        status, reopened = core.request("GET", path)
        assert status == 200 and target(reopened) == target(after)
        assert not list(validator.iter_errors(reopened))
    finally:
        core.stop()
