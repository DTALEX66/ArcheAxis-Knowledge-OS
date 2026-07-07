"""Retrospective summary generator — adapted from Obsidian-Assistance v8.

Generates periodic knowledge summaries from daily notes, reviews,
and machine knowledge activity.  Like a "weekly review" auto-generated.

Adapted from: scripts/v8/retro_summary_generator.py + daily_mission_generator.py
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import select_all  # noqa: E402


def weekly_summary(days: int = 7) -> dict[str, Any]:
    """Generate a weekly retrospective summary.

    Aggregates: reviews done, new cards, mistakes resolved,
    machine knowledge created, daily note activity.

    Returns:
        A structured summary dict suitable for rendering or API response.
    """
    today = date.today()
    cutoff = (today - timedelta(days=days)).isoformat()

    # Gather data
    reviews = [
        r
        for r in select_all("kb_reviews", limit=500)
        if (r.get("created_at", "") or "")[:10] >= cutoff[:10]
    ]
    cards = [
        c
        for c in select_all("kb_cards", limit=500)
        if (c.get("created_at", "") or "")[:10] >= cutoff[:10]
    ]
    mistakes = [
        m
        for m in select_all("kb_mistakes", limit=500)
        if (m.get("created_at", "") or "")[:10] >= cutoff[:10]
    ]
    mkus = [
        m
        for m in select_all("machine_knowledge_units", limit=500)
        if (m.get("created_at", "") or "")[:10] >= cutoff[:10]
    ]
    daily_notes = [
        d for d in select_all("daily_notes", limit=50) if d.get("date", "") >= cutoff[:10]
    ]

    # Compute stats
    review_count = len(reviews)
    avg_quality = round(sum(r.get("quality", 0) for r in reviews) / max(review_count, 1), 1)
    new_cards = len(cards)
    mistakes_found = len(mistakes)
    mistakes_resolved = sum(1 for m in mistakes if m.get("resolved"))
    new_mku = len(mkus)
    active_days = len(set(d.get("date", "")[:10] for d in daily_notes))

    # Top topics from cards
    topic_counter: Counter = Counter()
    for c in cards:
        tags = c.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        for t in tags[:3]:
            if t:
                topic_counter[t] += 1

    top_topics = [{"topic": t, "count": c} for t, c in topic_counter.most_common(5)]

    # Recommendations
    recommendations = []
    if active_days < days // 2:
        recommendations.append("Try to engage with KB more frequently — aim for daily reviews.")
    if new_cards == 0:
        recommendations.append(
            "No new cards this period. Consider importing new knowledge sources."
        )
    if mistakes_found > 0 and mistakes_resolved == 0:
        recommendations.append(
            f"{mistakes_found} mistakes recorded but none resolved. Review them."
        )

    return {
        "period": f"Last {days} days ({cutoff[:10]} to {today.isoformat()})",
        "stats": {
            "reviews_completed": review_count,
            "average_quality": avg_quality,
            "new_cards": new_cards,
            "mistakes_found": mistakes_found,
            "mistakes_resolved": mistakes_resolved,
            "new_machine_knowledge": new_mku,
            "active_days": active_days,
        },
        "top_topics": top_topics,
        "recommendations": recommendations,
    }


def generate_daily_missions() -> dict[str, Any]:
    """Auto-generate daily learning missions based on review queue + gaps.

    Adapted from v8 daily_mission_generator.py.

    Returns:
        {date, missions: [{type, target, reason}]}.
    """
    from reviews import get_due_reviews

    from shared.knowledge_gardener import detect_gaps

    due = get_due_reviews(limit=10)
    gaps = detect_gaps()

    missions = []

    # Mission 1: Review due cards
    if due:
        missions.append(
            {
                "type": "review",
                "priority": "high",
                "target": f"Review {len(due)} due cards",
                "details": [d.get("title", "")[:60] for d in due[:5]],
                "reason": f"{len(due)} cards are due for review",
            }
        )

    # Mission 2: Fill knowledge gaps
    thin_topics = gaps.get("gaps", [])[:3]
    if thin_topics:
        missions.append(
            {
                "type": "study",
                "priority": "medium",
                "target": "Study thin knowledge areas",
                "details": [t["topic"] for t in thin_topics],
                "reason": f"Topics with thin coverage: {', '.join(t['topic'] for t in thin_topics)}",
            }
        )

    # Mission 3: Create machine knowledge from mastered cards
    mastered = [
        c for c in select_all("kb_cards", limit=200) if c.get("review_status") == "mastered"
    ]
    if mastered:
        missions.append(
            {
                "type": "publish",
                "priority": "medium",
                "target": f"Publish {min(3, len(mastered))} mastered cards to machine knowledge",
                "details": [m.get("title", "")[:60] for m in mastered[:3]],
                "reason": "Mastered cards can be converted to machine knowledge units",
            }
        )

    return {
        "date": date.today().isoformat(),
        "mission_count": len(missions),
        "missions": missions,
    }
