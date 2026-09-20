"""R6 A07 machine growth lifecycle contract tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.machine_growth_v1 import MachineGrowthReceiptV1


def _steps(include_reuse: bool = True):
    steps = [
        {"stage": "experience", "state": "observed", "actor": "system", "evidence_refs": ["event-1"]},
        {"stage": "lesson", "state": "created", "actor": "system", "evidence_refs": ["event-1"]},
        {"stage": "skill_candidate", "state": "pending", "actor": "system", "evidence_refs": ["lesson-1"]},
        {"stage": "review", "state": "approved", "actor": "human", "evidence_refs": ["bundle-1"]},
    ]
    if include_reuse:
        steps.append({"stage": "reuse", "state": "used", "actor": "system", "evidence_refs": ["review-1"]})
    return steps


def test_growth_receipt_requires_human_approval_before_reuse():
    receipt = MachineGrowthReceiptV1(
        receipt_id="growth-1", source_event_ids=["event-1"], goal="improve import", outcome="success", steps=_steps()
    )
    assert receipt.machine_verified is False
    assert receipt.steps[-1].state == "used"


def test_growth_receipt_rejects_duplicate_source_events():
    with pytest.raises(ValidationError, match="source_event_ids must be unique"):
        MachineGrowthReceiptV1(
            receipt_id="growth-duplicate",
            source_event_ids=["event-1", "event-1"],
            goal="improve import",
            outcome="success",
            steps=_steps(),
        )


def test_reuse_without_approved_human_review_fails_closed():
    steps = _steps()
    steps[3] = {**steps[3], "state": "pending", "actor": "system"}
    with pytest.raises(ValidationError, match="approved human review"):
        MachineGrowthReceiptV1(
            receipt_id="growth-2", source_event_ids=["event-1"], goal="improve import", outcome="success", steps=steps
        )


def test_approved_review_cannot_be_machine_authored():
    steps = _steps(include_reuse=False)
    steps[3] = {**steps[3], "actor": "system"}
    with pytest.raises(ValidationError, match="human actor"):
        MachineGrowthReceiptV1(
            receipt_id="growth-3", source_event_ids=["event-1"], goal="improve import", outcome="partial", steps=steps
        )


def test_versioned_schema_is_present_and_machine_verified_is_false():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "packages/contracts/v1/machine-growth.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.machine-growth/v1"
    assert schema["properties"]["machine_verified"]["const"] is False
