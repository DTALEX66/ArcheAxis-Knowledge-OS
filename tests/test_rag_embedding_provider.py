"""Embedding provider routing for the RAG pipeline (A06 / M0 embedding requirement).

These tests exist because the configured embedding provider previously had no
effect on real indexing: ``app/rag/index.py`` called the built-in n-gram embedder
directly, so ``rag.embedding.provider`` was a setting nothing read. They pin the
behaviour that makes the setting real, and they pin the failure mode that keeps
the local runtime optional:

* the default configuration stays local, wide 384, with no outbound call;
* ``ollama`` routes through ``POST <base>/api/embed`` and its model width is used
  for both indexing and querying, instead of being coerced to 384;
* every provider failure - unreachable, wrong shape, ragged widths, bad timeout -
  falls back to the local embedder rather than raising;
* a transient runtime error is retried a bounded number of times, while a
  schema mismatch is not retried at all.
"""
from __future__ import annotations

import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.rag import embedder
from app.rag.index import index_document, search

STUB_DIM = 8


class _Doc:
    def __init__(self, doc_id: str, content: str):
        self.id = doc_id
        self.content = content


class _EmbedHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    response: dict = {}
    requests: list = []

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).requests.append({"path": self.path, "body": body})
        # A configured `response` is sent verbatim so malformed payloads are
        # genuinely malformed; synthesis only happens for the well-formed default.
        if type(self).response:
            payload = dict(type(self).response)
        else:
            inputs = body.get("input") or []
            payload = {
                "embeddings": [
                    [round(0.1 * (index + 1), 4)] * STUB_DIM
                    for index, _ in enumerate(inputs)
                ]
            }
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *args: object) -> None:  # keep pytest output clean
        return


@pytest.fixture
def embed_server():
    _EmbedHandler.response = {}
    _EmbedHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _EmbedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def settings(monkeypatch):
    # The default base URL is deliberately unroutable (TEST-NET-1) so no test can
    # accidentally depend on, or be perturbed by, a live local runtime: an
    # embedding model that happens to be serving on 127.0.0.1:11434 must not
    # change the outcome of any assertion here.
    def apply(**values):
        table = {
            "rag.embedding.provider": "local",
            "rag.embedding.model": "",
            "rag.embedding.ollama_base_url": "http://192.0.2.1:1",
            "rag.embedding.ollama_timeout_seconds": 1,
        }
        table.update(values)
        monkeypatch.setattr(embedder, "_setting", lambda key, default: table.get(key, default))
        return table

    return apply


def test_default_configuration_is_local_and_never_calls_out(monkeypatch) -> None:
    def explode(*args, **kwargs):
        raise AssertionError("local provider must not attempt an outbound call")

    monkeypatch.setattr(embedder, "ollama_embed", explode)
    monkeypatch.setattr(embedder, "llm_embed", explode)

    assert embedder.embedding_provider() == "local"
    vectors = embedder.configured_embed_many(["alpha beta", "gamma delta"])
    assert [len(v) for v in vectors] == [384, 384]
    assert embedder.local_embedding_dimension() == 384


def test_ollama_provider_uses_the_model_width_for_index_and_query(
    settings, embed_server
) -> None:
    settings(
        **{
            "rag.embedding.provider": "ollama",
            "rag.embedding.model": "qwen3-embedding:0.6b",
            "rag.embedding.ollama_base_url": embed_server,
        }
    )
    vectors = embedder.configured_embed_many(["alpha beta"])
    assert len(vectors[0]) == STUB_DIM, "provider width must not be coerced to 384"

    request = _EmbedHandler.requests[-1]
    assert request["path"] == "/api/embed"
    assert request["body"]["model"] == "qwen3-embedding:0.6b"
    assert request["body"]["input"] == ["alpha beta"]


def test_ollama_provider_index_and_search_agree_on_width(settings, embed_server, tmp_path) -> None:
    settings(
        **{
            "rag.embedding.provider": "ollama",
            "rag.embedding.model": "qwen3-embedding:0.6b",
            "rag.embedding.ollama_base_url": embed_server,
        }
    )
    db = tmp_path / "provider.sqlite"
    receipt = index_document(_Doc("d1", "photoshop mask layers are non-destructive"), db_path=db)
    assert receipt["dim"] == STUB_DIM, "index must be sized by the resolved provider"

    hits = search("photoshop mask layers", top_k=3, db_path=db)
    assert hits, "query must resolve the same width as the index"
    assert hits[0]["id"].startswith("d1")


def test_unreachable_ollama_falls_back_to_local(settings) -> None:
    settings(
        **{
            "rag.embedding.provider": "ollama",
            "rag.embedding.model": "qwen3-embedding:0.6b",
            # Reserved TEST-NET-1 address: guaranteed unroutable, fails fast.
            "rag.embedding.ollama_base_url": "http://192.0.2.1:1",
            "rag.embedding.ollama_timeout_seconds": 1,
        }
    )
    vectors = embedder.configured_embed_many(["alpha beta"])
    assert [len(v) for v in vectors] == [384]


def test_ollama_provider_with_no_model_falls_back_to_local(settings) -> None:
    settings(**{"rag.embedding.provider": "ollama", "rag.embedding.model": ""})
    vectors = embedder.configured_embed_many(["alpha beta"])
    assert [len(v) for v in vectors] == [384]


def test_malformed_ollama_response_falls_back_to_local(settings, embed_server) -> None:
    settings(
        **{
            "rag.embedding.provider": "ollama",
            "rag.embedding.model": "qwen3-embedding:0.6b",
            "rag.embedding.ollama_base_url": embed_server,
        }
    )
    for bad in (
        {"embeddings": [[0.1] * STUB_DIM]},           # one vector for two inputs
        {"embeddings": [[0.1] * STUB_DIM, [0.2] * 4]},  # ragged widths
        {"embeddings": []},
        {"not_embeddings": "x"},
    ):
        _EmbedHandler.response = bad
        vectors = embedder.configured_embed_many(["alpha beta", "gamma delta"])
        assert [len(v) for v in vectors] == [384, 384], bad
    _EmbedHandler.response = {}


def test_non_numeric_timeout_falls_back_to_the_default(settings, monkeypatch) -> None:
    settings(
        **{
            "rag.embedding.provider": "ollama",
            "rag.embedding.model": "qwen3-embedding:0.6b",
            "rag.embedding.ollama_timeout_seconds": "not-a-number",
        }
    )
    captured = {}

    def fake(texts, *, model, base_url=embedder._DEFAULT_OLLAMA_BASE_URL, timeout=None):
        captured["timeout"] = timeout
        return None

    monkeypatch.setattr(embedder, "ollama_embed", fake)
    # Must not raise on the invalid setting; falls back to the local embedder.
    vectors = embedder.configured_embed_many(["alpha beta"])
    assert [len(v) for v in vectors] == [384]
    assert captured["timeout"] == embedder._DEFAULT_OLLAMA_TIMEOUT_SECONDS


def test_llm_provider_still_routes_through_litellm(settings, monkeypatch) -> None:
    settings(**{"rag.embedding.provider": "llm", "rag.embedding.model": "text-embedding-3-small"})
    captured = {}

    def fake_llm(texts, *, model=None):
        captured["model"] = model
        return [[0.5] * 16 for _ in texts]

    monkeypatch.setattr(embedder, "llm_embed", fake_llm)
    vectors = embedder.configured_embed_many(["a", "b"])
    assert captured["model"] == "text-embedding-3-small"
    assert [len(v) for v in vectors] == [16, 16]


def test_explicit_dim_still_overrides_the_provider_width(settings, embed_server, tmp_path) -> None:
    """Backward compatibility: an explicit ``dim`` is honoured unchanged."""
    settings(
        **{
            "rag.embedding.provider": "ollama",
            "rag.embedding.model": "qwen3-embedding:0.6b",
            "rag.embedding.ollama_base_url": embed_server,
        }
    )
    db = tmp_path / "explicit.sqlite"
    receipt = index_document(
        _Doc("d1", "explicit dimension"), dim=STUB_DIM, db_path=db
    )
    assert receipt["dim"] == STUB_DIM


def test_empty_input_short_circuits_without_a_request(settings, monkeypatch) -> None:
    settings(**{"rag.embedding.provider": "ollama", "rag.embedding.model": "m"})

    def explode(*args, **kwargs):
        raise AssertionError("empty input must not reach the provider")

    monkeypatch.setattr(embedder, "ollama_embed", explode)
    assert embedder.configured_embed_many([]) == []


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _no_sleep(monkeypatch) -> None:
    monkeypatch.setattr(embedder.time, "sleep", lambda _seconds: None)


def test_transient_transport_failure_is_retried(monkeypatch) -> None:
    """A cold model can answer with a transient error; one retry must recover it.

    Observed against the real runtime: the first `/api/embed` for a model that was
    still loading returned HTTP 400, and the identical request succeeded on the
    next attempt.
    """
    calls = {"n": 0}

    def flaky(request, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(request.full_url, 400, "loading", {}, None)
        return _FakeResponse({"embeddings": [[0.1] * 4, [0.2] * 4]})

    monkeypatch.setattr(embedder.urllib.request, "urlopen", flaky)
    _no_sleep(monkeypatch)
    result = embedder.ollama_embed(["a", "b"], model="m", attempts=2)
    assert result == [[0.1] * 4, [0.2] * 4]
    assert calls["n"] == 2


def test_persistent_transport_failure_stops_at_the_attempt_bound(monkeypatch) -> None:
    calls = {"n": 0}

    def always_fail(request, timeout=None):
        calls["n"] += 1
        raise urllib.error.URLError("runtime down")

    monkeypatch.setattr(embedder.urllib.request, "urlopen", always_fail)
    _no_sleep(monkeypatch)
    assert embedder.ollama_embed(["a"], model="m", attempts=3) is None
    assert calls["n"] == 3, "retries must be bounded"


def test_malformed_response_is_not_retried(monkeypatch) -> None:
    """A wrong shape cannot be repaired by retrying, so it must fail fast."""
    calls = {"n": 0}

    def malformed(request, timeout=None):
        calls["n"] += 1
        return _FakeResponse({"embeddings": [[0.1] * 4]})

    monkeypatch.setattr(embedder.urllib.request, "urlopen", malformed)
    _no_sleep(monkeypatch)
    assert embedder.ollama_embed(["a", "b"], model="m", attempts=3) is None
    assert calls["n"] == 1
