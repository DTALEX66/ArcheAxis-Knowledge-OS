"""Temporal knowledge graph — absorbed from Graphiti (getzep) concepts.

A fact is not a timeless truth. Every fact carries its validity window, source,
version chain and conflict edges so the system can answer "what is true NOW":

    valid_from / valid_to     — when the fact holds
    version / supersedes      — linear version chain (V1 → V2)
    contradicts              — live conflict edges between facts
    confidence / source      — provenance for the fact

Key operations:
    add_fact              — record a new fact
    supersede_fact        — replace a fact with a newer version
    record_contradiction  — mark two facts as live contradictions
    active_facts(as_of)   — facts valid at time T, not superseded/contradicted/expired
    resolve_current       — the canonical current fact for an entity+predicate
    conflict_report       — everything known about a statement incl. stale/conflicting

Governance: append-only; superseding/contradicting only ever changes status,
never rewrites a fact. Expired or superseded facts remain queryable as history.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS temporal_facts (
    fact_id TEXT PRIMARY KEY,
    statement TEXT NOT NULL,
    entity TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    source TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    supersedes TEXT,
    confidence REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- active | superseded | contradicted | expired
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tf_entity ON temporal_facts(entity, predicate);
CREATE INDEX IF NOT EXISTS idx_tf_status ON temporal_facts(status);

CREATE TABLE IF NOT EXISTS fact_contradictions (
    edge_id TEXT PRIMARY KEY,
    fact_a TEXT NOT NULL,
    fact_b TEXT NOT NULL,
    noted_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0
);
"""


class TemporalGraphError(ValueError):
    """Raised when a temporal-fact operation is invalid."""


@dataclass(frozen=True)
class TemporalFact:
    fact_id: str
    statement: str
    entity: str
    predicate: str
    object: str
    valid_from: str | None
    valid_to: str | None
    source: str
    version: int
    supersedes: str | None
    confidence: float
    status: str
    created_at: str

    @property
    def is_current(self) -> bool:
        return self.status == "active"

    def as_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id, "statement": self.statement, "entity": self.entity,
            "predicate": self.predicate, "object": self.object, "valid_from": self.valid_from,
            "valid_to": self.valid_to, "source": self.source, "version": self.version,
            "supersedes": self.supersedes, "confidence": self.confidence,
            "status": self.status, "created_at": self.created_at,
        }


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(*parts: str) -> str:
    from hashlib import sha256

    payload = "\0".join(parts).encode("utf-8")
    return "fact_" + sha256(payload).hexdigest()[:24]


def _row_to_fact(row: sqlite3.Row) -> TemporalFact:
    return TemporalFact(fact_id=row["fact_id"], statement=row["statement"],
                        entity=row["entity"], predicate=row["predicate"], object=row["object"],
                        valid_from=row["valid_from"], valid_to=row["valid_to"],
                        source=row["source"], version=row["version"],
                        supersedes=row["supersedes"], confidence=row["confidence"],
                        status=row["status"], created_at=row["created_at"])


def add_fact(
    db: str | Path,
    *,
    statement: str,
    entity: str,
    predicate: str,
    object: str,
    source: str,
    confidence: float = 0.8,
    valid_from: str | None = None,
    valid_to: str | None = None,
    fact_id: str | None = None,
) -> TemporalFact:
    """Record a new fact version (V1 by default)."""
    if not statement.strip() or not entity.strip() or not predicate.strip():
        raise TemporalGraphError("statement, entity and predicate are required")
    if not 0.0 <= confidence <= 1.0:
        raise TemporalGraphError("confidence must be in [0,1]")
    fid = fact_id or _stable_id(entity, predicate, object, source)
    created_at = _now()
    with _connect(db) as conn:
        conn.execute(
            "INSERT INTO temporal_facts (fact_id, statement, entity, predicate, object, "
            "valid_from, valid_to, source, version, supersedes, confidence, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?, 'active', ?)",
            (fid, statement.strip(), entity.strip(), predicate.strip(), str(object),
             valid_from, valid_to, source, confidence, created_at),
        )
    return TemporalFact(fact_id=fid, statement=statement.strip(), entity=entity.strip(),
                        predicate=predicate.strip(), object=str(object),
                        valid_from=valid_from, valid_to=valid_to, source=source,
                        version=1, supersedes=None, confidence=confidence,
                        status="active", created_at=created_at)


def supersede_fact(
    db: str | Path,
    *,
    fact_id: str,
    statement: str,
    source: str,
    confidence: float = 0.8,
    valid_to: str | None = None,
) -> TemporalFact:
    """Replace an active fact with the next version (old → superseded)."""
    with _connect(db) as conn:
        row = conn.execute("SELECT * FROM temporal_facts WHERE fact_id=?", (fact_id,)).fetchone()
        if row is None:
            raise TemporalGraphError(f"fact not found: {fact_id}")
        if row["status"] != "active":
            raise TemporalGraphError("only active facts can be superseded")
        new_id = _stable_id(row["entity"], row["predicate"], row["object"], source, str(row["version"] + 1))
        created_at = _now()
        conn.execute(
            "INSERT INTO temporal_facts (fact_id, statement, entity, predicate, object, "
            "valid_from, valid_to, source, version, supersedes, confidence, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)",
            (new_id, statement, row["entity"], row["predicate"], row["object"],
             row["valid_from"], valid_to, source, row["version"] + 1, fact_id, confidence, created_at),
        )
        conn.execute("UPDATE temporal_facts SET status='superseded' WHERE fact_id=?", (fact_id,))
        new_row = conn.execute("SELECT * FROM temporal_facts WHERE fact_id=?", (new_id,)).fetchone()
        return _row_to_fact(new_row)


def record_contradiction(db: str | Path, fact_a: str, fact_b: str) -> str:
    """Mark two facts as live contradictions (both become 'contradicted')."""
    if fact_a == fact_b:
        raise TemporalGraphError("a fact cannot contradict itself")
    edge_id = _stable_id(fact_a, fact_b)
    with _connect(db) as conn:
        for fid in (fact_a, fact_b):
            row = conn.execute("SELECT fact_id FROM temporal_facts WHERE fact_id=?", (fid,)).fetchone()
            if row is None:
                raise TemporalGraphError(f"fact not found: {fid}")
        conn.execute(
            "INSERT OR IGNORE INTO fact_contradictions (edge_id, fact_a, fact_b, noted_at, resolved) "
            "VALUES (?, ?, ?, ?, 0)",
            (edge_id, fact_a, fact_b, _now()),
        )
        conn.execute("UPDATE temporal_facts SET status='contradicted' WHERE fact_id IN (?, ?)", (fact_a, fact_b))
    return edge_id


def active_facts(db: str | Path, *, as_of: str | None = None) -> list[TemporalFact]:
    """Facts that are active and valid at the given time."""
    as_of = as_of or _now()
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT * FROM temporal_facts WHERE status='active' "
            "AND (valid_from IS NULL OR valid_from <= ?) "
            "AND (valid_to IS NULL OR valid_to > ?) "
            "ORDER BY created_at",
            (as_of, as_of),
        ).fetchall()
    return [_row_to_fact(r) for r in rows]


def resolve_current(db: str | Path, *, entity: str, predicate: str,
                    as_of: str | None = None) -> TemporalFact | None:
    """Canonical current fact for entity+predicate (Graphiti 'current fact')."""
    as_of = as_of or _now()
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT * FROM temporal_facts WHERE entity=? AND predicate=? AND status='active' "
            "AND (valid_from IS NULL OR valid_from <= ?) "
            "AND (valid_to IS NULL OR valid_to > ?) "
            "ORDER BY version DESC, created_at DESC LIMIT 1",
            (entity, predicate, as_of, as_of),
        ).fetchall()
    return _row_to_fact(rows[0]) if rows else None


def fact_history(db: str | Path, *, entity: str, predicate: str) -> list[TemporalFact]:
    """Full version chain for an entity+predicate (oldest first)."""
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT * FROM temporal_facts WHERE entity=? AND predicate=? ORDER BY version, created_at",
            (entity, predicate),
        ).fetchall()
    return [_row_to_fact(r) for r in rows]


def conflict_report(db: str | Path, *, entity: str, predicate: str) -> dict[str, Any]:
    """Everything the graph knows about a statement, incl. stale/conflicting."""
    history = fact_history(db, entity=entity, predicate=predicate)
    active = [f for f in history if f.is_current]
    with _connect(db) as conn:
        edges = conn.execute(
            "SELECT * FROM fact_contradictions WHERE fact_a IN "
            "(SELECT fact_id FROM temporal_facts WHERE entity=? AND predicate=?) OR "
            "fact_b IN (SELECT fact_id FROM temporal_facts WHERE entity=? AND predicate=?)",
            (entity, predicate, entity, predicate),
        ).fetchall()
    return {
        "entity": entity,
        "predicate": predicate,
        "version_count": len(history),
        "active": [f.as_dict() for f in active],
        "superseded_count": sum(1 for f in history if f.status == "superseded"),
        "contradiction_edges": [dict(e) for e in edges],
        "current": resolve_current(db, entity=entity, predicate=predicate).as_dict()
        if resolve_current(db, entity=entity, predicate=predicate) else None,
    }
