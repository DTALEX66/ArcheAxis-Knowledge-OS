"""Mistake tracking — error patterns for learning feedback loop.

Captures mistakes during card reviews, analyzes patterns, and provides
feedback for targeted re-study.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from shared.storage import insert, select_all, select_one  # noqa: E402


def record_mistake(
    card_id: str,
    error_type: str,  # "recall_failure" | "concept_confusion" | "application_error"
    detail: str = "",
    source_topic: str = "",
) -> dict[str, Any]:
    """Record a mistake for later analysis.

    Args:
        card_id: the card where the mistake occurred.
        error_type: category of error.
        detail: free-text description.
        source_topic: topic for pattern grouping.

    Returns:
        The created mistake record.
    """
    import uuid

    mistake = {
        "id": f"mistake_{uuid.uuid4().hex[:12]}",
        "card_id": card_id,
        "error_type": error_type,
        "detail": detail,
        "source_topic": source_topic,
        "resolved": False,
        "created_at": datetime.now().isoformat(),
    }
    insert("kb_mistakes", mistake)
    return mistake


def resolve_mistake(mistake_id: str, resolution_note: str = "") -> dict | None:
    """Mark a mistake as resolved."""
    m = select_one("kb_mistakes", mistake_id)
    if not m:
        return None
    m["resolved"] = True
    m["resolution_note"] = resolution_note
    m["resolved_at"] = datetime.now().isoformat()
    insert("kb_mistakes", m)
    return m


def get_unresolved_mistakes(limit: int = 50) -> list[dict[str, Any]]:
    """Return all unresolved mistakes."""
    all_mistakes = select_all("kb_mistakes", limit=500)
    unresolved = [m for m in all_mistakes if not m.get("resolved", False)]
    unresolved.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return unresolved[:limit]


def analyze_patterns() -> dict[str, Any]:
    """Analyze mistake patterns for learning insights.

    Returns:
        Dict with top error types, topics, and recommendations.
    """
    all_mistakes = select_all("kb_mistakes", limit=500)

    # Count by error type
    type_counts: dict[str, int] = {}
    topic_counts: dict[str, int] = {}
    unresolved_count = 0

    for m in all_mistakes:
        et = m.get("error_type", "unknown")
        type_counts[et] = type_counts.get(et, 0) + 1

        topic = m.get("source_topic", "").strip()
        if topic:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        if not m.get("resolved", False):
            unresolved_count += 1

    # Top error types
    top_errors = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    recommendations = []
    for et, count in top_errors:
        if et == "recall_failure" and count >= 3:
            recommendations.append("Consider more frequent reviews for recall-heavy cards")
        elif et == "concept_confusion" and count >= 3:
            recommendations.append("Review related concept cards together to resolve confusion")
        elif et == "application_error" and count >= 3:
            recommendations.append("Add practical exercises or taskpacks for hands-on practice")

    return {
        "total_mistakes": len(all_mistakes),
        "unresolved": unresolved_count,
        "top_error_types": [{"type": et, "count": c} for et, c in top_errors],
        "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
        "recommendations": recommendations,
    }


def get_mistakes_for_card(card_id: str) -> list[dict[str, Any]]:
    """Return all mistakes for a specific card."""
    all_mistakes = select_all("kb_mistakes", limit=500)
    return [m for m in all_mistakes if m.get("card_id") == card_id]
