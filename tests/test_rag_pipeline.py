"""Tests for the real RAG embedding/indexing pipeline (sqlite-vec)."""
from __future__ import annotations

import pytest

from app.rag.embedder import embed, embed_many, llm_embed
from app.rag.index import chunk_text, index_document, search


class _Doc:
    def __init__(self, doc_id: str, content: str):
        self.id = doc_id
        self.content = content


def test_embed_is_dense_and_normalised():
    v = embed("photoshop mask layers")
    assert len(v) == 384
    import numpy as np
    norm = float(np.linalg.norm(v))
    assert norm == pytest.approx(1.0, abs=1e-3)


def test_embed_many_length():
    vecs = embed_many(["a b c", "d e f", "g h i"])
    assert len(vecs) == 3
    assert all(len(v) == 384 for v in vecs)


def test_llm_embed_falls_back_gracefully():
    result = llm_embed(["x"])
    assert result is None or isinstance(result, list)


def test_chunking_with_overlap():
    text = "word " * 300
    chunks = chunk_text(text, max_chars=128, overlap=32)
    assert len(chunks) > 1
    assert all(len(c) <= 128 for c in chunks)


def test_chunking_rejects_bad_params():
    with pytest.raises(ValueError):
        chunk_text("x", max_chars=0)
    with pytest.raises(ValueError):
        chunk_text("x", max_chars=10, overlap=10)


def test_index_and_search_roundtrip(tmp_path):
    db = tmp_path / "rag.sqlite"
    index_document(_Doc("d1", "photoshop mask layers are non-destructive editing"),
                   db_path=db)
    index_document(_Doc("d2", "python web server deployment with fastapi"),
                   db_path=db)
    hits = search("photoshop mask editing", top_k=2, db_path=db)
    assert hits
    assert hits[0]["id"].startswith("d1")
    assert hits[0]["score"] > 0


def test_search_empty_index(tmp_path):
    db = tmp_path / "rag2.sqlite"
    assert search("anything", db_path=db) == []
