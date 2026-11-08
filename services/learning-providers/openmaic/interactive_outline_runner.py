"""Private unregistered owned-child adapter for the interactive-outline prompt.

It runs the pinned worker as a direct child, bounds its pipes and lifetime, and
binds the reply to the requested outline identity. No product registration,
HTTP route, Core authorization, model or persistence is provided here. The
explicit Node path is trusted host configuration, never request data.
"""
from __future__ import annotations

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

SCHEMA = "archeaxis.openmaic-interactive-outline/v1"
RESULT = "archeaxis.openmaic-interactive-outline-result/v1"
BINDING = "archeaxis.openmaic-interactive-outline-binding/v1"
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
NODE_BYTES = 93_580_104
WORKER = Path(__file__).absolute().with_name("interactive-outline-worker.mjs")
WORKER_SHA256 = "4ab17fec95724da4c3e70b27ce3e93dff51f38e35abb2ee2c12cef665c4eae8b"
MAX_REQUEST = 65_536
MAX_STDOUT = 1_000_000
MAX_STDERR = 8_192
# Only the module instance is limited. If child or pipe cleanup is uncertain,
# retain the slot and fail closed until the host replaces it.
_SLOT = threading.BoundedSemaphore(1)
FIXED = {
    "schema": RESULT,
    "model_call": "NOT_INVOKED",
    "network_performed": False,
    "core_task": "NOT_CONNECTED",
    "core_authorization": "NOT_ESTABLISHED",
    "canonical_bindings_verified": False,
    "persisted": False,
    "active_content_executed": False,
    "full_generation_chain": False,
    "prompt_template": "interactive-outlines",
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
    """Bound reads; this cannot prevent file replacement after verification."""
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


def _request_id(raw: bytes) -> str | None:
    try:
        request = json.loads(raw.decode("utf-8", errors="strict"),
                             object_pairs_hook=_no_duplicates, parse_constant=_bad_constant)
        value = request["request_id"]
        return value if isinstance(value, str) and value.isascii() and 0 < len(value) <= 128 else None
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        return None


def _hex(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _validate_reply(raw: bytes, request_id: str) -> tuple[str, Any]:
    try:
        reply = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_no_duplicates,
                           parse_constant=_bad_constant)
        if not isinstance(reply, dict) or any(reply.get(key) != value for key, value in FIXED.items()):
            raise ValueError("invalid reply")
        status = reply.get("status")
        if status == "PROMPT_CAPTURED":
            binding = reply.get("binding")
            if (reply.get("request_id") != request_id or not isinstance(binding, dict) or
                    set(binding) != {"schema", "request_id", "input_sha256", "templates_manifest_sha256",
                                     "worker_sha256", "system", "user", "system_sha256", "user_sha256"} or
                    binding["schema"] != BINDING or binding["request_id"] != request_id or
                    not all(_hex(binding[key]) for key in ("input_sha256", "templates_manifest_sha256",
                                                           "worker_sha256", "system_sha256", "user_sha256")) or
                    not isinstance(binding["system"], str) or not isinstance(binding["user"], str)):
                raise ValueError("invalid binding")
            return "PROMPT_CAPTURED", reply
        if status == "CANDIDATE":
            data = reply.get("data")
            if (reply.get("request_id") != request_id or not isinstance(data, dict) or not isinstance(data.get("outlines"), list)
                    or not isinstance(reply.get("transformations"), list) or type(reply.get("exact_json_output")) is not bool
                    or not _hex(reply.get("input_sha256"))):
                raise ValueError("invalid candidate")
            return "CANDIDATE", reply
        if isinstance(status, str) and status.isascii() and status.isupper() and len(status) <= 64:
            return "REJECTED", status
        raise ValueError("invalid status")
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, AttributeError):
        return "REJECTED", "INVALID_WORKER_REPLY"


def run_candidate(request_json: bytes, *, node_executable: str | Path,
                  cancelled: threading.Event | None = None,
                  timeout_seconds: float = 30.0) -> dict[str, Any]:
    """Run one candidate. Caller must retain original bytes and protect result.

    ``node_executable`` must come from trusted host configuration. An event is a
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
        if (type(request_json) is not bytes or not 0 < len(request_json) <= MAX_REQUEST or
                isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or
                not math.isfinite(timeout_seconds) or not 0.25 <= timeout_seconds <= 60):
            return _reject("INVALID_ARGUMENT", process)
        request_id = _request_id(request_json)
        if request_id is None:
            return _reject("INVALID_ARGUMENT", process)
        deadline = time.monotonic() + timeout_seconds
        _check(deadline, cancelled)
        node = Path(node_executable)
        if not _identity(node, NODE_SHA256, NODE_BYTES, deadline, cancelled, NODE_BYTES):
            return _reject("NODE_IDENTITY_MISMATCH", process)
        if not _identity(WORKER, WORKER_SHA256, 1_000_000, deadline, cancelled):
            return _reject("WORKER_IDENTITY_MISMATCH", process)
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
                while offset < len(request_json):
                    count = child.stdin.write(request_json[offset:])
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
        if type(code) is not int:
            return _reject("WORKER_FAILED", process)
        status, content = _validate_reply(streams["stdout"], request_id)
        _check(deadline, cancelled)
        if status == "REJECTED":
            return _reject(content, process)
        if code != 0 and status == "CANDIDATE":
            return _reject("WORKER_FAILED", process)
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
