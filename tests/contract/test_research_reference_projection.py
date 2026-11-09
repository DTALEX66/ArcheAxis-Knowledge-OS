"""Research reference state is an observation beside an immutable snapshot."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def validator():
    schema = json.loads((ROOT / "packages/contracts/v1/core-document.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/ResearchReferenceProjectionDto"})


def test_research_projection_schema_bounds():
    projection = {"schema": "archeaxis.research-reference-projection/v1",
        "document": {"document_id": "doc", "version": 1, "content_sha256": "a" * 64},
        "metadata_status": "supported", "references": [{"entry_kind": "material", "entry_id": "m1",
            "field": "reference", "index": 0,
            "reference": {"kind": "document", "document_id": "source", "version": 1},
            "status": "unavailable", "object": None}]}
    check = validator()
    assert not list(check.iter_errors(projection))
    unconfirmed = {**projection["references"][0], "status": "resolved", "object": {},
                   "version_relation": "unconfirmed", "current_version": 0}
    assert not list(check.iter_errors({**projection, "references": [unconfirmed]}))
    assert list(check.iter_errors({**projection, "references": [{**unconfirmed, "version_relation": "verified"}]}))
    assert list(check.iter_errors({**projection, "metadata_status": "verified"}))
    assert list(check.iter_errors({**projection, "references": projection["references"] * 257}))
    assert list(check.iter_errors({**projection, "extra": "invalid"}))


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_real_core_research_projection_matches_contract_and_restart(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    core = Core(Path(os.environ["AAOS_TEST_CORE_EXE"]), tmp_path, Path(sys.executable))
    check = validator()
    try:
        core.start()
        status, material = core.request("POST", "/api/v1/documents", {
            "title": "Synthetic material", "editor_json": {"type": "doc", "content": []}})
        assert status == 201
        reference = {"kind": "document", "document_id": material["document_id"], "version": 1, "block_id": None}
        status, research = core.request("POST", "/api/v1/documents", {
            "title": "Synthetic research", "editor_json": {"type": "doc", "content": [], "attrs": {
                "archeaxis_research": {"schema": "archeaxis.research/v1", "question": "Synthetic",
                    "materials": [{"id": "source", "note": "Synthetic", "reference": reference}],
                    "hypotheses": [], "methods": [], "experiments": [], "counterevidence": [],
                    "conclusions": [], "unresolved": []}}}})
        assert status == 201
        path = f"/api/v1/documents/{research['document_id']}/research-references?version=1"
        status, before = core.request("GET", path)
        assert status == 200 and not list(check.iter_errors(before))
        assert before["references"][0]["object"]["version_relation"] == "current"
        assert before["references"][0]["version_relation"] == "current"
        status, _ = core.request("PUT", f"/api/v1/documents/{material['document_id']}/draft", {
            "expected_version": 1, "editor_json": {"type": "doc", "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "synthetic revision"}]}]}})
        assert status == 200
        status, after = core.request("GET", path)
        assert status == 200 and not list(check.iter_errors(after))
        assert after["document"] == before["document"]
        assert after["references"][0]["reference"] == reference
        assert after["references"][0]["object"]["version_relation"] == "historical"
        assert after["references"][0]["version_relation"] == "historical"
        assert after["references"][0]["current_version"] == 2
        core.stop()
        core.start()
        status, reopened = core.request("GET", path)
        assert status == 200 and reopened == after and not list(check.iter_errors(reopened))
        if output := os.environ.get("AAOS_TEST_RESEARCH_OUTPUT"):
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump({"before": before, "after": after, "reopened": reopened}, stream)
    finally:
        core.stop()


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE") or not os.environ.get("AAOS_TEST_BRIDGE_EXE"),
                    reason="explicit real Core and compiled host bridge binaries required")
def test_host_bridge_to_real_core_research_projection(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    core = Core(Path(os.environ["AAOS_TEST_CORE_EXE"]), tmp_path, Path(sys.executable))
    try:
        core.start()
        env = dict(os.environ, AAOS_SYNTHETIC_CORE_PORT=str(core.port), AAOS_SYNTHETIC_CORE_TOKEN=core.token)
        result = subprocess.run([os.environ["AAOS_TEST_BRIDGE_EXE"], "research_reference_real_core_transport",
                                 "--ignored", "--test-threads=1"], env=env, check=False)
        assert result.returncode == 0
    finally:
        core.stop()


@pytest.mark.skipif(not all(os.environ.get(key) for key in
                        ("AAOS_TEST_NODE", "AAOS_TEST_TYPESCRIPT", "AAOS_TEST_RESEARCH_FIXTURE")),
                    reason="explicit Node, TypeScript and real Core synthetic projections required")
def test_generated_client_validator_accepts_real_core_research_projection():
    script = r"""
const fs = require("node:fs"), assert = require("node:assert/strict");
const [typescriptPath, contractPath, fixturePath] = process.argv.slice(1);
const ts = require(typescriptPath);
const source = fs.readFileSync(contractPath, "utf8");
const js = ts.transpileModule(source, {compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022
}}).outputText;
const loaded = {exports: {}};
new Function("module", "exports", js)(loaded, loaded.exports);
const validate = loaded.exports.assertCoreDto;
const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
for (const projection of Object.values(fixture))
    assert.equal(validate("ResearchReferenceProjectionDto", projection), projection);
assert.throws(() => validate("ResearchReferenceProjectionDto", {...fixture.before, metadata_status: "verified"}));
assert.throws(() => validate("ResearchReferenceProjectionDto", {...fixture.before, extra: true}));
assert.throws(() => validate("ResearchReferenceProjectionDto", {...fixture.before,
    references: [{...fixture.before.references[0], version_relation: "verified"}]}));
assert.throws(() => validate("ResearchReferenceProjectionDto", {...fixture.before,
    references: Array(257).fill(fixture.before.references[0])}));
"""
    result = subprocess.run([os.environ["AAOS_TEST_NODE"], "-e", script, os.environ["AAOS_TEST_TYPESCRIPT"],
        str(ROOT / "frontend/src/api/generated/core-contract.ts"), os.environ["AAOS_TEST_RESEARCH_FIXTURE"]],
        check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
