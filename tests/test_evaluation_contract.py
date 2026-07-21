from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import EvalResult, EvaluationDimension


def test_runtime_evaluation_reports_seven_dimensions_without_inventing_truth():
    from app.evaluation.evaluator import evaluate
    from app.schemas import ExecutionTrace

    result = evaluate(
        ExecutionTrace(
            task_id="task-seven-dimensions",
            success=True,
            result={"status": "done"},
            events=[
                {
                    "step": {"tool": "file_read"},
                    "result": {
                        "tool": "file_read",
                        "risk_level": "low",
                        "status": "ok",
                        "dry_run": False,
                        "path": "AGENTS.md",
                        "content": "grounded evidence",
                    },
                }
            ],
        )
    )

    assert set(result.dimensions) == {
        "correctness",
        "completeness",
        "evidence",
        "safety",
        "efficiency",
        "maintainability",
        "knowledge_contribution",
    }
    assert result.dimensions["completeness"].status == "passed"
    assert result.dimensions["evidence"].status == "passed"
    assert result.dimensions["safety"].status == "passed"
    for name in ("correctness", "efficiency", "maintainability", "knowledge_contribution"):
        assert result.dimensions[name].status == "unverified"


def test_runtime_evaluation_roundtrips_losslessly_through_v1():
    from app.adapters.evaluation import from_runtime_evaluation, to_runtime_evaluation
    from app.contracts.v1 import CONTRACT_VERSION, EvaluationV1

    legacy = EvalResult(
        success=False,
        score=0.25,
        failure_reason="tool evidence was incomplete",
        improvement="collect evidence for every executed step",
        dimensions={
            "correctness": EvaluationDimension(
                status="unverified", reason="no reviewed truth pair"
            ),
            "evidence": EvaluationDimension(
                status="failed", reason="tool evidence was incomplete"
            ),
        },
    )

    canonical = from_runtime_evaluation(legacy)

    assert isinstance(canonical, EvaluationV1)
    assert canonical.schema_version == CONTRACT_VERSION
    assert to_runtime_evaluation(canonical).model_dump() == legacy.model_dump()


def test_evaluation_v1_forbids_unmapped_future_fields():
    from app.contracts.v1 import CONTRACT_VERSION, EvaluationV1

    with pytest.raises(ValidationError, match="invented"):
        EvaluationV1(
            schema_version=CONTRACT_VERSION,
            success=True,
            score=1.0,
            invented={"evidence_quality": 1.0},
        )


def test_contracts_facade_publishes_evaluation_v1_adapter_surface():
    from app.adapters.evaluation import from_runtime_evaluation, to_runtime_evaluation
    from app.contracts.v1 import EvaluationV1
    from app.facades import contracts

    assert contracts.EvaluationV1 is EvaluationV1
    assert contracts.from_runtime_evaluation is from_runtime_evaluation
    assert contracts.to_runtime_evaluation is to_runtime_evaluation
