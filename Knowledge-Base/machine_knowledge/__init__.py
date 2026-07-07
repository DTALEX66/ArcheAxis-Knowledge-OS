"""Machine knowledge units — AI-consumable structured knowledge for B-line.

Replaces the stub. Integrates with shared/storage.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from shared.storage import count, insert, select_all, select_one  # noqa: E402


def create_unit(
    title: str,
    content: str = "",
    unit_type: str = "rule",
    tags: list[str] | None = None,
    confidence: float = 0.5,
    source_type: str = "manual",
    source_id: str = "",
) -> dict[str, Any]:
    """Create a machine knowledge unit.

    Args:
        title: short label.
        content: the knowledge body (rule, fact, procedure).
        unit_type: 'rule' | 'fact' | 'procedure' | 'constraint' | 'pattern'.
        tags: list of topic tags.
        confidence: 0.0–1.0 trust score.
        source_type: where this came from ('a_to_b', 'manual', 'research').
        source_id: ID of the source card/document if applicable.

    Returns:
        The created unit dict.
    """
    unit_id = f"mku_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    unit = {
        "id": unit_id,
        "title": title,
        "content": content,
        "unit_type": unit_type,
        "tags": tags or [],
        "confidence": confidence,
        "source_type": source_type,
        "source_id": source_id,
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    insert("machine_knowledge_units", unit)
    return unit


def search_units(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Keyword search over machine knowledge units."""
    from shared.storage import fts5_search

    # Use FTS5 if available
    try:
        return fts5_search("machine_knowledge_units", query, top_k=limit)
    except Exception:
        pass

    # Fallback: LIKE
    rows = select_all("machine_knowledge_units", limit=200)
    terms = query.lower().split()
    results = []
    for r in rows:
        content = (r.get("title", "") + " " + r.get("content", "")).lower()
        score = sum(1 for t in terms if t in content)
        if score > 0:
            r["_score"] = score
            results.append(r)
    results.sort(key=lambda r: r.get("_score", 0), reverse=True)
    return results[:limit]


def get_unit(unit_id: str) -> dict[str, Any] | None:
    """Retrieve a single unit by ID."""
    return select_one("machine_knowledge_units", unit_id)


def list_by_type(unit_type: str, limit: int = 20) -> list[dict[str, Any]]:
    """List active units of a given type."""
    rows = select_all("machine_knowledge_units", limit=500)
    return [r for r in rows if r.get("unit_type") == unit_type and r.get("active", True)][:limit]


def deactivate_unit(unit_id: str) -> dict | None:
    """Mark a unit as inactive (soft delete)."""
    unit = select_one("machine_knowledge_units", unit_id)
    if not unit:
        return None
    unit["active"] = False
    unit["updated_at"] = datetime.now(timezone.utc).isoformat()
    insert("machine_knowledge_units", unit)
    return unit


def stats() -> dict[str, Any]:
    """Return machine knowledge statistics."""
    rows = select_all("machine_knowledge_units", limit=1000)
    active = [r for r in rows if r.get("active", True)]
    by_type: dict[str, int] = {}
    for r in active:
        t = r.get("unit_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total_units": len(rows),
        "active_units": len(active),
        "by_type": by_type,
        "avg_confidence": round(
            sum(r.get("confidence", 0) for r in active) / max(len(active), 1), 3
        ),
    }
