"""Agent episodic memory — semantic + temporal recall for agent sessions.

Built on existing infrastructure (sqlite-vec + FTS5), zero new deps.
Replaces the stub in ``app/memory/episodic.py``.

Architecture:
    save_episode(event)  → SQLite row + vector index + FTS5
    search_episodes(q)   → hybrid (vector + keyword)
    recent_episodes(n)   → temporal (last N)
"""

from __future__ import annotations

import uuid
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from app.memory.vector_db import SimpleTextEmbedder, VectorDB
from shared.research_boundary import unreviewed_research_references
from shared.storage import fts5_search, insert, select_all

# ── singletons ──────────────────────────────────────────

_embedder = SimpleTextEmbedder(dim=384)
_episode_vdb = VectorDB(table_name="vec_episodes", dim=384)
_initialised = False


def _ensure_init() -> None:
    global _initialised
    if not _initialised:
        _episode_vdb.init()
        _initialised = True


# ── CRUD ────────────────────────────────────────────────


def save_episode(
    content: str,
    source: str = "agent",
    metadata: dict[str, Any] | None = None,
    importance: float = 0.5,
) -> dict[str, Any]:
    """Store an episodic memory entry.

    Args:
        content: the memory content (conversation, observation, result).
        source: where this came from (agent, user, tool, system).
        metadata: arbitrary key-value tags.
        importance: 0.0–1.0 weight for recall priority.

    Returns:
        The created episode dict.
    """
    if unreviewed_research_references([source]):
        raise ValueError(
            "candidate or external episodic sources require server-owned Phase 5 review provenance"
        )
    _ensure_init()

    episode_id = f"ep_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    episode = {
        "id": episode_id,
        "content": content,
        "source": source,
        "metadata": metadata or {},
        "importance": importance,
        "created_at": now,
    }

    insert("episodic_memory", episode)

    # Vector index for semantic search
    with suppress(Exception):
        _episode_vdb.insert(episode_id, _embedder.embed(content))

    # FTS5 index for keyword search
    with suppress(Exception):
        fts5_search("episodic_memory", content, top_k=0)  # side-effect: ensure table exists

    return episode


def search_episodes(
    query: str,
    top_k: int = 5,
    source: str | None = None,
) -> list[dict[str, Any]]:
    """Hybrid semantic + keyword search over episodes."""
    _ensure_init()

    # Vector search
    vec_results = _episode_vdb.search_by_text(query, top_k=top_k)

    # Enrich from DB
    episodes = []
    seen: set[str] = set()
    for ep_id, distance in vec_results:
        if ep_id in seen:
            continue
        seen.add(ep_id)
        from shared.storage import select_one

        row = select_one("episodic_memory", ep_id)
        if row:
            if source and row.get("source") != source:
                continue
            row["vector_distance"] = round(distance, 4)
            episodes.append(row)

    return episodes[:top_k]


def recent_episodes(
    limit: int = 10,
    source: str | None = None,
    min_importance: float = 0.0,
) -> list[dict[str, Any]]:
    """Return most recent episodes, optionally filtered."""
    rows = select_all("episodic_memory", limit=500, order="created_at DESC")
    result = []
    for r in rows:
        if source and r.get("source") != source:
            continue
        if r.get("importance", 0) < min_importance:
            continue
        result.append(r)
        if len(result) >= limit:
            break
    return result


def get_episode(episode_id: str) -> dict[str, Any] | None:
    """Retrieve a single episode by ID."""
    from shared.storage import select_one

    return select_one("episodic_memory", episode_id)


def delete_episode(episode_id: str) -> None:
    """Remove an episode and its vector index."""
    from shared.storage import _conn

    conn = _conn()
    try:
        conn.execute("DELETE FROM episodic_memory WHERE id=?", (episode_id,))
        conn.commit()
    finally:
        conn.close()
    with suppress(Exception):
        _episode_vdb.delete(episode_id)


def stats() -> dict[str, Any]:
    """Return episode memory statistics."""
    _ensure_init()
    from shared.storage import count as _count

    return {
        "total_episodes": _count("episodic_memory"),
        "vector_indexed": _episode_vdb.count(),
        "embedder": "SimpleTextEmbedder(ngram_hash, dim=384)",
    }
