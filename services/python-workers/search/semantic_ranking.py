"""Bounded, read-only semantic ranking over the existing LM Studio service.

Embeddings use cosine similarity. Qwen reranking uses the first-position yes/no
logprobs exposed by Responses; generated text is never interpreted as a score.
"""
from __future__ import annotations

import json
import math
import sys
import time
import urllib.error
import urllib.request

SCHEMA = "archeaxis.semantic-ranking/v1"
ENGINE_VERSION = "0.2.0"
BASE = "http://127.0.0.1:1234"
EMBED_MODEL = "text-embedding-qwen3-embedding-0.6b"
# The identity advertised in the sidecar handshake for this route.
WORKER_IDENTITY = "python-worker-semantic-ranking-ndjson"
RERANK_MODEL = "qwen3-reranker-0.6b"
MAX_BYTES = 256_000
MAX_RESPONSE = 4_000_000
TOTAL_TIMEOUT = 30.0
RERANK_SYSTEM = ('Judge whether the Document meets the requirements based on the Query '
                 'and the Instruct provided. Note that the answer can only be "yes" or "no".')
RERANK_INSTRUCTION = "Given a web search query, retrieve relevant passages that answer the query"


class Unavailable(ValueError):
    pass


def http(path: str, payload: dict | None = None, *, timeout: float = 15) -> dict:
    # No credential, proxy, redirect, download, or model-load operation.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise Unavailable("endpoint redirect refused")

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(
        BASE + path, data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    deadline = time.monotonic() + timeout
    with opener.open(request, timeout=timeout) as response:
        chunks = []
        size = 0
        while size <= MAX_RESPONSE:
            if time.monotonic() >= deadline:
                raise Unavailable("endpoint exceeded total budget")
            chunk = response.read1(min(65536, MAX_RESPONSE + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        raw = b"".join(chunks)
    if time.monotonic() > deadline:
        raise Unavailable("endpoint exceeded total budget")
    if len(raw) > MAX_RESPONSE:
        raise Unavailable("response exceeds bound")
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get("error") is not None:
        raise Unavailable("endpoint returned invalid response or error")
    return value


def validate(request: dict) -> tuple[str, list[dict]]:
    if not isinstance(request, dict) or request.get("schema") != SCHEMA:
        raise ValueError("invalid schema")
    query, candidates = request.get("query"), request.get("candidates")
    if not isinstance(query, str) or not query.strip() or len(query) > 2048:
        raise ValueError("query must be nonblank and at most 2048 characters")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 16:
        raise ValueError("expected 1..16 candidates")
    seen = set()
    for entry in candidates:
        if not isinstance(entry, dict) or entry.get("status") != "accepted":
            raise ValueError("only accepted candidates may be ranked")
        for key in ("knowledge_id", "knowledge_version", "body"):
            text = entry.get(key)
            bound = 8192 if key == "body" else 256
            if not isinstance(text, str) or not text.strip() or len(text) > bound:
                raise ValueError("invalid candidate " + key)
        if entry["knowledge_id"] in seen:
            raise ValueError("duplicate knowledge_id")
        seen.add(entry["knowledge_id"])
    if len(json.dumps(request).encode()) > MAX_BYTES:
        raise ValueError("request exceeds byte bound")
    return query, candidates


def vectors(response: dict, count: int) -> list[list[float]]:
    if response.get("model") != EMBED_MODEL:
        raise Unavailable("embedding model mismatch")
    data = response.get("data")
    if not isinstance(data, list) or len(data) != count:
        raise Unavailable("embedding row count mismatch")
    ordered = {}
    dimension = None
    for entry in data:
        if not isinstance(entry, dict):
            raise Unavailable("invalid embedding row")
        index, vector = entry.get("index"), entry.get("embedding")
        if type(index) is not int or not 0 <= index < count or index in ordered:
            raise Unavailable("invalid embedding index")
        if not isinstance(vector, list) or not 1 <= len(vector) <= 4096:
            raise Unavailable("invalid embedding dimensions")
        if dimension is not None and dimension != len(vector):
            raise Unavailable("embedding dimension mismatch")
        dimension = len(vector)
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
            raise Unavailable("nonfinite embedding")
        norm = math.hypot(*vector)
        if not math.isfinite(norm) or norm == 0:
            raise Unavailable("invalid embedding norm")
        ordered[index] = [x / norm for x in vector]
    return [ordered[i] for i in range(count)]


def rank(request: dict, transport=http) -> dict:
    query, candidates = validate(request)
    result = {
        "schema": SCHEMA, "status": "UNAVAILABLE", "embedding_rank": [],
        "embedding": {"status": "UNAVAILABLE", "model": EMBED_MODEL,
                      "endpoint": BASE + "/v1/embeddings", "model_version": "UNVERIFIED"},
        "reranker": {"status": "UNAVAILABLE", "model": RERANK_MODEL,
                     "endpoint": BASE + "/v1/responses", "model_version": "UNVERIFIED", "rank": [],
                     "verification": "UNVERIFIED",
                     "protocol": "qwen-yes-no-first-token-logprobs/v1"},
        "engine_version": ENGINE_VERSION,
    }
    deadline = time.monotonic() + TOTAL_TIMEOUT
    def call(path, payload=None):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Unavailable("semantic ranking deadline exceeded")
        response = (transport(path, payload, timeout=min(15, remaining))
                    if transport is http else transport(path, payload))
        if time.monotonic() > deadline:
            raise Unavailable("semantic ranking deadline exceeded")
        return response
    try:
        models = call("/api/v0/models").get("data")
        if not isinstance(models, list):
            raise Unavailable("invalid model inventory")
    except (OSError, ValueError, urllib.error.URLError) as error:
        result["embedding"]["reason"] = str(error)[:256]
        result["reranker"]["reason"] = str(error)[:256]
        return result
    try:
        model = next((m for m in models if isinstance(m, dict) and m.get("id") == EMBED_MODEL), None)
        if model is None or model.get("state") != "loaded":
            raise Unavailable("embedding model is not already loaded; JIT loading forbidden")
        response = call("/v1/embeddings", {"model": EMBED_MODEL, "input": [query] + [c["body"] for c in candidates]})
        encoded = vectors(response, len(candidates) + 1)
        for candidate, vector in zip(candidates, encoded[1:], strict=True):
            score = math.fsum(a * b for a, b in zip(encoded[0], vector, strict=True))
            result["embedding_rank"].append({"knowledge_id": candidate["knowledge_id"],
                                             "knowledge_version": candidate["knowledge_version"],
                                             "score": max(-1.0, min(1.0, score))})
        result["embedding_rank"].sort(key=lambda r: (-r["score"], r["knowledge_id"]))
        result["embedding"].update(status="AVAILABLE", dimensions=len(encoded[0]),
                                   quantization=model.get("quantization", "UNVERIFIED"),
                                   protocol="openai-embeddings")
        result["status"] = "PARTIAL"
    except (OSError, ValueError, urllib.error.URLError) as error:
        result["embedding"]["reason"] = str(error)[:256]
    partial_scores = []
    try:
        reranker = next((m for m in models if isinstance(m, dict) and m.get("id") == RERANK_MODEL), None)
        if reranker is None or reranker.get("state") != "loaded":
            raise Unavailable("reranker model is not already loaded; JIT loading forbidden")
        for candidate in candidates:
            response = call("/v1/responses", {
                "model": RERANK_MODEL, "instructions": RERANK_SYSTEM,
                "input": f"<Instruct>: {RERANK_INSTRUCTION}\n<Query>: {query}\n<Document>: {candidate['body']}",
                "max_output_tokens": 1, "temperature": 1,
                "reasoning": {"effort": "none"}, "include": ["message.output_text.logprobs"],
                "top_logprobs": 20, "store": False, "stream": False,
            })
            score, evidence = rerank_score(response)
            partial_scores.append({"knowledge_id": candidate["knowledge_id"],
                                   "knowledge_version": candidate["knowledge_version"],
                                   "score": score, **evidence})
        partial_scores.sort(key=lambda r: (-r["score"], r["knowledge_id"]))
        result["reranker"].update(status="AVAILABLE", verification="VERIFIED_RESPONSE",
                                  rank=partial_scores, quantization=reranker.get("quantization", "UNVERIFIED"))
    except (OSError, ValueError, urllib.error.URLError) as error:
        result["reranker"].update(reason=str(error)[:256], partial_scores=partial_scores)
    available = [result["embedding"]["status"] == "AVAILABLE", result["reranker"]["status"] == "AVAILABLE"]
    result["status"] = "AVAILABLE" if all(available) else "PARTIAL" if any(available) else "UNAVAILABLE"
    return result


def rerank_score(response: dict) -> tuple[float, dict]:
    """Require exact yes/no from the same first output-token distribution."""
    if not isinstance(response, dict) or response.get("model") != RERANK_MODEL:
        raise Unavailable("reranker model mismatch")
    if response.get("status") != "completed" or response.get("error") is not None:
        raise Unavailable("reranker response did not complete")
    usage = response.get("usage")
    if not isinstance(usage, dict) or not isinstance(usage.get("output_tokens_details"), dict):
        raise Unavailable("reranker reasoning usage unavailable")
    reasoning = usage["output_tokens_details"].get("reasoning_tokens")
    if type(reasoning) is not int or reasoning != 0 or usage.get("output_tokens") != 1:
        raise Unavailable("reranker first-token position consumed by reasoning")
    output = response.get("output")
    if not isinstance(output, list):
        raise Unavailable("reranker output unavailable")
    positions = []
    for message in output:
        if (not isinstance(message, dict) or message.get("type") != "message"
                or message.get("role") != "assistant" or message.get("status") != "completed"):
            raise Unavailable("reranker output contains non-message positions")
        content = message.get("content")
        if not isinstance(content, list):
            raise Unavailable("invalid reranker content")
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "output_text" or not isinstance(item.get("logprobs"), list):
                raise Unavailable("reranker output logprobs unavailable")
            positions.extend(item["logprobs"])
    if len(positions) != 1 or not isinstance(positions[0], dict):
        raise Unavailable("reranker requires exactly one first-token position")
    token = positions[0]
    if token.get("token") not in ("yes", "no"):
        raise Unavailable("reranker generated a non-exact yes/no token")
    choices = token.get("top_logprobs")
    if not isinstance(choices, list):
        raise Unavailable("reranker top_logprobs unavailable")
    probabilities = {}
    for choice in choices:
        if not isinstance(choice, dict):
            raise Unavailable("invalid reranker logprob entry")
        if choice.get("token") in ("yes", "no"):
            name, value = choice["token"], choice.get("logprob")
            if name in probabilities or type(value) not in (int, float) or not math.isfinite(value) or value > 0:
                raise Unavailable("invalid exact-token logprob")
            probabilities[name] = value
    if set(probabilities) != {"yes", "no"}:
        raise Unavailable("reranker missing exact yes/no logprobs; no substitute permitted")
    selected = token.get("logprob")
    if (type(selected) not in (int, float) or not math.isfinite(selected)
            or selected != probabilities[token["token"]]):
        raise Unavailable("reranker generated-token probability mismatch")
    difference = probabilities["yes"] - probabilities["no"]
    score = (1 / (1 + math.exp(-difference)) if difference >= 0
             else math.exp(difference) / (1 + math.exp(difference)))
    return score, {"yes_logprob": probabilities["yes"], "no_logprob": probabilities["no"],
                   "reasoning_tokens": 0}


def main() -> int:
    if sys.argv[1:] == ["--hello"]:
        print(json.dumps({"schema": "archeaxis.derived-worker-hello/v1",
                          "capability": "search.semantic", "version": 1}))
        return 0
    # Sidecar mode is this route's wiring, exactly as machine.answer does it: the launch declares
    # the capability, and the packaging readiness check starts the worker with --staging-root and
    # requires the transport hello. Without this branch the route is served (the Core reaches it
    # through its own derived route) but can never be reported ready, so a runtime that declares
    # it fails its own readiness check while the feature works.
    if "--staging-root" in sys.argv:
        import argparse
        import importlib.util
        from pathlib import Path

        candidates = (
            Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py",
            Path(__file__).resolve().parents[2] / "services" / "python-workers" / "transport"
            / "text_ndjson.py",
        )
        transport_path = next((p for p in candidates if p.is_file()), candidates[0])
        spec = importlib.util.spec_from_file_location("search.semantic_transport", transport_path)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing"}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        sidecar = argparse.ArgumentParser(description=__doc__)
        sidecar.add_argument("--staging-root", type=Path, required=True)
        sidecar.add_argument("--artifact-root", type=Path, default=None)
        args = sidecar.parse_args()
        return transport.serve_stdio(WORKER_IDENTITY, ["search.semantic"], args.staging_root,
                                     args.artifact_root)
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("request exceeds byte bound")
        result = rank(json.loads(raw))
    except (ValueError, TypeError) as error:
        result = {"schema": SCHEMA, "status": "INVALID_REQUEST", "reason": str(error)[:256]}
    print(json.dumps(result, allow_nan=False, ensure_ascii=False))
    return 0 if result["status"] == "AVAILABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
