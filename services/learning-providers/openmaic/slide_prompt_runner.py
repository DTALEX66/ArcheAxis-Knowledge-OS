"""Private unregistered owned-child adapter for the original slide prompt.

No product registration, HTTP route, Core authorization, model or persistence.
The explicit Node path is trusted host configuration, never request data.
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

SCHEMA = "archeaxis.openmaic-slide-prompt/v1"
RESULT = "archeaxis.openmaic-slide-prompt-result/v1"
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
NODE_BYTES = 93_580_104
WORKER = Path(__file__).absolute().with_name("slide-prompt-worker.mjs")
WORKER_SHA256 = "8034b902686eaf594d5e6527d1afccdbfbafa5a927460a1a23befa84039bdf84"
MAX_REQUEST = 16_384
MAX_STDIN = 32_768
MAX_STDOUT = 196_608
MAX_STDERR = 8_192
_SLOT = threading.BoundedSemaphore(1)
CHILD_ERRORS = frozenset({"NODE_IDENTITY_MISMATCH", "ENVIRONMENT_OVERRIDE", "INVALID_REQUEST",
    "INPUT_TOO_LARGE", "OUTPUT_TOO_LARGE", "UPSTREAM_IDENTITY_MISMATCH", "UNLISTED_IMPORT",
    "UNLISTED_TEMPLATE_READ", "UNEXPECTED_UPSTREAM_RESULT", "INTERNAL_FAILURE"})
FIXED = {"schema": RESULT, "scope": "CALLER_SUPPLIED_UNVERIFIED", "operation": "UPSTREAM_SLIDE_PROMPT_ONLY",
    "model_call": "NOT_INVOKED", "full_generation": "NOT_PERFORMED", "core_authorization": "NOT_ESTABLISHED",
    "resource_availability": "NOT_VERIFIED", "network_isolation": "NOT_ESTABLISHED"}


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
    """Bound reads; this cannot prevent file replacement after verification."""
    _check(deadline, cancelled)
    try:
        # Reject lexical UNC/device forms before even asking the filesystem.
        # A local-looking mapped drive or ancestor reparse remains unverified.
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


def _validate_reply(raw: bytes, include_private: bool) -> tuple[str, Any]:
    try:
        obj = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_no_duplicates,
                         parse_constant=_bad_constant)
        if not isinstance(obj, dict) or any(obj.get(key) != value for key, value in FIXED.items()):
            raise ValueError("invalid reply")
        common = set(FIXED) | {"status", "private"}
        if obj.get("status") == "REJECTED":
            if set(obj) != common | {"error_code"} or obj["private"] is not None or obj["error_code"] not in CHILD_ERRORS:
                raise ValueError("invalid reply")
            return "REJECTED", obj["error_code"]
        if obj.get("status") != "BUILT" or set(obj) != common:
            raise ValueError("invalid reply")
        private = obj["private"]
        if not include_private:
            if private is not None:
                raise ValueError("unexpected private output")
        else:
            if not isinstance(private, dict) or set(private) != {"system", "user", "system_sha256", "user_sha256"}:
                raise ValueError("invalid private output")
            for name, limit in (("system", 65_536), ("user", 32_768)):
                if not isinstance(private[name], str):
                    raise ValueError("invalid prompt")
                encoded = private[name].encode("utf-8", errors="strict")
                if len(encoded) > limit or hashlib.sha256(encoded).hexdigest() != private[name + "_sha256"]:
                    raise ValueError("invalid prompt")
        return "BUILT", obj
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        return "REJECTED", "INVALID_WORKER_REPLY"


def run_candidate(request_json: bytes, *, node_executable: str | Path,
                  include_private: bool = False, cancelled: threading.Event | None = None,
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
        if (type(request_json) is not bytes or len(request_json) > MAX_REQUEST or type(include_private) is not bool or
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

        payload = (json.dumps({"schema": SCHEMA, "include_private": include_private,
                               "request_utf8_base64": base64.b64encode(request_json).decode("ascii")},
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
            except BaseException:
                pass
        try:
            code = child.wait(timeout=1)
            process["direct_child"] = "REAPED"
            process["exit_code"] = code
        except BaseException:
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
        status, content = _validate_reply(streams["stdout"], include_private)
        _check(deadline, cancelled)
        if status != "BUILT":
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
