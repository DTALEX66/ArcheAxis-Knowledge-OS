"""Adapters between the canonical and current runtime evaluation contracts."""

from app.contracts.v1 import CONTRACT_VERSION, EvaluationV1
from app.schemas import EvalResult as RuntimeEvaluation


def from_runtime_evaluation(evaluation: RuntimeEvaluation) -> EvaluationV1:
    """Convert the current runtime evaluation without dropping fields."""

    return EvaluationV1(
        schema_version=CONTRACT_VERSION,
        success=evaluation.success,
        score=evaluation.score,
        failure_reason=evaluation.failure_reason,
        improvement=evaluation.improvement,
    )


def to_runtime_evaluation(evaluation: EvaluationV1) -> RuntimeEvaluation:
    """Rebuild the current runtime evaluation without dropping fields."""

    return RuntimeEvaluation(
        success=evaluation.success,
        score=evaluation.score,
        failure_reason=evaluation.failure_reason,
        improvement=evaluation.improvement,
    )
