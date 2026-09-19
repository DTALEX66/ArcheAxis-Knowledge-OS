"""R6 A14 full closed-loop evidence contract tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.closed_loop_v1 import ClosedLoopReceiptV1


STAGES = ["source", "knowledge", "human_learning", "machine_use", "evaluation", "correction", "lesson", "retest"]


def _stages(*, evidence_level="synthetic", status="pass"):
    return [{"stage": stage, "status": status, "evidence_level": evidence_level, "evidence_refs": [f"{stage}-receipt"]} for stage in STAGES]


def test_synthetic_journey_is_explicitly_partial():
    receipt = ClosedLoopReceiptV1(
        journey_id="journey-1", canonical_writer="archeaxis-core-rust-sqlite", stages=_stages(), overall_status="partial", synthetic=True
    )
    assert receipt.overall_status == "partial"
    assert receipt.synthetic is True


def test_complete_requires_real_evidence_for_every_stage():
    with pytest.raises(ValidationError, match="real evidence"):
        ClosedLoopReceiptV1(
            journey_id="journey-2", canonical_writer="archeaxis-core-rust-sqlite", stages=_stages(), overall_status="complete", synthetic=False
        )
    complete = ClosedLoopReceiptV1(
        journey_id="journey-3", canonical_writer="archeaxis-core-rust-sqlite", stages=_stages(evidence_level="real"), overall_status="complete", synthetic=False
    )
    assert complete.stages[-1].stage == "retest"


def test_complete_requires_correction_and_retest_evidence_refs():
    for stage_name in STAGES:
        stages = _stages(evidence_level="real")
        next(stage for stage in stages if stage["stage"] == stage_name)["evidence_refs"] = []
        with pytest.raises(ValidationError, match=f"{stage_name} evidence refs"):
            ClosedLoopReceiptV1(
                journey_id=f"journey-missing-{stage_name}",
                canonical_writer="archeaxis-core-rust-sqlite",
                stages=stages,
                overall_status="complete",
                synthetic=False,
            )


def test_complete_rejects_whitespace_only_evidence_refs():
    stages = _stages(evidence_level="real")
    next(stage for stage in stages if stage["stage"] == "source")["evidence_refs"] = ["  "]
    with pytest.raises(ValidationError, match="source evidence refs"):
        ClosedLoopReceiptV1(
            journey_id="journey-blank-source-evidence",
            canonical_writer="archeaxis-core-rust-sqlite",
            stages=stages,
            overall_status="complete",
            synthetic=False,
        )


def test_stage_order_cannot_drift():
    stages = _stages()
    stages[0], stages[1] = stages[1], stages[0]
    with pytest.raises(ValidationError, match="canonical order"):
        ClosedLoopReceiptV1(
            journey_id="journey-4", canonical_writer="archeaxis-core-rust-sqlite", stages=stages, overall_status="partial", synthetic=True
        )


def test_versioned_schema_is_present_and_exposes_evidence_boundary():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "packages/contracts/v1/closed-loop.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.closed-loop/v1"
    assert "synthetic" in schema["required"]
