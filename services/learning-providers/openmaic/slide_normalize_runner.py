"""Private, unregistered owned-child runner for the limited slide normalization candidate.

This module provides no HTTP/Core endpoint and is not an OS sandbox. The Node
path is trusted host configuration, never a path selected by a scene request.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import threading
import time
from typing import Any


SCHEMA = "archeaxis.openmaic-slide-normalize/v1"
RESULT = "archeaxis.openmaic-slide-normalize-result/v1"
NODE_SHA256 = "ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
NODE_BYTES = 93_580_104
WORKER = Path(__file__).absolute().with_name("slide-normalize-worker.mjs")
WORKER_SHA256 = "d28803cae8168014b4ba54f32a4dcae744fef86b7b2eee711715a9b2f95e3d31"
SOURCE_SHA256 = "e4f21f3273d9d65dadd53768afc5049b5473d087d1c525ea804c3d057b5ecf06"
MAX_SCENE = 16_384
MAX_STDIN = 32_768
MAX_STDOUT = 196_608
MAX_STDERR = 8_192
MAX_NORMALIZED = 32_768
# Only this module instance is limited. If child or pipe cleanup is uncertain,
# retain the slot and fail closed until the host replaces this module instance.
_SLOT = threading.BoundedSemaphore(1)
CHILD_ERRORS = frozenset({
    "NODE_IDENTITY_MISMATCH", "ENVIRONMENT_OVERRIDE", "INVALID_REQUEST", "INVALID_SCENE",
    "UNSUPPORTED_SCENE", "INPUT_TIMEOUT", "INPUT_TOO_LARGE", "OUTPUT_TOO_LARGE",
    "UPSTREAM_IDENTITY_MISMATCH", "UNLISTED_IMPORT", "UNEXPECTED_UPSTREAM_RESULT",
    "UNEXPECTED_UPSTREAM_CHANGE", "UPSTREAM_MUTATED_INPUT", "PATCH_MISMATCH", "INTERNAL_FAILURE",
})
COMMON_KEYS = frozenset({
    "schema", "status", "scope", "privacy", "provider", "provider_version", "dsl_package_version",
    "expected_normalize_sha256", "source_verification", "node_version", "full_scene_generation",
    "rendering_authorized", "security_sanitizer", "core_authorization", "canonical_persistence",
    "network_isolation", "original_preservation",
})
SUCCESS_KEYS = COMMON_KEYS | frozenset({
    "request_id", "input_sha256", "input_bytes", "input_utf8_base64", "output_sha256", "output_bytes",
    "output_utf8_base64", "byte_patch", "semantic_changes", "serialization",
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


def _same_json(a: Any, b: Any) -> bool:
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return set(a) == set(b) and all(_same_json(value, b[key]) for key, value in a.items())
    if isinstance(a, list):
        return len(a) == len(b) and all(_same_json(x, y) for x, y in zip(a, b))
    return a == b


def _fields(value: Any, required: set[str], optional: set[str] = frozenset()) -> bool:
    return isinstance(value, dict) and required <= value.keys() and value.keys() <= required | optional


# ECMAScript String.trim whitespace/line terminators, not Python's slightly
# different Unicode strip set (which includes U+0085 and omits U+FEFF).
_JS_TRIM = ("\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680"
            "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
            "\u2028\u2029\u202f\u205f\u3000\ufeff")


def _text(value: Any, maximum: int) -> bool:
    if not isinstance(value, str) or not value.strip(_JS_TRIM) or "\0" in value:
        return False
    try:
        return len(value.encode("utf-16-le")) // 2 <= maximum
    except UnicodeEncodeError:
        return False


def _id(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value, re.ASCII) is not None


def _number(value: Any, minimum: float, maximum: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum


def _color(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(
        r"(?:#(?:[a-f\d]{3}|[a-f\d]{4}|[a-f\d]{6}|[a-f\d]{8})|[a-z]{1,24})",
        value, re.IGNORECASE | re.ASCII) is not None


def _supported_scene(scene: Any) -> bool:
    if not _fields(scene, {"id", "stageId", "type", "title", "order", "content", "actions"},
                   {"outlineId", "createdAt", "updatedAt"}):
        return False
    if (not _id(scene["id"]) or not _id(scene["stageId"]) or scene["type"] != "slide" or
            not _text(scene["title"], 240) or type(scene["order"]) is not int or
            not 0 <= scene["order"] <= 2**53 - 1 or scene["actions"] != [] or type(scene["actions"]) is not list):
        return False
    if "outlineId" in scene and not _id(scene["outlineId"]):
        return False
    if any(type(scene[key]) is not int or not 0 <= scene[key] <= 2**53 - 1
           for key in ("createdAt", "updatedAt") if key in scene):
        return False
    content = scene["content"]
    if (not _fields(content, {"type", "canvas"}, {"schemaVersion"}) or content["type"] != "slide" or
            ("schemaVersion" in content and (type(content["schemaVersion"]) is not int or content["schemaVersion"] != 1))):
        return False
    canvas = content["canvas"]
    if (not _fields(canvas, {"id", "viewportSize", "viewportRatio", "theme", "elements"}, {"background"}) or
            not _id(canvas["id"]) or not _number(canvas["viewportSize"], 1, 10000) or
            not _number(canvas["viewportRatio"], 0.1, 10)):
        return False
    theme = canvas["theme"]
    if (not _fields(theme, {"backgroundColor", "themeColors", "fontColor", "fontName"}, {"outline", "shadow"}) or
            not _color(theme["backgroundColor"]) or not _color(theme["fontColor"]) or
            not _text(theme["fontName"], 240) or not isinstance(theme["themeColors"], list) or
            len(theme["themeColors"]) > 32 or not all(_color(c) for c in theme["themeColors"])):
        return False
    if "outline" in theme:
        outline = theme["outline"]
        if (not _fields(outline, set(), {"color", "width", "style"}) or
                ("color" in outline and not _color(outline["color"])) or
                ("width" in outline and not _number(outline["width"], 0, 10000)) or
                ("style" in outline and outline["style"] not in ("solid", "dashed", "dotted"))):
            return False
    if "shadow" in theme:
        shadow = theme["shadow"]
        if (not _fields(shadow, {"h", "v", "blur", "color"}) or
                not _number(shadow["h"], -10000, 10000) or not _number(shadow["v"], -10000, 10000) or
                not _number(shadow["blur"], 0, 10000) or not _color(shadow["color"])):
            return False
    if "background" in canvas:
        bg = canvas["background"]
        if not _fields(bg, {"type"}, {"color"}) or bg["type"] != "solid" or ("color" in bg and not _color(bg["color"])):
            return False
    elements = canvas["elements"]
    if not isinstance(elements, list) or len(elements) > 200:
        return False
    seen = set()
    active = re.compile(r"<\s*(?:img|video|audio|iframe|object|embed|svg|canvas|script|style|link|base|form)\b",
                        re.IGNORECASE | re.ASCII)
    for element in elements:
        if (not _fields(element, {"type", "id", "left", "top", "width", "height", "rotate", "content"},
                        {"defaultFontName", "defaultColor"}) or element["type"] != "text" or
                not _id(element["id"]) or element["id"] in seen or not _text(element["content"], 16000) or
                active.search(element["content"]) or
                not _number(element["left"], -10000, 10000) or not _number(element["top"], -10000, 10000) or
                not _number(element["width"], 0.01, 10000) or not _number(element["height"], 0.01, 10000) or
                not _number(element["rotate"], -3600, 3600)):
            return False
        if "defaultFontName" in element and element["defaultFontName"] != "" and not _text(element["defaultFontName"], 240):
            return False
        if "defaultColor" in element and element["defaultColor"] != "" and not _color(element["defaultColor"]):
            return False
        seen.add(element["id"])
    return True


def _validate_reply(raw: bytes, original: bytes, request_id: str) -> tuple[str, Any]:
    """Check the exact original, replayable patch, and every permitted semantic change."""
    try:
        obj = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_no_duplicates,
                         parse_constant=_bad_constant)
        if not isinstance(obj, dict):
            raise ValueError("bad response")
        status = obj.get("status")
        keys = SUCCESS_KEYS if status == "CANDIDATE" else COMMON_KEYS | {"error_code"}
        if set(obj) != keys or status not in {"CANDIDATE", "REJECTED"}:
            raise ValueError("bad response")
        fixed = {"schema": RESULT, "scope": "CALLER_SUPPLIED_UNVERIFIED", "privacy": "PRIVATE_INPUT_AND_OUTPUT",
                 "provider": "openmaic", "provider_version": "1.3.0", "dsl_package_version": "0.12.0",
                 "expected_normalize_sha256": SOURCE_SHA256,
                 "source_verification": "VERIFIED_SELECTED_MEMBERS" if status == "CANDIDATE" else "NOT_ASSERTED",
                 "node_version": "24.21.0", "full_scene_generation": False, "rendering_authorized": False,
                 "security_sanitizer": False, "core_authorization": "NOT_ESTABLISHED",
                 "canonical_persistence": "NOT_PERFORMED", "network_isolation": "NOT_ESTABLISHED",
                 "original_preservation": "CALLER_RESPONSIBILITY"}
        if any(obj.get(k) != v or (v is False and obj.get(k) is not False) for k, v in fixed.items()):
            raise ValueError("bad response")
        if status == "REJECTED":
            code = obj["error_code"]
            if not isinstance(code, str) or code not in CHILD_ERRORS:
                raise ValueError("bad response")
            return status, code
        if (obj["request_id"] != request_id or type(obj["input_bytes"]) is not int or
                obj["input_bytes"] != len(original) or _decode_base64(obj["input_utf8_base64"]) != original or
                obj["input_sha256"] != hashlib.sha256(original).hexdigest()):
            raise ValueError("bad response")
        output = _decode_base64(obj["output_utf8_base64"])
        if (len(output) > MAX_NORMALIZED or type(obj["output_bytes"]) is not int or
                obj["output_bytes"] != len(output) or obj["output_sha256"] != hashlib.sha256(output).hexdigest() or
                obj["serialization"] != "ECMASCRIPT_JSON_RESERIALIZED"):
            raise ValueError("bad response")
        input_scene = json.loads(original.decode("utf-8", errors="strict"), object_pairs_hook=_no_duplicates,
                                 parse_constant=_bad_constant)
        output_scene = json.loads(output.decode("utf-8", errors="strict"), object_pairs_hook=_no_duplicates,
                                  parse_constant=_bad_constant)
        if not _supported_scene(input_scene) or not _supported_scene(output_scene):
            raise ValueError("bad scene")
        expected = copy.deepcopy(input_scene)
        changes = []
        for index, element in enumerate(expected["content"]["canvas"]["elements"]):
            for field, fallback in (("defaultFontName", "Microsoft YaHei"), ("defaultColor", "#333333")):
                if field not in element or element[field] == "":
                    changes.append({"path": f"/content/canvas/elements/{index}/{field}",
                                    "kind": "EMPTY_REPLACED_WITH_DEFAULT" if field in element else "ABSENT_FILLED_WITH_DEFAULT"})
                    element[field] = fallback
        if not _same_json(expected, output_scene) or not _same_json(changes, obj["semantic_changes"]):
            raise ValueError("bad semantic changes")
        patch = obj["byte_patch"]
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
        return status, obj
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return "REJECTED", "INVALID_WORKER_REPLY"


def run_candidate(scene_json: bytes, *, node_executable: str | Path,
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
        if (type(scene_json) is not bytes or len(scene_json) > MAX_SCENE or
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
                               "scene_utf8_base64": base64.b64encode(scene_json).decode("ascii")},
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
        status, content = _validate_reply(streams["stdout"], scene_json, request_id)
        _check(deadline, cancelled)
        if status != "CANDIDATE":
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
