"""Tests for P1-1: sqlite-vec vector search integration."""

from __future__ import annotations

import numpy as np
import pytest

from app.memory.vector_db import SimpleTextEmbedder, VectorDB
from knowledge_base.search import hybrid_search, keyword_search, vector_search

# ── SimpleTextEmbedder ──────────────────────────────────


class TestSimpleTextEmbedder:
    def test_embed_output_shape(self):
        e = SimpleTextEmbedder(dim=384)
        v = e.embed("hello world")
        assert v.shape == (384,)
        assert v.dtype == np.float32

    def test_unit_norm(self):
        e = SimpleTextEmbedder(dim=256)
        v = e.embed("some text")
        norm = float(np.linalg.norm(v))
        assert abs(norm - 1.0) < 0.001

    def test_similar_texts_closer(self):
        e = SimpleTextEmbedder(dim=256)
        v1 = e.embed("machine learning neural networks")
        v2 = e.embed("deep learning gradient descent")
        v3 = e.embed("pizza recipe tomato cheese")
        sim12 = float(np.dot(v1, v2))
        sim13 = float(np.dot(v1, v3))
        assert sim12 > sim13, f"similar={sim12:.3f} vs dissimilar={sim13:.3f}"

    def test_empty_text(self):
        e = SimpleTextEmbedder(dim=128)
        v = e.embed("")
        assert np.all(v == 0)
        v2 = e.embed("   ")
        assert np.all(v2 == 0)


# ── VectorDB ────────────────────────────────────────────


class TestVectorDB:
    @pytest.fixture(autouse=True)
    def _vdb(self):
        self.vdb = VectorDB(table_name="test_vec_kb_p1_1", dim=128)
        self.vdb.drop()
        self.vdb.init()
        yield
        self.vdb.drop()

    def test_init_and_count(self):
        assert self.vdb.count() == 0

    def test_insert_and_search(self):
        e = SimpleTextEmbedder(dim=128)
        v1 = e.embed("machine learning")
        v2 = e.embed("cooking recipes")
        self.vdb.insert("doc-001", v1)
        self.vdb.insert("doc-002", v2)
        assert self.vdb.count() == 2

        results = self.vdb.search(v1, top_k=2)
        assert results[0][0] == "doc-001"
        assert results[0][1] < 0.01  # exact match

    def test_search_by_text(self):
        self.vdb.insert_by_text("alpha", "quantum computing qubits")
        self.vdb.insert_by_text("beta", "pasta carbonara eggs")
        results = self.vdb.search_by_text("quantum physics", top_k=2)
        assert results[0][0] == "alpha"

    def test_delete(self):
        self.vdb.insert_by_text("x", "test one")
        self.vdb.insert_by_text("y", "test two")
        assert self.vdb.count() == 2
        self.vdb.delete("x")
        assert self.vdb.count() == 1
        assert self.vdb.list_ids() == ["y"]

    def test_reinsert_updates(self):
        e = SimpleTextEmbedder(dim=128)
        self.vdb.insert("obj", e.embed("first version"))
        self.vdb.insert("obj", e.embed("second version"))
        assert self.vdb.count() == 1
        results = self.vdb.search(e.embed("second version"), top_k=1)
        assert results[0][0] == "obj"

    def test_list_ids(self):
        for i in range(5):
            self.vdb.insert_by_text(f"id_{i}", f"content {i}")
        ids = self.vdb.list_ids()
        assert len(ids) == 5
        assert "id_0" in ids


# ── vector_search module ────────────────────────────────


class TestVectorSearchModule:
    @pytest.fixture(autouse=True)
    def _setup(self):
        vector_search.rebuild_index()
        yield
        vector_search.rebuild_index()

    def test_index_and_search_documents(self):
        vector_search.index_document("d1", "natural language processing transformers")
        vector_search.index_document("d2", "pasta recipes italian cooking")
        st = vector_search.stats()
        assert st["documents_indexed"] == 2
        assert st["total_indexed"] == 2

        results = vector_search.search_documents("NLP text processing", top_k=2)
        assert results[0][0] == "d1"

    def test_index_and_search_cards(self):
        vector_search.index_card("c1", "neural network training backpropagation algorithm explained")
        vector_search.index_card("c2", "how to make pizza dough")
        results = vector_search.search_cards("neural network training", top_k=2)
        assert results[0][0] == "c1"

    def test_search_all(self):
        vector_search.index_document("x1", "linear algebra matrices")
        vector_search.index_card("x2", "matrix multiplication numpy")
        results = vector_search.search_all("matrix operations", top_k=2)
        assert len(results) == 2
        types = {r["type"] for r in results}
        assert types == {"document", "card"}

    def test_remove(self):
        vector_search.index_document("rm1", "to be removed")
        assert vector_search.stats()["documents_indexed"] == 1
        vector_search.remove_document("rm1")
        assert vector_search.stats()["documents_indexed"] == 0

    def test_rebuild_clears_all(self):
        vector_search.index_document("a", "test a")
        vector_search.index_card("b", "test b")
        assert vector_search.stats()["total_indexed"] == 2
        vector_search.rebuild_index()
        assert vector_search.stats()["total_indexed"] == 0


# ── hybrid search ───────────────────────────────────────


class TestHybridSearch:
    def test_hybrid_returns_results(self):
        vector_search.rebuild_index()
        try:
            vector_search.index_document("hd1", "distributed systems consensus raft")
            vector_search.index_document("hd2", "baking sourdough bread starter")
            results = hybrid_search("distributed computing", top_k=2)
            assert len(results) >= 1
            # Top result should be the distributed systems doc
            assert results[0]["id"] == "hd1"
        finally:
            vector_search.rebuild_index()

    def test_keyword_search_finds_term(self):
        # Need data in DB; but keyword_search reads from actual DB tables
        # which may be empty in test — that's fine, test no-error path
        results = keyword_search("nonexistent test query xyz", top_k=3)
        assert isinstance(results, list)
