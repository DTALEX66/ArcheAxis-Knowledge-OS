"""Real embedding provider for the RAG pipeline (replaces the hash stub)."""
from __future__ import annotations
from typing import Any
import numpy as np
from app.memory.vector_db import SimpleTextEmbedder

_DEFAULT_EMBEDDER = SimpleTextEmbedder(dim=384)


def embed(text: str) -> list[float]:
    return _DEFAULT_EMBEDDER.embed(text).tolist()


def embed_many(texts: list[str]) -> list[list[float]]:
    return [_DEFAULT_EMBEDDER.embed(t).tolist() for t in texts]


def llm_embed(texts: list[str], *, model: str | None = None) -> list[list[float]] | None:
    try:
        import litellm
    except ImportError:
        return None
    if not model:
        model = "text-embedding-3-small"
    try:
        response = litellm.embedding(model=model, input=texts)
        data = response.get("data", [])
        if not data:
            return None
        data.sort(key=lambda item: item.get("index", 0))
        return [list(item["embedding"]) for item in data]
    except Exception:
        return None


def _as_vector(values: list[float] | Any) -> np.ndarray:
    return np.asarray(values, dtype=np.float32)


def configured_embed_many(texts: list[str]) -> list[list[float]]:
    """Embeddings driven by config (rag.embedding.provider).

    provider=llm + configured model → remote embeddings; anything else or any
    provider failure → local n-gram embedder (never a hard dependency).
    """
    try:
        from shared.config import config
        provider = str(config.get("rag.embedding.provider", "local") or "local").lower()
        model = str(config.get("rag.embedding.model", "") or "").strip()
    except Exception:
        provider, model = "local", ""
    if provider == "llm" and model:
        remote = llm_embed(texts, model=model)
        if remote is not None:
            return remote
    return embed_many(texts)
