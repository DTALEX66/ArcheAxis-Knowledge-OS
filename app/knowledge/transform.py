"""AXW-053: traceable knowledge → learning → AI transformations.

Records every transformation between knowledge, learning and AI artifacts
as an append-only provenance event:

- source (type + id) and target (type + id);
- tool / model + version that performed the transformation;
- loss notes (what the transformation dropped);
- review status (unreviewed transformations default to candidate);
- supersede chain (a transformation can supersede an earlier one).

Transformation outputs are candidates by default: nothing produced by a
transformation is directly active until reviewed — AI retrieval and
learning projection only read the reviewed, non-superseded set.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transformation_records (
    transform_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    loss_notes TEXT,
    reviewed INTEGER NOT NULL DEFAULT 0,
    reviewer TEXT,
    reviewed_at TEXT,
    superseded_by TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transform_target ON transformation_records(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_transform_source ON transformation_records(source_type, source_id);
"""

_VALID_TYPES = frozenset({"knowledge", "learning", "ai_asset", "evidence", "lesson"})


class TransformError(ValueError):
    """Raised when a transformation record is invalid."""


@dataclass(frozen=True)
class Transformation:
    transform_id: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    tool: str
    tool_version: str
    loss_notes: str | None
    reviewed: bool
    reviewer: str | None
    reviewed_at: str | None
    superseded_by: str | None
    created_at: str

    @property
    def is_candidate(self) -> bool:
        """Unreviewed transformations are candidates (never directly active)."""
        return not self.reviewed


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_transformation(
    db: str | Path,
    *,
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
    tool: str,
    tool_version: str = "unknown",
    loss_notes: str | None = None,
    supersede: str | None = None,
) -> Transformation:
    """Record one transformation (append-only, candidate by default)."""
    for t in (source_type, target_type):
        if t not in _VALID_TYPES:
            raise TransformError(f"invalid transformation type: {t}")
    if not source_id or not target_id:
        raise TransformError("source_id and target_id are required")
    if not tool:
        raise TransformError("tool is required for provenance")

    transform_id = f"tr_{abs(hash((source_id, target_id, tool, _now()))) % (10**12):012d}"
    created_at = _now()
    with _connect(db) as conn:
        if supersede is not None:
            row = conn.execute(
                "SELECT superseded_by FROM transformation_records WHERE transform_id=?",
                (supersede,),
            ).fetchone()
            if row is None:
                raise TransformError(f"supersede target not found: {supersede}")
            if row[0] is not None:
                raise TransformError(f"supersede target already superseded: {supersede}")
            conn.execute(
                "UPDATE transformation_records SET superseded_by=? WHERE transform_id=?",
                (transform_id, supersede),
            )
        conn.execute(
            "INSERT INTO transformation_records "
            "(transform_id, source_type, source_id, target_type, target_id, tool, tool_version, "
            "loss_notes, reviewed, reviewer, reviewed_at, superseded_by, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,0,NULL,NULL,NULL,?)",
            (transform_id, source_type, source_id, target_type, target_id, tool, tool_version, loss_notes, created_at),
        )
        conn.commit()
    return Transformation(
        transform_id=transform_id,
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        tool=tool,
        tool_version=tool_version,
        loss_notes=loss_notes,
        reviewed=False,
        reviewer=None,
        reviewed_at=None,
        superseded_by=None,
        created_at=created_at,
    )


def review_transformation(
    db: str | Path,
    *,
    transform_id: str,
    reviewer: str,
    approved: bool = True,
) -> dict[str, Any]:
    """Mark a transformation reviewed (append-only status flip).

    Only reviewed, non-superseded transformations are eligible for
    projection; approving a transformation does not mutate its history.
    """
    if not reviewer:
        raise TransformError("reviewer is required")
    reviewed_at = _now()
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT reviewed FROM transformation_records WHERE transform_id=?",
            (transform_id,),
        ).fetchone()
        if row is None:
            raise TransformError(f"transformation not found: {transform_id}")
        conn.execute(
            "UPDATE transformation_records SET reviewed=?, reviewer=?, reviewed_at=? WHERE transform_id=?",
            (1 if approved else 0, reviewer, reviewed_at, transform_id),
        )
        conn.commit()
    return {"transform_id": transform_id, "reviewed": approved, "reviewer": reviewer, "reviewed_at": reviewed_at}


def active_transformations(
    db: str | Path, *, target_type: str | None = None
) -> list[Transformation]:
    """Reviewed, non-superseded transformations for projection."""
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        params: tuple = ()
        where = "superseded_by IS NULL AND reviewed = 1"
        if target_type is not None:
            where += " AND target_type = ?"
            params = (target_type,)
        rows = conn.execute(
            f"SELECT * FROM transformation_records WHERE {where} ORDER BY created_at, transform_id",
            params,
        ).fetchall()
    return [
        Transformation(
            transform_id=r["transform_id"],
            source_type=r["source_type"],
            source_id=r["source_id"],
            target_type=r["target_type"],
            target_id=r["target_id"],
            tool=r["tool"],
            tool_version=r["tool_version"],
            loss_notes=r["loss_notes"],
            reviewed=bool(r["reviewed"]),
            reviewer=r["reviewer"],
            reviewed_at=r["reviewed_at"],
            superseded_by=r["superseded_by"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def provenance_of(
    db: str | Path, *, target_type: str, target_id: str
) -> list[Transformation]:
    """Full history of transformations that produced a target (audit)."""
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM transformation_records WHERE target_type=? AND target_id=? "
            "ORDER BY created_at, transform_id",
            (target_type, target_id),
        ).fetchall()
    return [
        Transformation(
            transform_id=r["transform_id"],
            source_type=r["source_type"],
            source_id=r["source_id"],
            target_type=r["target_type"],
            target_id=r["target_id"],
            tool=r["tool"],
            tool_version=r["tool_version"],
            loss_notes=r["loss_notes"],
            reviewed=bool(r["reviewed"]),
            reviewer=r["reviewer"],
            reviewed_at=r["reviewed_at"],
            superseded_by=r["superseded_by"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
