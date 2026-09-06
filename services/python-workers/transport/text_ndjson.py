"""One-request text.extract v1 transport; Core owns deadlines and DB authority.

Staging is explicitly selected, with input/<sha256> and output/<sha256> files.
This checks metadata before/after IO; it is not an OS sandbox against a hostile
concurrent filesystem writer. deadline_ms is a relative execution budget checked
between phases; Core must terminate a worker that stalls inside a parser.
Only the first stdin line is processed; subsequent lines are not validated.
Core sends one request and closes stdin for this single-shot transport.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import time

ROOT = Path(__file__).absolute().parents[3]
MAX_LINE_BYTES = 1024 * 1024
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_SAFE_INTEGER = 2**53 - 1
OUTPUT_SCHEMAS = ["archeaxis.text/v1", "archeaxis.document-structure/v1", "archeaxis.loss-receipt/v1"]


class Rejected(ValueError):
    pass


def safe_path(path: Path, *, missing=False) -> Path:
    text = str(path).replace("\\", "/")
    if text.lower().startswith(("e:", "//")) or ".." in path.parts:
        raise Rejected("protected drive, UNC, or parent traversal is not permitted")
    path = Path(os.path.abspath(path))
    private = {".codex", ".dsh", ".hermes", ".openhuman", ".claude", ".agents", ".env"}
    if any(part.casefold() in private for part in path.parts):
        raise Rejected("private agent paths are not staging")
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise Rejected("staging path is missing")
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise Rejected("symlink or reparse staging paths are forbidden")
    return path


def read_regular(path: Path) -> tuple[bytes, tuple]:
    path = safe_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise Rejected("staging asset must be a regular file with exactly one link")
    if before.st_size > MAX_INPUT_BYTES:
        raise Rejected("staging asset exceeds byte limit")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_nlink) != (before.st_dev, before.st_ino, 1):
            raise Rejected("staging asset identity changed while opening")
        raw = handle.read(MAX_INPUT_BYTES + 1)
        after = os.fstat(handle.fileno())
    safe_path(path)
    current = path.lstat()
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)
    if identity(before) != identity(after) or identity(before) != identity(current) or len(raw) != before.st_size:
        raise Rejected("staging asset changed during read")
    return raw, identity(before)


def strict_json(line: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Rejected("duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(value):
        raise Rejected("nonfinite JSON numbers are forbidden")

    return json.loads(line.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)


def integer_value(value, minimum):
    """Accept JSON mathematical integers, excluding bool and unsafe magnitudes."""
    if (type(value) not in (int, float) or not minimum <= value <= MAX_SAFE_INTEGER
            or (isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()))):
        raise Rejected(f"integer must be between {minimum} and {MAX_SAFE_INTEGER}")
    return int(value)


def response_for(request):
    request = request if isinstance(request, dict) else {}
    try:
        attempt = integer_value(request.get("attempt"), 1)
    except Rejected:
        attempt = 1
    return {
        "schema": "archeaxis.worker-response/v1", "type": "job_result",
        "request_id": request.get("request_id") if isinstance(request.get("request_id"), str) else "",
        "job_id": request.get("job_id") if isinstance(request.get("job_id"), str) else "",
        "attempt": attempt,
        "protocol_minor": 0, "status": "rejected", "outputs": [],
        "measurements": {}, "warnings": [], "error": None,
    }


def execute(request, staging: Path):
    # Closed single-capability request validation keeps production stdlib-only.
    # Tests validate real messages against the independently owned JSON Schema.
    required = {"schema", "type", "request_id", "job_id", "attempt", "protocol_minor",
                "capability", "capability_version", "deadline_ms", "inputs", "parameters"}
    if not isinstance(request, dict) or set(request) != required:
        raise Rejected("request fields must match worker-request/v1 exactly")
    for field in ("schema", "type", "request_id", "job_id", "capability", "capability_version"):
        if not isinstance(request[field], str):
            raise Rejected(f"{field} must be a string")
    if request.get("schema") != "archeaxis.worker-request/v1" or request.get("type") != "job_request":
        raise Rejected("worker-request/v1 is required")
    request = dict(request)
    for field, minimum in (("attempt", 1), ("deadline_ms", 1), ("protocol_minor", 0)):
        request[field] = integer_value(request[field], minimum)
    if request["capability"] != "text.extract" or request["capability_version"] != "1" or request["protocol_minor"] != 0:
        raise Rejected("unsupported capability or protocol version")
    if (not isinstance(request["parameters"], dict)
            or request["parameters"] or not isinstance(request["inputs"], list) or len(request["inputs"]) != 1):
        raise Rejected("text.extract v1 requires one input, integer minor and empty parameters")
    deadline = time.monotonic() + request["deadline_ms"] / 1000

    def check_deadline():
        if time.monotonic() > deadline:
            raise TimeoutError("relative request execution budget exceeded; Core owns forced cancellation")

    staging = safe_path(staging)
    if not staging.is_dir():
        raise Rejected("staging root must be a directory")
    asset = request["inputs"][0]
    if (not isinstance(asset, dict) or set(asset) != {"uri", "sha256", "media_type"}
            or any(not isinstance(value, str) for value in asset.values())):
        raise Rejected("input asset must contain exactly uri, sha256 and media_type strings")
    digest = asset["sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or asset["uri"] != f"job://input/{digest}":
        raise Rejected("input URI must match its sha256")
    allowed_media = {"text/plain", "text/markdown", "text/csv", "text/tab-separated-values", "application/json", "application/xml", "text/xml"}
    if asset["media_type"].split(";", 1)[0].strip().lower() not in allowed_media:
        raise Rejected("unsupported text media type")
    source = staging / "input" / digest
    raw, identity = read_regular(source)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise Rejected("input content hash mismatch")
    check_deadline()
    spec = importlib.util.spec_from_file_location("worker_text", ROOT / "services/python-workers/document/worker_text.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    result = worker.extract(str(source))
    reread, current_identity = read_regular(source)
    if current_identity != identity or reread != raw:
        raise Rejected("input changed during extraction")
    check_deadline()
    encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    artifacts = [
        ("text", OUTPUT_SCHEMAS[0], "text/plain; charset=utf-8", result["text"].encode("utf-8")),
        ("document_structure", OUTPUT_SCHEMAS[1], "application/json", encode(result["structure"])),
        ("loss_report", OUTPUT_SCHEMAS[2], "application/json", encode(result["loss_receipt"])),
    ]
    output_dir = safe_path(staging / "output", missing=True)
    output_dir.mkdir(exist_ok=True)
    prepared = []
    # Check every pre-existing object before producing any new artifact.
    for kind, output_schema, media_type, data in artifacts:
        digest = hashlib.sha256(data).hexdigest()
        path = safe_path(output_dir / digest, missing=True)
        if path.exists():
            previous, _ = read_regular(path)
            if previous != data:
                raise Rejected("existing output hash path contains different bytes")
        prepared.append((kind, output_schema, media_type, data, digest, path))
    outputs = []
    for kind, output_schema, media_type, data, digest, path in prepared:
        check_deadline()
        safe_path(path, missing=True)
        if not path.exists():
            with path.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        actual, _ = read_regular(path)
        if actual != data:
            raise RuntimeError("output content changed during write")
        outputs.append({"kind": kind, "uri": f"job://output/{digest}", "sha256": hashlib.sha256(actual).hexdigest(),
                        "media_type": media_type, "byte_length": len(actual), "schema": output_schema,
                        "authority_effect": "candidate_or_measurement_only"})
    check_deadline()
    return outputs, {"input_bytes": len(raw)}, result["loss_receipt"].get("losses", [])


def emit(message):
    sys.stdout.buffer.write(json.dumps(message, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-root", type=Path, required=True)
    args = parser.parse_args()
    emit({"schema": "archeaxis.worker-hello/v1", "type": "hello",
          "protocol": {"major": 1, "min_minor": 0, "max_minor": 0},
          "worker": {"name": "python-worker-text-ndjson", "version": "1"},
          "capabilities": ["text.extract"], "schemas": OUTPUT_SCHEMAS})
    request = None
    response = response_for(request)
    try:
        line = sys.stdin.buffer.readline(MAX_LINE_BYTES + 1)
        if not line or len(line) > MAX_LINE_BYTES:
            raise Rejected("request line is empty or exceeds 1 MiB")
        try:
            request = strict_json(line)
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise Rejected("invalid strict JSON request") from exc
        response = response_for(request)
        outputs, measurements, warnings = execute(request, args.staging_root)
        response.update(status="succeeded", outputs=outputs, measurements=measurements, warnings=warnings)
    except Rejected as exc:
        response.update(status="rejected", outputs=[], error={"code": "AAK-PROTO-001", "message": str(exc), "retryable": False})
    except Exception as exc:
        response.update(status="failed", outputs=[], error={"code": "AAK-WORKER-001", "message": str(exc), "retryable": False})
    emit(response)
    return 0 if response["status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
