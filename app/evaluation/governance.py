"""Reviewer-gated evaluation feedback projection."""
from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.evaluator import evaluate
from app.evaluation.feedback import compile_lesson
from app.schemas import EvalResult, ExecutionTrace, MachineLesson
from shared import core_schema


class EvaluationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    trace_id: str
    trace_digest: str
    evaluation: EvalResult
    status: str = "candidate"
    lesson: MachineLesson | None = None


class EvaluationApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


class ReviewedFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    trace_id: str
    evaluation: EvalResult
    reviewer_id: str
    rationale: str
    reviewed_at: str


def _load_authoritative_trace(
    connection: sqlite3.Connection, trace_id: str
) -> ExecutionTrace:
    row = connection.execute(
        "SELECT id, task_id, events_json, result_json, success, created_at "
        "FROM execution_traces WHERE id=?",
        (trace_id,),
    ).fetchone()
    if row is None:
        raise ValueError("persisted execution trace not found")
    success = None if row["success"] is None else bool(row["success"])
    return ExecutionTrace(
        id=str(row["id"]),
        task_id=row["task_id"],
        events=json.loads(str(row["events_json"])),
        result=json.loads(str(row["result_json"])),
        success=success,
        created_at=str(row["created_at"]),
    )


def _trace_digest(trace: ExecutionTrace) -> str:
    canonical = json.dumps(
        trace.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _same_candidate_evidence(
    recorded: EvaluationCandidate, requested: EvaluationCandidate
) -> bool:
    return (
        recorded.candidate_id == requested.candidate_id
        and recorded.trace_id == requested.trace_id
        and recorded.trace_digest == requested.trace_digest
        and recorded.evaluation == requested.evaluation
    )


def create_evaluation_candidate(
    trace: ExecutionTrace, *, db_path: str | Path
) -> EvaluationCandidate:
    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        connection.execute("BEGIN IMMEDIATE")
        authoritative_trace = _load_authoritative_trace(connection, trace.id)
        if authoritative_trace != trace:
            raise RuntimeError(
                "evaluation input does not match the persisted execution trace"
            )
        candidate = EvaluationCandidate(
            candidate_id="evaluation_" + sha256(trace.id.encode()).hexdigest()[:24],
            trace_id=trace.id,
            trace_digest=_trace_digest(authoritative_trace),
            evaluation=evaluate(authoritative_trace),
        )
        row = connection.execute(
            "SELECT evaluation_json FROM evaluation_candidates_v1 "
            "WHERE id=? OR trace_id=?",
            (candidate.candidate_id, trace.id),
        ).fetchone()
        if row is not None:
            recorded = EvaluationCandidate.model_validate_json(row["evaluation_json"])
            if not _same_candidate_evidence(recorded, candidate):
                raise RuntimeError(
                    "evaluation trace id conflicts with the recorded candidate"
                )
            return recorded
        connection.execute(
            "INSERT INTO evaluation_candidates_v1"
            "(id, trace_id, evaluation_json, status) VALUES (?, ?, ?, 'candidate')",
            (candidate.candidate_id, trace.id, candidate.model_dump_json()),
        )
        connection.commit()
    return candidate


def approve_evaluation_candidate(
    approval: EvaluationApproval, *, db_path: str | Path
) -> MachineLesson:
    with sqlite3.connect(Path(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT evaluation_json, status, reviewer_id, rationale, reviewed_at "
            "FROM evaluation_candidates_v1 WHERE id=?",
            (approval.candidate_id,),
        ).fetchone()
        if row is None:
            raise ValueError("evaluation candidate not found")
        candidate = EvaluationCandidate.model_validate_json(row["evaluation_json"])
        trace = _load_authoritative_trace(connection, candidate.trace_id)
        if _trace_digest(trace) != candidate.trace_digest:
            raise RuntimeError(
                "persisted execution trace changed after candidate creation"
            )
        recorded_review = (row["reviewer_id"], row["rationale"], row["reviewed_at"])
        requested_review = (
            approval.reviewer_id,
            approval.rationale,
            approval.reviewed_at,
        )
        if row["status"] == "approved":
            if recorded_review != requested_review:
                raise RuntimeError(
                    "reviewed evaluation conflicts with the recorded receipt"
                )
            if candidate.lesson is None:
                raise RuntimeError(
                    "approved evaluation is missing its durable lesson receipt"
                )
            return candidate.lesson
        lesson = compile_lesson(candidate.evaluation, trace)
        approved_candidate = candidate.model_copy(
            update={"status": "approved", "lesson": lesson}
        )
        cursor = connection.execute(
            "UPDATE evaluation_candidates_v1 "
            "SET evaluation_json=?, status='approved', reviewer_id=?, rationale=?, "
            "reviewed_at=? WHERE id=? AND status='candidate'",
            (
                approved_candidate.model_dump_json(),
                *requested_review,
                candidate.candidate_id,
            ),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("reviewed evaluation conflicts with the recorded receipt")
        connection.commit()
        return lesson


def list_reviewed_feedback(
    *, db_path: str | Path, limit: int = 20
) -> list[ReviewedFeedback]:
    if limit < 1:
        return []
    database = Path(db_path)
    if not database.is_file():
        return []
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        core_schema.validate(connection)
        rows = connection.execute(
            "SELECT id, evaluation_json, reviewer_id, rationale, reviewed_at "
            "FROM evaluation_candidates_v1 WHERE status='approved' "
            "ORDER BY reviewed_at DESC, id LIMIT ?",
            (limit,),
        ).fetchall()
    feedback = []
    for row in rows:
        candidate = EvaluationCandidate.model_validate_json(row["evaluation_json"])
        feedback.append(
            ReviewedFeedback(
                candidate_id=str(row["id"]),
                trace_id=candidate.trace_id,
                evaluation=candidate.evaluation,
                reviewer_id=str(row["reviewer_id"]),
                rationale=str(row["rationale"]),
                reviewed_at=str(row["reviewed_at"]),
            )
        )
    return feedback
