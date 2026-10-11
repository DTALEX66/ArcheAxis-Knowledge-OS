"""G4: a machine answer is a labelled candidate, and a broken call is a named failure.

The answer's wording is not pinned here - a model's phrasing is not a fact this repository can fix -
but the failure paths and the labelling are, because "the model produced nothing" must never become
an empty answer, and a truncated answer must never look like a finished one.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "machine" / "worker_machine_answer.py"


@pytest.mark.parametrize("url", ["http://example.invalid/v1", "https://127.0.0.1/v1", "http://user:pass@127.0.0.1/v1", "http://0.0.0.0/v1", "http://[::]/v1", "http://127.0.0.1/v1#fragment"])
def test_local_transport_rejects_nonlocal_or_ambiguous_targets_before_open(monkeypatch,url):
    monkeypatch.setattr(machine.urllib.request,"build_opener",lambda *args:pytest.fail("Blocked endpoint opened"))
    with pytest.raises(ValueError):machine.local_urlopen(url,timeout=1)


def test_local_transport_disables_proxy_normalizes_localhost_and_refuses_redirect(monkeypatch):
    observed={}
    class Opener:
        def open(self,request,timeout):
            observed.update(url=request.full_url,data=request.data,timeout=timeout)
            return "synthetic"
    def build(*handlers):
        assert isinstance(handlers[0],machine.urllib.request.ProxyHandler) and handlers[0].proxies=={}
        assert isinstance(handlers[1],machine.NoLocalRedirect)
        with pytest.raises(ValueError):handlers[1].redirect_request(None,None,307,"",{},"http://example.invalid/")
        return Opener()
    monkeypatch.setattr(machine.urllib.request,"build_opener",build)
    req=machine.urllib.request.Request("http://localhost:1234/v1/chat/completions",data=b"synthetic")
    assert machine.local_urlopen(req,timeout=2)=="synthetic"
    assert observed=={"url":"http://127.0.0.1:1234/v1/chat/completions","data":b"synthetic","timeout":2}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


machine = _load("worker_machine_under_test", WORKER)


@pytest.mark.parametrize("model", ["", " ", "m\n", "m\x00", "m" * 257, 7, False])
def test_explicit_invalid_model_refuses_before_endpoint_or_call(monkeypatch, model):
    monkeypatch.setattr(machine, "_endpoint", lambda: pytest.fail("invalid selection discovered endpoint"))
    monkeypatch.setattr(machine, "_call", lambda *args: pytest.fail("invalid selection called model"))
    with pytest.raises(ValueError, match="invalid model selection"):
        machine.answer("synthetic context", "synthetic question", model=model)


def test_model_response_is_bounded_before_json_decode(monkeypatch):
    import io
    monkeypatch.setattr(machine, "MAX_MODEL_RESPONSE_BYTES", 16)
    class Response(io.BytesIO):
        def read(self, size=-1):
            assert size == 17
            return super().read(size)
    with pytest.raises(ValueError, match="size limit"):
        machine.read_model_json(Response(b"x" * 18))
    assert machine.read_model_json(Response(b'{"ok":true}')) == {"ok": True}


@pytest.mark.parametrize("raw", [b'[]', b'null', b'7', b'"text"'])
def test_model_response_requires_object(raw):
    import io
    with pytest.raises(ValueError, match="JSON object"):
        machine.read_model_json(io.BytesIO(raw))


def test_oversized_inventory_is_failed_not_empty_or_available(monkeypatch):
    import io
    monkeypatch.setattr(machine, "MAX_MODEL_RESPONSE_BYTES", 16)
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m"})
    monkeypatch.setattr(machine, "local_urlopen", lambda *args, **kwargs: io.BytesIO(b"x" * 18))
    result = machine.probe()
    assert result["inventory_status"] == "READ_FAILED" and result["capability"] is False
    assert "available" not in result


@pytest.mark.parametrize("status", [301,302,303,307,308])
def test_integrated_loopback_redirect_never_reaches_second_server(monkeypatch,status):
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from threading import Thread
    hits={"source":0,"target":0}
    class Target(BaseHTTPRequestHandler):
        def do_GET(self):
            hits["target"]+=1;self.send_response(200);self.end_headers()
        do_POST=do_GET
        def log_message(self,*args):pass
    target=ThreadingHTTPServer(("127.0.0.1",0),Target)
    class Source(BaseHTTPRequestHandler):
        def do_POST(self):
            hits["source"]+=1
            assert self.rfile.read(int(self.headers['Content-Length']))==b"synthetic-context"
            self.send_response(status)
            self.send_header("Location",f"http://127.0.0.1:{target.server_port}/redirected")
            self.end_headers()
        def log_message(self,*args):pass
    source=ThreadingHTTPServer(("127.0.0.1",0),Source)
    threads=[Thread(target=s.serve_forever,daemon=True) for s in [target,source]]
    for thread in threads:thread.start()
    monkeypatch.setenv("HTTP_PROXY","http://127.0.0.1:1")
    try:
        request=machine.urllib.request.Request(f"http://localhost:{source.server_port}/generate",data=b"synthetic-context")
        with pytest.raises(ValueError,match="redirects are refused"):
            machine.local_urlopen(request,timeout=2)
        assert hits=={"source":1,"target":0}
    finally:
        for server in [source,target]:server.shutdown();server.server_close()
        for thread in threads:thread.join(timeout=2);assert not thread.is_alive()


@pytest.mark.parametrize("payload", [{"data": []}, {"data": [{"id": "different-model"}]}])
def test_probe_distinguishes_reachable_inventory_from_unavailable_model(monkeypatch, payload):
    import io
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "local_urlopen", lambda *args, **kwargs: io.BytesIO(json.dumps(payload).encode()))
    result = machine.probe()
    assert result["capability"] is False
    assert result["reason"] == "model m is not available"
    assert result["inventory_status"] == "READ_VERIFIED"
    assert result["available"] == [row["id"] for row in payload["data"]]


@pytest.mark.parametrize("payload", [{}, {"data": {}}, {"data": [None]}, {"data": [{"id": 7}]}])
def test_probe_rejects_malformed_inventory_without_claiming_empty_models(monkeypatch, payload):
    import io
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "local_urlopen", lambda *args, **kwargs: io.BytesIO(json.dumps(payload).encode()))
    result = machine.probe()
    assert result["capability"] is False
    assert result["inventory_status"] == "READ_FAILED"
    assert result["error_type"] in {"ValueError", "JSONDecodeError"}
    assert "available" not in result


def test_probe_retains_request_failure_type_without_echoing_server_error(monkeypatch):
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "ollama", "base": "http://127.0.0.1:1", "model": "m", "discovered": False})
    def refuse(*args, **kwargs):
        raise machine.urllib.error.URLError("SYNTHETIC private response must not be echoed")
    monkeypatch.setattr(machine, "local_urlopen", refuse)
    result = machine.probe()
    assert result["capability"] is False
    assert result["inventory_status"] == "READ_FAILED"
    assert result["error_type"] == "URLError"
    assert "SYNTHETIC private" not in json.dumps(result)


@pytest.mark.parametrize("protocol,key,identity", [("openai", "data", "id"), ("ollama", "models", "name")])
def test_verified_selected_inventory_is_availability_only_without_inference(monkeypatch, protocol, key, identity):
    import io
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": protocol, "base": "http://127.0.0.1:1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "local_urlopen", lambda *args, **kwargs: io.BytesIO(json.dumps({key: [{identity: "m"}]}).encode()))
    monkeypatch.setattr(machine, "_call", lambda *args, **kwargs: pytest.fail("Availability probe invoked inference"))
    result = machine.probe()
    assert result["capability"] is True and result["inventory_status"] == "READ_VERIFIED"
    assert result["model"] == "m" and result["available"] == ["m"]
    assert result["availability"] == "MODEL_LISTED_INFERENCE_UNVERIFIED"
    assert result["evidence_scope"] == "MODEL_INVENTORY_ONLY"
    assert result["inference_status"] == "NOT_EXECUTED"
    assert result["loaded_status"] == "UNKNOWN"
    assert "answer" not in result


def test_a_question_is_required_rather_than_answering_nothing():
    # An answer to no question is not a task, so the route refuses instead of returning model noise.
    with pytest.raises(ValueError) as raised:
        machine.answer("some context", "")
    assert "question is required" in str(raised.value)


def test_a_context_is_required_rather_than_answering_ungrounded():
    # The whole point of grounding is that the answer comes from accepted material. Without a context
    # the model would answer from its weights, which is a different capability with a different risk.
    with pytest.raises(ValueError) as raised:
        machine.answer("", "what is it?")
    assert "context is required" in str(raised.value)


def test_an_empty_model_answer_is_a_named_failure_not_an_empty_success(monkeypatch):
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *a, **k: ("", "length", None, "content"))

    with pytest.raises(ValueError) as raised:
        machine.answer("context", "question", max_tokens=8)
    message = str(raised.value)
    # the budget is named, because that is what the caller has to change
    assert "no answer within 8 tokens" in message
    assert "length" in message


def test_a_truncated_answer_is_reported_as_a_loss_not_as_an_answer(monkeypatch):
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *a, **k: ("a partial answer", "length", None, "content"))

    result = machine.answer("context", "question", max_tokens=16)
    receipt = result["loss_receipt"]
    assert result["truncated"] is True
    assert receipt["params"]["finish_reason"] == "length"
    assert receipt["params"]["max_tokens"] == 16
    kinds = [loss["kind"] for loss in receipt["losses"]]
    assert kinds == ["truncated_answer"], receipt


def test_a_finished_answer_carries_no_loss(monkeypatch):
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *a, **k: ("a complete answer", "stop", None, "content"))

    result = machine.answer("context", "question")
    assert result["truncated"] is False
    assert result["loss_receipt"]["losses"] == []
    assert result["loss_receipt"]["params"]["finish_reason"] == "stop"


def test_the_answer_is_labelled_a_candidate_and_never_knowledge(monkeypatch):
    """The receipt is the promise: a reader must see that this is unreviewed model output."""
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *a, **k: ("an answer", "stop", None, "content"))

    result = machine.answer("context", "question")
    receipt = result["loss_receipt"]
    assert receipt["params"]["authority"] == "candidate"
    assert "human review" in receipt["loss_note"]
    assert "not accepted knowledge" in receipt["loss_note"]
    # and nothing claims the model was trained or that knowledge changed
    blob = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in ("accuracy", "promoted", "trained"):
        assert forbidden not in blob, forbidden


def test_extract_forwards_the_token_budget(monkeypatch, tmp_path):
    """A budget that is accepted and then dropped makes the flag a lie.

    This is the bug the test exists for: `--max-tokens` was parsed, then `extract` did not take it,
    so every call silently used the default and a deliberately small budget still reported the
    default's finish reason.
    """
    seen: dict = {}

    def fake_call(endpoint, model, prompt, timeout_s, max_tokens):
        seen["max_tokens"] = max_tokens
        return "an answer", "stop", None, "content"

    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", fake_call)

    context = tmp_path / "ctx.txt"
    context.write_text("some accepted material", encoding="utf-8")
    result = machine.extract(str(context), "question", max_tokens=777)

    assert seen["max_tokens"] == 777
    assert result["loss_receipt"]["params"]["max_tokens"] == 777
    assert result["max_tokens"] == 777
    assert result["finish_reason"] == "stop"
    assert result["truncated"] is False
    assert isinstance(result["elapsed_s"], (int, float))


def test_route_extraction_preserves_actual_truncation_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *args, **kwargs: ("partial answer", "length", None, "content"))
    context = tmp_path / "ctx.txt"
    context.write_text("synthetic accepted material", encoding="utf-8")
    result = machine.extract(str(context), "question", max_tokens=128)
    assert result["finish_reason"] == result["loss_receipt"]["params"]["finish_reason"] == "length"
    assert result["truncated"] is True
    assert result["max_tokens"] == 128
    assert result["elapsed_s"] >= 0
    assert result["loss_receipt"]["losses"][0]["kind"] == "truncated_answer"


@pytest.mark.parametrize("observed", ["m", "different-model", None, 7, ""])
@pytest.mark.parametrize("protocol", ["openai", "ollama"])
def test_http_response_identity_is_observed_without_request_fallback(monkeypatch, observed, protocol):
    """SIMULATED HTTP response; never an actual-model qualification."""
    import io
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": protocol, "base": "http://127.0.0.1:1", "model": "m"})
    payload = {"model": observed, "choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}],
               "response": "answer", "done_reason": "stop"}
    monkeypatch.setattr(machine, "local_urlopen", lambda *a, **k: io.BytesIO(json.dumps(payload).encode()))
    result = machine.answer("context", "question")
    assert result["requested_model"] == result["model"] == "m"
    assert result["observed_model"] == (observed if isinstance(observed, str) and observed else None)
    assert result["answer_source"] == ("content" if protocol == "openai" else "response")
    assert result["loss_receipt"]["params"]["observed_model"] == result["observed_model"]
    assert result["usage"] is None and result["cost"] is None
    assert result["usage_status"] == result["cost_status"] == "UNKNOWN"


@pytest.mark.parametrize("protocol,payload,expected", [
    ("openai", {"usage":{"prompt_tokens":10,"completion_tokens":0,"total_tokens":10}}, {"input_tokens":10,"output_tokens":0,"total_tokens":10}),
    ("ollama", {"prompt_eval_count":12,"eval_count":3}, {"input_tokens":12,"output_tokens":3}),
    ("openai", {"usage":{"prompt_tokens":True,"completion_tokens":-1,"total_tokens":"0"}}, None),
    ("openai", {"usage":{"prompt_tokens":4,"completion_tokens":2**54}}, {"input_tokens":4}),
])
def test_usage_preserves_reported_counts_without_inventing_total_or_missing_zero(protocol,payload,expected):
    assert machine.reported_usage(payload,protocol)==expected


@pytest.mark.parametrize("finish", ["stop", "length"])
def test_reasoning_only_response_cannot_be_published_as_an_answer(monkeypatch, tmp_path, finish):
    import io
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1", "model": "m"})
    payload = {"model": "m", "choices": [{"message": {"content": "", "reasoning_content": "synthetic reasoning"}, "finish_reason": finish}]}
    monkeypatch.setattr(machine, "local_urlopen", lambda *a, **k: io.BytesIO(json.dumps(payload).encode()))
    context = tmp_path / "context.txt"
    context.write_text("synthetic context", encoding="utf-8")
    with pytest.raises(ValueError, match="no final answer") as raised:
        machine.extract(str(context), "question")
    assert "synthetic reasoning" not in str(raised.value)


def test_final_content_is_used_without_publishing_reasoning(monkeypatch):
    import io
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1", "model": "m"})
    payload = {"model": "m", "choices": [{"message": {
        "content": "final answer", "reasoning_content": "synthetic private reasoning"},
        "finish_reason": "stop"}]}
    monkeypatch.setattr(machine, "local_urlopen", lambda *a, **k: io.BytesIO(json.dumps(payload).encode()))
    result = machine.answer("context", "question")
    assert result["answer"] == "final answer"
    assert result["answer_source"] == "content"
    assert "synthetic private reasoning" not in json.dumps(result)


def test_a_missing_context_file_is_a_named_failure(tmp_path):
    with pytest.raises(ValueError) as raised:
        machine.extract(str(tmp_path / "absent.txt"), "question")
    assert "context file not found" in str(raised.value)


def test_extract_without_a_question_is_refused(tmp_path):
    context = tmp_path / "ctx.txt"
    context.write_text("some accepted material", encoding="utf-8")
    with pytest.raises(ValueError) as raised:
        machine.extract(str(context), None)
    assert "needs a question" in str(raised.value)


def test_the_worker_identity_and_engine_are_declared():
    assert machine.WORKER_IDENTITY == "python-worker-machine-answer-ndjson"
    assert machine.ENGINE == "python-worker-machine-answer"
    # the prompt version is part of reproducibility, so it must be non-empty and dated
    assert machine.PROMPT_VERSION.startswith("archeaxis.vnext/")

@pytest.mark.parametrize("error,code", [(machine.ModelCallFailure("SYNTHETIC_PRIVATE"), "MODEL_CALL_FAILED"), (machine.FinalAnswerFailure("SYNTHETIC_PRIVATE", "NO_FINAL_ANSWER"), "NO_FINAL_ANSWER"), (machine.FinalAnswerFailure("SYNTHETIC_PRIVATE", "EMPTY_ANSWER"), "EMPTY_ANSWER"), (ValueError("SYNTHETIC_PRIVATE"), "WORKER_FAILED"), (machine.FinalAnswerFailure("SYNTHETIC_PRIVATE", "SYNTHETIC_PRIVATE"), "WORKER_FAILED")])
def test_machine_failure_receipt_is_allowlisted_and_contains_no_exception(error, code):
    assert machine.failure_receipt(error) == {"schema": "archeaxis.machine-worker-failure/v1", "reason_code": code}
    assert "SYNTHETIC_PRIVATE" not in json.dumps(machine.failure_receipt(error))

def test_cli_failure_does_not_echo_context_or_raw_exception(monkeypatch, capsys):
    monkeypatch.setattr(machine.sys, "argv", ["worker", "synthetic-context", "--question", "synthetic-question"])
    def fail(*args, **kwargs):
        raise machine.FinalAnswerFailure("SYNTHETIC_PRIVATE", "NO_FINAL_ANSWER")
    monkeypatch.setattr(machine, "extract", fail)
    assert machine.main() == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {"schema": "archeaxis.machine-worker-failure/v1", "reason_code": "NO_FINAL_ANSWER"}
    assert "SYNTHETIC_PRIVATE" not in captured.out
