"""Real document indexing for the RAG pipeline (replaces the stub)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

from app.rag.embedder import _as_vector, embed, embed_many
from app.memory.vector_db import VectorDB

DEFAULT_TABLE = "vec_documents"
DEFAULT_DIM = 384


def chunk_text(text: str, *, max_chars: int = 512, overlap: int = 64) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or not text.strip():
        return []
    if max_chars <= 0 or overlap < 0 or overlap >= max_chars:
        raise ValueError("max_chars > 0 and 0 <= overlap < max_chars required")
    text = re.sub(r"\s+", " ", text.strip())
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start += max_chars - overlap
    return chunks


def index_document(
    doc: Any,
    *,
    table: str = DEFAULT_TABLE,
    dim: int = DEFAULT_DIM,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Index one document; returns the legacy-compatible receipt dict."""
    content = getattr(doc, "content", None) or getattr(doc, "text", None)
    if content is None:
        raise ValueError("document requires content or text")
    chunks = chunk_text(str(content))
    if not chunks:
        return {"indexed": True, "id": doc.id, "chunks": 0}
    vectors = embed_many(chunks)
    vdb = VectorDB(table_name=table, dim=dim, db_path=db_path)
    vdb.init()
    for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
        vdb.insert("{}::{}".format(doc.id, i), _as_vector(vector))
    return {"indexed": True, "id": doc.id, "chunks": len(chunks)}


def search(
    query: str,
    *,
    table: str = DEFAULT_TABLE,
    dim: int = DEFAULT_DIM,
    top_k: int = 5,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Vector search over an indexed table."""
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    vdb = VectorDB(table_name=table, dim=dim, db_path=db_path)
    if not vdb._index_exists():
        return []
    hits = vdb.search(_as_vector(embed(query)), top_k=top_k)
    return [
        {"id": object_id, "distance": float(distance),
         "score": round(float(max(0.0, 1.0 - distance)), 3)}
        for object_id, distance in hits
    ]
