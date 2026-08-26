"""Append-only learning events and receipt-derived mastery projections."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.knowledge.dual_mastery import HumanEvidence, HumanMasteryLevel, human_mastery_level

EventType = Literal[
    "review",
    "quiz",
    "teach_back",
    "mistake",
    "hint",
    "session_started",
    "session_completed",
]


class EventConflictError(ValueError):
    """Raised when an idempotency key is reused for a different event."""


class EvidenceGateError(ValueError):
    """Raised when a machine receipt lacks verified evidence."""


@dataclass(frozen=True)
class LearningEvent:
    event_id: str
    learner_id: str
    node_id: str
    event_type: EventType
    payload: dict[str, Any]
    occurred_at: str
    idempotency_key: str
    source_system: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.event_id, "event_id"),
            (self.learner_id, "learner_id"),
            (self.node_id, "node_id"),
            (self.idempotency_key, "idempotency_key"),
            (self.source_system, "source_system"),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))


@dataclass(frozen=True)
class HumanLearningProjection:
    learner_id: str
    node_id: str
    event_count: int
    level: HumanMasteryLevel
    evidence: HumanEvidence


def _connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(Path(path)), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    required = {
        "learning_events_v2",
        "distillation_candidates_v2",
        "machine_competence_receipts_v2",
    }
    if not required <= tables:
        connection.close()
        raise RuntimeError("AXR learning truth migration is pending")
    return connection


def _payload_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _row_to_event(row: sqlite3.Row) -> LearningEvent:
    return LearningEvent(
        event_id=str(row["event_id"]),
        learner_id=str(row["learner_id"]),
        node_id=str(row["node_id"]),
        event_type=str(row["event_type"]),  # type: ignore[arg-type]
        payload=json.loads(str(row["payload_json"])),
        occurred_at=str(row["occurred_at"]),
        idempotency_key=str(row["idempotency_key"]),
        source_system=str(row["source_system"]),
    )


def append_event(db_path: str | Path, event: LearningEvent) -> LearningEvent:
    payload_json = _payload_json(event.payload)
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT * FROM learning_events_v2 WHERE idempotency_key=?",
            (event.idempotency_key,),
        ).fetchone()
        if existing is not None:
            expected = (
                event.learner_id,
                event.node_id,
                event.event_type,
                payload_json,
                event.occurred_at,
                event.source_system,
            )
            actual = tuple(existing[key] for key in (
                "learner_id",
                "node_id",
                "event_type",
                "payload_json",
                "occurred_at",
                "source_system",
            ))
            if actual != expected:
                raise EventConflictError("idempotency key is bound to different event data")
            return _row_to_event(existing)
        created_at = datetime.now(UTC).isoformat()
        connection.execute(
            "INSERT INTO learning_events_v2 "
            "(event_id,learner_id,node_id,event_type,payload_json,occurred_at,"
            "idempotency_key,source_system,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                event.event_id,
                event.learner_id,
                event.node_id,
                event.event_type,
                payload_json,
                event.occurred_at,
                event.idempotency_key,
                event.source_system,
                created_at,
            ),
        )
        row = connection.execute(
            "SELECT * FROM learning_events_v2 WHERE event_id=?", (event.event_id,)
        ).fetchone()
        if row is None:
            raise RuntimeError("learning event readback failed")
        connection.commit()
        return _row_to_event(row)


def replay_human_state(
    db_path: str | Path, *, learner_id: str, node_id: str
) -> HumanLearningProjection:
    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT event_type,payload_json FROM learning_events_v2 "
            "WHERE learner_id=? AND node_id=? ORDER BY occurred_at,event_id",
            (learner_id, node_id),
        ).fetchall()
    payloads = [(str(row["event_type"]), json.loads(str(row["payload_json"]))) for row in rows]
    teach_scores = [
        float(payload.get("score", 0))
        for event_type, payload in payloads
        if event_type == "teach_back"
    ]
    success_count = sum(
        bool(payload.get("correct"))
        or (event_type == "teach_back" and float(payload.get("score", 0)) >= 0.7)
        for event_type, payload in payloads
    )
    evidence = HumanEvidence(
        reviewed=bool(payloads),
        review_state="review" if payloads else "new",
        stability_days=float(len(payloads)),
        bkt_mastery=(success_count / len(payloads) if payloads else 0.0),
        quiz_pass=any(
            event_type == "quiz" and bool(payload.get("correct"))
            for event_type, payload in payloads
        ),
        teach_back_score=max(teach_scores) if teach_scores else None,
        transfer_pass=any(bool(payload.get("transfer_pass")) for _, payload in payloads),
        creation_evidence=any(
            bool(payload.get("creation_evidence")) for _, payload in payloads
        ),
        teaching_evidence=any(
            bool(payload.get("teaching_evidence")) for _, payload in payloads
        ),
    )
    return HumanLearningProjection(
        learner_id=learner_id,
        node_id=node_id,
        event_count=len(rows),
        level=human_mastery_level(evidence),
        evidence=evidence,
    )


def create_distillation_candidate(
    db_path: str | Path,
    *,
    candidate_id: str,
    source_event_id: str,
    source_card_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    created_at = datetime.now(UTC).isoformat()
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO distillation_candidates_v2 "
            "(candidate_id,source_event_id,source_card_id,payload_json,status,created_at) "
            "VALUES (?,?,?,?, 'unverified', ?)",
            (candidate_id, source_event_id, source_card_id, _payload_json(payload), created_at),
        )
        row = connection.execute(
            "SELECT * FROM distillation_candidates_v2 WHERE candidate_id=?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("distillation candidate readback failed")
        connection.commit()
    return dict(row)


def record_machine_receipt(
    db_path: str | Path,
    *,
    receipt_id: str,
    node_id: str,
    task_id: str,
    level: str,
    outcome: str,
    evidence_bundle_id: str,
    evaluator: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    created_at = datetime.now(UTC).isoformat()
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        review = connection.execute(
            "SELECT decision FROM evidence_bundle_reviews_v1 WHERE bundle_id=? "
            "ORDER BY reviewed_at DESC,id DESC LIMIT 1",
            (evidence_bundle_id,),
        ).fetchone()
        if review is None or review["decision"] != "verified":
            raise EvidenceGateError("machine competence requires a verified evidence bundle")
        connection.execute(
            "INSERT INTO machine_competence_receipts_v2 "
            "(receipt_id,node_id,task_id,level,outcome,evidence_bundle_id,evaluator,"
            "payload_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                receipt_id,
                node_id,
                task_id,
                level,
                outcome,
                evidence_bundle_id,
                evaluator,
                _payload_json(payload),
                created_at,
            ),
        )
        row = connection.execute(
            "SELECT * FROM machine_competence_receipts_v2 WHERE receipt_id=?",
            (receipt_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("machine receipt readback failed")
        connection.commit()
    return dict(row)


def current_machine_level(db_path: str | Path, *, node_id: str) -> str | None:
    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT DISTINCT level FROM machine_competence_receipts_v2 "
            "WHERE node_id=? AND outcome='passed'",
            (node_id,),
        ).fetchall()
    achieved = {str(row[0]) for row in rows}
    current: str | None = None
    for level in ("K0", "K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8"):
        if level not in achieved:
            break
        current = level
    return current
