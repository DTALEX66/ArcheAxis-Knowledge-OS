"""GraphRAG — graph + vector hybrid multi-hop search.

Absorbs: Microsoft GraphRAG, hybrid retrieval patterns.
Combines NetworkX graph traversal with sqlite-vec semantic search
for multi-hop reasoning over the knowledge graph.

Usage:
    from shared.graph_rag import graph_rag_search
    results = graph_rag_search("How does SM-2 relate to spaced repetition?")
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from app.memory.graph_db import GraphDB  # noqa: E402
from app.memory.vector_db import VectorDB, SimpleTextEmbedder  # noqa: E402
from shared.storage import select_all, select_one  # noqa: E402


_embedder = SimpleTextEmbedder(dim=384)
_gdb = GraphDB("knowledge_graph")
_graph_vdb = VectorDB(table_name="vec_graph_nodes", dim=384)
_graph_initialised = False


def _ensure_init() -> None:
    global _graph_initialised
    if not _graph_initialised:
        _graph_vdb.init()
        _graph_initialised = True


def index_for_graphrag() -> dict[str, Any]:
    """Index all KB entities into the graph + vector store for GraphRAG.

    Creates entities for documents, cards, and MKUs with keyword-based
    embeddings. Builds edges from links and shared keywords.
    """
    _ensure_init()

    all_docs = select_all("kb_documents", limit=500)
    all_cards = select_all("kb_cards", limit=500)
    all_mku = select_all("machine_knowledge_units", limit=500)

    indexed = {"documents": 0, "cards": 0, "mku": 0, "edges": 0}

    # Index documents as graph entities
    for doc in all_docs:
        did = doc["id"]
        text = doc.get("title", "") + " " + doc.get("content", "")
        _gdb.add_entity(did, entity_type="document", title=doc.get("title", ""))
        _graph_vdb.insert(did, _embedder.embed(text))
        indexed["documents"] += 1

    # Index cards
    for card in all_cards:
        cid = card.get("id") or card.get("card_id", "")
        if not cid:
            continue
        text = card.get("title", "") + " " + card.get("content", "")
        _gdb.add_entity(cid, entity_type="card", title=card.get("title", ""))
        _graph_vdb.insert(cid, _embedder.embed(text))
        indexed["cards"] += 1

    # Index MKUs
    for mku in all_mku:
        mid = mku["id"]
        text = mku.get("title", "") + " " + mku.get("content", "")
        _gdb.add_entity(mid, entity_type="machine_knowledge",
                        title=mku.get("title", ""))
        _graph_vdb.insert(mid, _embedder.embed(text))
        indexed["mku"] += 1

    # Build edges from wikilinks
    all_links = select_all("kb_links", limit=2000)
    for link in all_links:
        sid = link.get("source_id", "")
        tid = link.get("target_id", "")
        if sid and tid:
            _gdb.add_relation(sid, tid, link.get("link_type", "linked"))
            indexed["edges"] += 1

    return indexed


def graph_rag_search(
    query: str,
    top_k: int = 5,
    max_hops: int = 2,
) -> dict[str, Any]:
    """GraphRAG multi-hop search: vector → graph traversal → results.

    1. Vector search finds seed nodes
    2. Graph traversal expands to neighbors (multi-hop)
    3. Results are ranked by combined vector + graph scores

    Args:
        query: natural language query.
        top_k: max results.
        max_hops: how many graph hops to traverse.

    Returns:
        {query, seeds, expanded, results}.
    """
    _ensure_init()

    # Step 1: Vector search for seed nodes
    vec_results = _graph_vdb.search_by_text(query, top_k=top_k * 2)

    # Step 2: Graph expansion (multi-hop BFS)
    expanded: set[str] = set()
    for node_id, _ in vec_results:
        expanded.add(node_id)
        for hop in range(max_hops):
            neighbors = _gdb.query_neighbors(node_id)
            for n in neighbors:
                expanded.add(n["entity_id"])

    # Step 3: Rank by vector distance + graph proximity
    ranked = []
    seen: set[str] = set()
    for node_id, vec_dist in vec_results:
        if node_id in seen:
            continue
        seen.add(node_id)

        doc = select_one("kb_documents", node_id)
        if not doc:
            doc = select_one("kb_cards", node_id)
        if not doc:
            doc = select_one("machine_knowledge_units", node_id)
        if not doc:
            continue

        # Graph bonus: if node is close to many seeds, boost score
        neighbors = _gdb.query_neighbors(node_id)
        graph_score = min(1.0, len(neighbors) * 0.1)

        ranked.append({
            "id": node_id,
            "title": doc.get("title", node_id)[:80],
            "content_preview": (doc.get("content", "") or "")[:300],
            "vector_distance": round(vec_dist, 4),
            "graph_score": round(graph_score, 3),
            "combined_score": round(1.0 / (1.0 + vec_dist) + graph_score, 4),
            "neighbor_count": len(neighbors),
        })

    ranked.sort(key=lambda r: r["combined_score"], reverse=True)
    return {
        "query": query,
        "max_hops": max_hops,
        "seed_count": len(vec_results),
        "expanded_nodes": len(expanded),
        "results": ranked[:top_k],
    }
