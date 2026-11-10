"""One bounded local-model call for the OpenMAIC outline generate route.

The OpenMAIC outline worker owns the prompts and the delivery callback; this
worker only sends the captured system/user pair to the local text model and
returns the model's final text. Core owns the ownership chain: it captures the
prompt binding, dispatches this call, then replays the reply through the Node
outline worker. Nothing here starts Node, persists anything or promotes text.

The HTTP client is not re-implemented here: `machine/worker_machine_answer.py`
already provides the numeric-loopback-only opener with no inherited proxy or
redirects, the bounded response reader and the reported-usage reader. This
module loads that file by path under isolated Python (`-I`) and calls those
functions; it only builds the request body, because this route must send the
system and user prompts as two separate messages.

Every non-success is named, no text is invented, no cloud fallback and no
automatic retry: `MODEL_UNAVAILABLE`, `MODEL_TIMEOUT`, `MODEL_REJECTED`,
`NO_FINAL_ANSWER` and `INVALID_MODEL_OUTPUT`. `MODEL_REJECTED` means the lane
answered and refused the request (for example a prompt larger than the model's
loaded context); its diagnostic carries only the HTTP status and integer engine
fields, never prompt text.

Usage: one bounded JSON request line on stdin, one JSON result line on stdout.
Exit 0 only for `REPLY`, 2 for every named failure (the Core preserves it).
"""

from __future__ import annotations

import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

SCHEMA = "archeaxis.openmaic-outline-model-request/v1"
REPLY_SCHEMA = "archeaxis.openmaic-outline-model-reply/v1"
ENGINE = "python-worker-openmaic-outline-local-model"
ENGINE_VERSION = "0.1.0"
# The identity advertised in the sidecar handshake for this route.
WORKER_IDENTITY = "python-worker-openmaic-outline-local-model-ndjson"
CAPABILITY = "course.openmaic.outline-model"
MAX_INPUT = 256_000
MAX_OUTPUT = 1_000_000
# The donor's own per-prompt bound (outline-prompt-guard.mjs).
MAX_PROMPT_BYTES = 200_000
# The reply budget the Node replay request accepts.
MAX_REPLY_BYTES = 120_000
DEFAULT_TIMEOUT_S = 30
MAX_TIMEOUT_S = 120
INTERACTIVE_SCENE_TIMEOUT_S = 200
DEEPTUTOR_CHOICE_SCHEMA_KIND = "deeptutor_choice_json_schema"
REQUEST_KEYS = {"schema", "system", "user", "model", "timeout_s", "request_kind"}
MAX_REJECTION_BYTES = 8192


def _rejection_diagnostic(error: urllib.error.HTTPError) -> dict:
    """Bounded, text-free description of a refused request.

    Only the HTTP status and integer engine fields are carried out: an engine
    message can quote the prompt, so it never leaves this process.
    """
    diagnostic = {"error_type": "HTTPError", "http_status": int(error.code)}
    try:
        payload = json.loads(error.read(MAX_REJECTION_BYTES).decode("utf-8", "strict"))
    except (OSError, ValueError, UnicodeError, http.client.HTTPException):
        return diagnostic
    engine = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(engine, str):
        # Some lanes prefix the engine's JSON with prose ("... returned 400: {...}").
        start, end = engine.find("{"), engine.rfind("}")
        if start < 0 or end <= start:
            return diagnostic
        try:
            engine = json.loads(engine[start:end + 1])
        except ValueError:
            return diagnostic
        engine = engine.get("error") if isinstance(engine, dict) else None
    if not isinstance(engine, dict):
        return diagnostic
    if type(engine.get("code")) is int:
        diagnostic["engine_code"] = engine["code"]
    inner = engine.get("error") if isinstance(engine.get("error"), dict) else engine
    for name in ("n_prompt_tokens", "n_ctx"):
        if type(inner.get(name)) is int:
            diagnostic[name] = inner[name]
    return diagnostic


def _machine():
    """Load the hardened local-model transport by file path; never a second client."""
    path = Path(__file__).resolve().parent.parent / "machine" / "worker_machine_answer.py"
    spec = importlib.util.spec_from_file_location("openmaic_outline_machine_answer", path)
    if spec is None or spec.loader is None:
        raise ImportError("local model worker is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _receipt(status: str, reason: str | None = None, **fields) -> dict:
    return {
        "schema": REPLY_SCHEMA, "status": status, "reason": reason,
        "content": None, "content_sha256": None, "content_bytes": None,
        "model": None, "requested_model": None, "observed_model": None,
        "finish_reason": None, "usage": None, "usage_status": "UNKNOWN",
        "elapsed_ms": 0, "max_tokens": None, "timeout_s": None,
        "model_call": "INVOKED", "network_performed": False,
        "network_scope": "LOOPBACK_LOCAL_MODEL_ONLY",
        "model_output_verification": "UNREVIEWED_LOCAL_MODEL_TEXT",
        "persisted": False, "core_task": "NOT_CONNECTED",
        "core_authorization": "NOT_ESTABLISHED", "human_review_required": True,
        "engine": ENGINE, "engine_version": ENGINE_VERSION,
        **fields,
    }


def _prompt(value) -> bool:
    if not isinstance(value, str) or "\0" in value:
        return False
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return len(encoded) <= MAX_PROMPT_BYTES


def _model_selection(value) -> bool:
    return (isinstance(value, str) and value == value.strip() and 0 < len(value) <= 256
            and not any(ord(char) < 32 or ord(char) == 127 for char in value))


def _request_valid(request) -> bool:
    if not isinstance(request, dict) or not set(request) <= REQUEST_KEYS:
        return False
    if request.get("schema") != SCHEMA or not _prompt(request.get("system")) \
            or not _prompt(request.get("user")):
        return False
    if "model" in request and not _model_selection(request["model"]):
        return False
    if "request_kind" in request and request["request_kind"] not in (
            "interactive_scene", DEEPTUTOR_CHOICE_SCHEMA_KIND):
        return False
    if "timeout_s" in request:
        value = request["timeout_s"]
        limit = INTERACTIVE_SCENE_TIMEOUT_S if request.get("request_kind") == "interactive_scene" else MAX_TIMEOUT_S
        if type(value) is not int or not 1 <= value <= limit:
            return False
    return True


def _body(protocol: str, model: str, system: str, user: str, max_tokens: int) -> dict:
    """Only the two captured messages: the route sends no other role or content."""
    if protocol == "openai":
        return {"model": model, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
    # The explicit legacy protocol carries its system prompt in its own field.
    return {"model": model, "prompt": user, "system": system, "stream": False,
            "options": {"num_predict": max_tokens}}


def _deeptutor_choice_response_format() -> dict:
    """One fixed, bounded schema; callers cannot supply arbitrary grammar."""
    def obj(properties):
        return {"type": "object", "properties": properties,
                "required": list(properties), "additionalProperties": False}
    def string():
        return {"type": "string"}
    return {"type": "json_schema", "json_schema": {
        "name": "archeaxis_response", "strict": True, "schema": obj({
            "question_type": {"type": "string", "enum": ["choice"]},
            "question": string(),
            "options": obj({key: string() for key in "ABCD"}),
            "correct_answer": {"type": "string", "enum": list("ABCD")},
            "explanation": string(),
        })}}


def _finish_reason_error(value) -> str | None:
    """A model reply is complete only when the provider says it stopped normally."""
    if value is None or value == "":
        return "MODEL_FINISH_REASON_UNKNOWN"
    if not isinstance(value, str):
        return "MODEL_FINISH_REASON_INVALID"
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return "MODEL_RESPONSE_INVALID"
    if value == "stop":
        return None
    if value in {"length", "content_filter", "tool_calls", "function_call", "error"}:
        return "MODEL_NONSTOP"
    return "MODEL_FINISH_REASON_INVALID"


def _answer(payload: dict, protocol: str):
    """The final text, finish reason, and independently observed model identity."""
    if protocol == "openai":
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            return None, "MODEL_RESPONSE_SHAPE", None
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            return None, "MODEL_RESPONSE_SHAPE", None
        calls = message.get("tool_calls")
        if calls is not None and (not isinstance(calls, list) or calls):
            return None, "MODEL_TOOL_CALL_UNSUPPORTED", None
        if message.get("function_call") is not None:
            return None, "MODEL_TOOL_CALL_UNSUPPORTED", None
        content, reasoning = message.get("content"), message.get("reasoning_content")
        if content is not None and not isinstance(content, str):
            return None, "MODEL_CONTENT_INVALID", None
        if reasoning is not None and not isinstance(reasoning, str):
            return None, "MODEL_CONTENT_INVALID", None
        finish = choice.get("finish_reason")
        finish_error = _finish_reason_error(finish)
        if finish_error is not None:
            return None, finish_error, None
        observed = payload.get("model")
        observed = observed.strip() if isinstance(observed, str) and observed.strip() else None
        if not (content or "").strip():
            reason = "REASONING_ONLY" if (reasoning or "").strip() else "EMPTY_CONTENT"
            return None, reason, observed
        return {"content": content, "finish_reason": finish or None, "observed": observed}, None, None
    text = payload.get("response")
    if not isinstance(text, str):
        return None, "MODEL_RESPONSE_SHAPE", None
    if payload.get("done") is not True:
        return None, "MODEL_COMPLETION_UNCONFIRMED", None
    finish = payload.get("done_reason")
    finish_error = _finish_reason_error(finish)
    if finish_error is not None:
        return None, finish_error, None
    observed = payload.get("model")
    observed = observed.strip() if isinstance(observed, str) and observed.strip() else None
    if not text.strip():
        return None, "EMPTY_CONTENT", observed
    return {"content": text, "finish_reason": finish or None, "observed": observed}, None, None


def process(request) -> dict:
    if not _request_valid(request):
        return _receipt("INVALID_MODEL_OUTPUT",
                        "request contract or prompt budget rejected")
    try:
        machine = _machine()
    except ImportError:
        return _receipt("MODEL_UNAVAILABLE", "local model worker is unavailable")

    timeout_s = request.get("timeout_s", DEFAULT_TIMEOUT_S)
    max_tokens = machine.DEFAULT_MAX_TOKENS
    system, user = request["system"], request["user"]
    started = time.monotonic()
    try:
        endpoint = machine._endpoint()
    except Exception as error:  # noqa: BLE001 - an unreadable lane declaration is not a lane
        return _receipt("MODEL_UNAVAILABLE", "MODEL_ENDPOINT_UNRESOLVED",
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                        diagnostic={"error_type": type(error).__name__})
    model = request.get("model") or endpoint["model"]
    response_format = None
    response_format_sha256 = None
    if request.get("request_kind") == DEEPTUTOR_CHOICE_SCHEMA_KIND:
        if endpoint["protocol"] != "openai":
            return _receipt("MODEL_REJECTED", "MODEL_STRUCTURED_PROTOCOL_UNSUPPORTED",
                            model=model, requested_model=model,
                            endpoint=endpoint["base"], protocol=endpoint["protocol"],
                            network_performed=False)
        response_format = _deeptutor_choice_response_format()
        canonical = json.dumps(response_format, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
        response_format_sha256 = hashlib.sha256(canonical).hexdigest()
    try:
        body_fields = _body(endpoint["protocol"], model, system, user, max_tokens)
        if response_format is not None:
            body_fields["response_format"] = response_format
        body = json.dumps(body_fields, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError):
        return _receipt("INVALID_MODEL_OUTPUT", "request body could not be encoded")
    path = "/chat/completions" if endpoint["protocol"] == "openai" else "/api/generate"
    http_request = urllib.request.Request(
        f"{endpoint['base']}{path}", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        # Endpoint validation happens inside this opener, before any connection.
        response = machine.local_urlopen(http_request, timeout=timeout_s)
    except ValueError as error:
        # Only loopback is accepted, and a refused endpoint is configuration, not a reply.
        return _receipt("MODEL_UNAVAILABLE", "MODEL_ENDPOINT_INVALID",
                        model=model, requested_model=model,
                        endpoint=endpoint["base"], protocol=endpoint["protocol"],
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                        diagnostic={"error_type": type(error).__name__})
    except urllib.error.HTTPError as error:
        # A 4xx is the lane refusing this request (a context overflow or an
        # unsupported parameter): an operator-visible capacity decision, not an
        # unreachable endpoint. A 5xx is the lane itself failing healthy delivery.
        if error.code >= 500:
            return _receipt("MODEL_UNAVAILABLE", "MODEL_ENDPOINT_UNHEALTHY",
                            model=model, requested_model=model,
                            endpoint=endpoint["base"], protocol=endpoint["protocol"],
                            elapsed_ms=int((time.monotonic() - started) * 1000),
                            network_performed=True,
                            diagnostic={"error_type": "HTTPError", "http_status": int(error.code)})
        return _receipt("MODEL_REJECTED", "MODEL_HTTP_REJECTED",
                        model=model, requested_model=model,
                        endpoint=endpoint["base"], protocol=endpoint["protocol"],
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                        network_performed=True,
                        diagnostic=_rejection_diagnostic(error))
    except Exception as error:  # noqa: BLE001 - unreachable/timed-out lanes stay local failures
        timed_out = isinstance(error, TimeoutError) or (
            isinstance(error, urllib.error.URLError)
            and not isinstance(error, urllib.error.HTTPError)
            and isinstance(error.reason, TimeoutError))
        return _receipt(
            "MODEL_TIMEOUT" if timed_out else "MODEL_UNAVAILABLE",
            "MODEL_REQUEST_TIMEOUT" if timed_out else "MODEL_ENDPOINT_UNREACHABLE",
            model=model, requested_model=model,
            endpoint=endpoint["base"], protocol=endpoint["protocol"],
            elapsed_ms=int((time.monotonic() - started) * 1000),
            # Before response headers, the transport cannot tell whether the
            # loopback peer received the request; do not assert it did not.
            network_performed=None,
            diagnostic={"error_type": type(error).__name__})
    try:
        with response:
            payload = machine.read_model_json(response)
    except TimeoutError as error:
        # Headers arrived, but the response body did not finish before the
        # socket deadline. This is a timeout, not evidence of malformed JSON.
        return _receipt("MODEL_TIMEOUT", "MODEL_RESPONSE_TIMEOUT",
                        model=model, requested_model=model,
                        endpoint=endpoint["base"], protocol=endpoint["protocol"],
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                        network_performed=True,
                        diagnostic={"error_type": type(error).__name__})
    except (ValueError, TypeError, UnicodeError, OSError, http.client.HTTPException) as error:
        return _receipt("INVALID_MODEL_OUTPUT", "MODEL_RESPONSE_INVALID",
                        model=model, requested_model=model,
                        endpoint=endpoint["base"], protocol=endpoint["protocol"],
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                        network_performed=True,
                        diagnostic={"error_type": type(error).__name__})
    elapsed = time.monotonic() - started
    if elapsed >= timeout_s:
        # A complete body that arrives after the budget is a timeout, not a reply.
        return _receipt("MODEL_TIMEOUT", "MODEL_RESPONSE_AFTER_DEADLINE",
                        model=model, requested_model=model,
                        endpoint=endpoint["base"], protocol=endpoint["protocol"],
                        network_performed=True,
                        elapsed_ms=int(elapsed * 1000))
    answer, reason, observed = _answer(payload, endpoint["protocol"])
    try:
        if answer is None:
            if observed is not None:
                observed.encode("utf-8")
            encoded_content = None
        else:
            encoded_content = answer["content"].encode("utf-8")
            for value in (answer["finish_reason"], answer["observed"]):
                if value is not None:
                    value.encode("utf-8")
    except UnicodeEncodeError:
        # JSON can contain escaped unpaired surrogates. Do not misreport an
        # invalid model response as an invalid input or echo its contents.
        return _receipt("INVALID_MODEL_OUTPUT", "MODEL_RESPONSE_INVALID",
                        model=model, requested_model=model,
                        endpoint=endpoint["base"], protocol=endpoint["protocol"],
                        network_performed=True,
                        elapsed_ms=int((time.monotonic() - started) * 1000))
    if answer is None:
        return _receipt("NO_FINAL_ANSWER" if reason in ("EMPTY_CONTENT", "REASONING_ONLY")
                        else "INVALID_MODEL_OUTPUT", reason,
                        model=model, requested_model=model, observed_model=observed,
                        endpoint=endpoint["base"], protocol=endpoint["protocol"],
                        max_tokens=max_tokens, timeout_s=timeout_s,
                        network_performed=True,
                        elapsed_ms=int(elapsed * 1000))
    content = answer["content"]
    if len(encoded_content) > MAX_REPLY_BYTES:
        # A reply the replay contract cannot carry is refused, never truncated.
        return _receipt("INVALID_MODEL_OUTPUT", "MODEL_REPLY_BUDGET",
                        model=model, requested_model=model, observed_model=answer["observed"],
                        finish_reason=answer["finish_reason"],
                        endpoint=endpoint["base"], protocol=endpoint["protocol"],
                        max_tokens=max_tokens, timeout_s=timeout_s,
                        network_performed=True,
                        elapsed_ms=int(elapsed * 1000))
    usage = machine.reported_usage(payload, endpoint["protocol"])
    return _receipt("REPLY", None,
                    content=content,
                    content_sha256=hashlib.sha256(encoded_content).hexdigest(),
                    content_bytes=len(encoded_content),
                    model=model, requested_model=model, observed_model=answer["observed"],
                    finish_reason=answer["finish_reason"],
                    usage=usage, usage_status="REPORTED" if usage is not None else "UNKNOWN",
                    max_tokens=max_tokens, timeout_s=timeout_s,
                    elapsed_ms=int(elapsed * 1000),
                    endpoint=endpoint["base"], protocol=endpoint["protocol"],
                    network_performed=True,
                    **({"response_format_sha256": response_format_sha256}
                       if response_format_sha256 is not None else {}))


def _bounded(result: dict) -> dict:
    if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_OUTPUT:
        return _receipt("INVALID_MODEL_OUTPUT", "RESULT_EXCEEDS_BOUND")
    return result


def main() -> int:
    if sys.argv[1:] == ["--hello"]:
        print(json.dumps({"schema": "archeaxis.derived-worker-hello/v1",
                          "capability": CAPABILITY, "version": 1,
                          "model_call": "NOT_INVOKED", "network_performed": False}))
        return 0
    if "--staging-root" in sys.argv:
        import argparse

        candidates = (
            Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py",
            Path(__file__).resolve().parents[2] / "services" / "python-workers" / "transport"
            / "text_ndjson.py",
        )
        transport_path = next((p for p in candidates if p.is_file()), candidates[0])
        spec = importlib.util.spec_from_file_location("openmaic_outline_model_transport",
                                                      transport_path)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing"}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        sidecar = argparse.ArgumentParser(description=__doc__)
        sidecar.add_argument("--staging-root", type=Path, required=True)
        sidecar.add_argument("--artifact-root", type=Path, default=None)
        args = sidecar.parse_args()
        return transport.serve_stdio(WORKER_IDENTITY, [CAPABILITY], args.staging_root,
                                     args.artifact_root)
    raw = sys.stdin.buffer.readline(MAX_INPUT + 1)
    try:
        if len(raw) > MAX_INPUT:
            raise ValueError("input bound")
        result = _bounded(process(json.loads(raw)))
    except (ValueError, TypeError, RecursionError, UnicodeError):
        result = _receipt("INVALID_MODEL_OUTPUT", "invalid bounded JSON request")
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] == "REPLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
