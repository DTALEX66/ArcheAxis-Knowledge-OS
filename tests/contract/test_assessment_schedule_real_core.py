"""Synthetic review isolation through a real Core and the local FSRS worker."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def state_validator():
    schema = json.loads((ROOT / "packages/contracts/v1/core-document.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/LearningStateDto"})


def test_learning_state_contract_accepts_legacy_and_checks_optional_assessment_scope():
    check = state_validator()
    legacy = {"item_key": "legacy", "learner": {"event_count": 1, "correct_streak": 1,
        "scheduled_events": 1, "unscheduled_events": 0}}
    assert not list(check.iter_errors(legacy))
    progress = {"assessment_id": "a", "knowledge_id": "k", "knowledge_version": "k",
        "event_count": 0, "correct_streak": 0, "latest_review": None}
    scoped = {**legacy, "learner": {**legacy["learner"], "correct_streak_scope": "assessment",
        "aggregate_scope": "item_history", "next_review": None, "assessment_progress": progress}}
    assert not list(check.iter_errors(scoped))
    assert list(check.iter_errors({**scoped, "learner": {**scoped["learner"], "correct_streak_scope": "unknown"}}))
    assert list(check.iter_errors({**scoped, "learner": {**scoped["learner"], "assessment_progress": {
        **progress, "event_count": -1}}}))
    missing_identity = {key: value for key, value in progress.items() if key != "assessment_id"}
    assert list(check.iter_errors({**scoped, "learner": {**scoped["learner"], "assessment_progress": missing_identity}}))


def test_review_schema_requires_explicit_bounded_reset_identity_and_reason():
    schema = json.loads((ROOT / "packages/contracts/learning/v1/review.schema.json").read_text(encoding="utf-8"))
    check = Draft202012Validator(schema)
    base = {"item_key": "item", "client_event_id": "key", "correct": True}
    reset = {"mode": "start_new", "reason": "Known historical gap", "expected_latest_event_id": 17}
    assert not list(check.iter_errors(base))
    assert not list(check.iter_errors({**base, "schedule_reset": reset}))
    for invalid in ({**reset, "mode": "automatic"}, {**reset, "reason": "  "},
                    {**reset, "expected_latest_event_id": 0}, {**reset, "expected_latest_event_id": 9007199254740992},
                    {**reset, "extra": True}, {"mode": "start_new", "reason": "missing cursor"}):
        assert list(check.iter_errors({**base, "schedule_reset": invalid}))


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_unbound_review_boundary_survives_restart_and_restore(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)
    core_sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    core = Core(exe, tmp_path, Path(sys.executable))
    item = "synthetic-legacy-to-assessment"
    base = f"/api/v1/learning/items/{item}"
    legacy = {"item_key": item, "client_event_id": "legacy-before-assessment", "correct": True,
              "rating": 3, "now": "2026-10-01T00:00:00+00:00"}
    unbound = {**legacy, "client_event_id": "unbound-after-assessment", "now": "2026-10-01T00:10:00+00:00"}
    later_unbound = {**unbound, "client_event_id": "later-unbound"}
    event_item = "synthetic-legacy-event"
    old_event = {"item_key": event_item, "client_event_id": "legacy-event-before", "correct": True}
    new_event = {**old_event, "client_event_id": "legacy-event-after"}

    def call(method, path, body=None, expected=200):
        status, value = core.request(method, path, body)
        assert status == expected, (method, path, status, value)
        return value

    try:
        core.start()
        first = call("POST", "/api/v1/learning/reviews", legacy, expected=201)
        assert first["schedule_authority"] == "fsrs" and first["next_review"] == "2026-10-01T00:10:00+00:00"
        first_event = call("POST", "/api/v1/learning/events", old_event, expected=201)
        knowledge = call("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": "Synthetic assessed fact", "status": "accepted", "created_by": "fixture"}, expected=201)
        call("POST", base + "/references", {"knowledge_id": knowledge["knowledge_id"]}, expected=201)
        assessment = call("POST", base + "/assessment", {"knowledge_id": knowledge["knowledge_id"]}, expected=201)
        event_base = f"/api/v1/learning/items/{event_item}"
        call("POST", event_base + "/references", {"knowledge_id": knowledge["knowledge_id"]}, expected=201)
        call("POST", event_base + "/assessment", {"knowledge_id": knowledge["knowledge_id"]}, expected=201)
        assert call("POST", "/api/v1/learning/events", old_event)["event_id"] == first_event["event_id"]
        assert "assessment binding conflict" in call("POST", "/api/v1/learning/events", new_event, expected=409)["raw"]
        replay = call("POST", "/api/v1/learning/reviews", legacy)
        assert replay["duplicate"] is True and replay["event_id"] == first["event_id"]
        refusal = call("POST", "/api/v1/learning/reviews", unbound, expected=409)
        assert "assessment binding conflict" in refusal["raw"]
        pending = call("GET", base + "/state")
        assert pending["learner"]["event_count"] == 1
        assert pending["learner"]["assessment_progress"]["event_count"] == 0
        assert pending["learner"]["next_review"] is None
        bound = {**unbound, "assessment_id": assessment["assessment_id"], "knowledge_version": assessment["knowledge_version"]}
        accepted = call("POST", "/api/v1/learning/reviews", bound, expected=201)
        assert accepted["schedule_authority"] == "fsrs" and accepted["streak_after"] == 1
        assert accepted["next_review"] == "2026-10-01T00:20:00+00:00"
        state = call("GET", base + "/state")
        history = call("GET", f"/api/v1/learning/events/{item}")
        outcomes = [json.loads(row["outcome"]) for row in history["events"]]
        assert [row["assessment_id"] for row in outcomes] == [None, assessment["assessment_id"]]
        core.stop()
        core.start()
        assert call("GET", base + "/state") == state
        assert call("POST", "/api/v1/learning/reviews", legacy)["event_id"] == first["event_id"]
        assert "event_key conflict" in call("POST", "/api/v1/learning/reviews", unbound, expected=409)["raw"]
        assert call("POST", "/api/v1/learning/reviews", later_unbound, expected=409)["raw"] == refusal["raw"]
        backup = call("POST", "/api/v1/workspace/backups", {}, expected=201)
        assert backup["verified"] is True and Path(backup["filename"]).name == backup["filename"]
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        core.stop()
        destination = tmp_path / "independent-restore"
        destination.mkdir()
        result = subprocess.run([str(exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
            str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        restored = json.loads(result.stdout) if result.stdout else {}
        assert result.returncode == 0 and restored.get("ok") is True
        assert restored.get("authorization_requires_new_grants") is True
        core = Core(exe, destination, Path(sys.executable))
        core.start()
        assert call("GET", base + "/state") == state
        assert call("GET", f"/api/v1/learning/events/{item}") == history
        assert call("POST", "/api/v1/learning/reviews", legacy)["event_id"] == first["event_id"]
        assert call("POST", "/api/v1/learning/reviews", later_unbound, expected=409)["raw"] == refusal["raw"]
        assert call("POST", "/api/v1/learning/reviews", bound)["event_id"] == accepted["event_id"]
        assert call("POST", "/api/v1/learning/events", old_event)["event_id"] == first_event["event_id"]
        assert "assessment binding conflict" in call("POST", "/api/v1/learning/events", new_event, expected=409)["raw"]
        assert hashlib.sha256(exe.read_bytes()).hexdigest() == core_sha
        if output := os.environ.get("AAOS_TEST_UNBOUND_REVIEW_OUTPUT"):
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump({"synthetic": True, "core_sha256": core_sha, "legacy_replayed": True,
                    "new_unbound_refused": True, "legacy_event_refused": True,
                    "bound_review_fresh": True, "restarted": True,
                    "backup_verified": True, "independent_restore": True, "human_learning": "NOT_ESTABLISHED"}, stream)
    finally:
        core.stop()


@pytest.mark.skipif(not os.environ.get("AAOS_TEST_CORE_EXE"), reason="explicit real Core binary required")
def test_revision_starts_fresh_schedule_and_survives_restore(tmp_path):
    from scripts.ci.real_core_grading_journey import Core

    core_exe = Path(os.environ["AAOS_TEST_CORE_EXE"]).resolve(strict=True)
    core_sha = hashlib.sha256(core_exe.read_bytes()).hexdigest()
    core = Core(core_exe, tmp_path, Path(sys.executable))
    check_state = state_validator()
    item = "synthetic-revision-card"
    base = f"/api/v1/learning/items/{item}"

    def call(method, path, body=None, expected=200):
        status, result = core.request(method, path, body)
        assert status == expected, (method, path, status, result)
        return result

    def review(assessment, request_id, now):
        return {"item_key": item, "client_event_id": request_id, "correct": True, "rating": 3,
            "now": now, "answer": "synthetic learner answer", "assessment_id": assessment["assessment_id"],
            "knowledge_version": assessment["knowledge_version"]}

    try:
        core.start()
        original = call("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": "Synthetic old lesson", "status": "accepted", "created_by": "fixture"}, expected=201)
        old_id = original["knowledge_id"]
        call("POST", base + "/references", {"knowledge_id": old_id}, expected=201)
        old = call("POST", base + "/assessment", {"knowledge_id": old_id}, expected=201)
        old_review = call("POST", "/api/v1/learning/reviews", review(old, "old-review", "2026-10-01T00:00:00+00:00"), expected=201)
        assert old_review["schedule_authority"] == "fsrs"
        assert old_review["next_review"] == "2026-10-01T00:10:00+00:00"
        successor = call("POST", f"/api/v1/knowledge-items/{old_id}/review-decisions", {
            "action": "modified", "reviewer": "fixture", "new_body": "Synthetic revised lesson"})["knowledge_id"]
        call("POST", f"/api/v1/knowledge-items/{successor}/review-decisions", {"action": "accepted", "reviewer": "fixture"})
        call("POST", base + "/references", {"knowledge_id": successor}, expected=201)
        revised = call("POST", base + "/assessment", {"knowledge_id": successor}, expected=201)
        before = call("GET", base + "/state")
        assert not list(check_state.iter_errors(before))
        assert before["learner"]["assessment"]["assessment_id"] == revised["assessment_id"]
        assert before["learner"]["correct_streak"] == 0 and before["learner"]["next_review"] is None
        assert before["learner"]["latest_review"]["assessment_id"] == old["assessment_id"]
        assert before["learner"]["assessment_progress"]["event_count"] == 0
        request = review(revised, "new-review", "2026-10-01T00:10:00+00:00")
        result = call("POST", "/api/v1/learning/reviews", request, expected=201)
        assert result["schedule_authority"] == "fsrs" and result["schedule_state"]["state"] == "learning"
        assert result["schedule_state"]["step"] == 1 and result["next_review"] == "2026-10-01T00:20:00+00:00"
        assert result["streak_after"] == result["mastery_projection"]["attempts"] == 1
        history = call("GET", f"/api/v1/learning/events/{item}")
        assert history["count"] == 2
        outcomes = [json.loads(row["outcome"]) for row in history["events"]]
        assert [row["assessment_id"] for row in outcomes] == [old["assessment_id"], revised["assessment_id"]]
        state = call("GET", base + "/state")
        assert not list(check_state.iter_errors(state))
        assert state["learner"]["assessment_progress"]["event_count"] == 1
        assert state["learner"]["next_review"] == result["next_review"]
        assert next(row for row in call("GET", "/api/v1/learning/items")["items"] if row["item_key"] == item)["next_review"] == result["next_review"]
        core.stop()
        core.start()
        assert call("GET", base + "/state") == state
        replay = call("POST", "/api/v1/learning/reviews", request)
        assert replay["duplicate"] is True and replay["event_id"] == result["event_id"]
        assert call("GET", f"/api/v1/learning/events/{item}") == history
        backup = call("POST", "/api/v1/workspace/backups", {}, expected=201)
        assert backup["verified"] is True
        core.stop()
        assert Path(backup["filename"]).name == backup["filename"]
        artifact = tmp_path / "backups" / backup["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == backup["sha256"]
        destination = tmp_path / "independent-restore"
        destination.mkdir()
        completed = subprocess.run([str(core_exe), "--maintenance-restore", str(destination / "workspace.sqlite"),
            str(artifact)], capture_output=True, text=True, timeout=120, check=False)
        receipt = json.loads(completed.stdout) if completed.stdout else {}
        assert completed.returncode == 0 and receipt.get("ok") is True
        assert receipt.get("authorization_requires_new_grants") is True
        core = Core(core_exe, destination, Path(sys.executable))
        core.start()
        assert call("GET", base + "/state") == state
        assert call("GET", f"/api/v1/learning/events/{item}") == history
        assert hashlib.sha256(core_exe.read_bytes()).hexdigest() == core_sha
        if output := os.environ.get("AAOS_TEST_SCHEDULE_FIXTURE"):
            with Path(output).open("x", encoding="utf-8") as stream:
                json.dump({"before": before, "after": state}, stream, ensure_ascii=False)
    finally:
        core.stop()


@pytest.mark.skipif(not all(os.environ.get(key) for key in
                    ("AAOS_TEST_NODE", "AAOS_TEST_TYPESCRIPT", "AAOS_TEST_SCHEDULE_FIXTURE")),
                    reason="explicit Node, TypeScript and actual Core states required")
def test_generated_client_validates_actual_scoped_state_and_matches_host_digest():
    script = r"""
const fs = require("node:fs"), assert = require("node:assert/strict"), crypto = require("node:crypto");
const [typescriptPath, corePath, hostPath, rustPath, fixturePath, hostSchemaPath, coreSchemaPath] = process.argv.slice(1);
const ts = require(typescriptPath);
function load(path) {
  const source = fs.readFileSync(path, "utf8");
  const js = ts.transpileModule(source, {compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022
  }}).outputText;
  const loaded = {exports: {}}; new Function("module", "exports", js)(loaded, loaded.exports);
  return loaded.exports;
}
const core = load(corePath), host = load(hostPath), fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
for (const value of Object.values(fixture)) assert.equal(core.assertCoreDto("LearningStateDto", value), value);
const integrity = {state:"unverified",reason:"scheduled_gap_replay_unverified"};
const flagged = {...fixture.after, learner:{...fixture.after.learner, next_review:null, schedule_integrity:integrity}};
assert.equal(core.assertCoreDto("LearningStateDto", flagged), flagged);
const queue = {items:[{item_key:"item", next_review:null, schedule_integrity:integrity}],count:1};
assert.equal(core.assertCoreDto("LearningItemsDto", queue), queue);
assert.throws(() => core.assertCoreDto("LearningItemsDto", {items:[{...queue.items[0], schedule_integrity:{...integrity, reason:"invented"}}],count:1}));
const legacy = {item_key:"legacy",learner:{event_count:0,correct_streak:0,scheduled_events:0,unscheduled_events:0}};
assert.equal(core.assertCoreDto("LearningStateDto", legacy), legacy);
assert.throws(() => core.assertCoreDto("LearningStateDto", {...fixture.before, learner:{...fixture.before.learner, correct_streak_scope:"unknown"}}));
assert.throws(() => core.assertCoreDto("LearningStateDto", {...fixture.after, learner:{...fixture.after.learner, assessment_progress:{...fixture.after.learner.assessment_progress, event_count:-1}}}));
const {assessment_id, ...missingIdentity} = fixture.after.learner.assessment_progress;
assert.throws(() => core.assertCoreDto("LearningStateDto", {...fixture.after, learner:{...fixture.after.learner, assessment_progress:missingIdentity}}));
const rust = fs.readFileSync(rustPath, "utf8");
const digest = rust.match(/pub const CONTRACT_DIGEST: &str = "([a-f0-9]{64})"/);
assert.ok(digest); assert.equal(host.UI_HOST_CONTRACT_DIGEST, digest[1]);
const canonical = crypto.createHash("sha256").update(fs.readFileSync(hostSchemaPath)).update(Buffer.from([0])).update(fs.readFileSync(coreSchemaPath)).digest("hex");
assert.equal(host.UI_HOST_CONTRACT_DIGEST, canonical);
const hostRequest = {schema:"archeaxis.ui-host-request/v2", contract_digest:host.UI_HOST_CONTRACT_DIGEST,
  request_id:"synthetic", workspace_id:"a".repeat(32), restore_epoch:"initial", operation:"model.inventory.read", input:{}};
host.assertUiHostRequest(hostRequest);
assert.throws(() => host.assertUiHostRequest({...hostRequest, contract_digest:"3826d07e70d1d8dff5c421d8c6e8f704b5927683e48809ac47019ed996ec82bb"}));
"""
    result = subprocess.run([os.environ["AAOS_TEST_NODE"], "-e", script, os.environ["AAOS_TEST_TYPESCRIPT"],
        str(ROOT / "frontend/src/api/generated/core-contract.ts"), str(ROOT / "frontend/src/api/generated/ui-host-contract.ts"),
        str(ROOT / "crates/archeaxis-contracts/src/generated/ui_host.rs"), os.environ["AAOS_TEST_SCHEDULE_FIXTURE"],
        str(ROOT / "packages/contracts/v2/ui-host.schema.json"), str(ROOT / "packages/contracts/v1/core-document.schema.json")],
        check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_learning_schedule_integrity_is_optional_but_reason_is_typed():
    schema = json.loads((ROOT / "packages/contracts/v1/core-document.schema.json").read_text(encoding="utf-8"))
    def validate(name):
        return Draft202012Validator({"$defs": schema["$defs"], "$ref": f"#/$defs/{name}"})
    integrity = {"state": "unverified", "reason": "scheduled_gap_replay_unverified"}
    state = {"item_key": "item", "learner": {"event_count": 1, "correct_streak": 1,
        "scheduled_events": 1, "unscheduled_events": 0, "next_review": None, "schedule_integrity": integrity}}
    queue = {"items": [{"item_key": "item", "next_review": None, "schedule_integrity": integrity}], "count": 1}
    assert not list(validate("LearningStateDto").iter_errors(state))
    assert not list(validate("LearningItemsDto").iter_errors(queue))
    bad = {"state": "unverified", "reason": "invented"}
    assert list(validate("LearningStateDto").iter_errors({**state, "learner": {**state["learner"], "schedule_integrity": bad}}))
    assert list(validate("LearningItemsDto").iter_errors({**queue, "items": [{**queue["items"][0], "schedule_integrity": bad}]}))
