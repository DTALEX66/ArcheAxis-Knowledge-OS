"""Knowledge-Base search — FTS5 full-text + sqlite-vec vector hybrid.

This module provides a unified search entry point that combines:
1. FTS5 full-text search (fast BM25 ranking, always available)
2. Vector / semantic search via ``vector_search`` (sqlite-vec cosine distance)

Both are merged in ``hybrid_search()`` for best results.
"""

from __future__ import annotations

from knowledge_base.search import vector_search
from shared.storage import fts5_search as _fts5


def keyword_search(query: str, top_k: int = 5) -> list[dict]:
    """FTS5 full-text keyword search over documents and cards.

    Uses BM25 ranking. Falls back to LIKE scan if FTS5 index not yet built.
    """
    if not query or not query.strip():
        return []

    results = []
    for table, typ in [("kb_documents", "document"), ("kb_cards", "card")]:
        hits = _fts5(table, query, top_k=top_k)
        for h in hits:
            results.append(
                {
                    "id": h["id"],
                    "type": typ,
                    "title": h.get("title", ""),
                    "score": -h.get("rank", 999),  # negate so higher = better
                    "snippet": h.get("snippet", ""),
                }
            )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    """Unified hybrid search: vector + keyword, merged by distance/score."""
    from shared.storage import select_one

    # Vector results
    vec_results = vector_search.search_all(query, top_k=top_k)

    # Keyword results (FTS5)
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
        has_both = 0 if (item["vector_distance"] is not None and item["keyword_score"] > 0) else 1
        vec_dist = item["vector_distance"] if item["vector_distance"] is not None else 999
        kw_score = -item["keyword_score"]
        return (has_both, vec_dist, kw_score)

    sorted_items = sorted(merged.values(), key=sort_key)
    return sorted_items[:top_k]
