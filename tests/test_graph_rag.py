"""Tests for shared.graph_rag (graph + vector hybrid multi-hop search).

The module instantiates module-level GraphDB/VectorDB singletons at
import time; tests replace them with fakes so no sqlite-vec / DB
initialization is required.
"""

from __future__ import annotations

import shared.graph_rag as gr


class _FakeGraph:
    def __init__(self) -> None:
        self.entities = {}
        self.relations = []

    def add_entity(self, eid, entity_type="", title=""):
        self.entities[eid] = {"entity_type": entity_type, "title": title}

    def add_relation(self, source, target, rel_type="linked"):
        self.relations.append((source, target, rel_type))

    def query_neighbors(self, node_id):
        neighbors = []
        for s, t, _rt in self.relations:
            if s == node_id:
                neighbors.append({"entity_id": t})
            if t == node_id:
                neighbors.append({"entity_id": s})
        return neighbors


class _FakeVDB:
    def __init__(self) -> None:
        self.rows = {}
        self.init_called = False

    def init(self):
        self.init_called = True

    def insert(self, eid, vector):
        self.rows[eid] = vector

    def search_by_text(self, query, top_k=5):
        # deterministic fake: return inserted rows in insertion order
        return [(eid, 0.5) for eid in list(self.rows)[:top_k]]


class _FakeEmbedder:
    def embed(self, text):
        return [0.0] * 384


def test_index_for_graphrag_counts(monkeypatch) -> None:
    fake_gdb = _FakeGraph()
    fake_vdb = _FakeVDB()
    monkeypatch.setattr(gr, "_gdb", fake_gdb)
    monkeypatch.setattr(gr, "_graph_vdb", fake_vdb)
    monkeypatch.setattr(gr, "_embedder", _FakeEmbedder())
    monkeypatch.setattr(gr, "_graph_initialised", False)

    docs = [{"id": "d1", "title": "Doc", "content": "text"}]
    cards = [{"card_id": "c1", "title": "Card", "content": "body"}]
    mkus = [{"id": "m1", "title": "MKU", "content": "rule"}]
    links = [{"source_id": "d1", "target_id": "c1", "link_type": "linked"}]

    def fake_select_all(table, limit):
        return {"kb_documents": docs, "kb_cards": cards, "machine_knowledge_units": mkus, "kb_links": links}[table]

    monkeypatch.setattr("shared.graph_rag.select_all", fake_select_all)
    indexed = gr.index_for_graphrag()
    assert indexed["documents"] == 1
    assert indexed["cards"] == 1
    assert indexed["mku"] == 1
    assert indexed["edges"] == 1
    assert fake_vdb.init_called is True
    assert "d1" in fake_gdb.entities
    assert "c1" in fake_gdb.entities
    assert len(fake_vdb.rows) == 3


def test_graph_rag_search_expands_and_ranks(monkeypatch) -> None:
    fake_gdb = _FakeGraph()
    fake_gdb.relations = [("d1", "c1", "linked")]
    fake_vdb = _FakeVDB()
    fake_vdb.rows = {"d1": [0.0] * 384, "c1": [0.0] * 384}
    monkeypatch.setattr(gr, "_gdb", fake_gdb)
    monkeypatch.setattr(gr, "_graph_vdb", fake_vdb)
    monkeypatch.setattr(gr, "_graph_initialised", True)

    docs = {"d1": {"id": "d1", "title": "Doc One", "content": "content here"}}
    cards = {"c1": {"card_id": "c1", "title": "Card One", "content": "card body"}}

    def fake_select_one(table, sid):
        return docs.get(sid) or cards.get(sid) or ({"id": sid, "title": sid, "content": ""} if table == "machine_knowledge_units" else None)

    monkeypatch.setattr("shared.graph_rag.select_one", fake_select_one)
    result = gr.graph_rag_search("spaced repetition", top_k=5, max_hops=2)
    assert result["query"] == "spaced repetition"
    assert result["seed_count"] == 2
    assert result["expanded_nodes"] >= 2
    assert len(result["results"]) == 2
    ids = [r["id"] for r in result["results"]]
    assert "d1" in ids
    assert "c1" in ids
    # combined_score includes vector + graph components
    assert all(r["combined_score"] > 0 for r in result["results"])
    assert all("neighbor_count" in r for r in result["results"])
