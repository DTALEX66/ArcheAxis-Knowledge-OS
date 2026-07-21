"""Adapters between the canonical and current runtime evaluation contracts."""

from app.contracts.v1 import CONTRACT_VERSION, EvaluationDimensionV1, EvaluationV1
from app.schemas import EvalResult as RuntimeEvaluation
from app.schemas import EvaluationDimension as RuntimeEvaluationDimension


def from_runtime_evaluation(evaluation: RuntimeEvaluation) -> EvaluationV1:
    """Convert the current runtime evaluation without dropping fields."""

    return EvaluationV1(
        schema_version=CONTRACT_VERSION,
        success=evaluation.success,
        score=evaluation.score,
        failure_reason=evaluation.failure_reason,
        improvement=evaluation.improvement,
        dimensions={
            name: EvaluationDimensionV1.model_validate(dimension.model_dump())
            for name, dimension in evaluation.dimensions.items()
        },
    )


def to_runtime_evaluation(evaluation: EvaluationV1) -> RuntimeEvaluation:
    """Rebuild the current runtime evaluation without dropping fields."""

    return RuntimeEvaluation(
        success=evaluation.success,
        score=evaluation.score,
        failure_reason=evaluation.failure_reason,
        improvement=evaluation.improvement,
        dimensions={
            name: RuntimeEvaluationDimension.model_validate(dimension.model_dump())
            for name, dimension in evaluation.dimensions.items()
        },
    )
