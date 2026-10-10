import importlib.util
from pathlib import Path

import pytest
import json
import subprocess
import sys

spec = importlib.util.spec_from_file_location(
    "semantic_ranking", Path(__file__).parents[1] / "services/python-workers/search/semantic_ranking.py"
)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def request():
    return {"schema": worker.SCHEMA, "query": "France capital", "candidates": [
        {"knowledge_id": "paris", "knowledge_version": "v1", "body": "Paris", "status": "accepted"},
        {"knowledge_id": "banana", "knowledge_version": "v2", "body": "Banana", "status": "accepted"},
    ]}


def response():
    return {"model": worker.EMBED_MODEL, "data": [
        {"index": 2, "embedding": [0, 1]}, {"index": 0, "embedding": [1, 0]},
        {"index": 1, "embedding": [1, 0]},
    ]}


def test_real_vectors_rank_bound_identity_without_fake_reranker():
    def transport(path, payload=None):
        if path.endswith("models"):
            return {"data": [{"id": worker.EMBED_MODEL, "state": "loaded"}]}
        return response()
    ranked = worker.rank(request(), transport)
    assert ranked["status"] == "PARTIAL"
    assert ranked["embedding_rank"] == [
        {"knowledge_id": "paris", "knowledge_version": "v1", "score": 1.0},
        {"knowledge_id": "banana", "knowledge_version": "v2", "score": 0.0},
    ]
    assert ranked["reranker"]["status"] == "UNAVAILABLE"
    assert ranked["reranker"]["verification"] == "UNVERIFIED"
    assert "not already loaded" in ranked["reranker"]["reason"]
    assert ranked["reranker"]["rank"] == []


def test_not_loaded_never_issues_inference_or_load_request():
    calls = []
    def transport(path, payload=None):
        calls.append(path)
        return {"data": [{"id": worker.EMBED_MODEL, "state": "not-loaded"}]}
    assert worker.rank(request(), transport)["status"] == "UNAVAILABLE"
    assert calls == ["/api/v0/models"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, "1"])
def test_nonfinite_or_invalid_embedding_rejected(bad):
    payload = response()
    payload["data"][0]["embedding"][0] = bad
    with pytest.raises(worker.Unavailable):
        worker.vectors(payload, 3)


@pytest.mark.parametrize("shape", ["zero", "dimension", "index", "model", "count"])
def test_inconsistent_embedding_rejected(shape):
    payload = response()
    if shape == "zero": payload["data"][0]["embedding"] = [0, 0]
    if shape == "dimension": payload["data"][0]["embedding"] = [1]
    if shape == "index": payload["data"][0]["index"] = 0
    if shape == "model": payload["model"] = "different-model"
    if shape == "count": payload["data"].pop()
    with pytest.raises(worker.Unavailable):
        worker.vectors(payload, 3)


@pytest.mark.parametrize("shape", ["candidate", "duplicate", "query", "version", "schema"])
def test_invalid_request_rejected_before_http(shape):
    payload = request()
    if shape == "candidate": payload["candidates"][0]["status"] = "candidate"
    if shape == "duplicate": payload["candidates"][1]["knowledge_id"] = "paris"
    if shape == "query": payload["query"] = " "
    if shape == "version": payload["candidates"][0]["knowledge_version"] = ""
    if shape == "schema": payload["schema"] = "unknown"
    with pytest.raises(ValueError):
        worker.rank(payload, lambda *args: pytest.fail("HTTP must not run"))


def test_hello_stdlib_only_without_network(tmp_path):
    isolated = tmp_path / "worker.py"
    isolated.write_bytes(Path(worker.__file__).read_bytes())
    launcher = (
        "import runpy,sys; "
        "sys.addaudithook(lambda event,args: (_ for _ in ()).throw(AssertionError('network forbidden')) if event.startswith('socket.') else None); "
        "sys.argv=[sys.argv[1],'--hello']; runpy.run_path(sys.argv[0],run_name='__main__')"
    )
    child = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", launcher, str(isolated)],
                           cwd=tmp_path, text=True, capture_output=True, timeout=5)
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout) == {
        "schema": "archeaxis.derived-worker-hello/v1", "capability": "search.semantic", "version": 1}


def rerank_response():
    return {"model": worker.RERANK_MODEL, "status": "completed", "error": None,
            "usage": {"output_tokens": 1, "output_tokens_details": {"reasoning_tokens": 0}},
            "output": [{"type": "message", "role": "assistant", "status": "completed", "content": [
                {"type": "output_text", "text": "arbitrary text is not a score", "logprobs": [
                    {"token": "yes", "logprob": -0.1, "top_logprobs": [
                        {"token": "yes", "logprob": -0.1}, {"token": "no", "logprob": -2.1}]}]}]}]}


def test_rerank_uses_same_position_logprob_difference():
    score, evidence = worker.rerank_score(rerank_response())
    assert score == pytest.approx(0.8807970779778823)
    assert evidence["reasoning_tokens"] == 0


@pytest.mark.parametrize("case", ["model", "missing_yes", "missing_no", "nan", "multiple", "reasoning", "exact", "selected", "incomplete"])
def test_bad_rerank_cannot_be_scored(case):
    data = rerank_response()
    position = data["output"][0]["content"][0]["logprobs"][0]
    if case == "model": data["model"] = "other"
    if case == "missing_yes": position["top_logprobs"].pop(0)
    if case == "missing_no": position["top_logprobs"].pop(1)
    if case == "nan": position["top_logprobs"][0]["logprob"] = float("nan")
    if case == "multiple": data["output"][0]["content"][0]["logprobs"].append(position.copy())
    if case == "reasoning": data["usage"]["output_tokens_details"]["reasoning_tokens"] = 1
    if case == "exact": position["top_logprobs"][0]["token"] = " yes"
    if case == "selected": position["logprob"] = -7
    if case == "incomplete": data["status"] = "incomplete"
    with pytest.raises(worker.Unavailable):
        worker.rerank_score(data)


def test_missing_token_retains_embedding_and_marks_partial_rerank():
    calls = []
    def transport(path, payload=None):
        calls.append((path, payload))
        if path.endswith("models"):
            return {"data": [{"id": worker.EMBED_MODEL, "state": "loaded"},
                             {"id": worker.RERANK_MODEL, "state": "loaded"}]}
        if path.endswith("embeddings"):
            return response()
        data = rerank_response()
        if len([c for c in calls if c[0].endswith("responses")]) == 2:
            data["output"][0]["content"][0]["logprobs"][0]["top_logprobs"].pop()
        return data
    result = worker.rank(request(), transport)
    assert result["status"] == "PARTIAL"
    assert result["embedding"]["status"] == "AVAILABLE"
    assert result["reranker"]["rank"] == []
    assert len(result["reranker"]["partial_scores"]) == 1
    assert "missing exact" in result["reranker"]["reason"]
    sent = calls[-1][1]
    assert sent["max_output_tokens"] == 1 and sent["reasoning"] == {"effort": "none"}
    assert sent["store"] is False and sent["stream"] is False


def test_complete_rerank_and_embeddings_available():
    def transport(path, payload=None):
        if path.endswith("models"):
            return {"data": [{"id": worker.EMBED_MODEL, "state": "loaded"},
                             {"id": worker.RERANK_MODEL, "state": "loaded"}]}
        return response() if path.endswith("embeddings") else rerank_response()
    result = worker.rank(request(), transport)
    assert result["status"] == "AVAILABLE"
    assert len(result["reranker"]["rank"]) == 2
    assert result["reranker"]["verification"] == "VERIFIED_RESPONSE"


def test_exhausted_budget_never_issues_request(monkeypatch):
    monkeypatch.setattr(worker, "TOTAL_TIMEOUT", 0)
    result = worker.rank(request(), lambda *args: pytest.fail("deadline must precede HTTP"))
    assert result["status"] == "UNAVAILABLE"
    assert "deadline" in result["reranker"]["reason"]
