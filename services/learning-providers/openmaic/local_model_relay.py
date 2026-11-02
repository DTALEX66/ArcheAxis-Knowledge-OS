"""Unregistered, text-only loopback relay prototype; no Core or product route.

The caller supplies a finite internal stage and an explicit local OpenAI profile.
This module does not select or change global model settings and does not grant
material access. Its child is owned only by this prototype. A successful HTTP
reply can be supplied by a test stub; it is not proof of real model inference.
The interpreter and script/parent paths are not identity-pinned. Child stdout
is bounded as it is read, but this is not a production security sandbox.
Only one call per module instance may own a child at a time; if child or pipe
cleanup cannot be confirmed, that instance remains unavailable. Descendants
are not tracked and network isolation is not established by this module.
All SHA-256 digests are unsalted; low-entropy prompts or requests may be guessed
from them, so digests are not a confidentiality or redaction mechanism.
Only the provider's content field is returned. That field is unreviewed and
may itself contain sensitive or inaccurate text; this is not a privacy filter.
The finite HTTP/1 response profile accepts a single Content-Length or strict
chunked frame, without chunk extensions or trailers. Close-delimited responses
are unsupported. The declared frame boundary is checked; physical socket EOF
and any bytes after the frame are not verified. Header parser defects and
folds still observable in parsed values are refused; this cannot detect raw
header forms already normalized away by the HTTP parser. Content-Encoding is
restricted to an absent header or one explicit identity value.
"""
from __future__ import annotations

import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse

REQUEST_SCHEMA = "archeaxis.openmaic-local-relay-prototype/v1"
RESULT_SCHEMA = "archeaxis.openmaic-local-relay-prototype-result/v1"
MAX_INPUT = 256_000
MAX_PROMPT = 200_000
MAX_HTTP_BODY = 4 * 1024 * 1024
MAX_HTTP_CHUNKS = 4_096
MAX_CONTENT = 120_000
MAX_OUTPUT = 1_000_000
_CLEANUP_WAIT_SECONDS = 2.0
_CHILD_SLOT = threading.BoundedSemaphore(1)


class Rejected(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise Rejected("DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def invalid_constant(_value):
    raise Rejected("NONFINITE_JSON_VALUE")


def decode_json(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=unique_object,
                          parse_constant=invalid_constant)
    except Rejected:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise Rejected("INVALID_JSON") from None


def exact_keys(value, expected):
    return type(value) is dict and set(value) == set(expected)


def token(value):
    return (type(value) is str and 1 <= len(value) <= 128 and
            all(c.isascii() and (c.isalnum() or c in "_-") for c in value))


def endpoint_ok(value):
    if type(value) is not str or not 1 <= len(value) <= 256 or value != value.strip():
        return False
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    if (parsed.scheme != "http" or parsed.username is not None or parsed.password is not None
            or parsed.hostname not in {"127.0.0.1", "::1"} or port is None or not 1 <= port <= 65535
            or parsed.path != "/v1" or parsed.query or parsed.fragment):
        return False
    expected_authority = f"127.0.0.1:{port}" if parsed.hostname == "127.0.0.1" else f"[::1]:{port}"
    return parsed.netloc == expected_authority and value == f"http://{expected_authority}/v1"


def validate(raw: bytes) -> dict:
    if not raw or len(raw) > MAX_INPUT:
        raise Rejected("INPUT_BUDGET")
    value = decode_json(raw)
    if type(value) is dict and "images" in value:
        raise Rejected("IMAGES_UNSUPPORTED")
    if not exact_keys(value, ("schema", "request_id", "stage", "profile", "system", "user")):
        raise Rejected("INVALID_REQUEST")
    if (value["schema"] != REQUEST_SCHEMA or not token(value["request_id"])
            or type(value["stage"]) is not str or value["stage"] not in {"outline", "quiz_content", "quiz_actions"}):
        raise Rejected("INVALID_REQUEST")
    profile = value["profile"]
    if not exact_keys(profile, ("protocol", "endpoint", "model", "max_tokens", "timeout_s")):
        raise Rejected("INVALID_PROFILE")
    model = profile["model"]
    if (profile["protocol"] != "openai" or not endpoint_ok(profile["endpoint"])
            or type(model) is not str or not model.strip() or model != model.strip() or len(model) > 256
            or any(ord(c) < 32 or ord(c) == 127 for c in model)
            or type(profile["max_tokens"]) is not int or not 128 <= profile["max_tokens"] <= 4096
            or type(profile["timeout_s"]) is not int or not 1 <= profile["timeout_s"] <= 120):
        raise Rejected("INVALID_PROFILE")
    try:
        model.encode("utf-8")
    except UnicodeError:
        raise Rejected("INVALID_PROFILE") from None
    for name in ("system", "user"):
        text = value[name]
        if (type(text) is not str or not text.strip() or "\0" in text
                or len(text.encode("utf-8")) > MAX_PROMPT):
            raise Rejected("PROMPT_BUDGET")
    return value


def base(raw: bytes, reason: str, request: dict | None = None):
    body = {"schema": RESULT_SCHEMA, "status": "REJECTED", "reason": reason,
            "request_sha256": digest(raw), "core_task": "NOT_CONNECTED",
            "core_authorization": "NOT_ESTABLISHED", "persisted": False,
            "upstream_generation": "NOT_INVOKED", "execution_scope": "UNREGISTERED_INTERNAL_PROTOTYPE",
            "inference_status": "UNKNOWN", "provider_stop_state": "NOT_REQUESTED",
            "digest_privacy": "UNSALTED_SHA256_NOT_CONFIDENTIAL",
            "content_verification": "UNREVIEWED_PROVIDER_TEXT",
            "provider_reply": None}
    if request is not None:
        body.update(request_id=request["request_id"], stage=request["stage"],
                    requested_model=request["profile"]["model"], observed_model=None,
                    system_sha256=digest(request["system"].encode("utf-8")),
                    user_sha256=digest(request["user"].encode("utf-8")))
    return body


def machine_local_urlopen():
    # Resolve only the fixed project-relative source; importing it does not call
    # its model discovery or change the host's environment.
    root = Path(__file__).resolve(strict=True).parents[3]
    path = root / "services/python-workers/machine/worker_machine_answer.py"
    if not path.is_file() or path.is_symlink():
        raise Rejected("NETWORK_GUARD_UNAVAILABLE")
    spec = importlib.util.spec_from_file_location("archeaxis_machine_network_guard", path)
    if spec is None or spec.loader is None:
        raise Rejected("NETWORK_GUARD_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.local_urlopen


def read_http_exact(reader, length: int) -> bytes:
    body = bytearray()
    while len(body) < length:
        maximum = min(65_536, length - len(body))
        chunk = reader.read(maximum)
        if type(chunk) is not bytes or not chunk or len(chunk) > maximum:
            raise Rejected("HTTP_BODY_INCOMPLETE")
        body.extend(chunk)
    return bytes(body)


def read_http_response(response) -> bytes:
    """Verify one supported HTTP message frame; do not claim physical EOF."""
    if not isinstance(response, http.client.HTTPResponse) or response.status != 200:
        raise Rejected("HTTP_RESPONSE_INVALID")
    if response.headers.defects:
        raise Rejected("HTTP_HEADERS_INVALID")
    for name, value in response.headers.raw_items():
        if type(name) is not str or type(value) is not str or "\r" in value or "\n" in value:
            raise Rejected("HTTP_HEADERS_INVALID")
    encodings = response.headers.get_all("Content-Encoding", [])
    if len(encodings) > 1:
        raise Rejected("HTTP_CONTENT_ENCODING_AMBIGUOUS")
    if encodings and encodings[0].strip(" \t").lower() != "identity":
        raise Rejected("HTTP_CONTENT_ENCODING_UNSUPPORTED")
    lengths = response.headers.get_all("Content-Length", [])
    transfers = response.headers.get_all("Transfer-Encoding", [])
    if len(lengths) > 1 or len(transfers) > 1 or (lengths and transfers):
        raise Rejected("HTTP_FRAMING_AMBIGUOUS")
    if lengths:
        value = lengths[0].strip(" \t")
        if re.fullmatch(r"[0-9]{1,9}", value, flags=re.ASCII) is None:
            raise Rejected("HTTP_FRAMING_INVALID")
        length = int(value)
        if length > MAX_HTTP_BODY:
            raise Rejected("RESPONSE_BUDGET")
        if response.chunked or response.length != length:
            raise Rejected("HTTP_FRAMING_INVALID")
        body = read_http_exact(response, length)
        if response.read(1) != b"" or response.length != 0 or not response.isclosed():
            raise Rejected("HTTP_BODY_INCOMPLETE")
        return body
    if not transfers or transfers[0].strip(" \t").lower() != "chunked":
        raise Rejected("HTTP_FRAMING_UNSUPPORTED")
    # This caller passes the fresh, unread response returned by urlopen.
    # HTTPResponse can leave chunked=False for valid trailing ASCII OWS; after
    # confirming the sole TE and absence of Content-Length, parse the raw body.
    if response.fp is None or response.length is not None:
        raise Rejected("HTTP_FRAMING_INVALID")
    reader = response.fp
    body = bytearray()
    for count in range(MAX_HTTP_CHUNKS + 1):
        line = reader.readline(12)
        if type(line) is not bytes or re.fullmatch(rb"[0-9A-Fa-f]{1,8}\r\n", line) is None:
            raise Rejected("HTTP_CHUNK_FRAMING_INVALID")
        size = int(line[:-2], 16)
        if size == 0:
            if read_http_exact(reader, 2) != b"\r\n":
                raise Rejected("HTTP_CHUNK_FRAMING_INVALID")
            return bytes(body)
        if count == MAX_HTTP_CHUNKS:
            raise Rejected("HTTP_CHUNK_COUNT_LIMIT")
        if len(body) + size > MAX_HTTP_BODY:
            raise Rejected("RESPONSE_BUDGET")
        body.extend(read_http_exact(reader, size))
        if read_http_exact(reader, 2) != b"\r\n":
            raise Rejected("HTTP_CHUNK_FRAMING_INVALID")
    raise Rejected("HTTP_CHUNK_COUNT_LIMIT")


def network_child(raw: bytes, request: dict):
    result = base(raw, "MODEL_RESPONSE_INVALID", request)
    profile = request["profile"]
    payload = {"model": profile["model"], "max_tokens": profile["max_tokens"],
               "messages": [{"role": "system", "content": request["system"]},
                            {"role": "user", "content": request["user"]}]}
    wire = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    result["serialized_request_sha256"] = digest(wire)
    result["serialized_request_bytes"] = len(wire)
    try:
        from urllib.request import Request
        local_urlopen = machine_local_urlopen()
        http_request = Request(profile["endpoint"] + "/chat/completions", data=wire,
                               headers={"Content-Type": "application/json"}, method="POST")
        with local_urlopen(http_request, timeout=profile["timeout_s"]) as response:
            body = read_http_response(response)
    except Rejected as error:
        result["reason"] = error.reason
        return result
    except urllib.error.HTTPError:
        result["reason"] = "HTTP_ERROR_OR_REDIRECT"
        return result
    except ValueError as error:
        # The reused guard deliberately raises this fixed message before a
        # redirect is followed; never echo arbitrary exception text.
        result["reason"] = ("HTTP_REDIRECT_REFUSED" if str(error) == "Local model redirects are refused"
                            else "LOCAL_TRANSPORT_FAILURE")
        return result
    except TimeoutError:
        result["reason"] = "LOCAL_SOCKET_TIMEOUT"
        result["provider_stop_state"] = "UNKNOWN"
        return result
    except urllib.error.URLError as error:
        result["reason"] = "LOCAL_SOCKET_TIMEOUT" if isinstance(error.reason, TimeoutError) else "LOCAL_TRANSPORT_FAILURE"
        result["provider_stop_state"] = "UNKNOWN"
        return result
    except OSError:
        result["reason"] = "LOCAL_TRANSPORT_FAILURE"
        result["provider_stop_state"] = "UNKNOWN"
        return result
    except Exception:  # Do not expose exception text, environment or provider bodies.
        result["reason"] = "LOCAL_TRANSPORT_FAILURE"
        result["provider_stop_state"] = "UNKNOWN"
        return result
    result["response_body_bytes"] = len(body)
    result["response_body_sha256"] = digest(body)
    if len(body) > MAX_HTTP_BODY:
        result["reason"] = "RESPONSE_BUDGET"
        return result
    try:
        payload = decode_json(body)
    except Rejected as error:
        result["reason"] = error.reason
        return result
    if type(payload) is not dict or "error" in payload:
        result["reason"] = "MODEL_RESPONSE_INVALID"
        return result
    observed = payload.get("model")
    if observed is not None and (type(observed) is not str or not observed.strip() or len(observed) > 256
                                 or any(ord(c) < 32 or ord(c) == 127 for c in observed)):
        result["reason"] = "OBSERVED_MODEL_INVALID"
        return result
    if observed is not None:
        try:
            observed.encode("utf-8")
        except UnicodeError:
            result["reason"] = "OBSERVED_MODEL_INVALID"
            return result
    result["observed_model"] = observed
    result["observed_model_source"] = "response_declared_unverified" if observed is not None else "not_reported"
    result["model_identity_status"] = ("NOT_REPORTED" if observed is None else
                                       "MATCHED" if observed == profile["model"] else "DIFFERENT")
    choices = payload.get("choices")
    if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
        result["reason"] = "MODEL_RESPONSE_INVALID"
        return result
    choice = choices[0]
    message = choice.get("message")
    finish = choice.get("finish_reason")
    if type(message) is not dict or ("index" in choice and (type(choice["index"]) is not int or choice["index"] != 0)):
        result["reason"] = "MODEL_RESPONSE_INVALID"
        return result
    content = message.get("content")
    known_finish = type(finish) is str and finish in {"stop", "length", "tool_calls", "function_call", "content_filter", "error"}
    if type(content) is str:
        try:
            content_bytes = content.encode("utf-8")
        except UnicodeError:
            result["reason"] = "INVALID_CONTENT_ENCODING"
            return result
        if len(content_bytes) > MAX_CONTENT:
            result["reason"] = "CONTENT_BUDGET"
            return result
        result["provider_reply"] = {"content": content, "content_sha256": digest(content_bytes),
                                    "content_utf8_bytes": len(content_bytes),
                                    "finish_reason": finish if known_finish else None}
    if not known_finish:
        result["reason"] = "MODEL_FINISH_REASON_INVALID"
        return result
    if message.get("role") != "assistant":
        result["reason"] = "MODEL_ROLE_INVALID"
        return result
    if finish != "stop":
        result["reason"] = "MODEL_NONSTOP"
        return result
    if type(content) is not str or not content.strip():
        result["reason"] = "MODEL_CONTENT_MISSING"
        return result
    calls = message.get("tool_calls")
    calls_shape = ("ABSENT" if "tool_calls" not in message else "NULL" if calls is None else
                   "EMPTY_ARRAY" if type(calls) is list and not calls else
                   "NONEMPTY_ARRAY" if type(calls) is list else "INVALID_TYPE")
    function = message.get("function_call")
    function_shape = ("ABSENT" if "function_call" not in message else "NULL" if function is None
                      else "PRESENT_NON_NULL")
    # Report only the finite shape; never echo tool names, arguments or other
    # provider data. An empty array contains no tool calls.
    result["tool_call_observation"] = {"tool_calls": calls_shape, "function_call": function_shape}
    if calls_shape not in {"ABSENT", "NULL", "EMPTY_ARRAY"} or function_shape == "PRESENT_NON_NULL":
        result["reason"] = "MODEL_TOOL_CALL_UNSUPPORTED"
        return result
    if observed is None:
        result["reason"] = "MODEL_IDENTITY_NOT_REPORTED"
        return result
    if observed != profile["model"]:
        result["reason"] = "MODEL_IDENTITY_DIFFERENT"
        return result
    result["status"] = "CANDIDATE"
    result["reason"] = None
    return result


def collect_owned_child(child, raw: bytes, deadline: float):
    """Bound both pipes while retaining ownership of this direct child.

    A pipe may be held by a descendant; never close a stream from a different
    thread while its read/write is in progress. Report cleanup as unknown and
    retain the module slot if the direct child or either pipe cannot be joined.
    """
    output = []
    overflow = threading.Event()
    io_error = threading.Event()
    close_error = threading.Event()

    def read_stdout():
        try:
            data = child.stdout.read(MAX_OUTPUT + 1)
            output.append(data)
            if len(data) > MAX_OUTPUT:
                overflow.set()
        except (OSError, ValueError):
            io_error.set()
        finally:
            try:
                child.stdout.close()
            except (OSError, ValueError):
                close_error.set()
                io_error.set()

    def write_stdin():
        try:
            if child.stdin.write(raw) != len(raw):
                io_error.set()
        except (OSError, ValueError):
            io_error.set()
        finally:
            try:
                child.stdin.close()
            except (OSError, ValueError):
                close_error.set()
                io_error.set()

    threads = [threading.Thread(target=read_stdout, daemon=True),
               threading.Thread(target=write_stdin, daemon=True)]
    pipes_not_handed_off = [child.stdout, child.stdin]
    attempted = []
    launch_complete = False
    reason = None
    try:
        for index, thread in enumerate(threads):
            # A failed start can still have started the thread. Never close
            # that pipe from this thread once its hand-off was attempted.
            pipes_not_handed_off[index] = None
            attempted.append(thread)
            thread.start()
        launch_complete = True
        while True:
            if overflow.is_set():
                reason = "CHILD_OUTPUT_LIMIT"
                break
            if io_error.is_set():
                reason = "CHILD_IO_FAILURE"
                break
            if child.poll() is not None and all(not thread.is_alive() for thread in threads):
                break
            if time.monotonic() >= deadline:
                reason = "TOTAL_DEADLINE_EXCEEDED"
                break
            time.sleep(0.01)
    except Exception:
        reason = "CHILD_IO_FAILURE"
    finally:
        # This also runs for KeyboardInterrupt/SystemExit while the coordinator
        # is waiting. The handle belongs only to the child started above.
        try:
            should_kill = child.poll() is None
        except OSError:
            # A failed poll is not evidence that the child exited.
            should_kill = True
        if should_kill:
            try:
                child.kill()
            except OSError:
                pass
        try:
            child.wait(timeout=_CLEANUP_WAIT_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            pass
        for stream in pipes_not_handed_off:
            if stream is not None:
                try:
                    stream.close()
                except (OSError, ValueError):
                    close_error.set()
        join_until = time.monotonic() + _CLEANUP_WAIT_SECONDS
        for thread in attempted:
            if thread.ident is not None:
                thread.join(timeout=max(0.0, join_until - time.monotonic()))

    try:
        reaped = child.poll() is not None
    except OSError:
        reaped = False
    joined = launch_complete and all(not thread.is_alive() for thread in threads) and not close_error.is_set()
    if reason is None:
        if not reaped or not joined:
            reason = "CHILD_CLEANUP_UNVERIFIED"
        elif overflow.is_set():
            reason = "CHILD_OUTPUT_LIMIT"
        elif io_error.is_set():
            reason = "CHILD_IO_FAILURE"
        elif time.monotonic() >= deadline:
            reason = "TOTAL_DEADLINE_EXCEEDED"
    return (output[0] if output else b""), reason, reaped, joined


def relay(raw: bytes):
    try:
        request = validate(raw)
    except Rejected as error:
        return base(raw, error.reason)
    except (UnicodeError, RecursionError):
        return base(raw, "INVALID_REQUEST")
    if not _CHILD_SLOT.acquire(blocking=False):
        return base(raw, "CHILD_BUSY_OR_CLEANUP_UNCONFIRMED", request)
    started = time.monotonic()
    deadline = started + request["profile"]["timeout_s"]
    child_env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
    cleanup_confirmed = False
    child = None
    try:
        try:
            child = subprocess.Popen([sys.executable, "-I", "-B", "-S", "-X", "utf8", str(Path(__file__).resolve()),
                                      "--_owned-network-child"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, env=child_env,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
        except OSError:
            # Popen can fail after creating a process but before returning its
            # handle. We cannot confirm cleanup, so retain the instance slot.
            result = base(raw, "CHILD_SPAWN_FAILED", request)
            result.update(owned_child_stop_state="UNKNOWN", pipe_threads="UNKNOWN", provider_stop_state="UNKNOWN")
            return result
        stdout, reason, reaped, joined = collect_owned_child(child, raw, deadline)
        cleanup_confirmed = reaped and joined
        if reason is not None:
            result = base(raw, reason, request)
            result.update(owned_child_stop_state="REAPED" if reaped else "UNKNOWN",
                          pipe_threads="JOINED" if joined else "UNKNOWN", provider_stop_state="UNKNOWN")
            return result
        if child.returncode not in (0, 2):
            result = base(raw, "CHILD_RESPONSE_INVALID", request)
        else:
            try:
                result = decode_json(stdout)
            except Rejected:
                result = None
            if (type(result) is not dict or result.get("schema") != RESULT_SCHEMA
                    or result.get("request_sha256") != digest(raw) or result.get("request_id") != request["request_id"]
                    or result.get("stage") != request["stage"] or result.get("requested_model") != request["profile"]["model"]
                    or result.get("status") not in {"CANDIDATE", "REJECTED"}
                    or (result["status"] == "CANDIDATE") != (child.returncode == 0)):
                result = base(raw, "CHILD_RESPONSE_INVALID", request)
        result["owned_child_stop_state"] = "REAPED"
        result["pipe_threads"] = "JOINED"
        return result
    finally:
        if child is not None and not cleanup_confirmed:
            # Protect the entire interval after Popen returned its handle,
            # including an interruption before the collector is entered. Only
            # the returned direct child belongs to this module. Cleanup here
            # cannot attest pipe-thread termination, so retain the slot.
            try:
                should_kill = child.poll() is None
            except BaseException:
                should_kill = True
            if should_kill:
                try:
                    child.kill()
                except BaseException:
                    pass
            try:
                child.wait(timeout=_CLEANUP_WAIT_SECONDS)
            except BaseException:
                pass
        if cleanup_confirmed:
            _CHILD_SLOT.release()


def main():
    args = sys.argv[1:]
    raw = sys.stdin.buffer.read(MAX_INPUT + 1)
    if args == ["--_owned-network-child"]:
        try:
            request = validate(raw)
            result = network_child(raw, request)
        except Rejected as error:
            result = base(raw, error.reason)
        except Exception:
            result = base(raw, "CHILD_INTERNAL_FAILURE")
    elif not args:
        result = relay(raw)
    else:
        result = base(raw, "INVALID_ARGUMENTS")
    encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_OUTPUT:
        encoded = json.dumps(base(raw, "OUTPUT_BUDGET"), separators=(",", ":")).encode("utf-8")
        result = {"status": "REJECTED"}
    sys.stdout.buffer.write(encoded + b"\n")
    return 0 if result["status"] == "CANDIDATE" else 2


if __name__ == "__main__":
    sys.exit(main())
