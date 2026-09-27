"""Negative controls for the synthetic M0 protocol probe, not real M0 evidence."""
import copy
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "m0_verdict_test", Path(__file__).parents[1] / "scripts/probes/m0_full_loop_smoke.py"
)
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


def complete_receipt():
    stages = [dict(stage=name, status=200) for name in (
        "import_source", "enqueue", "execute", "transform_readback",
        "promote_anchored_knowledge", "knowledge_v3_readback", "search", "human_accept",
        "knowledge_v3_after_accept", "learning_reference", "learning_event",
        "learning_event_replay", "assessment", "answer_recorded", "learning_state",
        "machine_task_failed", "human_correction", "accept_successor", "machine_retest",
        "machine_readback", "pre_restart_learning_state", "restart_learning_state", "restart_knowledge_v3")]
    by = {s["stage"]: s for s in stages}
    by["import_source"]["source_id"] = "s1"
    by["transform_readback"].update(transform_id="t1", text_chars=20)
    by["promote_anchored_knowledge"].update(knowledge_id="k1", anchor_id="a1")
    by["search"].update(items=1, source_found=True)
    by["knowledge_v3_after_accept"]["status_value"] = "accepted"
    by["learning_event_replay"]["duplicate"] = True
    by["assessment"].update(assessment_id="a", knowledge_version="k1")
    by["answer_recorded"].update(schedule_authority="fsrs", next_review="tomorrow")
    for name in ("learning_state", "restart_learning_state"):
        by[name].update(answer=probe.ANSWER, next_review="tomorrow", state={"id": "l1"})
    by["pre_restart_learning_state"]["state"] = {"id": "l1"}
    by["machine_task_failed"]["task_id"] = "m1"
    by["human_correction"]["successor_id"] = "k2"
    for name in ("machine_retest", "machine_readback"):
        by[name].update(task_id="m2", retest_of="m1", knowledge_version="k2")
    for name in ("knowledge_v3_readback", "restart_knowledge_v3"):
        by[name].update(knowledge_id="k1", anchor_id="a1")
    stages += [dict(stage="job_settled", state="succeeded"),
               dict(stage="online_backup", exit_code=0),
               dict(stage="online_restore", exit_code=0, verified=True,
                    counts_before={"learning_events": 2}, counts_mutated={"learning_events": 0},
                    counts_after={"learning_events": 2}),
               dict(stage="legacy_migration", status="ok", original_untouched=True)]
    return dict(stages=stages)


def test_complete_synthetic_receipt():
    assert probe.verdict_errors(complete_receipt()) == []


@pytest.mark.parametrize("index", range(len(complete_receipt()["stages"])))
def test_missing_stage_cannot_pass(index):
    receipt = complete_receipt()
    del receipt["stages"][index]
    assert probe.verdict_errors(receipt)


@pytest.mark.parametrize("name", [s["stage"] for s in complete_receipt()["stages"]
                                 if isinstance(s.get("status"), int)])
def test_http_failure_cannot_pass(name):
    receipt = complete_receipt()
    next(s for s in receipt["stages"] if s["stage"] == name)["status"] = 500
    assert probe.verdict_errors(receipt)


@pytest.mark.parametrize("name,field,value", [
    ("search", "source_found", False), ("human_correction", "successor_id", "k1"),
    ("machine_readback", "knowledge_version", "k1"),
    ("machine_readback", "retest_of", "unrelated"),
    ("restart_learning_state", "answer", "wrong"),
    ("restart_learning_state", "state", {"id": "other"}),
    ("restart_knowledge_v3", "anchor_id", "other"),
    ("answer_recorded", "schedule_authority", "unavailable"),
    ("online_restore", "counts_after", {}),
    ("online_restore", "counts_mutated", {"learning_events": 2}),
])
def test_broken_chain_identity_cannot_pass(name, field, value):
    receipt = copy.deepcopy(complete_receipt())
    next(s for s in receipt["stages"] if s["stage"] == name)[field] = value
    assert probe.verdict_errors(receipt)
