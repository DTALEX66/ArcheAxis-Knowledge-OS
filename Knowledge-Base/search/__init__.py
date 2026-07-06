"""Knowledge-Base search — full-text (LIKE) + semantic (sqlite-vec) hybrid.

This module provides a unified search entry point that combines:
1. ``LIKE``-based keyword search (fast, always available)
2. Vector / semantic search via ``vector_search`` (requires sqlite-vec index)

For now, the FTS5 path delegates to LIKE-based text search in ``shared/storage``;
full FTS5 virtual table integration is tracked as P1-2.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root + Knowledge-Base dir are on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

# Import from the sibling `search` package
from search import vector_search  # noqa: E402


def keyword_search(
    query: str, top_k: int = 5
) -> list[dict]:
    """Keyword search over documents and cards using LIKE.

    Falls back to full-table scan with LIKE when no FTS5 index exists.
    """
    from shared.storage import select_all

    terms = query.strip().split()
    if not terms:
        return []

    results = []
    for table, typ in [("kb_documents", "document"), ("kb_cards", "card")]:
        rows = select_all(table, limit=200)
        for row in rows:
            content = row.get("content", "") + " " + row.get("title", "")
            score = sum(1 for t in terms if t.lower() in content.lower())
            if score > 0:
                results.append(
                    {
                        "id": row["id"],
                        "type": typ,
                        "title": row.get("title", ""),
                        "score": score,
                        "snippet": content[:200],
                    }
                )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def hybrid_search(
    query: str, top_k: int = 5
) -> list[dict]:
    """Unified hybrid search: vector + keyword, merged by distance/score."""
    from shared.storage import select_one

    # Vector results
    vec_results = vector_search.search_all(query, top_k=top_k)

    # Keyword results
    kw_results = keyword_search(query, top_k=top_k)

    # Merge: enrich vector results with title/snippet from DB
    merged = {}
    for r in vec_results:
        table = f"kb_{r['type']}s"
        row = select_one(table, r["id"])
        merged[r["id"]] = {
            "id": r["id"],
            "type": r["type"],
            "title": row.get("title", "") if row else "",
            "vector_distance": r["distance"],
            "keyword_score": 0,
            "snippet": (row.get("content", "") if row else "")[:200],
        }

    for r in kw_results:
        if r["id"] in merged:
            merged[r["id"]]["keyword_score"] = r["score"]
        else:
            merged[r["id"]] = {
                "id": r["id"],
                "type": r["type"],
                "title": r.get("title", ""),
                "vector_distance": None,
                "keyword_score": r["score"],
                "snippet": r.get("snippet", ""),
            }

    # Sort: prefer items with both signals, then by vector distance
    def sort_key(item: dict) -> tuple:
        has_both = (
            0
            if (item["vector_distance"] is not None and item["keyword_score"] > 0)
            else 1
        )
        vec_dist = (
            item["vector_distance"] if item["vector_distance"] is not None else 999
        )
        kw_score = -item["keyword_score"]
        return (has_both, vec_dist, kw_score)

    sorted_items = sorted(merged.values(), key=sort_key)
    return sorted_items[:top_k]
