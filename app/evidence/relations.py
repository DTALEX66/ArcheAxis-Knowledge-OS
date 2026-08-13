"""AXW-024C: versioned evidence relations and human adjudication.

Every supports/refutes/qualifies relation between a claim and an evidence
item is recorded append-only in SQLite: changing a relation writes a new
version that supersedes the old one — history is never silently overwritten.
Human adjudication of conflicts is also versioned with reviewer attribution.

Query helpers expose both the full history (for audit) and the active set
(for projection), so downstream AI/learning projections can only read the
currently effective relations.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_KINDS = frozenset({"supports", "refutes", "qualifies"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_relations (
    relation_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    reviewed INTEGER NOT NULL DEFAULT 0,
    superseded_by TEXT,
    FOREIGN KEY (superseded_by) REFERENCES evidence_relations(relation_id)
);
CREATE INDEX IF NOT EXISTS idx_relations_claim ON evidence_relations(claim_id);
CREATE TABLE IF NOT EXISTS relation_adjudications (
    adjudication_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    note TEXT,
    reviewer TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_adjudications_claim ON relation_adjudications(claim_id);
"""


class RelationError(ValueError):
    """Raised when an evidence relation operation is invalid."""


@dataclass(frozen=True)
class EvidenceRelation:
    relation_id: str
    claim_id: str
    evidence_id: str
    kind: str
    created_at: str
    actor: str
    reviewed: bool
    superseded_by: str | None

    @property
    def active(self) -> bool:
        return self.superseded_by is None


def _stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    conn.executescript(_SCHEMA)
    return conn


def record_relation(
    db: str | Path,
    *,
    claim_id: str,
    evidence_id: str,
    kind: str,
    actor: str,
    reviewed: bool = False,
    supersede: str | None = None,
) -> EvidenceRelation:
    """Record one relation version (append-only).

    ``supersede`` optionally names an existing active relation_id that this
    new relation replaces; that old relation is marked superseded in the same
    transaction (no silent overwrite — history is preserved).
    """
    if not claim_id or not evidence_id:
        raise RelationError("claim_id and evidence_id are required")
    if kind not in VALID_KINDS:
        raise RelationError(f"invalid relation kind: {kind}")
    if not actor:
        raise RelationError("actor is required for audit")

    relation_id = _stable_id("rel", claim_id, evidence_id, kind, _now(), actor)
    created_at = _now()

    with _connect(db) as conn:
        if supersede is not None:
            row = conn.execute(
                "SELECT relation_id, superseded_by FROM evidence_relations WHERE relation_id=?",
                (supersede,),
            ).fetchone()
            if row is None:
                raise RelationError(f"supersede target not found: {supersede}")
            if row[1] is not None:
                raise RelationError(f"supersede target already superseded: {supersede}")
            conn.execute(
                "UPDATE evidence_relations SET superseded_by=? WHERE relation_id=?",
                (relation_id, supersede),
            )
        conn.execute(
            "INSERT INTO evidence_relations "
            "(relation_id, claim_id, evidence_id, kind, created_at, actor, reviewed, superseded_by) "
            "VALUES (?,?,?,?,?,?,?,NULL)",
            (relation_id, claim_id, evidence_id, kind, created_at, actor, 1 if reviewed else 0),
        )
        conn.commit()

    return EvidenceRelation(
        relation_id=relation_id,
        claim_id=claim_id,
        evidence_id=evidence_id,
        kind=kind,
        created_at=created_at,
        actor=actor,
        reviewed=reviewed,
        superseded_by=None,
    )


def _row_to_relation(row: sqlite3.Row) -> EvidenceRelation:
    return EvidenceRelation(
        relation_id=row["relation_id"],
        claim_id=row["claim_id"],
        evidence_id=row["evidence_id"],
        kind=row["kind"],
        created_at=row["created_at"],
        actor=row["actor"],
        reviewed=bool(row["reviewed"]),
        superseded_by=row["superseded_by"],
    )


def list_relations(db: str | Path, *, claim_id: str) -> list[EvidenceRelation]:
    """Full append-only history for a claim (oldest first)."""
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM evidence_relations WHERE claim_id=? ORDER BY rowid, relation_id",
            (claim_id,),
        ).fetchall()
    return [_row_to_relation(r) for r in rows]


def active_relations(db: str | Path, *, claim_id: str) -> list[EvidenceRelation]:
    """Currently effective (non-superseded) relations for projection."""
    return [r for r in list_relations(db, claim_id=claim_id) if r.active]


def has_conflict(db: str | Path, *, claim_id: str) -> bool:
    """True when active relations mix supports and refutes."""
    kinds = {r.kind for r in active_relations(db, claim_id=claim_id)}
    return "supports" in kinds and "refutes" in kinds


def adjudicate(
    db: str | Path,
    *,
    claim_id: str,
    decision: str,
    reviewer: str,
    note: str | None = None,
) -> dict[str, str]:
    """Record one human adjudication of a conflicting bundle (append-only)."""
    if decision not in {"support", "refute", "insufficient"}:
        raise RelationError(f"invalid adjudication decision: {decision}")
    if not reviewer:
        raise RelationError("reviewer is required for adjudication")

    adjudication_id = _stable_id("adj", claim_id, decision, _now(), reviewer)
    created_at = _now()
    with _connect(db) as conn:
        conn.execute(
            "INSERT INTO relation_adjudications "
            "(adjudication_id, claim_id, decision, note, reviewer, created_at) VALUES (?,?,?,?,?,?)",
            (adjudication_id, claim_id, decision, note, reviewer, created_at),
        )
        conn.commit()
    return {"adjudication_id": adjudication_id, "claim_id": claim_id, "decision": decision}


def list_adjudications(db: str | Path, *, claim_id: str) -> list[dict[str, Any]]:
    """Append-only adjudication history (oldest first)."""
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM relation_adjudications WHERE claim_id=? ORDER BY rowid, adjudication_id",
            (claim_id,),
        ).fetchall()
    return [dict(r) for r in rows]
