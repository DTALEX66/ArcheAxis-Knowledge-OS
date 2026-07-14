from __future__ import annotations

import pytest

from app.schemas import MachineLesson


def test_runtime_lesson_roundtrips_losslessly_through_v1():
    from app.adapters.lesson import from_runtime_lesson, to_runtime_lesson
    from app.contracts.v1 import CONTRACT_VERSION, LessonV1

    legacy = MachineLesson(
        id="lesson_runtime_001",
        pattern="tool evidence was complete",
        lesson_type="success",
        future_constraint="require the same evidence class on future runs",
        evidence_trace_id="trace_runtime_001",
        created_at="2026-07-15T00:05:00+00:00",
    )

    canonical = from_runtime_lesson(legacy)

    assert isinstance(canonical, LessonV1)
    assert canonical.schema_version == CONTRACT_VERSION
    assert canonical.lesson_id == legacy.id
    assert to_runtime_lesson(canonical).model_dump() == legacy.model_dump()


def test_sqlite_lesson_row_roundtrips_losslessly_through_v1():
    from app.adapters.lesson import from_lesson_row, to_lesson_row

    row = {
        "id": "lesson_row_001",
        "pattern": "blocked tools never execute",
        "lesson_type": "constraint",
        "future_constraint": "preserve the blocked tool decision",
        "evidence_trace_id": "trace_row_001",
        "created_at": "2026-07-15T00:06:00+00:00",
    }

    assert to_lesson_row(from_lesson_row(row)) == row


def test_sqlite_lesson_row_rejects_unmapped_columns():
    from app.adapters.lesson import from_lesson_row
    from app.adapters.taskpack import ContractMappingError

    row = {
        "id": "lesson_row_002",
        "pattern": "evidence incomplete",
        "lesson_type": "failure",
        "future_constraint": "collect complete evidence",
        "evidence_trace_id": "trace_row_002",
        "created_at": "2026-07-15T00:07:00+00:00",
        "approval_status": "approved",
    }

    with pytest.raises(ContractMappingError, match="unmapped fields: approval_status"):
        from_lesson_row(row)


def test_lesson_v1_crosses_the_real_sqlite_row_boundary(tmp_path, monkeypatch):
    from app.adapters.lesson import from_lesson_row, to_lesson_row
    from app.contracts.v1 import CONTRACT_VERSION, LessonV1
    from app.memory import database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "lesson-contract.sqlite")
    database.init_db()
    canonical = LessonV1(
        schema_version=CONTRACT_VERSION,
        lesson_id="lesson_sqlite_001",
        pattern="a real tool produced attributable evidence",
        lesson_type="success",
        future_constraint="retain the evidence trace link",
        evidence_trace_id="trace_sqlite_001",
        created_at="2026-07-15T00:08:00+00:00",
    )

    database.save_lesson_db(to_lesson_row(canonical))
    persisted = next(
        row for row in database.list_lessons_db() if row["id"] == canonical.lesson_id
    )

    assert from_lesson_row(persisted) == canonical


def test_contracts_facade_publishes_lesson_v1_adapter_surface():
    from app.adapters.lesson import (
        from_lesson_row,
        from_runtime_lesson,
        to_lesson_row,
        to_runtime_lesson,
    )
    from app.contracts.v1 import LessonV1
    from app.facades import contracts

    assert contracts.LessonV1 is LessonV1
    assert contracts.from_runtime_lesson is from_runtime_lesson
    assert contracts.to_runtime_lesson is to_runtime_lesson
    assert contracts.from_lesson_row is from_lesson_row
    assert contracts.to_lesson_row is to_lesson_row
