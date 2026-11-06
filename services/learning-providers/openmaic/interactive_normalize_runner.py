"""Private unregistered owned-child runner for the interactive HTML normalizer.

No product route, Core authorization, renderer or persistence. The Node path is
trusted host configuration, never request data. Exactly one call runs at a time.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import threading
import time
from typing import Any


SCHEMA = "archeaxis.openmaic-interactive-normalize/v1"
RESULT = SCHEMA
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
NODE_BYTES = 93_580_104
WORKER = Path(__file__).absolute().with_name("interactive-normalize-worker.mjs")
WORKER_SHA256 = "a59d60c116bb168f184cf737e40f398bc36966e950f5f8d60523744a34f40826"
MAX_REPLY = 131_072
MAX_STDIN = 262_144
MAX_STDOUT = 262_144
MAX_STDERR = 8_192
MAX_OUTPUT_HTML = 98_304
WIDGETS = frozenset({"simulation", "diagram", "code", "game", "visualization3d"})
STRATEGIES = frozenset({"COMPLETE_DOCUMENT", "FENCED_BLOCK", "TRIMMED_DOCUMENT"})
# Only this module instance is limited; an uncertain cleanup keeps it closed.
_SLOT = threading.BoundedSemaphore(1)
CHILD_ERRORS = frozenset({
    "NODE_IDENTITY_MISMATCH", "ENVIRONMENT_OVERRIDE", "INVALID_REQUEST", "UNSUPPORTED_WIDGET_TYPE",
    "INVALID_MODEL_HTML", "INPUT_TOO_LARGE", "OUTPUT_TOO_LARGE", "UPSTREAM_IDENTITY_MISMATCH",
    "DEPENDENCY_IDENTITY_MISMATCH", "UNLISTED_IMPORT", "UPSTREAM_UNEXPECTED_RESULT", "INTERNAL_FAILURE",
})
FIXED = {
    "schema": SCHEMA, "scope": "CALLER_SUPPLIED_UNVERIFIED", "model_call": "NOT_INVOKED",
    "rendering_authorized": False, "security_sanitizer": False, "resource_availability": "NOT_VERIFIED",
    "network_isolation": "NOT_ESTABLISHED", "core_authorization": "NOT_ESTABLISHED",
    "external_references": "NOT_ENUMERATED", "script_validation": "CLASSIC_INLINE_COMPILED_NOT_EXECUTED",
    "original_preservation": "CALLER_RESPONSIBILITY",
}
COMMON = set(FIXED) | {"status", "node_version"}
SUCCESS = COMMON | {
    "request_id", "widget_type", "extraction_strategy", "input_sha256", "input_bytes",
    "extracted_sha256", "extracted_bytes", "output_sha256", "output_bytes",
    "output_utf8_base64", "katex_injected",
}


class _Stopped(Exception):
    def __init__(self, code: str):
        self.code = code


def _check(deadline: float, cancelled: threading.Event) -> None:
    if cancelled.is_set():
        raise _Stopped("CANCELLED")
    if time.monotonic() >= deadline:
        raise _Stopped("DEADLINE_EXCEEDED")


def _identity(path: Path, expected: str, limit: int, deadline: float,
              cancelled: threading.Event, exact_size: int | None = None) -> bool:
    """Bound reads; a replacement after this check is not detected."""
    _check(deadline, cancelled)
    try:
        if str(path).startswith(("\\\\", "//")) or not path.is_absolute() or path.is_symlink():
            return False
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size > limit:
            return False
        if exact_size is not None and info.st_size != exact_size:
            return False
        digest = hashlib.sha256()
        total = 0
        with path.open("rb") as stream:
            while True:
                _check(deadline, cancelled)
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    return False
                digest.update(chunk)
        return total == info.st_size and digest.hexdigest() == expected
    except (OSError, ValueError):
        return False


def _metadata() -> dict[str, Any]:
    return {"direct_child": "NOT_STARTED", "exit_code": None, "termination_requested": False,
            "pipe_threads": "NOT_STARTED", "descendants": "UNKNOWN", "network_isolation": "NOT_ESTABLISHED"}


def _reject(code: str, process: dict[str, Any]) -> dict[str, Any]:
    return {"status": "REJECTED", "error_code": code, "process": process}


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


def _bad_constant(_value: str) -> None:
    raise ValueError("non-finite JSON")


def _request_parts(raw: bytes) -> tuple[str, str, bytes] | None:
    try:
        request = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_no_duplicates,
                             parse_constant=_bad_constant)
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        return None
    if not isinstance(request, dict) or set(request) != {"schema", "request_id", "widget_type",
                                                         "reply_utf8_base64"}:
        return None
    widget = request["widget_type"]
    request_id = request["request_id"]
    if not isinstance(widget, str) or not isinstance(request_id, str) or widget not in WIDGETS:
        return None
    if request["schema"] != SCHEMA or not isinstance(request["reply_utf8_base64"], str):
        return None
    try:
        reply = _decode_base64(request["reply_utf8_base64"])
    except (ValueError, TypeError):
        return None
    return widget, request_id, reply


def _validate_reply(raw: bytes, original: bytes, request_id: str, widget: str) -> tuple[str, Any]:
    try:
        obj = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_no_duplicates,
                         parse_constant=_bad_constant)
        if not isinstance(obj, dict) or any(obj.get(key) != value for key, value in FIXED.items()):
            raise ValueError("invalid reply")
        if obj.get("node_version") != "24.21.0":
            raise ValueError("invalid reply")
        if obj.get("status") == "REJECTED":
            if set(obj) != COMMON | {"error_code"} or obj["error_code"] not in CHILD_ERRORS:
                raise ValueError("invalid reply")
            return "REJECTED", obj["error_code"]
        if obj.get("status") != "OBSERVED_CANDIDATE" or set(obj) != SUCCESS:
            raise ValueError("invalid reply")
        if (obj["request_id"] != request_id or obj["widget_type"] != widget
                or obj["extraction_strategy"] not in STRATEGIES or type(obj["katex_injected"]) is not bool):
            raise ValueError("invalid reply")
        if (type(obj["input_bytes"]) is not int or obj["input_bytes"] != len(original)
                or obj["input_sha256"] != hashlib.sha256(original).hexdigest()):
            raise ValueError("invalid reply")
        output = _decode_base64(obj["output_utf8_base64"])
        if (len(output) > MAX_OUTPUT_HTML or type(obj["output_bytes"]) is not int
                or obj["output_bytes"] != len(output)
                or obj["output_sha256"] != hashlib.sha256(output).hexdigest()):
            raise ValueError("invalid reply")
        output.decode("utf-8", errors="strict")
        if type(obj["extracted_bytes"]) is not int or obj["extracted_bytes"] > MAX_REPLY:
            raise ValueError("invalid reply")
        if not isinstance(obj["extracted_sha256"], str) or len(obj["extracted_sha256"]) != 64:
            raise ValueError("invalid reply")
        return "OBSERVED_CANDIDATE", obj
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        return "REJECTED", "INVALID_WORKER_REPLY"


def _decode_base64(value: Any) -> bytes:
    if not isinstance(value, str):
        raise ValueError("invalid base64")
    raw = base64.b64decode(value, validate=True)
    if base64.b64encode(raw).decode("ascii") != value:
        raise ValueError("invalid base64")
    return raw


def run_candidate(request_json: bytes, *, node_executable: str | Path,
                  cancelled: threading.Event | None = None,
                  timeout_seconds: float = 30.0) -> dict[str, Any]:
    """Run one normalize candidate; the caller keeps the reply and the result."""
    process = _metadata()
    child: subprocess.Popen | None = None
    threads: list[threading.Thread] = []
    attempted_threads: list[threading.Thread] = []
    unhanded_pipes: list[Any] = []
    launch_complete = False
    io_error = threading.Event()
    close_error = threading.Event()
    if cancelled is None:
        cancelled = threading.Event()
    if not _SLOT.acquire(blocking=False):
        return _reject("BUSY_OR_CLEANUP_UNCONFIRMED", process)
    try:
        if (type(request_json) is not bytes or len(request_json) > MAX_REPLY or
                isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or
                not math.isfinite(timeout_seconds) or not 0.25 <= timeout_seconds <= 60):
            return _reject("INVALID_ARGUMENT", process)
        parts = _request_parts(request_json)
        if parts is None:
            return _reject("INVALID_ARGUMENT", process)
        widget, request_id, reply = parts
        if len(reply) > MAX_REPLY:
            return _reject("INVALID_ARGUMENT", process)
        deadline = time.monotonic() + timeout_seconds
        _check(deadline, cancelled)
        node = Path(node_executable)
        if not _identity(node, NODE_SHA256, NODE_BYTES, deadline, cancelled, NODE_BYTES):
            return _reject("NODE_IDENTITY_MISMATCH", process)
        if not _identity(WORKER, WORKER_SHA256, 1_000_000, deadline, cancelled):
            return _reject("WORKER_IDENTITY_MISMATCH", process)
        payload = request_json + b"\n"
        if len(payload) > MAX_STDIN:
            return _reject("INVALID_ARGUMENT", process)
        _check(deadline, cancelled)
        env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        process["direct_child"] = "UNKNOWN"
        process["pipe_threads"] = "UNKNOWN"
        child = subprocess.Popen([str(node), str(WORKER)], shell=False, cwd=str(WORKER.parent), env=env,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 close_fds=True, creationflags=flags)
        unhanded_pipes = [child.stdout, child.stderr, child.stdin]
        streams: dict[str, bytes] = {}
        overflow = threading.Event()

        def read_pipe(stream: Any, name: str, limit: int) -> None:
            try:
                data = stream.read(limit + 1)
                streams[name] = data
                if len(data) > limit:
                    overflow.set()
            except BaseException:
                io_error.set()
            finally:
                try:
                    stream.close()
                except BaseException:
                    close_error.set()
                    io_error.set()

        def write_pipe() -> None:
            try:
                offset = 0
                while offset < len(payload):
                    count = child.stdin.write(payload[offset:])
                    if type(count) is not int or count <= 0:
                        raise OSError("short pipe write")
                    offset += count
            except BaseException:
                io_error.set()
            finally:
                try:
                    child.stdin.close()
                except BaseException:
                    close_error.set()
                    io_error.set()

        threads = [threading.Thread(target=read_pipe, args=(child.stdout, "stdout", MAX_STDOUT), daemon=True),
                   threading.Thread(target=read_pipe, args=(child.stderr, "stderr", MAX_STDERR), daemon=True),
                   threading.Thread(target=write_pipe, daemon=True)]
        for index, thread in enumerate(threads):
            unhanded_pipes[index] = None
            attempted_threads.append(thread)
            thread.start()
        launch_complete = True
        reason: str | None = None
        while child.poll() is None:
            if cancelled.is_set():
                reason = "CANCELLED"
                break
            if time.monotonic() >= deadline:
                reason = "DEADLINE_EXCEEDED"
                break
            if overflow.is_set():
                reason = "OUTPUT_LIMIT_EXCEEDED"
                break
            if io_error.is_set():
                reason = "PIPE_IO_FAILED"
                break
            time.sleep(0.01)
        if reason is not None and child.poll() is None:
            process["termination_requested"] = True
            try:
                child.kill()
            except BaseException:
                pass
        try:
            code = child.wait(timeout=1)
            process["direct_child"] = "REAPED"
            process["exit_code"] = code
        except BaseException:
            return _reject(reason or "CHILD_REAP_UNKNOWN", process)
        join_until = time.monotonic() + 1.0
        for thread in threads:
            thread.join(timeout=max(0.0, join_until - time.monotonic()))
        if any(thread.is_alive() for thread in threads):
            return _reject(reason or "PIPE_CLEANUP_UNKNOWN", process)
        process["pipe_threads"] = "JOINED"
        if close_error.is_set():
            return _reject("PIPE_IO_FAILED", process)
        if cancelled.is_set():
            return _reject("CANCELLED", process)
        if reason is not None:
            return _reject(reason, process)
        if time.monotonic() >= deadline:
            return _reject("DEADLINE_EXCEEDED", process)
        if overflow.is_set():
            return _reject("OUTPUT_LIMIT_EXCEEDED", process)
        if io_error.is_set() or "stdout" not in streams or "stderr" not in streams:
            return _reject("PIPE_IO_FAILED", process)
        if code != 0:
            return _reject("WORKER_FAILED", process)
        status, content = _validate_reply(streams["stdout"], reply, request_id, widget)
        _check(deadline, cancelled)
        if status != "OBSERVED_CANDIDATE":
            return _reject(content, process)
        return {"status": status, "candidate": content, "process": process}
    except _Stopped as stopped:
        return _reject(stopped.code, process)
    except Exception:
        return _reject("INTERNAL_FAILURE", process)
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    process["termination_requested"] = True
                    try:
                        child.kill()
                    except BaseException:
                        pass
                child.wait(timeout=1)
                process["direct_child"] = "REAPED"
                process["exit_code"] = child.returncode
            except BaseException:
                process["direct_child"] = "UNKNOWN"
            if not launch_complete:
                for stream in unhanded_pipes:
                    if stream is not None:
                        try:
                            stream.close()
                        except BaseException:
                            close_error.set()
                            io_error.set()
                join_until = time.monotonic() + 1.0
                for thread in attempted_threads:
                    try:
                        if thread.ident is not None:
                            thread.join(timeout=max(0.0, join_until - time.monotonic()))
                    except BaseException:
                        io_error.set()
        if (process["direct_child"] == "NOT_STARTED" or
                (process["direct_child"] == "REAPED" and process["pipe_threads"] == "JOINED"
                 and not close_error.is_set())):
            _SLOT.release()
