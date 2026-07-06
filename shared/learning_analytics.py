"""Learning analytics — adapted from Obsidian-Assistance v8 training_streak_radar.

Tracks learning streaks, completion rates, and training patterns
from review and daily note data.

Adapted from: scripts/v8/training_streak_radar.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import select_all  # noqa: E402


def review_streak(days: int = 30) -> dict[str, Any]:
    """Compute review streak and stats over the last N days.

    Returns:
        {current_streak, longest_streak, daily_counts, completion_rate, trend}.
    """
    reviews = select_all("kb_reviews", limit=1000)
    daily_notes = select_all("daily_notes", limit=100)

    # Build daily activity map
    today = date.today()
    daily_activity: dict[str, int] = {}

    for r in reviews:
        created = r.get("created_at", "")[:10]
        if created:
            daily_activity[created] = daily_activity.get(created, 0) + 1

    for dn in daily_notes:
        d = dn.get("date", "")
        if d:
            daily_activity[d] = daily_activity.get(d, 0) + 1

    # Compute streak (consecutive days with activity)
    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    for i in range(days):
        d = (today - timedelta(days=i)).isoformat()
        if daily_activity.get(d, 0) > 0:
            temp_streak += 1
            if i == 0:
                current_streak = 1  # today counts
        else:
            longest_streak = max(longest_streak, temp_streak)
            if i == 0:
                current_streak = 0
            temp_streak = 0

    longest_streak = max(longest_streak, temp_streak)

    # Daily counts
    daily_counts = [
        {"date": (today - timedelta(days=i)).isoformat(),
         "count": daily_activity.get((today - timedelta(days=i)).isoformat(), 0)}
        for i in range(min(days, 14))
    ]

    # Completion rate (quality >= 3 reviews)
    total_reviews = len(reviews)
    good_reviews = sum(1 for r in reviews if r.get("quality", 0) >= 3)
    completion_rate = round(good_reviews / max(total_reviews, 1) * 100, 1)

    # Trend (comparing last 7 days vs previous 7)
    last_7 = sum(
        daily_activity.get((today - timedelta(days=i)).isoformat(), 0)
        for i in range(7)
    )
    prev_7 = sum(
        daily_activity.get((today - timedelta(days=i)).isoformat(), 0)
        for i in range(7, 14)
    )
    if prev_7 > 0:
        trend = "up" if last_7 > prev_7 else "down" if last_7 < prev_7 else "stable"
    else:
        trend = "new"

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "days_tracked": days,
        "total_reviews": total_reviews,
        "completion_rate": completion_rate,
        "trend": trend,
        "daily_counts": daily_counts,
    }


def topic_heatmap(limit: int = 20) -> list[dict[str, Any]]:
    """Generate a topic activity heatmap from review data.

    Returns topics sorted by review frequency.
    """
    reviews = select_all("kb_reviews", limit=1000)
    cards = {c.get("id") or c.get("card_id", ""): c for c in select_all("kb_cards", limit=500)}

    topic_activity: dict[str, dict[str, int]] = {}
    for r in reviews:
        cid = r.get("card_id", "")
        card = cards.get(cid, {})
        tags = card.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        for tag in tags[:3]:
            if tag not in topic_activity:
                topic_activity[tag] = {"reviews": 0, "avg_quality": 0, "qualities": []}
            topic_activity[tag]["reviews"] += 1
            q = r.get("quality", 0)
            if q:
                topic_activity[tag]["qualities"].append(q)

    heatmap = []
    for tag, data in topic_activity.items():
        quals = data["qualities"]
        avg_q = round(sum(quals) / len(quals), 1) if quals else 0
        heatmap.append({
            "topic": tag,
            "review_count": data["reviews"],
            "avg_quality": avg_q,
            "intensity": "🔥" if data["reviews"] >= 10 else "🟡" if data["reviews"] >= 5 else "🔵",
        })

    heatmap.sort(key=lambda h: h["review_count"], reverse=True)
    return heatmap[:limit]
