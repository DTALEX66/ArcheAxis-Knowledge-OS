"""Finite original-CAS relation input and transport contract boundaries."""
import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "packages/contracts/v1/core-document.schema.json").read_text("utf-8"))


def validator(name):
    return Draft202012Validator({"$ref": "#/$defs/" + name, "$defs": SCHEMA["$defs"]})


def request():
    return {"workspace_id": "workspace", "restore_epoch": "epoch", "source_id": "src_original",
            "source_revision": "a" * 64, "document_id": "doc_original", "expected_version": 1,
            "content_sha256": "b" * 64, "targets": [{"ordinal": 2, "source_id": "src_attachment",
            "source_revision": "c" * 64, "document": None}]}


def test_original_binding_is_finite_and_rejects_extra_claims():
    check = validator("IngestRelationsApplyInput")
    assert check.is_valid(request())
    for field, bad in [("expected_version", 0), ("source_revision", "wrong"),
                       ("targets", request()["targets"] * 201), ("source_id", "../outside")]:
        value = request()
        value[field] = bad
        assert not check.is_valid(value), field
    value = request()
    value["links"] = [{"status": "resolved"}]
    assert not check.is_valid(value), "the caller cannot supply parsed business relations"
    value = request()
    value["targets"][0]["foreign_batch_id"] = "other"
    assert not check.is_valid(value)
    value = request()
    value["targets"][0]["document"] = {"document_id": "doc", "version": 1, "content_sha256": "d" * 64}
    assert check.is_valid(value)
    del value["targets"][0]["document"]["content_sha256"]
    assert not check.is_valid(value), "a target document requires its fixed content identity"


def test_operation_and_openapi_reuse_canonical_definitions():
    commands = json.loads((ROOT / "packages/contracts/v1/core-command.schema.json").read_text("utf-8"))
    assert commands["properties"]["operation"]["enum"].count("ingest_member_relations_apply") == 1
    outline = yaml.safe_load((ROOT / "packages/contracts/v1/openapi-outline.yaml").read_text("utf-8"))
    op = outline["paths"]["/api/v1/ingest-batches/{batch_id}/members/{ordinal}/relations"]["post"]
    assert op["x-allowed-actor"] == "human"
    assert op["x-max-request-bytes"] == 256 * 1024
    assert op["requestBody"]["content"]["application/json"]["schema"] == {"$ref": "./core-document.schema.json#/$defs/IngestRelationsApplyInput"}
    assert op["responses"]["200"]["content"]["application/json"]["schema"] == {"$ref": "./core-document.schema.json#/$defs/IngestRelationsDto"}
    assert {"400", "401", "403", "404", "409", "413", "422"} <= op["responses"].keys()
    Draft202012Validator.check_schema(copy.deepcopy(SCHEMA))


def test_explicit_fragment_binding_remains_bounded_and_cannot_supply_other_claims():
    check = validator("IngestRelationsApplyInput")
    value = request()
    binding = {"link_ordinal": 0, "target_ordinal": 2, "fragment": "Heading",
               "fragment_is_block": False, "block_id": "block_a"}
    value["fragment_bindings"] = [binding]
    assert check.is_valid(value)
    for key, bad in [("link_ordinal", 256), ("target_ordinal", 10000), ("fragment", ""),
                     ("block_id", "../outside"), ("fragment_is_block", "false"),
                     ("resolution", "automatic")]:
        changed = copy.deepcopy(value)
        changed["fragment_bindings"][0][key] = bad
        assert not check.is_valid(changed), key
    value["fragment_bindings"] = [binding] * 257
    assert not check.is_valid(value)


def test_embed_presentation_extends_existing_relation_without_changing_ordinary_links():
    check = validator("RelationDto")
    relation = {"id": "existing", "kind": "related", "label": "Authored link",
                "target": {"kind": "document", "document_id": "peer", "version": 1}}
    assert check.is_valid(relation)
    assert check.is_valid({**relation, "presentation": "embed"})
    for invalid in ("execute_html", None, [], {"mode": "embed"}):
        assert not check.is_valid({**relation, "presentation": invalid})
    assert not check.is_valid({**relation, "presentation": "embed", "execute": True})
    updated = SCHEMA["$defs"]["IngestRelationsDto"]["properties"]["updated_relations"]
    count = Draft202012Validator(updated)
    assert count.is_valid(0) and count.is_valid(2)
    assert not count.is_valid(-1) and not count.is_valid("1")
