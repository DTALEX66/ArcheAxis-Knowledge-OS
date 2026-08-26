"""Human-reviewed, evidence-gated and reversible distillation promotion."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class DistillationApprovalError(ValueError):
    """Raised when a distillation gate cannot prove a safe transition."""


def _connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    required = {
        "distillation_candidates_v2",
        "distillation_candidate_reviews_v2",
        "machine_knowledge_candidates_v2",
        "evidence_bundles_v1",
        "evidence_bundle_reviews_v1",
    }
    if not required <= tables:
        connection.close()
        raise RuntimeError("AXR distillation review migration is pending")
    return connection


def _candidate(connection: sqlite3.Connection, candidate_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM distillation_candidates_v2 WHERE candidate_id=?", (candidate_id,)
    ).fetchone()
    if row is None:
        raise KeyError(candidate_id)
    return row


def _require_verified_bundle(
    connection: sqlite3.Connection, evidence_bundle_id: str
) -> None:
    row = connection.execute(
        "SELECT r.decision FROM evidence_bundles_v1 b "
        "LEFT JOIN evidence_bundle_reviews_v1 r ON r.id=("
        "SELECT r2.id FROM evidence_bundle_reviews_v1 r2 "
        "WHERE r2.bundle_id=b.id ORDER BY r2.reviewed_at DESC,r2.id DESC LIMIT 1) "
        "WHERE b.id=?",
        (evidence_bundle_id,),
    ).fetchone()
    if row is None or str(row["decision"]) != "verified":
        raise DistillationApprovalError("verified evidence bundle review is required")


def _result(connection: sqlite3.Connection, candidate_id: str) -> dict[str, Any]:
    distillation = _candidate(connection, candidate_id)
    machine = connection.execute(
        "SELECT status FROM machine_knowledge_candidates_v2 "
        "WHERE distillation_candidate_id=?",
        (candidate_id,),
    ).fetchone()
    return {
        "candidate_id": candidate_id,
        "distillation_status": str(distillation["status"]),
        "machine_candidate_status": str(machine["status"]) if machine else None,
        "machine_verified": False,
    }


def approve_candidate(
    db_path: str | Path,
    *,
    candidate_id: str,
    review_id: str,
    reviewer_id: str,
    evidence_bundle_id: str,
    rationale: str,
    reviewed_at: str,
) -> dict[str, Any]:
    if not reviewer_id.strip() or not rationale.strip():
        raise DistillationApprovalError("human reviewer and rationale are required")
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        candidate = _candidate(connection, candidate_id)
        if str(candidate["status"]) not in {"unverified", "reviewed"}:
            raise DistillationApprovalError("candidate is not available for approval")
        _require_verified_bundle(connection, evidence_bundle_id)
        connection.execute(
            "INSERT INTO distillation_candidate_reviews_v2 "
            "(review_id,candidate_id,decision,evidence_bundle_id,reviewer_id,rationale,reviewed_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                review_id,
                candidate_id,
                "approved",
                evidence_bundle_id,
                reviewer_id,
                rationale,
                reviewed_at,
            ),
        )
        connection.execute(
            "INSERT INTO machine_knowledge_candidates_v2 "
            "(machine_candidate_id,distillation_candidate_id,status,payload_json,"
            "evidence_bundle_id,created_at) VALUES (?,?,?,?,?,?)",
            (
                f"machine:{candidate_id}",
                candidate_id,
                "CANDIDATE",
                candidate["payload_json"],
                evidence_bundle_id,
                reviewed_at,
            ),
        )
        connection.execute(
            "UPDATE distillation_candidates_v2 SET status='promoted' WHERE candidate_id=?",
            (candidate_id,),
        )
        result = _result(connection, candidate_id)
        connection.commit()
        return result


def reject_candidate(
    db_path: str | Path,
    *,
    candidate_id: str,
    review_id: str,
    reviewer_id: str,
    rationale: str,
    reviewed_at: str,
) -> dict[str, Any]:
    if not reviewer_id.strip() or not rationale.strip():
        raise DistillationApprovalError("human reviewer and rationale are required")
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        candidate = _candidate(connection, candidate_id)
        if str(candidate["status"]) not in {"unverified", "reviewed"}:
            raise DistillationApprovalError("candidate is not available for rejection")
        connection.execute(
            "INSERT INTO distillation_candidate_reviews_v2 "
            "(review_id,candidate_id,decision,reviewer_id,rationale,reviewed_at) "
            "VALUES (?,?,?,?,?,?)",
            (review_id, candidate_id, "rejected", reviewer_id, rationale, reviewed_at),
        )
        connection.execute(
            "UPDATE distillation_candidates_v2 SET status='rejected' WHERE candidate_id=?",
            (candidate_id,),
        )
        result = _result(connection, candidate_id)
        connection.commit()
        return result


def revoke_promotion(
    db_path: str | Path,
    *,
    candidate_id: str,
    review_id: str,
    reviewer_id: str,
    rationale: str,
    reviewed_at: str,
) -> dict[str, Any]:
    if not reviewer_id.strip() or not rationale.strip():
        raise DistillationApprovalError("human reviewer and rationale are required")
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        candidate = _candidate(connection, candidate_id)
        machine = connection.execute(
            "SELECT * FROM machine_knowledge_candidates_v2 "
            "WHERE distillation_candidate_id=?",
            (candidate_id,),
        ).fetchone()
        if str(candidate["status"]) != "promoted" or machine is None or str(machine["status"]) != "CANDIDATE":
            raise DistillationApprovalError("no active promotion is available to revoke")
        connection.execute(
            "INSERT INTO distillation_candidate_reviews_v2 "
            "(review_id,candidate_id,decision,evidence_bundle_id,reviewer_id,rationale,reviewed_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                review_id,
                candidate_id,
                "revoked",
                machine["evidence_bundle_id"],
                reviewer_id,
                rationale,
                reviewed_at,
            ),
        )
        connection.execute(
            "UPDATE machine_knowledge_candidates_v2 SET status='REVOKED',revoked_at=? "
            "WHERE distillation_candidate_id=?",
            (reviewed_at, candidate_id),
        )
        connection.execute(
            "UPDATE distillation_candidates_v2 SET status='reviewed' WHERE candidate_id=?",
            (candidate_id,),
        )
        result = _result(connection, candidate_id)
        connection.commit()
        return result
