"""Unregistered relay against synthetic loopback stubs; never a real model."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import gzip
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
RELAY = ROOT / "services/learning-providers/openmaic/local_model_relay.py"


@contextmanager
def stub(body: bytes, status: int = 200, headers: dict | None = None, trickle_headers: bool = False):
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(size)
            seen.append({"path": self.path, "body": raw, "headers": dict(self.headers)})
            try:
                if trickle_headers:
                    self.connection.sendall(b"HTTP/1.1 200 OK\r\nX-Slow: ")
                    for _ in range(20):
                        time.sleep(0.2)
                        self.connection.sendall(b"x")
                    return
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def frame(port: int) -> dict:
    return {"schema": "archeaxis.openmaic-local-relay-prototype/v1", "request_id": "synthetic_request_1",
            "stage": "quiz_content", "profile": {"protocol": "openai", "endpoint": f"http://127.0.0.1:{port}/v1",
                "model": "synthetic-requested-model", "max_tokens": 256, "timeout_s": 5},
            "system": "  SYSTEM 合成\n原样保留  ", "user": "\nUSER 合成材料与问题\n"}


def response(content="  合成回答\n", finish="stop", model="synthetic-requested-model") -> bytes:
    result = {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": finish}]}
    if model is not None:
        result["model"] = model
    return json.dumps(result, ensure_ascii=False).encode("utf-8")


def invoke(data: dict | bytes, env: dict | None = None) -> tuple[int, dict]:
    raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
    process = subprocess.run([sys.executable, "-I", "-B", "-S", "-X", "utf8", str(RELAY)], input=raw,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False,
                             env=env)
    try:
        result = json.loads(process.stdout.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise AssertionError(f"relay did not return JSON: exit={process.returncode}") from error
    assert process.stderr == b""
    return process.returncode, result


def test_two_roles_and_original_text_reach_only_synthetic_stub_and_model_claim_is_not_verified():
    body = response()
    with stub(body) as (port, seen):
        data = frame(port)
        code, result = invoke(data)
    assert code == 0 and result["status"] == "CANDIDATE", result
    assert len(seen) == 1 and seen[0]["path"] == "/v1/chat/completions"
    sent = json.loads(seen[0]["body"].decode("utf-8"))
    assert sent == {"model": "synthetic-requested-model", "max_tokens": 256,
                    "messages": [{"role": "system", "content": data["system"]},
                                 {"role": "user", "content": data["user"]}]}
    assert result["serialized_request_sha256"] == hashlib.sha256(seen[0]["body"]).hexdigest()
    assert result["system_sha256"] == hashlib.sha256(data["system"].encode("utf-8")).hexdigest()
    assert result["user_sha256"] == hashlib.sha256(data["user"].encode("utf-8")).hexdigest()
    assert result["requested_model"] == "synthetic-requested-model"
    assert result["observed_model"] == "synthetic-requested-model" and result["model_identity_status"] == "MATCHED"
    assert result["observed_model_source"] == "response_declared_unverified"
    assert result["provider_reply"]["content"] == "  合成回答\n"
    assert result["provider_reply"]["content_sha256"] == hashlib.sha256("  合成回答\n".encode()).hexdigest()
    assert result["response_body_sha256"] == hashlib.sha256(body).hexdigest()
    assert result["core_task"] == "NOT_CONNECTED" and result["core_authorization"] == "NOT_ESTABLISHED"
    assert result["upstream_generation"] == "NOT_INVOKED" and result["persisted"] is False
    assert result["inference_status"] == "UNKNOWN"
    assert result["digest_privacy"] == "UNSALTED_SHA256_NOT_CONFIDENTIAL"
    assert result["content_verification"] == "UNREVIEWED_PROVIDER_TEXT"


def test_unreported_model_is_not_replaced_by_the_requested_model():
    with stub(response(model=None)) as (port, _seen):
        code, result = invoke(frame(port))
    assert code == 2 and result["status"] == "REJECTED" and result["reason"] == "MODEL_IDENTITY_NOT_REPORTED"
    assert result["requested_model"] == "synthetic-requested-model"
    assert result["observed_model"] is None and result["model_identity_status"] == "NOT_REPORTED"
    assert result["observed_model_source"] == "not_reported"
    assert result["provider_reply"]["content"] == "  合成回答\n"


@pytest.mark.parametrize("calls_shape,calls", [("ABSENT", None), ("NULL", None), ("EMPTY_ARRAY", [])])
@pytest.mark.parametrize("function_shape", ["ABSENT", "NULL"])
def test_no_tool_call_including_empty_array_is_admitted_without_claiming_a_tool_was_called(calls_shape, calls, function_shape):
    message = {"role": "assistant", "content": "READY"}
    if calls_shape != "ABSENT":
        message["tool_calls"] = calls
    if function_shape == "NULL":
        message["function_call"] = None
    payload = {"model": "synthetic-requested-model", "choices": [{"index": 0,
        "message": message, "finish_reason": "stop"}]}
    with stub(json.dumps(payload).encode("utf-8")) as (port, seen):
        code, result = invoke(frame(port))
    assert code == 0 and result["status"] == "CANDIDATE" and len(seen) == 1
    assert result["provider_reply"]["content"] == "READY"
    assert result["tool_call_observation"] == {"tool_calls": calls_shape, "function_call": function_shape}


@pytest.mark.parametrize("calls,shape", [
    ([{"id": "SYNTHETIC_PRIVATE", "function": {"arguments": "SYNTHETIC_PRIVATE"}}], "NONEMPTY_ARRAY"),
    ({"arguments": "SYNTHETIC_PRIVATE"}, "INVALID_TYPE"), (False, "INVALID_TYPE"),
    (0, "INVALID_TYPE"), ("", "INVALID_TYPE"),
])
def test_nonempty_or_malformed_tool_calls_are_rejected_without_echoing_details(calls, shape):
    payload = {"model": "synthetic-requested-model", "choices": [{"index": 0,
        "message": {"role": "assistant", "content": "READY", "tool_calls": calls}, "finish_reason": "stop"}]}
    with stub(json.dumps(payload).encode("utf-8")) as (port, _seen):
        code, result = invoke(frame(port))
    assert code == 2 and result["status"] == "REJECTED" and result["reason"] == "MODEL_TOOL_CALL_UNSUPPORTED"
    assert result["tool_call_observation"] == {"tool_calls": shape, "function_call": "ABSENT"}
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("function", [{}, [], False, {"name": "SYNTHETIC_PRIVATE", "arguments": "SYNTHETIC_PRIVATE"}])
def test_any_nonnull_legacy_function_call_is_rejected_even_with_empty_tool_calls(function):
    payload = {"model": "synthetic-requested-model", "choices": [{"index": 0,
        "message": {"role": "assistant", "content": "READY", "tool_calls": [], "function_call": function},
        "finish_reason": "stop"}]}
    with stub(json.dumps(payload).encode("utf-8")) as (port, _seen):
        code, result = invoke(frame(port))
    assert code == 2 and result["reason"] == "MODEL_TOOL_CALL_UNSUPPORTED"
    assert result["tool_call_observation"] == {"tool_calls": "EMPTY_ARRAY", "function_call": "PRESENT_NON_NULL"}
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result)


def test_different_observed_model_is_rejected_and_original_reply_preserved():
    with stub(response(model="synthetic-other-model")) as (port, _seen):
        code, result = invoke(frame(port))
    assert code == 2 and result["status"] == "REJECTED" and result["reason"] == "MODEL_IDENTITY_DIFFERENT"
    assert result["requested_model"] == "synthetic-requested-model"
    assert result["observed_model"] == "synthetic-other-model" and result["model_identity_status"] == "DIFFERENT"
    assert result["observed_model_source"] == "response_declared_unverified"
    assert result["provider_reply"]["content"] == "  合成回答\n"


@pytest.mark.parametrize("bad", ["remote", "hostname", "https", "userinfo", "query", "protocol", "images", "images_empty", "stage"])
def test_invalid_endpoint_profile_images_and_stage_are_rejected_before_any_request(bad):
    with stub(response()) as (port, seen):
        data = frame(port)
        if bad == "remote":
            data["profile"]["endpoint"] = f"http://192.0.2.1:{port}/v1"
        elif bad == "hostname":
            data["profile"]["endpoint"] = f"http://localhost:{port}/v1"
        elif bad == "https":
            data["profile"]["endpoint"] = f"https://127.0.0.1:{port}/v1"
        elif bad == "userinfo":
            data["profile"]["endpoint"] = f"http://synthetic:secret@127.0.0.1:{port}/v1"
        elif bad == "query":
            data["profile"]["endpoint"] += "?override=1"
        elif bad == "protocol":
            data["profile"]["protocol"] = "ollama"
        elif bad == "images":
            data["images"] = [{"id": "i", "src": "synthetic"}]
        elif bad == "images_empty":
            data["images"] = []
        else:
            data["stage"] = ["unknown"]
        code, result = invoke(data)
    assert code == 2 and result["status"] == "REJECTED" and seen == []
    assert result["reason"] == ("IMAGES_UNSUPPORTED" if bad.startswith("images") else
                                "INVALID_REQUEST" if bad == "stage" else "INVALID_PROFILE")
    assert "synthetic:secret" not in json.dumps(result)


@pytest.mark.parametrize("body,reason", [
    (response(content="truncated original", finish="length"), "MODEL_NONSTOP"),
    (response(content=None), "MODEL_CONTENT_MISSING"),
    (response(content="   "), "MODEL_CONTENT_MISSING"),
    (b'{"model":"m","choices":[{"index":0,"message":{"content":"a","content":"b"},"finish_reason":"stop"}]}', "DUPLICATE_JSON_KEY"),
    (b'{"model":"m","choices":[{"index":0,"message":{"content":"a"},"finish_reason":"stop"}],"usage":{"x":NaN}}', "NONFINITE_JSON_VALUE"),
    (b'{"error":{"message":"do not echo provider body"}}', "MODEL_RESPONSE_INVALID"),
])
def test_nonfinal_missing_ambiguous_and_error_responses_are_rejected(body, reason):
    with stub(body) as (port, seen):
        code, result = invoke(frame(port))
    assert code == 2 and result["status"] == "REJECTED" and result["reason"] == reason
    assert len(seen) == 1 and result["response_body_sha256"] == hashlib.sha256(body).hexdigest()
    assert "do not echo provider body" not in json.dumps(result)
    if reason == "MODEL_NONSTOP":
        assert result["provider_reply"]["content"] == "truncated original"
        assert result["provider_reply"]["content_sha256"] == hashlib.sha256(b"truncated original").hexdigest()


def test_request_duplicate_keys_and_oversize_never_start_a_network_call():
    duplicate = b'{"schema":"x","system":"a","sys\\u0074em":"b"}'
    assert invoke(duplicate)[1]["reason"] == "DUPLICATE_JSON_KEY"
    assert invoke(b" " * 256_001)[1]["reason"] == "INPUT_BUDGET"


@pytest.mark.parametrize("finish", [
    {"reasoning_content": "SYNTHETIC_PRIVATE", "echoed_input": "SYNTHETIC_PRIVATE"},
    "SYNTHETIC_PRIVATE" * 100,
    False,
])
def test_untrusted_nonstring_or_unknown_finish_reason_never_returns_its_structure(finish):
    payload = {"model": "synthetic-requested-model", "choices": [{"index": 0,
        "message": {"content": "可保存的合成内容"}, "finish_reason": finish}]}
    with stub(json.dumps(payload, ensure_ascii=False).encode("utf-8")) as (port, _seen):
        code, result = invoke(frame(port))
    assert code == 2 and result["reason"] == "MODEL_FINISH_REASON_INVALID"
    assert result["provider_reply"]["content"] == "可保存的合成内容"
    assert result["provider_reply"]["finish_reason"] is None
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize("role", [None, "user", "Assistant", {"reasoning_content": "SYNTHETIC_PRIVATE"}])
def test_missing_or_nonassistant_response_role_is_not_admitted(role):
    message = {"content": "原样合成内容"}
    if role is not None:
        message["role"] = role
    payload = {"model": "synthetic-requested-model", "choices": [{"index": 0,
        "message": message, "finish_reason": "stop"}]}
    with stub(json.dumps(payload, ensure_ascii=False).encode("utf-8")) as (port, _seen):
        code, result = invoke(frame(port))
    assert code == 2 and result["status"] == "REJECTED" and result["reason"] == "MODEL_ROLE_INVALID"
    assert result["provider_reply"]["content"] == "原样合成内容"
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize("content", [None, "安全的合成回答"])
def test_reasoning_field_is_never_returned_or_used_as_final_content(content):
    payload = {"model": "synthetic-requested-model", "choices": [{"index": 0,
        "message": {"role": "assistant", "content": content, "reasoning_content": "SYNTHETIC_PRIVATE"},
        "finish_reason": "stop"}]}
    with stub(json.dumps(payload, ensure_ascii=False).encode("utf-8")) as (port, _seen):
        code, result = invoke(frame(port))
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result, ensure_ascii=False)
    if content is None:
        assert code == 2 and result["reason"] == "MODEL_CONTENT_MISSING" and result["provider_reply"] is None
    else:
        assert code == 0 and result["status"] == "CANDIDATE"
        assert result["provider_reply"]["content"] == content
        assert result["content_verification"] == "UNREVIEWED_PROVIDER_TEXT"


def test_redirect_is_refused_and_no_redirect_target_is_contacted():
    with stub(response()) as (target_port, target_seen):
        with stub(b"", status=302, headers={"Location": f"http://127.0.0.1:{target_port}/v1/chat/completions"}) as (source_port, seen):
            code, result = invoke(frame(source_port))
    assert code == 2 and result["reason"] == "HTTP_REDIRECT_REFUSED"
    assert len(seen) == 1 and target_seen == []


def test_proxy_and_credential_environment_are_not_forwarded():
    with stub(response()) as (proxy_port, proxy_seen):
        with stub(response()) as (port, seen):
            env = dict(os.environ)
            env.update({"HTTP_PROXY": f"http://127.0.0.1:{proxy_port}", "HTTPS_PROXY": f"http://127.0.0.1:{proxy_port}",
                        "ALL_PROXY": f"http://127.0.0.1:{proxy_port}", "NO_PROXY": "",
                        "OPENAI_API_KEY": "synthetic-secret-not-to-forward"})
            code, result = invoke(frame(port), env=env)
    assert code == 0 and result["status"] == "CANDIDATE" and len(seen) == 1 and proxy_seen == []
    assert "Authorization" not in seen[0]["headers"]
    assert b"synthetic-secret-not-to-forward" not in seen[0]["body"]
    assert "synthetic-secret-not-to-forward" not in json.dumps(result)


def test_response_and_content_bounds_are_rejected():
    with stub(response(content="x" * 120_001)) as (port, _seen):
        assert invoke(frame(port))[1]["reason"] == "CONTENT_BUDGET"
    with stub(b"x" * (4 * 1024 * 1024 + 1)) as (port, _seen):
        assert invoke(frame(port))[1]["reason"] == "RESPONSE_BUDGET"


def test_total_timeout_stops_owned_child_even_with_trickling_headers():
    with stub(b"", trickle_headers=True) as (port, seen):
        data = frame(port)
        data["profile"]["timeout_s"] = 1
        started = time.monotonic()
        code, result = invoke(data)
        elapsed = time.monotonic() - started
    assert code == 2 and result["reason"] == "TOTAL_DEADLINE_EXCEEDED"
    assert result["provider_stop_state"] == "UNKNOWN" and result["provider_reply"] is None
    assert result["owned_child_stop_state"] == "REAPED"
    assert len(seen) == 1 and elapsed < 5


class InMemoryHttpBytes(io.BytesIO):
    def __init__(self, wire, fragmented):
        super().__init__(wire)
        self.fragmented = fragmented
        self.unread_before_close = None

    def read(self, size=-1):
        if self.fragmented and size > 0:
            size = min(size, 3)
        return super().read(size)

    def close(self):
        if not self.closed:
            self.unread_before_close = len(self.getvalue()) - self.tell()
        super().close()


class InMemoryHttpSocket:
    """A real HTTPResponse parses these bytes; no socket or network is opened."""

    def __init__(self, wire, fragmented=False):
        self.stream = InMemoryHttpBytes(wire, fragmented)

    def makefile(self, *_args, **_kwargs):
        return self.stream


def relay_from_memory(monkeypatch, headers: bytes, body: bytes, *, status: int = 200,
                      fragmented: bool = False, include_socket: bool = False):
    spec = importlib.util.spec_from_file_location("openmaic_relay_http_frame_test", RELAY)
    assert spec is not None and spec.loader is not None
    relay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(relay)
    wire = b"HTTP/1.1 " + str(status).encode("ascii") + b" synthetic\r\n" + headers + b"\r\n" + body
    sock = InMemoryHttpSocket(wire, fragmented)
    response = http.client.HTTPResponse(sock)
    response.begin()
    sent = []

    def fake_open(request, timeout):
        sent.append((request.full_url, request.data, timeout))
        return response

    monkeypatch.setattr(relay, "machine_local_urlopen", lambda: fake_open)
    input_frame = frame(1234)
    raw = json.dumps(input_frame, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    result = relay.network_child(raw, relay.validate(raw))
    assert len(sent) == 1 and sent[0][0] == "http://127.0.0.1:1234/v1/chat/completions"
    assert sent[0][2] == input_frame["profile"]["timeout_s"]
    return (result, sock) if include_socket else result


def test_http_length_truncated_after_complete_valid_json_is_not_a_candidate(monkeypatch):
    body = response(content="SYNTHETIC_FRAME_SENTINEL")
    # The JSON is itself complete, but the declared HTTP body is seven bytes
    # longer and the in-memory transport ends immediately after this body.
    headers = f"Content-Length: {len(body) + 7}\r\n".encode("ascii")
    result = relay_from_memory(monkeypatch, headers, body)
    assert result["status"] == "REJECTED"
    assert result["provider_reply"] is None


@pytest.mark.parametrize("framing", ["content_length", "chunked"])
@pytest.mark.parametrize("fragmented", [False, True])
def test_complete_unambiguous_http_message_frame_is_accepted(monkeypatch, framing, fragmented):
    body = response(content="合成的完整回答")
    if framing == "content_length":
        headers = f"Content-Length: {len(body)}\r\n".encode("ascii")
        wire_body = body
    else:
        headers = b"Transfer-Encoding: chunked\r\n"
        halves = (body[:len(body) // 2], body[len(body) // 2:])
        wire_body = b"".join(format(len(part), "x").encode("ascii") + b"\r\n" + part + b"\r\n"
                             for part in halves) + b"0\r\n\r\n"
    result = relay_from_memory(monkeypatch, headers, wire_body, fragmented=fragmented)
    assert result["status"] == "CANDIDATE"
    assert result["provider_reply"]["content"] == "合成的完整回答"
    assert result["response_body_bytes"] == len(body)
    assert result["response_body_sha256"] == hashlib.sha256(body).hexdigest()


@pytest.mark.parametrize("framing", ["content_length", "chunked"])
def test_verified_message_boundary_does_not_claim_physical_socket_eof(monkeypatch, framing):
    body = response(content="synthetic-frame-body")
    extra = b"SYNTHETIC_BYTES_AFTER_FRAME"
    if framing == "content_length":
        headers = f"Content-Length: {len(body)}\r\n".encode("ascii")
        framed = body
    else:
        headers = b"Transfer-Encoding: chunked\r\n"
        framed = format(len(body), "x").encode("ascii") + b"\r\n" + body + b"\r\n0\r\n\r\n"
    result, sock = relay_from_memory(monkeypatch, headers, framed + extra, include_socket=True)
    assert result["status"] == "CANDIDATE"
    assert result["response_body_sha256"] == hashlib.sha256(body).hexdigest()
    assert sock.stream.unread_before_close == len(extra)


def test_declared_oversize_is_rejected_before_reading_any_body(monkeypatch):
    body = response(content="SYNTHETIC_NOT_READ")
    headers = b"Content-Length: 4194305\r\n"
    result, sock = relay_from_memory(monkeypatch, headers, body, include_socket=True)
    assert result["status"] == "REJECTED" and result["reason"] == "RESPONSE_BUDGET"
    assert result["provider_reply"] is None and sock.stream.unread_before_close == len(body)


def test_chunk_count_limit_is_enforced_before_model_json(monkeypatch):
    headers = b"Transfer-Encoding: chunked\r\n"
    body = b"1\r\nx\r\n" * 4097 + b"0\r\n\r\n"
    result = relay_from_memory(monkeypatch, headers, body)
    assert result["status"] == "REJECTED" and result["reason"] == "HTTP_CHUNK_COUNT_LIMIT"
    assert result["provider_reply"] is None


@pytest.mark.parametrize("case", ["duplicate_equal_length", "duplicate_different_length", "length_and_chunked",
                                  "duplicate_transfer", "combined_length", "unsupported_transfer",
                                  "invalid_length", "negative_length", "no_framing", "unexpected_status",
                                  "incomplete_chunk_end", "chunk_extension", "chunk_trailer"])
def test_ambiguous_or_unsupported_http_message_frame_is_not_a_candidate(monkeypatch, case):
    body = response(content="SYNTHETIC_FRAME_SENTINEL")
    length = str(len(body)).encode("ascii")
    complete_chunk = format(len(body), "x").encode("ascii") + b"\r\n" + body + b"\r\n0\r\n\r\n"
    status = 200
    wire_body = body
    if case == "duplicate_equal_length":
        headers = b"Content-Length: " + length + b"\r\nContent-Length: " + length + b"\r\n"
    elif case == "duplicate_different_length":
        headers = b"Content-Length: " + length + b"\r\nContent-Length: " + str(len(body) + 7).encode() + b"\r\n"
    elif case == "length_and_chunked":
        headers = b"Content-Length: " + length + b"\r\nTransfer-Encoding: chunked\r\n"
        wire_body = complete_chunk
    elif case == "duplicate_transfer":
        headers = b"Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked\r\n"
        wire_body = complete_chunk
    elif case == "combined_length":
        headers = b"Content-Length: " + length + b", " + length + b"\r\n"
    elif case == "unsupported_transfer":
        headers = b"Transfer-Encoding: gzip, chunked\r\n"
    elif case == "invalid_length":
        headers = b"Content-Length: invalid\r\n"
    elif case == "negative_length":
        headers = b"Content-Length: -1\r\n"
    elif case == "no_framing":
        # Close-delimited HTTP is valid in some contexts but is deliberately
        # unsupported here because body completeness cannot be established.
        headers = b"Connection: close\r\n"
    elif case == "unexpected_status":
        headers = b"Content-Length: " + length + b"\r\n"
        status = 206
    elif case == "incomplete_chunk_end":
        headers = b"Transfer-Encoding: chunked\r\n"
        wire_body = complete_chunk[:-2]
    elif case == "chunk_extension":
        # Extensions/trailers are valid HTTP in general, but are outside the
        # finite strict profile borrowed from the local DeepTutor probe.
        headers = b"Transfer-Encoding: chunked\r\n"
        wire_body = format(len(body), "x").encode("ascii") + b";x=1\r\n" + body + b"\r\n0\r\n\r\n"
    else:
        headers = b"Transfer-Encoding: chunked\r\n"
        wire_body = format(len(body), "x").encode("ascii") + b"\r\n" + body + b"\r\n0\r\nX-Test: a\r\n\r\n"
    result = relay_from_memory(monkeypatch, headers, wire_body, status=status)
    assert result["status"] == "REJECTED"
    assert result["provider_reply"] is None


@pytest.mark.parametrize("case", ["hidden_length", "hidden_transfer", "folded_other"])
def test_observed_header_defects_or_observable_folds_are_not_candidates(monkeypatch, case):
    body = response(content="SYNTHETIC_HEADER_SENTINEL")
    length = str(len(body)).encode("ascii")
    if case == "hidden_length":
        headers = (b"Content-Length: " + length + b"\r\nMalformed Header\r\n"
                   + b"Content-Length: " + str(len(body) + 7).encode("ascii") + b"\r\n")
    elif case == "hidden_transfer":
        headers = b"Content-Length: " + length + b"\r\nMalformed Header\r\nTransfer-Encoding: chunked\r\n"
    else:
        # This continuation belongs to X-Note, not an actual TE field.  The
        # finite profile rejects folded headers without relabeling this line.
        headers = b"X-Note: synthetic\r\n Transfer-Encoding: chunked\r\nContent-Length: " + length + b"\r\n"

    wire = b"HTTP/1.1 200 synthetic\r\n" + headers + b"\r\n" + body
    parsed = http.client.HTTPResponse(InMemoryHttpSocket(wire))
    parsed.begin()
    if case.startswith("hidden_"):
        assert parsed.headers.defects, "the parser must observe a malformed header block"
        assert len(parsed.headers.get_all("Content-Length", [])) == 1
        assert not parsed.headers.get_all("Transfer-Encoding", [])
    else:
        assert any("\r" in value or "\n" in value for _, value in parsed.headers.raw_items())
        if case == "folded_other":
            assert not parsed.headers.get_all("Transfer-Encoding", [])
    parsed.close()
    result = relay_from_memory(monkeypatch, headers, body)
    assert result["status"] == "REJECTED"
    assert result["provider_reply"] is None


def test_empty_first_line_length_fold_is_not_observable_after_http_parsing(monkeypatch):
    body = response(content="synthetic-unobservable-fold")
    length = str(len(body)).encode("ascii")
    headers = b"Content-Length:\r\n " + length + b"\r\n"
    parsed = http.client.HTTPResponse(InMemoryHttpSocket(b"HTTP/1.1 200 synthetic\r\n" + headers + b"\r\n" + body))
    parsed.begin()
    assert not parsed.headers.defects
    assert list(parsed.headers.raw_items()) == [("Content-Length", length.decode("ascii"))]
    parsed.close()
    # The already-parsed HTTPResponse is indistinguishable from an ordinary
    # Content-Length header here; acceptance does not establish raw-wire form.
    result = relay_from_memory(monkeypatch, headers, body)
    assert result["status"] == "CANDIDATE"
    assert result["provider_reply"]["content"] == "synthetic-unobservable-fold"


def test_unfolded_unrelated_header_with_one_length_remains_supported(monkeypatch):
    body = response(content="synthetic-unfolded-control")
    headers = b"X-Note: synthetic\r\nContent-Length: " + str(len(body)).encode("ascii") + b"\r\n"
    result = relay_from_memory(monkeypatch, headers, body)
    assert result["status"] == "CANDIDATE"
    assert result["provider_reply"]["content"] == "synthetic-unfolded-control"


@pytest.mark.parametrize("encoding", ["absent", "identity"])
def test_identity_or_absent_content_encoding_is_supported(monkeypatch, encoding):
    body = response(content="synthetic-encoding-control")
    headers = b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n"
    if encoding == "identity":
        headers += b"Content-Encoding: identity\r\n"
    result = relay_from_memory(monkeypatch, headers, body)
    assert result["status"] == "CANDIDATE"
    assert result["provider_reply"]["content"] == "synthetic-encoding-control"


@pytest.mark.parametrize("encoding", ["gzip_plaintext", "gzip_actual", "duplicate_identity", "combined_identity", "other"])
def test_unsupported_or_ambiguous_content_encoding_is_rejected(monkeypatch, encoding):
    body = response(content="SYNTHETIC_ENCODING_SENTINEL")
    wire_body = gzip.compress(body, mtime=0) if encoding == "gzip_actual" else body
    headers = b"Content-Length: " + str(len(wire_body)).encode("ascii") + b"\r\n"
    if encoding in ("gzip_plaintext", "gzip_actual"):
        headers += b"Content-Encoding: gzip\r\n"
    elif encoding == "duplicate_identity":
        headers += b"Content-Encoding: identity\r\nContent-Encoding: identity\r\n"
    elif encoding == "combined_identity":
        headers += b"Content-Encoding: identity, identity\r\n"
    else:
        headers += b"Content-Encoding: br\r\n"
    result = relay_from_memory(monkeypatch, headers, wire_body)
    assert result["status"] == "REJECTED"
    assert result["provider_reply"] is None


@pytest.mark.parametrize("header", ["content_length", "content_encoding", "transfer_encoding"])
@pytest.mark.parametrize("position", ["before", "after"])
def test_non_ascii_nbsp_is_not_accepted_as_http_optional_whitespace(monkeypatch, header, position):
    body = response(content="SYNTHETIC_NBSP_SENTINEL")
    length = str(len(body)).encode("ascii")
    name = {"content_length": b"Content-Length", "content_encoding": b"Content-Encoding",
            "transfer_encoding": b"Transfer-Encoding"}[header]
    value = {"content_length": length, "content_encoding": b"identity", "transfer_encoding": b"chunked"}[header]
    value = b"\xa0" + value if position == "before" else value + b"\xa0"
    headers = name + b": " + value + b"\r\n"
    if header == "content_encoding":
        headers += b"Content-Length: " + length + b"\r\n"
    wire_body = body
    if header == "transfer_encoding":
        wire_body = format(len(body), "x").encode("ascii") + b"\r\n" + body + b"\r\n0\r\n\r\n"
    wire = b"HTTP/1.1 200 synthetic\r\n" + headers + b"\r\n" + wire_body
    parsed = http.client.HTTPResponse(InMemoryHttpSocket(wire))
    parsed.begin()
    assert "\u00a0" in parsed.headers.get_all(name.decode("ascii"))[0], "NBSP must be observable"
    parsed.close()
    result = relay_from_memory(monkeypatch, headers, wire_body)
    assert result["status"] == "REJECTED"
    assert result["provider_reply"] is None


@pytest.mark.parametrize("header", ["content_length", "content_encoding", "transfer_leading", "transfer_surrounding"])
def test_ascii_space_and_tab_are_supported_as_http_optional_whitespace(monkeypatch, header):
    body = response(content="synthetic-ascii-ows")
    length = str(len(body)).encode("ascii")
    wire_body = body
    if header == "content_length":
        headers = b"Content-Length:\t " + length + b"\t \r\n"
    elif header == "content_encoding":
        headers = b"Content-Length: " + length + b"\r\nContent-Encoding:\t identity\t \r\n"
    else:
        suffix = b"\t " if header == "transfer_surrounding" else b""
        headers = b"Transfer-Encoding:\t chunked" + suffix + b"\r\n"
        wire_body = format(len(body), "x").encode("ascii") + b"\r\n" + body + b"\r\n0\r\n\r\n"
        if header == "transfer_surrounding":
            parsed = http.client.HTTPResponse(InMemoryHttpSocket(b"HTTP/1.1 200 synthetic\r\n" + headers + b"\r\n" + wire_body))
            parsed.begin()
            assert parsed.headers.get_all("Transfer-Encoding") == ["chunked\t "]
            assert parsed.chunked is False, "document the stdlib parser behavior used by this control"
            parsed.close()
    result = relay_from_memory(monkeypatch, headers, wire_body)
    assert result["status"] == "CANDIDATE"
    assert result["provider_reply"]["content"] == "synthetic-ascii-ows"
