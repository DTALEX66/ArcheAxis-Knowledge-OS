"""Teaching records must accept the knowledge state actually returned by Core."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def validator(path, name):
    schema = json.loads((ROOT / path).read_text(encoding="utf-8"))
    return Draft202012Validator({"$defs": schema["$defs"], "$ref": f"#/$defs/{name}"})


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_real_core_teaching_view_and_receipt_include_knowledge_state(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    core = Core(Path(os.environ["AAOS_TEST_CORE_EXE"]), tmp_path, Path(sys.executable))
    view_check = validator("packages/contracts/v2/teaching.schema.json", "RecordView")
    working_check = validator("packages/contracts/v2/ui-working-state.schema.json", "RecordView")
    receipt_check = validator("packages/contracts/v2/teaching.schema.json", "WriteReceipt")
    try:
        core.start()
        status, knowledge = core.request("POST", "/api/v1/knowledge-items", {
            "knowledge_type": "FACTUAL_CLAIM", "body": "Synthetic knowledge",
            "status": "accepted", "created_by": "synthetic owner"})
        assert status == 201
        kid = knowledge["knowledge_id"]
        record = {"schema": "archeaxis.teaching-record/v2", "record_id": "synthetic_observation",
            "kind": "observation", "knowledge_id": kid, "knowledge_version": kid,
            "course_id": None, "parent_id": None, "purpose": "synthetic learning",
            "scope": "personal", "privacy": "local_only", "content": "synthetic note",
            "feedback_class": None, "assessment_id": None, "rubric_version": None,
            "assisted": False, "producer_kind": "human_authored"}
        status, created = core.request("POST", "/api/v2/teaching/records", record)
        assert status == 201
        assert not list(receipt_check.iter_errors(created))
        view = created["item"]
        assert not list(view_check.iter_errors(view))
        assert not list(working_check.iter_errors(view))
        assert view["knowledge_state"]["currentness"] == "current"
        legacy = {key: value for key, value in view.items() if key != "knowledge_state"}
        assert not list(view_check.iter_errors(legacy))
        assert not list(working_check.iter_errors(legacy))
        invalid = {**view, "knowledge_state": {**view["knowledge_state"], "currentness": "verified"}}
        assert list(view_check.iter_errors(invalid))
        assert list(working_check.iter_errors(invalid))
        invalid = {**view, "knowledge_state": {**view["knowledge_state"], "extra": "invalid"}}
        assert list(view_check.iter_errors(invalid))
        status, page = core.request("GET", "/api/v2/teaching/records")
        assert status == 200 and not list(validator("packages/contracts/v2/teaching.schema.json", "RecordPage").iter_errors(page))
        status, successor = core.request("POST", f"/api/v1/knowledge-items/{kid}/review-decisions", {
            "action": "modified", "reviewer": "synthetic owner", "new_body": "Synthetic corrected knowledge"})
        assert status == 200
        status, after = core.request("GET", "/api/v2/teaching/records/synthetic_observation")
        assert status == 200 and not list(view_check.iter_errors(after))
        assert after["knowledge_state"]["knowledge_id"] == kid
        assert after["knowledge_state"]["currentness"] == "superseded"
        assert after["knowledge_state"]["superseded_by"] == successor["knowledge_id"]
        assert after["record"] == view["record"] and after["content_sha256"] == view["content_sha256"]
        core.stop()
        core.start()
        status, reopened = core.request("GET", "/api/v2/teaching/records/synthetic_observation")
        assert status == 200 and reopened == after
        assert not list(working_check.iter_errors(reopened))
        if output := os.environ.get("AAOS_TEST_TEACHING_OUTPUT"):
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump({"created": created, "after": after, "legacy": legacy, "page": page}, stream)
    finally:
        core.stop()


@pytest.mark.skipif(not all(os.environ.get(key) for key in
                        ("AAOS_TEST_NODE", "AAOS_TEST_TYPESCRIPT", "AAOS_TEST_TEACHING_FIXTURE")),
                    reason="explicit Node, TypeScript and real Core synthetic teaching records required")
def test_generated_client_validators_accept_the_real_teaching_state():
    script = r"""
const fs=require("node:fs"), assert=require("node:assert/strict");
const [typescriptPath, teachingPath, statePath, fixturePath]=process.argv.slice(1), ts=require(typescriptPath);
function load(path) {
  const js=ts.transpileModule(fs.readFileSync(path,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const loaded={exports:{}}; new Function("module","exports",js)(loaded,loaded.exports); return loaded.exports;
}
const teaching=load(teachingPath), state=load(statePath), fixture=JSON.parse(fs.readFileSync(fixturePath,"utf8"));
for(const value of [fixture.created.item,fixture.after,fixture.legacy]) {
  assert.equal(teaching.assertTeachingDto("RecordView",value),value);
  assert.equal(state.assertUiWorkingState("RecordView",value),value);
}
assert.equal(teaching.assertTeachingDto("WriteReceipt",fixture.created),fixture.created);
assert.equal(teaching.assertTeachingDto("RecordPage",fixture.page),fixture.page);
const invalid={...fixture.after,knowledge_state:{...fixture.after.knowledge_state,currentness:"verified"}};
assert.throws(()=>teaching.assertTeachingDto("RecordView",invalid));
assert.throws(()=>state.assertUiWorkingState("RecordView",invalid));
"""
    result = subprocess.run([os.environ["AAOS_TEST_NODE"], "-e", script, os.environ["AAOS_TEST_TYPESCRIPT"],
        str(ROOT / "frontend/src/api/generated/teaching-contract.ts"),
        str(ROOT / "frontend/src/api/generated/ui-working-state-contract.ts"), os.environ["AAOS_TEST_TEACHING_FIXTURE"]],
        check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
