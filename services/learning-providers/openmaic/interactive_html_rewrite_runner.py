"""Private, unregistered owned-child runner for the limited HTML candidate.

This module provides no HTTP/Core endpoint and is not an OS sandbox. The Node
path is trusted host configuration, never a path selected by an HTML request.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import stat
import subprocess
import threading
import time
from typing import Any


SCHEMA = "archeaxis.openmaic-interactive-html-rewrite/v1"
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
NODE_BYTES = 93_580_104
WORKER = Path(__file__).absolute().with_name("interactive-html-rewrite-worker.mjs")
WORKER_SHA256 = "036a4355d9615a59e606d5cee6a2445aa0077ffec5cc9d8c33a8340feb89c927"
SOURCE_SHA256 = "fe4637cc0e32cd557dcdc285017008cfe741e7799478a9c9ec102cc97194b1fe"
MAX_HTML = 8_192
MAX_STDIN = 16_384
MAX_STDOUT = 65_536
MAX_STDERR = 8_192
MAX_OUTPUT_HTML = 16_384
# Only this module instance is limited. If child or pipe cleanup is uncertain,
# retain the slot and fail closed until the host replaces this module instance.
_SLOT = threading.BoundedSemaphore(1)
POSSIBLE_EFFECTS = ["INTEGRITY_REMOVAL", "CROSSORIGIN_CHANGE", "TEXT_LINE_ENDING_CHANGE",
                    "UNSCANNED_REFERENCES", "SILENT_PARSE_FAILURE"]
CHILD_ERRORS = frozenset({
    "NODE_IDENTITY_MISMATCH", "ENVIRONMENT_OVERRIDE", "INVALID_REQUEST", "UNSUPPORTED_HTML",
    "UNSUPPORTED_SOURCE_MAP", "INPUT_TIMEOUT", "INPUT_TOO_LARGE", "OUTPUT_TOO_LARGE",
    "UPSTREAM_IDENTITY_MISMATCH", "DEPENDENCY_IDENTITY_MISMATCH", "UNLISTED_IMPORT",
    "UPSTREAM_UNEXPECTED_RESULT", "PATCH_MISMATCH", "INTERNAL_FAILURE",
})
COMMON_KEYS = frozenset({
    "schema", "status", "scope", "privacy", "expected_source_sha256", "source_verification",
    "node_version", "resource_availability", "network_isolation", "security_sanitizer",
    "core_authorization", "unmatched_hosts_scope", "original_preservation",
})
SUCCESS_KEYS = COMMON_KEYS | frozenset({
    "request_id", "input_sha256", "input_bytes", "output_sha256", "output_bytes",
    "output_utf8_base64", "patch", "upstream_unmatched_external_hosts", "possible_effects",
})


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
    """Bound file reads; this does not prevent replacement after the check."""
    _check(deadline, cancelled)
    try:
        if not path.is_absolute() or path.is_symlink():
            return False
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size > limit:
            return False
        if exact_size is not None and info.st_size != exact_size:
            return False
        h = hashlib.sha256()
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
                h.update(chunk)
        return total == info.st_size and h.hexdigest() == expected
    except (OSError, ValueError):
        return False


def _metadata() -> dict[str, Any]:
    return {"direct_child": "NOT_STARTED", "exit_code": None,
            "termination_requested": False, "pipe_threads": "NOT_STARTED",
            "descendants": "UNKNOWN", "network_isolation": "NOT_ESTABLISHED"}


def _reject(code: str, process: dict[str, Any]) -> dict[str, Any]:
    # Never include input, output, error text, command line, or stderr here.
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


def _decode_base64(value: Any) -> bytes:
    if not isinstance(value, str):
        raise ValueError("invalid base64")
    raw = base64.b64decode(value, validate=True)
    if base64.b64encode(raw).decode("ascii") != value:
        raise ValueError("invalid base64")
    return raw


def _validate_reply(raw: bytes, original: bytes, request_id: str) -> tuple[str, Any]:
    """Independently check the bounded reply, original hash and byte patch."""
    try:
        obj = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_no_duplicates,
                         parse_constant=_bad_constant)
        if not isinstance(obj, dict):
            raise ValueError("bad response")
        status = obj.get("status")
        keys = SUCCESS_KEYS if status == "OBSERVED_CANDIDATE" else COMMON_KEYS | {"error_code"}
        if set(obj) != keys or status not in {"OBSERVED_CANDIDATE", "REJECTED"}:
            raise ValueError("bad response")
        fixed = {"schema": SCHEMA, "scope": "CALLER_SUPPLIED_UNVERIFIED",
                 "privacy": "PRIVATE_INPUT_AND_OUTPUT", "expected_source_sha256": SOURCE_SHA256,
                 "source_verification": "VERIFIED_SELECTED_MEMBERS" if status == "OBSERVED_CANDIDATE" else "NOT_ASSERTED",
                 "node_version": "24.21.0", "resource_availability": "NOT_VERIFIED",
                 "network_isolation": "NOT_ESTABLISHED", "security_sanitizer": False,
                 "core_authorization": "NOT_ESTABLISHED", "unmatched_hosts_scope": "PARTIAL_REFERENCES_ONLY",
                 "original_preservation": "CALLER_RESPONSIBILITY"}
        if any(obj.get(k) != v or (v is False and obj.get(k) is not False) for k, v in fixed.items()):
            raise ValueError("bad response")
        if status == "REJECTED":
            code = obj["error_code"]
            if not isinstance(code, str) or code not in CHILD_ERRORS:
                raise ValueError("bad response")
            return status, code
        if (obj["request_id"] != request_id or type(obj["input_bytes"]) is not int or
                obj["input_bytes"] != len(original) or
                obj["input_sha256"] != hashlib.sha256(original).hexdigest()):
            raise ValueError("bad response")
        output = _decode_base64(obj["output_utf8_base64"])
        if (len(output) > MAX_OUTPUT_HTML or type(obj["output_bytes"]) is not int or
                obj["output_bytes"] != len(output) or
                obj["output_sha256"] != hashlib.sha256(output).hexdigest()):
            raise ValueError("bad response")
        output.decode("utf-8", errors="strict")
        patch = obj["patch"]
        if not isinstance(patch, dict) or set(patch) != {"unit", "start", "delete_bytes", "insert_base64"}:
            raise ValueError("bad patch")
        start, deleted = patch["start"], patch["delete_bytes"]
        if (patch["unit"] != "bytes" or type(start) is not int or type(deleted) is not int or
                start < 0 or deleted < 0 or start + deleted > len(original)):
            raise ValueError("bad patch")
        inserted = _decode_base64(patch["insert_base64"])
        if original[:start] + inserted + original[start + deleted:] != output:
            raise ValueError("bad patch")
        prefix = 0
        while prefix < min(len(original), len(output)) and original[prefix] == output[prefix]:
            prefix += 1
        suffix = 0
        while (suffix < len(original) - prefix and suffix < len(output) - prefix and
               original[len(original) - 1 - suffix] == output[len(output) - 1 - suffix]):
            suffix += 1
        if start != prefix or deleted != len(original) - prefix - suffix:
            raise ValueError("bad patch")
        hosts = obj["upstream_unmatched_external_hosts"]
        if (not isinstance(hosts, dict) or
                any(not isinstance(k, str) or not k or type(v) is not int or v < 1 for k, v in hosts.items()) or
                obj["possible_effects"] != POSSIBLE_EFFECTS):
            raise ValueError("bad response")
        return status, obj
    except (ValueError, TypeError, KeyError, OverflowError):
        return "REJECTED", "INVALID_WORKER_REPLY"


def run_candidate(html: bytes, *, node_executable: str | Path,
                  cancelled: threading.Event | None = None,
                  timeout_seconds: float = 30.0) -> dict[str, Any]:
    """Run one candidate. Caller must retain original bytes and protect result.

    ``node_executable`` must come from trusted host configuration. The caller
    must bound calls across processes and module instances. An event is a
    best-effort cancellation signal; it is not a Core authorization fence.
    """
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
        if (type(html) is not bytes or len(html) > MAX_HTML or
                isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or
                not math.isfinite(timeout_seconds) or not 0.25 <= timeout_seconds <= 60):
            return _reject("INVALID_ARGUMENT", process)
        deadline = time.monotonic() + timeout_seconds
        _check(deadline, cancelled)
        node = Path(node_executable)
        if not _identity(node, NODE_SHA256, NODE_BYTES, deadline, cancelled, NODE_BYTES):
            return _reject("NODE_IDENTITY_MISMATCH", process)
        if not _identity(WORKER, WORKER_SHA256, 1_000_000, deadline, cancelled):
            return _reject("WORKER_IDENTITY_MISMATCH", process)
        request_id = secrets.token_hex(16)
        payload = (json.dumps({"schema": SCHEMA, "request_id": request_id,
                               "html_utf8_base64": base64.b64encode(html).decode("ascii")},
                              separators=(",", ":")) + "\n").encode("ascii")
        if len(payload) > MAX_STDIN:
            return _reject("INVALID_ARGUMENT", process)
        _check(deadline, cancelled)
        env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        # Popen can raise after creating a process but before handing us its
        # handle. Once the call begins, a spawn failure is not proof of no child.
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
                child.stdin.write(payload)
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
            # start() can launch its thread and then raise: never close that
            # pipe from this thread, even when start() did not return.
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
            except OSError:
                pass
        try:
            code = child.wait(timeout=1)
            process["direct_child"] = "REAPED"
            process["exit_code"] = code
        except (OSError, subprocess.TimeoutExpired):
            return _reject(reason or "CHILD_REAP_UNKNOWN", process)
        # A descendant can retain a pipe. Bound the wait and do not claim cleanup.
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
        status, content = _validate_reply(streams["stdout"], html, request_id)
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
                    except OSError:
                        pass
                child.wait(timeout=1)
                process["direct_child"] = "REAPED"
                process["exit_code"] = child.returncode
            except (OSError, subprocess.TimeoutExpired):
                process["direct_child"] = "UNKNOWN"
            if not launch_complete:
                # Close only pipes never handed to start(). Attempted starts
                # remain unknown; do not close those pipes across threads.
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
