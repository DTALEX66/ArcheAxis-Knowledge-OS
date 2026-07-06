"""Semantic vector search for Knowledge-Base documents and cards.

Built on top of :class:`app.memory.vector_db.VectorDB` with sqlite-vec.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))

from app.memory.vector_db import SimpleTextEmbedder, VectorDB  # noqa: E402

# ── singleton ───────────────────────────────────────────

_embedder = SimpleTextEmbedder(dim=384)
_doc_vdb = VectorDB(table_name="vec_kb_documents", dim=384)
_card_vdb = VectorDB(table_name="vec_kb_cards", dim=384)
_initialised = False


def _ensure_init() -> None:
    global _initialised
    if not _initialised:
        _doc_vdb.init()
        _card_vdb.init()
        _initialised = True


# ── index ───────────────────────────────────────────────


def index_document(doc_id: str, content: str) -> None:
    """Index a KB document for vector search."""
    _ensure_init()
    vec = _embedder.embed(content)
    _doc_vdb.insert(doc_id, vec)


def index_card(card_id: str, content: str) -> None:
    """Index a KB card for vector search."""
    _ensure_init()
    vec = _embedder.embed(content)
    _card_vdb.insert(card_id, vec)


def remove_document(doc_id: str) -> None:
    _ensure_init()
    _doc_vdb.delete(doc_id)


def remove_card(card_id: str) -> None:
    _ensure_init()
    _card_vdb.delete(card_id)


# ── search ──────────────────────────────────────────────


def search_documents(
    query: str, top_k: int = 5
) -> list[tuple[str, float]]:
    """Semantic search over indexed documents. Returns (doc_id, distance)."""
    _ensure_init()
    return _doc_vdb.search_by_text(query, top_k=top_k)


def search_cards(
    query: str, top_k: int = 5
) -> list[tuple[str, float]]:
    """Semantic search over indexed cards. Returns (card_id, distance)."""
    _ensure_init()
    return _card_vdb.search_by_text(query, top_k=top_k)


def search_all(
    query: str, top_k: int = 5
) -> list[dict]:
    """Combined search: documents + cards, merged by distance.

    Returns list of dicts: {id, type, distance}.
    """
    _ensure_init()
    docs = _doc_vdb.search_by_text(query, top_k=top_k)
    cards = _card_vdb.search_by_text(query, top_k=top_k)

    results = []
    for oid, dist in docs:
        results.append({"id": oid, "type": "document", "distance": round(dist, 4)})
    for oid, dist in cards:
        results.append({"id": oid, "type": "card", "distance": round(dist, 4)})

    results.sort(key=lambda r: r["distance"])
    return results[:top_k]


# ── stats ───────────────────────────────────────────────


def stats() -> dict:
    """Return index statistics."""
    _ensure_init()
    return {
        "documents_indexed": _doc_vdb.count(),
        "cards_indexed": _card_vdb.count(),
        "total_indexed": _doc_vdb.count() + _card_vdb.count(),
        "embedder": "SimpleTextEmbedder(ngram_hash, dim=384)",
    }


def rebuild_index() -> dict:
    """Drop and recreate both vector indexes (data-lossy — re-index needed)."""
    _ensure_init()
    _doc_vdb.drop()
    _card_vdb.drop()
    _doc_vdb.init()
    _card_vdb.init()
    global _initialised
    _initialised = True
    return {"status": "rebuilt", "documents_indexed": 0, "cards_indexed": 0}
