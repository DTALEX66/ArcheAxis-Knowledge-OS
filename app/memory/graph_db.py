"""NetworkX-based graph database for entity-relationship storage.

Replaces the 3-line stub.  Builds on NetworkX (already in requirements.txt).
Stores graphs as JSON-serializable dicts in SQLite for persistence,
with NetworkX in-memory for fast traversal.

Usage:
    from app.memory.graph_db import GraphDB
    gdb = GraphDB()
    gdb.add_entity("alice", type="person", props={"role": "agent"})
    gdb.add_relation("alice", "bob", "knows")
    gdb.query_neighbors("alice")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from shared.research_boundary import unreviewed_research_references
from shared.storage import insert, select_all

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class GraphDB:
    """Entity-relationship graph with SQLite persistence + NetworkX queries."""

    def __init__(self, graph_name: str = "default") -> None:
        self.graph_name = graph_name
        self._g = nx.DiGraph()
        self._loaded = False

    # ── persistence ──────────────────────────────────

    def _load(self) -> None:
        """Load graph from SQLite into NetworkX."""
        if self._loaded:
            return
        rows = select_all("graph_entities", limit=5000)
        for r in rows:
            props = r.get("properties", {})
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except (json.JSONDecodeError, TypeError):
                    props = {}
            self._g.add_node(r["id"], type=r.get("entity_type", ""), **props)

        rels = select_all("graph_relations", limit=5000)
        for r in rels:
            self._g.add_edge(
                r["source_id"],
                r["target_id"],
                relation=r.get("relation_type", ""),
                weight=r.get("weight", 1.0),
            )
        self._loaded = True

    def _persist_entity(self, entity_id: str, entity_type: str, props: dict) -> None:
        insert(
            "graph_entities",
            {
                "id": entity_id,
                "entity_type": entity_type,
                "properties": props,
                "graph_name": self.graph_name,
            },
        )

    def _persist_relation(self, source: str, target: str, relation: str, weight: float) -> None:
        import uuid

        rid = f"rel_{uuid.uuid4().hex[:12]}"
        insert(
            "graph_relations",
            {
                "id": rid,
                "source_id": source,
                "target_id": target,
                "relation_type": relation,
                "weight": weight,
                "graph_name": self.graph_name,
            },
        )

    # ── CRUD ─────────────────────────────────────────

    def add_entity(self, entity_id: str, entity_type: str = "node", **props: Any) -> None:
        """Add or update an entity node."""
        if unreviewed_research_references([entity_id]):
            raise ValueError(
                "candidate or external graph entities require server-owned Phase 5 review provenance"
            )
        self._load()
        self._g.add_node(entity_id, entity_type=entity_type, **props)
        self._persist_entity(entity_id, entity_type, props)

    def add_relation(
        self, source: str, target: str, relation: str, weight: float = 1.0
    ) -> dict[str, Any]:
        """Add a directed edge between entities."""
        if unreviewed_research_references([source, target]):
            raise ValueError(
                "candidate or external graph relations require server-owned Phase 5 review provenance"
            )
        self._load()
        # Ensure nodes exist (lazy auto-create)
        if source not in self._g:
            self.add_entity(source)
        if target not in self._g:
            self.add_entity(target)

        self._g.add_edge(source, target, relation=relation, weight=weight)
        self._persist_relation(source, target, relation, weight)
        return {"source": source, "target": target, "relation": relation}

    def query_neighbors(self, entity_id: str, max_depth: int = 1) -> list[dict[str, Any]]:
        """Return all neighbors (1-hop by default)."""
        self._load()
        if entity_id not in self._g:
            return []

        neighbors = []
        for neighbor in nx.neighbors(self._g, entity_id):
            edge = self._g.edges[entity_id, neighbor]
            node = self._g.nodes[neighbor]
            neighbors.append(
                {
                    "entity_id": neighbor,
                    "type": node.get("entity_type", ""),
                    "relation": edge.get("relation", ""),
                    "weight": edge.get("weight", 1.0),
                    "props": {k: v for k, v in node.items() if k != "entity_type"},
                }
            )
        return neighbors

    def shortest_path(self, source: str, target: str) -> list[str] | None:
        """Find shortest path between two entities."""
        self._load()
        try:
            return nx.shortest_path(self._g, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def find_by_type(self, entity_type: str, limit: int = 50) -> list[dict[str, Any]]:
        """Find all entities of a given type."""
        self._load()
        results = []
        for nid, data in self._g.nodes(data=True):
            if data.get("entity_type") == entity_type:
                results.append(
                    {
                        "entity_id": nid,
                        "type": entity_type,
                        "props": {k: v for k, v in data.items() if k != "entity_type"},
                    }
                )
                if len(results) >= limit:
                    break
        return results

    def subgraph(self, entity_ids: list[str], depth: int = 1) -> dict[str, Any]:
        """Extract a subgraph around given entities."""
        self._load()
        nodes: set[str] = set(entity_ids)
        for _ in range(depth):
            frontier = set()
            for n in list(nodes):
                frontier.update(self._g.neighbors(n))
                frontier.update(self._g.predecessors(n))
            nodes.update(frontier)

        sg = self._g.subgraph(nodes)
        return {
            "nodes": [{"id": n, "type": d.get("entity_type", "")} for n, d in sg.nodes(data=True)],
            "edges": [
                {"source": u, "target": v, "relation": d.get("relation", "")}
                for u, v, d in sg.edges(data=True)
            ],
        }

    def stats(self) -> dict[str, Any]:
        """Return graph statistics."""
        self._load()
        return {
            "node_count": self._g.number_of_nodes(),
            "edge_count": self._g.number_of_edges(),
            "graph_name": self.graph_name,
        }

    def clear(self) -> None:
        """Clear the in-memory graph (persisted data remains until DB cleanup)."""
        self._g.clear()
        self._loaded = False
