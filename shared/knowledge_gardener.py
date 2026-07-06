"""Knowledge gardener — detects orphans, suggests connections, finds gaps.

Absorbs: Zettelkasten knowledge gardener, Andy Matuschak's evergreen notes,
Tiago Forte's idea emergence patterns.

Capabilities:
1. find_orphans() → notes with no incoming/outgoing links
2. suggest_connections(doc_id) → top candidates for linking
3. detect_gaps(topic) → knowledge areas with thin coverage
4. score_evergreen(doc_id) → how "evergreen" is this note?
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import select_all, select_one  # noqa: E402
from shared.backlinks import compute_backlinks, compute_graph  # noqa: E402
from shared.auto_tagger import extract_keywords  # noqa: E402


def find_orphans(limit: int = 50) -> list[dict[str, Any]]:
    """Find documents and cards with no links (incoming or outgoing).

    Returns:
        List of orphaned items with {id, title, type, link_count}.
    """
    all_docs = select_all("kb_documents", limit=500)
    all_cards = select_all("kb_cards", limit=500)
    all_links = select_all("kb_links", limit=2000)

    # Build link index
    outgoing: set[str] = set()
    incoming: set[str] = set()
    for link in all_links:
        if link.get("source_id"):
            outgoing.add(link["source_id"])
        if link.get("target_id"):
            incoming.add(link["target_id"])

    orphans = []
    for item in list(all_docs) + list(all_cards):
        iid = item.get("id") or item.get("card_id", "")
        if not iid:
            continue
        linked = iid in outgoing or iid in incoming
        if not linked:
            orphans.append({
                "id": iid,
                "title": item.get("title", iid)[:80],
                "type": "card" if "card" in str(type(item)) else "document",
                "link_count": 0,
            })

    return orphans[:limit]


def suggest_connections(doc_id: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Suggest documents/cards that should be linked to the given one.

    Uses keyword similarity to find semantic connections.
    """
    source = select_one("kb_documents", doc_id)
    if not source:
        source = select_one("kb_cards", doc_id)
    if not source:
        return []

    src_text = source.get("title", "") + " " + source.get("content", "")
    src_kw = {k["keyword"] for k in extract_keywords(src_text, top_k=15)}

    all_docs = select_all("kb_documents", limit=200)
    all_cards = select_all("kb_cards", limit=200)

    scored = []
    for item in all_docs + all_cards:
        iid = item.get("id") or item.get("card_id", "")
        if not iid or iid == doc_id:
            continue

        item_text = item.get("title", "") + " " + item.get("content", "")
        item_kw = {k["keyword"] for k in extract_keywords(item_text, top_k=10)}

        overlap = len(src_kw & item_kw)
        if overlap > 0:
            scored.append({
                "id": iid,
                "title": item.get("title", iid)[:80],
                "overlap": overlap,
                "score": round(overlap / max(len(src_kw), 1), 3),
            })

    scored.sort(key=lambda s: s["overlap"], reverse=True)
    return scored[:top_k]


def detect_gaps() -> dict[str, Any]:
    """Analyze knowledge gaps: areas with thin coverage.

    Returns:
        {topics: [{name, count, status}], recommendations}.
    """
    all_cards = select_all("kb_cards", limit=500)
    all_docs = select_all("kb_documents", limit=500)

    # Count by tags
    tag_counts: dict[str, int] = {}
    for item in all_cards + all_docs:
        tags = item.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        for tag in tags:
            if tag and len(tag) > 2:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Sort by count ascending (least covered first)
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1])
    gaps = [
        {"topic": tag, "count": count, "status": "thin" if count < 3 else "moderate"}
        for tag, count in sorted_tags[:15]
    ]

    recommendations = []
    thin_topics = [g for g in gaps if g["status"] == "thin"]
    if thin_topics:
        recommendations.append(
            f"Consider adding more content to: {', '.join(g['topic'] for g in thin_topics[:5])}"
        )
    if len(all_cards) < 10:
        recommendations.append("Very few cards — consider importing more knowledge sources")

    return {
        "total_documents": len(all_docs),
        "total_cards": len(all_cards),
        "total_tags": len(tag_counts),
        "gaps": gaps[:10],
        "recommendations": recommendations,
    }


def score_evergreen(doc_id: str) -> dict[str, Any]:
    """Score how 'evergreen' a note is (Andy Matuschak criteria).

    Evergreen = atomic, well-linked, frequently reviewed, recently updated.
    """
    doc = select_one("kb_documents", doc_id)
    if not doc:
        doc = select_one("kb_cards", doc_id)
    if not doc:
        return {"error": "not found"}

    from shared.auto_tagger import detect_atomicity
    from reviews import get_review_history

    content = doc.get("content", "")
    atomic = detect_atomicity(content)

    # Link count
    backlinks = compute_backlinks(doc_id)
    link_count = len(backlinks)

    # Review count
    reviews = get_review_history(doc_id)
    review_count = len(reviews)
    avg_quality = sum(r.get("quality", 0) for r in reviews) / max(review_count, 1)

    # Compute evergreen score (0-100)
    atomic_score = 30 if atomic["is_atomic"] else 10
    link_score = min(30, link_count * 5)
    review_score = min(20, review_count * 4)
    quality_score = min(20, avg_quality * 4)

    total = atomic_score + link_score + review_score + quality_score

    if total >= 70:
        level = "evergreen"
    elif total >= 40:
        level = "maturing"
    else:
        level = "seedling"

    return {
        "id": doc_id,
        "title": doc.get("title", "")[:80],
        "evergreen_score": total,
        "level": level,
        "breakdown": {
            "atomicity": atomic_score,
            "links": link_score,
            "reviews": review_score,
            "quality": quality_score,
        },
        "atomic": atomic["is_atomic"],
        "link_count": link_count,
        "review_count": review_count,
    }
