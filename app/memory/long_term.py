"""Long-term memory — absorbed from Mem0 (mem0ai) patterns.

A simple, local, mem0-style memory layer: add / update / search with
importance scoring, deduplication and recency weighting — backed by SQLite
(no external vector service; the project's sqlite-vec index remains the
optional semantic layer elsewhere).

    add(db, content, metadata)      → memory_id (dedup by content hash)
    update(db, memory_id, content)  → new version (append-only history)
    search(db, query, top_k)        → score = overlap + importance + recency
    forget(db, memory_id)           → soft delete (status=forgotten)
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS long_term_memory (
    memory_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ltm_status ON long_term_memory(status);
"""


class LongTermMemoryError(ValueError):
    """Raised when a long-term memory operation is invalid."""


@dataclass(frozen=True)
class MemoryHit:
    memory_id: str
    content: str
    importance: float
    score: float


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(content: str) -> str:
    from hashlib import sha256

    return "ltm_" + sha256(content.encode()).hexdigest()[:24]


def _terms(text: str) -> set[str]:
    words = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    return {w for w in words if w.strip() and len(w) > 1}


def add(
    db: str | Path,
    *,
    content: str,
    metadata: dict[str, Any] | None = None,
    importance: float = 0.5,
) -> str:
    """Add one memory (dedup by content; returns memory_id)."""
    if not content.strip():
        raise LongTermMemoryError("memory content is required")
    if not 0.0 <= importance <= 1.0:
        raise LongTermMemoryError("importance must be in [0,1]")
    memory_id = _stable_id(content.strip())
    now = _now()
    with _connect(db) as conn:
        row = conn.execute("SELECT memory_id FROM long_term_memory WHERE memory_id=?", (memory_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO long_term_memory (memory_id, content, metadata_json, importance, "
                "version, status, created_at, updated_at) VALUES (?, ?, ?, ?, 1, 'active', ?, ?)",
                (memory_id, content.strip(),
                 json.dumps(metadata or {}, ensure_ascii=False), importance, now, now),
            )
    return memory_id


def update(db: str | Path, memory_id: str, *, content: str) -> str:
    """Update a memory to a new version (history preserved via version bump)."""
    if not content.strip():
        raise LongTermMemoryError("memory content is required")
    with _connect(db) as conn:
        row = conn.execute("SELECT * FROM long_term_memory WHERE memory_id=?", (memory_id,)).fetchone()
        if row is None:
            raise LongTermMemoryError(f"memory not found: {memory_id}")
        new_id = f"{memory_id}__v{row['version'] + 1}"
        now = _now()
        conn.execute(
            "INSERT INTO long_term_memory (memory_id, content, metadata_json, importance, "
            "version, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
            (new_id, content.strip(), row["metadata_json"], row["importance"],
             row["version"] + 1, row["created_at"], now),
        )
        conn.execute("UPDATE long_term_memory SET status='superseded' WHERE memory_id=?", (memory_id,))
        return new_id


def search(db: str | Path, query: str, *, top_k: int = 5) -> list[MemoryHit]:
    """Rank active memories by term overlap + importance + recency."""
    if top_k < 1:
        raise LongTermMemoryError("top_k must be >= 1")
    query_terms = _terms(query)
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT * FROM long_term_memory WHERE status='active' ORDER BY updated_at DESC"
        ).fetchall()
    hits: list[MemoryHit] = []
    for i, row in enumerate(rows):
        content_terms = _terms(row["content"])
        hits_count = sum(1 for qt in query_terms
                         if any(qt in ct or ct in qt for ct in content_terms))
        overlap = hits_count / max(len(query_terms), 1)
        recency = max(0.0, 1.0 - i / max(len(rows), 1))
        score = round(0.6 * overlap + 0.25 * row["importance"] + 0.15 * recency, 3)
        hits.append(MemoryHit(memory_id=row["memory_id"], content=row["content"],
                              importance=row["importance"], score=score))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


def forget(db: str | Path, memory_id: str) -> None:
    """Soft-delete a memory (status = forgotten)."""
    with _connect(db) as conn:
        row = conn.execute("SELECT memory_id FROM long_term_memory WHERE memory_id=?", (memory_id,)).fetchone()
        if row is None:
            raise LongTermMemoryError(f"memory not found: {memory_id}")
        conn.execute("UPDATE long_term_memory SET status='forgotten' WHERE memory_id=?", (memory_id,))


_MEMORY_KINDS = ("preference", "fact", "procedure", "project", "persona")


def classify_kind(content: str) -> str:
    """Coarse MemoryKind classification (D4, local)."""
    lowered = content.lower()
    if any(m in lowered for m in ("prefer", "喜欢", "偏好", "习惯", "i like")):
        return "preference"
    if any(m in lowered for m in ("步骤", "先", "然后", "最后", "ensure", "verify", "如何")):
        return "procedure"
    if any(m in lowered for m in ("project", "work-lab", "design-lab", "项目", "工单")):
        return "project"
    if any(m in lowered for m in ("我", "我的", "我是", "persona", "profile")):
        return "persona"
    return "fact"


def add_from_conversation(
    db: str | Path,
    messages: list[dict[str, Any]],
    *,
    importance: float = 0.5,
) -> list[str]:
    """Extract and store key statements from a conversation (D4).

    messages: [{"role": "user|assistant", "content": "..."}]. Every message is
    classified by MemoryKind and stored via add(); returns the memory ids.
    """
    if not messages:
        raise LongTermMemoryError("messages must be non-empty")
    ids: list[str] = []
    for message in messages:
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        kind = classify_kind(content)
        metadata = {"kind": kind, "role": message.get("role", "unknown")}
        ids.append(add(db, content=content, metadata=metadata, importance=importance))
    if not ids:
        raise LongTermMemoryError("no usable content in messages")
    return ids
