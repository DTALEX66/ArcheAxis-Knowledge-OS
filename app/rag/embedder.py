"""Embedding providers for the RAG pipeline.

The local character n-gram embedder (:class:`~app.memory.vector_db.SimpleTextEmbedder`)
is always importable and is the configured default, so no provider failure can
turn into a hard dependency.

:func:`configured_embed_many` routes on ``rag.embedding.provider``:

``local``
    The n-gram embedder above. Default; no model, no network.
``ollama``
    The registered local Ollama runtime, for example ``qwen3-embedding:0.6b``
    from the shared model library. Uses the same ``POST /api/embed`` request
    shape as ``scripts/pipeline/eval_retrieval.py``.
``llm``
    LiteLLM remote embeddings for the configured model.

Every provider failure falls back to the local embedder. A fallback changes the
vector width, so the width is a property of the *resolved* provider: callers must
not assume the historical fixed 384, and index and query must resolve through the
same configuration.
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

import numpy as np

from app.memory.vector_db import SimpleTextEmbedder

_DEFAULT_EMBEDDER = SimpleTextEmbedder(dim=384)
_DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_OLLAMA_TIMEOUT_SECONDS = 60.0
_RETRY_BACKOFF_SECONDS = 0.25


def _setting(key: str, default: Any) -> Any:
    """Read one product setting; a broken config must not break embedding."""
    try:
        from shared.config import config

        return config.get(key, default)
    except Exception:
        return default


def embed(text: str) -> list[float]:
    return _DEFAULT_EMBEDDER.embed(text).tolist()


def embed_many(texts: list[str]) -> list[list[float]]:
    return [_DEFAULT_EMBEDDER.embed(t).tolist() for t in texts]


def local_embedding_dimension() -> int:
    """Width produced by the always-available local embedder."""
    return int(_DEFAULT_EMBEDDER.dim)


def embedding_provider() -> str:
    return str(_setting("rag.embedding.provider", "local") or "local").strip().lower()


def embedding_model() -> str:
    return str(_setting("rag.embedding.model", "") or "").strip()


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


def ollama_embed(
    texts: list[str],
    *,
    model: str,
    base_url: str = _DEFAULT_OLLAMA_BASE_URL,
    timeout: float = _DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    attempts: int = 2,
) -> list[list[float]] | None:
    """Embed through a local Ollama runtime, or return ``None``.

    Mirrors ``scripts/pipeline/eval_retrieval.py``: ``POST <base>/api/embed`` with
    ``{"model": ..., "input": [...]}`` returns ``{"embeddings": [[...], ...]}``.
    Uses only the standard library, so the local runtime stays an optional
    dependency.

    Transport and HTTP failures are retried ``attempts`` times with a short
    backoff, because the runtime answers intermittently while it loads a model
    for the first time (observed as a transient HTTP 400 on a cold model that
    succeeds unchanged on the next attempt). A response that is well-formed but
    the wrong shape is *not* retried, since a retry cannot repair a schema
    mismatch. Either way the caller falls back rather than failing the request.
    """
    if not texts:
        return []
    endpoint = f"{str(base_url).rstrip('/')}/api/embed"
    body = json.dumps({"model": model, "input": texts}).encode("utf-8")
    for attempt in range(max(1, int(attempts))):
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            if attempt + 1 < max(1, int(attempts)):
                time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            return None
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            return None
        widths = {len(vector) for vector in embeddings}
        if len(widths) != 1 or 0 in widths:
            return None
        return [[float(value) for value in vector] for vector in embeddings]
    return None


def configured_embed_many(texts: list[str]) -> list[list[float]]:
    """Embed ``texts`` with the configured provider, falling back to local.

    The fallback is unconditional by design: retrieval must degrade to the
    deterministic local embedder rather than fail when the local runtime is
    absent, which is what the previous config-only implementation intended.
    """
    if not texts:
        return []
    provider = embedding_provider()
    model = embedding_model()
    if provider == "ollama" and model:
        base_url = str(_setting("rag.embedding.ollama_base_url", _DEFAULT_OLLAMA_BASE_URL))
        try:
            timeout = float(
                _setting(
                    "rag.embedding.ollama_timeout_seconds", _DEFAULT_OLLAMA_TIMEOUT_SECONDS
                )
            )
        except (TypeError, ValueError):
            timeout = _DEFAULT_OLLAMA_TIMEOUT_SECONDS
        remote = ollama_embed(texts, model=model, base_url=base_url, timeout=timeout)
        if remote is not None:
            return remote
    elif provider == "llm" and model:
        remote = llm_embed(texts, model=model)
        if remote is not None:
            return remote
    return embed_many(texts)


def configured_embed(text: str) -> list[float]:
    """Single-text form of :func:`configured_embed_many`."""
    vectors = configured_embed_many([text])
    return vectors[0] if vectors else embed(text)


def _as_vector(values: list[float] | Any) -> np.ndarray:
    return np.asarray(values, dtype=np.float32)
