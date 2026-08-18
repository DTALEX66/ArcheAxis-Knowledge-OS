"""Layered memory — absorbed from MemoryOS / MemOS / Hermes Memory OS concepts.

The AI (and the workspace) keeps FOUR memory layers instead of one bag:

    L1 WORKING      current task context (short-lived, ring buffer)
    L2 PROJECT      WORK-LAB / DESIGN-LAB / project vaults
    L3 PROFESSIONAL reusable domain knowledge (design, code, research…)
    L4 PERSONA      long-term user habits, methods, preferences

Layers share one store shape but have different retention policies and recall
priorities. Classification is deterministic and local; routing is explicit so
callers can place a memory deliberately.

Governance:
    * L4 writes require an explicit persona tag (never inferred silently)
    * recall from L1 is recency-ranked; L3/L4 are semantic/keyword ranked
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

WORKING_MEMORY_CAPACITY = 50  # L1 ring buffer size

_L2_MARKERS = ("project", "work-lab", "design-lab", "任务", "项目", "工单", "迭代",
               "milestone", "sprint", "workspace", "交付", "gate", "门禁")
_L4_MARKERS = ("i prefer", "i like", "i use", "my workflow", "i always",
               "i usually", "i never", "我习惯", "我偏好", "我喜欢", "我总是",
               "我通常", "我的工作流", "我是", "我的")


class MemoryLayer(str, Enum):
    L1_WORKING = "L1_working"
    L2_PROJECT = "L2_project"
    L3_PROFESSIONAL = "L3_professional"
    L4_PERSONA = "L4_persona"


class MemoryLayerError(ValueError):
    """Raised when a layered-memory operation is invalid."""


@dataclass(frozen=True)
class LayeredMemory:
    memory_id: str
    layer: MemoryLayer
    content: str
    tags: tuple[str, ...]
    importance: float
    created_at: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS layered_memory (
    memory_id TEXT PRIMARY KEY,
    layer TEXT NOT NULL,
    content TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lm_layer ON layered_memory(layer, created_at);
"""


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
    return "mem_" + sha256(payload).hexdigest()[:24]


def classify_content(text: str, *, explicit_layer: MemoryLayer | None = None,
                     tags: list[str] | None = None) -> MemoryLayer:
    """Deterministic layer classification (explicit layer wins)."""
    if explicit_layer is not None:
        return explicit_layer
    lowered = text.lower()
    tags = tags or []
    tag_text = " ".join(tags).lower()
    if any(m in lowered or m in tag_text for m in _L2_MARKERS):
        return MemoryLayer.L2_PROJECT
    if any(m in lowered or m in tag_text for m in _L4_MARKERS):
        return MemoryLayer.L4_PERSONA
    return MemoryLayer.L3_PROFESSIONAL


def store(db: str | Path, *, content: str, layer: MemoryLayer | None = None,
          tags: list[str] | None = None, importance: float = 0.5) -> LayeredMemory:
    """Store one memory in its layer (L1 is a ring buffer)."""
    if not content.strip():
        raise MemoryLayerError("memory content is required")
    if not 0.0 <= importance <= 1.0:
        raise MemoryLayerError("importance must be in [0,1]")
    resolved = classify_content(content, explicit_layer=layer, tags=tags)
    if resolved == MemoryLayer.L4_PERSONA and not tags:
        raise MemoryLayerError("L4 persona memories require an explicit persona tag")
    memory_id = _stable_id(resolved.value, content, _now())
    created_at = _now()
    with _connect(db) as conn:
        conn.execute(
            "INSERT INTO layered_memory (memory_id, layer, content, tags_json, importance, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (memory_id, resolved.value, content.strip(),
             _json(list(tags or [])), importance, created_at),
        )
        if resolved == MemoryLayer.L1_WORKING:
            rows = conn.execute(
                "SELECT memory_id FROM layered_memory WHERE layer=? ORDER BY created_at",
                (MemoryLayer.L1_WORKING.value,),
            ).fetchall()
            overflow = len(rows) - WORKING_MEMORY_CAPACITY
            for row in rows[: max(overflow, 0)]:
                conn.execute("DELETE FROM layered_memory WHERE memory_id=?", (row["memory_id"],))
    return LayeredMemory(memory_id=memory_id, layer=resolved, content=content.strip(),
                         tags=tuple(tags or []), importance=importance, created_at=created_at)


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _terms(text: str) -> set[str]:
    words = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    return {w for w in words if w.strip() and len(w) > 1}


def recall(db: str | Path, *, query: str, layers: list[MemoryLayer] | None = None,
           top_k: int = 5) -> list[dict[str, Any]]:
    """Recall memories across the given layers (default: L2+L3+L4)."""
    if top_k < 1:
        raise MemoryLayerError("top_k must be >= 1")
    layers = layers or [MemoryLayer.L2_PROJECT, MemoryLayer.L3_PROFESSIONAL, MemoryLayer.L4_PERSONA]
    query_terms = _terms(query)
    placeholders = ",".join("?" for _ in layers)
    with _connect(db) as conn:
        rows = conn.execute(
            f"SELECT * FROM layered_memory WHERE layer IN ({placeholders})",
            [l.value for l in layers],
        ).fetchall()
    scored = []
    for r in rows:
        content = r["content"]
        content_terms = _terms(content)
        hits = sum(1 for qt in query_terms if any(qt in ct or ct in qt for ct in content_terms))
        overlap = hits / max(len(query_terms), 1)
        score = round(0.7 * overlap + 0.3 * r["importance"], 3)
        scored.append((score, {
            "memory_id": r["memory_id"], "layer": r["layer"], "content": content,
            "tags": _json(r["tags_json"]), "importance": r["importance"], "score": score,
        }))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:top_k]]


def recent_working(db: str | Path, *, top_k: int = 10) -> list[dict[str, Any]]:
    """L1 working memory, recency-ranked (most recent first)."""
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT * FROM layered_memory WHERE layer=? ORDER BY created_at DESC LIMIT ?",
            (MemoryLayer.L1_WORKING.value, top_k),
        ).fetchall()
    return [{"memory_id": r["memory_id"], "layer": r["layer"], "content": r["content"],
             "tags": _json(r["tags_json"]), "importance": r["importance"],
             "created_at": r["created_at"]} for r in rows]


def working_memory_capacity() -> int:
    return WORKING_MEMORY_CAPACITY
