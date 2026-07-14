"""Adapters between canonical and current runtime machine lessons."""

from typing import Any

from app.adapters.taskpack import ContractMappingError
from app.contracts.v1 import CONTRACT_VERSION, LessonV1
from app.schemas import MachineLesson as RuntimeLesson


def from_runtime_lesson(lesson: RuntimeLesson) -> LessonV1:
    """Convert the current runtime lesson without dropping fields."""

    return LessonV1(
        schema_version=CONTRACT_VERSION,
        lesson_id=lesson.id,
        pattern=lesson.pattern,
        lesson_type=lesson.lesson_type,
        future_constraint=lesson.future_constraint,
        evidence_trace_id=lesson.evidence_trace_id,
        created_at=lesson.created_at,
    )


def to_runtime_lesson(lesson: LessonV1) -> RuntimeLesson:
    """Rebuild the current runtime lesson without dropping fields."""

    return RuntimeLesson(
        id=lesson.lesson_id,
        pattern=lesson.pattern,
        lesson_type=lesson.lesson_type,
        future_constraint=lesson.future_constraint,
        evidence_trace_id=lesson.evidence_trace_id,
        created_at=lesson.created_at,
    )


def from_lesson_row(row: dict[str, Any]) -> LessonV1:
    """Map a decoded SQLite lesson row without silently dropping columns."""

    expected = {
        "id",
        "pattern",
        "lesson_type",
        "future_constraint",
        "evidence_trace_id",
        "created_at",
    }
    unmapped = sorted(row.keys() - expected)
    if unmapped:
        raise ContractMappingError(f"machine lesson row unmapped fields: {', '.join(unmapped)}")

    return LessonV1(
        schema_version=CONTRACT_VERSION,
        lesson_id=row["id"],
        pattern=row["pattern"],
        lesson_type=row["lesson_type"],
        future_constraint=row["future_constraint"],
        evidence_trace_id=row["evidence_trace_id"],
        created_at=row["created_at"],
    )


def to_lesson_row(lesson: LessonV1) -> dict[str, Any]:
    """Map v1 to the decoded row shape accepted by the SQLite writer."""

    return {
        "id": lesson.lesson_id,
        "pattern": lesson.pattern,
        "lesson_type": lesson.lesson_type,
        "future_constraint": lesson.future_constraint,
        "evidence_trace_id": lesson.evidence_trace_id,
        "created_at": lesson.created_at,
    }
