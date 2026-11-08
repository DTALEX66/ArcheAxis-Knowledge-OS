"""The OpenMAIC outline local-model worker against synthetic loopback stubs.

No real model, no Node, no Core: a stub HTTP server answers, and the worker is
invoked exactly as the Core invokes it (isolated `-I -B -X utf8` Python, one
bounded JSON line on stdin, one JSON line on stdout).
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/course/worker_outline_local_model.py"
SCHEMA = "archeaxis.openmaic-outline-model-request/v1"


@contextmanager
def stub(body: bytes, status: int = 200, delay: float = 0.0, body_delay: float = 0.0,
         truncate_chunked: bool = False):
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(size)
            seen.append({"path": self.path, "body": raw, "headers": dict(self.headers)})
            if delay:
                time.sleep(delay)
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                if truncate_chunked:
                    self.send_header("Transfer-Encoding", "chunked")
                else:
                    self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.flush()
                if body_delay:
                    time.sleep(body_delay)
                if truncate_chunked:
                    self.wfile.write(b"20\r\n{\"private\":\"SYNTHETIC_PRIVATE\"")
                    self.wfile.flush()
                    self.close_connection = True
                    return
                self.wfile.write(body)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def frame(port: int, **overrides) -> dict:
    data = {"schema": SCHEMA, "system": "SYNTHETIC_SYSTEM 原样保留\n",
            "user": "\nSYNTHETIC_USER 合成材料\n"}
    data.update(overrides)
    return data


def response(content="  合成回答\n", finish="stop", model="synthetic-requested-model",
             usage=None) -> bytes:
    result = {"model": model,
              "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                           "finish_reason": finish}]}
    if usage is not None:
        result["usage"] = usage
    return json.dumps(result, ensure_ascii=False).encode("utf-8")


def free_port() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def invoke(data, port: int, *, model: str | None = "synthetic-requested-model",
           timeout_s: int | None = None, protocol: str = "openai") -> tuple[int, dict]:
    env = dict(os.environ)
    for key in ("ARCHEAXIS_MACHINE_ENDPOINT", "ARCHEAXIS_MACHINE_MODEL",
                "ARCHEAXIS_MACHINE_PROTOCOL"):
        env.pop(key, None)
    env["ARCHEAXIS_MACHINE_ENDPOINT"] = f"http://127.0.0.1:{port}" + ("/v1" if protocol == "openai" else "")
    env["ARCHEAXIS_MACHINE_PROTOCOL"] = protocol
    if model is not None:
        env["ARCHEAXIS_MACHINE_MODEL"] = model
    if isinstance(data, dict):
        data = {**data}
        if timeout_s is not None:
            data["timeout_s"] = timeout_s
    raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
    process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(WORKER)],
                             input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=30, check=False, env=env)
    try:
        result = json.loads(process.stdout.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise AssertionError(
            f"worker did not return JSON: exit={process.returncode}") from error
    assert process.stderr == b""
    assert process.returncode == (0 if result["status"] == "REPLY" else 2)
    return process.returncode, result


def test_the_two_captured_messages_are_sent_and_the_text_is_returned_verbatim():
    body = response(content="  {合成回答}\n", usage={
        "prompt_tokens": 11, "completion_tokens": 5, "total_tokens": 16})
    with stub(body) as (port, seen):
        code, result = invoke(frame(port), port)
    assert code == 0 and result["status"] == "REPLY" and result["reason"] is None, result
    assert len(seen) == 1 and seen[0]["path"] == "/v1/chat/completions"
    sent = json.loads(seen[0]["body"].decode("utf-8"))
    assert sent == {"model": "synthetic-requested-model", "max_tokens": 2048,
                    "messages": [{"role": "system", "content": "SYNTHETIC_SYSTEM 原样保留\n"},
                                 {"role": "user", "content": "\nSYNTHETIC_USER 合成材料\n"}]}
    assert result["content"] == "  {合成回答}\n", "provider text is never trimmed or rewritten"
    assert result["content_sha256"] == hashlib.sha256("  {合成回答}\n".encode()).hexdigest()
    assert result["content_bytes"] == len("  {合成回答}\n".encode())
    assert result["requested_model"] == result["model"] == "synthetic-requested-model"
    assert result["observed_model"] == "synthetic-requested-model"
    assert result["finish_reason"] == "stop"
    assert result["usage"] == {"input_tokens": 11, "output_tokens": 5, "total_tokens": 16}
    assert result["usage_status"] == "REPORTED"
    assert result["model_call"] == "INVOKED" and result["network_performed"] is True
    assert result["network_scope"] == "LOOPBACK_LOCAL_MODEL_ONLY"
    assert result["model_output_verification"] == "UNREVIEWED_LOCAL_MODEL_TEXT"
    assert result["persisted"] is False and result["core_task"] == "NOT_CONNECTED"
    assert result["human_review_required"] is True


def test_an_explicit_model_selection_overrides_the_lane_model():
    with stub(response()) as (port, seen):
        code, result = invoke(frame(port, model="synthetic-other-model"), port,
                              model="synthetic-lane-model")
    assert code == 0 and result["requested_model"] == "synthetic-other-model"
    assert json.loads(seen[0]["body"].decode("utf-8"))["model"] == "synthetic-other-model"


def test_interactive_scene_has_a_separate_bounded_model_budget():
    with stub(response()) as (port, seen):
        code, result = invoke(frame(port, request_kind="interactive_scene", timeout_s=200), port)
    assert code == 0 and result["status"] == "REPLY"
    assert result["timeout_s"] == 200
    assert len(seen) == 1
    sent = json.loads(seen[0]["body"])
    assert "request_kind" not in sent and "timeout_s" not in sent


@pytest.mark.parametrize("overrides", [
    {"timeout_s": 121},
    {"request_kind": "interactive_scene", "timeout_s": 201},
    {"request_kind": "other", "timeout_s": 200},
    {"request_kind": None, "timeout_s": 200},
    {"request_kind": "interactive_scene", "timeout_s": True},
])
def test_longer_budget_is_refused_outside_its_bounded_kind(overrides):
    with stub(response()) as (port, seen):
        code, result = invoke(frame(port, **overrides), port)
    assert code == 2 and result["status"] == "INVALID_MODEL_OUTPUT"
    assert result["network_performed"] is False and seen == []


def test_a_slow_lane_is_named_as_a_timeout_without_retrying():
    with stub(response(), delay=3.0) as (port, seen):
        started = time.monotonic()
        code, result = invoke(frame(port), port, timeout_s=1)
        elapsed = time.monotonic() - started
    assert code == 2 and result["status"] == "MODEL_TIMEOUT", result
    assert result["reason"] == "MODEL_REQUEST_TIMEOUT"
    assert result["content"] is None
    assert result["network_performed"] is None
    assert len(seen) == 1, "a timeout never becomes a second attempt"
    assert elapsed < 10


def test_a_slow_response_body_is_a_timeout_not_invalid_model_output():
    with stub(response(), body_delay=3.0) as (port, seen):
        code, result = invoke(frame(port), port, timeout_s=1)
    assert code == 2 and result["status"] == "MODEL_TIMEOUT", result
    assert result["reason"] == "MODEL_RESPONSE_TIMEOUT"
    assert result["content"] is None
    assert result["network_performed"] is True
    assert len(seen) == 1, "a body timeout must not retry the model request"


@pytest.mark.parametrize("finish,reason", [
    ("length", "MODEL_NONSTOP"),
    ("content_filter", "MODEL_NONSTOP"),
    ("tool_calls", "MODEL_NONSTOP"),
    ("function_call", "MODEL_NONSTOP"),
    ("error", "MODEL_NONSTOP"),
    (None, "MODEL_FINISH_REASON_UNKNOWN"),
    ("vendor_private_reason", "MODEL_FINISH_REASON_INVALID"),
])
def test_unfinished_or_unconfirmed_output_is_not_a_reply(finish, reason):
    with stub(response(content="SYNTHETIC_PRIVATE", finish=finish)) as (port, seen):
        code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "INVALID_MODEL_OUTPUT"
    assert result["reason"] == reason
    assert result["content"] is None and result["network_performed"] is True
    assert len(seen) == 1
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result)
    assert "vendor_private_reason" not in json.dumps(result)


@pytest.mark.parametrize("done,finish,expected", [
    (True, "stop", "REPLY"),
    (True, "length", "MODEL_NONSTOP"),
    (True, None, "MODEL_FINISH_REASON_UNKNOWN"),
    (False, "stop", "MODEL_COMPLETION_UNCONFIRMED"),
    (None, "stop", "MODEL_COMPLETION_UNCONFIRMED"),
])
def test_ollama_requires_a_confirmed_normal_completion(done, finish, expected):
    payload = json.dumps({"model": "synthetic-requested-model", "response": "SYNTHETIC_PRIVATE",
                          "done": done, "done_reason": finish}).encode("utf-8")
    with stub(payload) as (port, seen):
        code, result = invoke(frame(port), port, protocol="ollama")
    assert len(seen) == 1 and seen[0]["path"] == "/api/generate"
    assert result["network_performed"] is True
    if expected == "REPLY":
        assert code == 0 and result["status"] == "REPLY"
        assert result["content"] == "SYNTHETIC_PRIVATE"
    else:
        assert code == 2 and result["status"] == "INVALID_MODEL_OUTPUT"
        assert result["reason"] == expected and result["content"] is None
        assert "SYNTHETIC_PRIVATE" not in json.dumps(result)


def test_empty_or_reasoning_only_content_is_no_final_answer():
    for content, reason in ((None, "REASONING_ONLY"), ("   ", "EMPTY_CONTENT")):
        payload = {"model": "synthetic-requested-model",
                   "choices": [{"index": 0, "finish_reason": "stop",
                                "message": {"role": "assistant", "content": content,
                                            **({"reasoning_content": "SYNTHETIC_PRIVATE"}
                                               if content is None else {})}}]}
        with stub(json.dumps(payload, ensure_ascii=False).encode("utf-8")) as (port, _seen):
            code, result = invoke(frame(port), port)
        assert code == 2 and result["status"] == "NO_FINAL_ANSWER", result
        assert result["reason"] == reason
        assert result["content"] is None
        assert result["network_performed"] is True
        assert "SYNTHETIC_PRIVATE" not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize("body,reason", [
    (b'{"model":"m","choices":[]}', "MODEL_RESPONSE_SHAPE"),
    (b'{"model":"m","choices":[{"index":0,"message":{"content":"a",'
     b'"tool_calls":[{"id":"SYNTHETIC_PRIVATE"}]},"finish_reason":"stop"}]}',
     "MODEL_TOOL_CALL_UNSUPPORTED"),
    (b'{"model":"m","choices":[{"index":0,"message":{"content":7},'
     b'"finish_reason":"stop"}]}', "MODEL_CONTENT_INVALID"),
    (b'{"model":"m","choices":[{"index":0,"message":{"content":"a"},'
     b'"finish_reason":{"private":"SYNTHETIC_PRIVATE"}}]}',
     "MODEL_FINISH_REASON_INVALID"),
])
def test_unusable_provider_bodies_are_invalid_output_not_a_candidate(body, reason):
    with stub(body) as (port, seen):
        code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "INVALID_MODEL_OUTPUT", result
    assert result["reason"] == reason
    assert result["content"] is None and len(seen) == 1
    assert result["network_performed"] is True
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result)


def test_invalid_json_after_response_headers_records_the_observed_loopback_call():
    with stub(b"{") as (port, seen):
        code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "INVALID_MODEL_OUTPUT"
    assert result["reason"] == "MODEL_RESPONSE_INVALID"
    assert result["network_performed"] is True and len(seen) == 1


def test_a_truncated_chunked_response_is_a_named_failure_without_echo():
    with stub(b"", truncate_chunked=True) as (port, seen):
        code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "INVALID_MODEL_OUTPUT"
    assert result["reason"] == "MODEL_RESPONSE_INVALID"
    assert result["network_performed"] is True and len(seen) == 1
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result)


def test_a_truncated_http_rejection_keeps_the_status_without_echo():
    with stub(b"", status=400, truncate_chunked=True) as (port, seen):
        code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "MODEL_REJECTED"
    assert result["reason"] == "MODEL_HTTP_REJECTED"
    assert result["diagnostic"]["http_status"] == 400
    assert result["network_performed"] is True and len(seen) == 1
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("field", ["content", "finish_reason", "model", "empty_model"])
def test_unpaired_surrogates_in_emitted_model_fields_are_named_failures(field):
    payload = {"model": "synthetic-requested-model", "choices": [{"index": 0,
               "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}]}
    if field == "content":
        payload["choices"][0]["message"]["content"] = "\ud800"
    elif field == "finish_reason":
        payload["choices"][0]["finish_reason"] = "\ud800"
    else:
        payload["model"] = "\ud800"
        if field == "empty_model":
            payload["choices"][0]["message"]["content"] = " "
    with stub(json.dumps(payload).encode("ascii")) as (port, seen):
        code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "INVALID_MODEL_OUTPUT"
    assert result["reason"] == "MODEL_RESPONSE_INVALID"
    assert result["content"] is None and result["network_performed"] is True
    assert len(seen) == 1


def test_http_server_failure_records_the_observed_loopback_call():
    with stub(b"{}", status=503) as (port, seen):
        code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "MODEL_UNAVAILABLE"
    assert result["reason"] == "MODEL_ENDPOINT_UNHEALTHY"
    assert result["network_performed"] is True and len(seen) == 1


def test_a_lane_that_refuses_the_request_is_a_named_rejection_without_prompt_text():
    # LM Studio answers a prompt larger than the loaded context with 400 and an
    # engine body prefixed by prose; the lane is reachable, the request is not.
    engine = {"error": {"code": 400,
        "message": "request (9496 tokens) exceeds the available context size (8192 tokens)",
        "type": "exceed_context_size_error", "n_prompt_tokens": 9496, "n_ctx": 8192}}
    body = json.dumps({"error": "Engine protocol predict request returned 400: " +
                       json.dumps(engine)}).encode()
    with stub(body, status=400) as (port, seen):
        code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "MODEL_REJECTED", result
    assert result["reason"] == "MODEL_HTTP_REJECTED"
    assert result["network_performed"] is True
    assert result["diagnostic"]["http_status"] == 400
    assert result["diagnostic"]["n_prompt_tokens"] == 9496
    assert result["diagnostic"]["n_ctx"] == 8192
    assert len(seen) == 1 and result["content"] is None
    serialized = json.dumps(result, ensure_ascii=False)
    assert "SYNTHETIC_SYSTEM" not in serialized
    assert "exceeds the available context" not in serialized


def test_a_reply_beyond_the_replay_budget_is_refused_not_truncated():
    with stub(response(content="x" * 120_001)) as (port, _seen):
        code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "INVALID_MODEL_OUTPUT"
    assert result["reason"] == "MODEL_REPLY_BUDGET" and result["content"] is None
    assert result["network_performed"] is True


def test_a_non_loopback_endpoint_is_refused_before_any_request():
    with stub(response()) as (port, seen):
        env = dict(os.environ)
        env["ARCHEAXIS_MACHINE_ENDPOINT"] = f"http://192.0.2.1:{port}/v1"
        env["ARCHEAXIS_MACHINE_PROTOCOL"] = "openai"
        raw = json.dumps(frame(port), ensure_ascii=False).encode("utf-8")
        process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(WORKER)],
                                 input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=30, check=False, env=env)
        result = json.loads(process.stdout.decode("utf-8"))
    assert process.returncode == 2 and result["status"] == "MODEL_UNAVAILABLE", result
    assert result["reason"] == "MODEL_ENDPOINT_INVALID"
    assert result["content"] is None
    assert seen == [], "a refused endpoint contacts nothing"


def test_no_local_model_is_unavailable_not_a_500():
    port = free_port()
    code, result = invoke(frame(port), port)
    assert code == 2 and result["status"] == "MODEL_UNAVAILABLE", result
    assert result["reason"] == "MODEL_ENDPOINT_UNREACHABLE"
    assert result["content"] is None
    assert result["network_performed"] is None


@pytest.mark.parametrize("data", [
    {"schema": SCHEMA, "system": "s"},
    {"schema": SCHEMA, "system": "s", "user": "u", "reply": "x"},
    {"schema": "archeaxis.openmaic-outline-model-request/v2", "system": "s", "user": "u"},
    {"schema": SCHEMA, "system": "s", "user": "u", "model": "not a\nmodel"},
    {"schema": SCHEMA, "system": "s", "user": "u", "timeout_s": 0},
    {"schema": SCHEMA, "system": "x" * 200_001, "user": "u"},
])
def test_malformed_requests_are_refused_before_any_network_call(data):
    port = free_port()
    code, result = invoke(data, port)
    assert code == 2 and result["status"] == "INVALID_MODEL_OUTPUT", result
    assert result["content"] is None and result["network_performed"] is False


def test_hello_declares_the_capability_and_no_model_call():
    process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(WORKER), "--hello"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
                             check=False, env={**os.environ})
    assert process.returncode == 0
    hello = json.loads(process.stdout.decode("utf-8"))
    assert hello == {"schema": "archeaxis.derived-worker-hello/v1",
                     "capability": "course.openmaic.outline-model", "version": 1,
                     "model_call": "NOT_INVOKED", "network_performed": False}
