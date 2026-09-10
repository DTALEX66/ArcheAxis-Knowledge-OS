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
    def __init__(self, message, code="AAK-VAL-001"):
        super().__init__(message)
        self.code = code


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
        raise Rejected("staging asset exceeds byte limit", "AAK-VAL-003")
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


# R08: one job contract for every extraction route. The request/response
# envelope, the rejection semantics and the artifact triple (text +
# document_structure + loss_report) are identical for all of them; a route only
# declares its capability version, its worker module and the media types it
# accepts. Adding a route here must not relax any existing check.
ROUTES = {
    "text.extract": {
        "version": "1",
        "worker": "services/python-workers/document/worker_text.py",
        "media_types": {
            "text/plain",
            "text/markdown",
            "text/csv",
            "text/tab-separated-values",
            "application/json",
            "application/xml",
            "text/xml",
        },
        "call": "path",
        # R15/F01: this worker derives format facts from the declared media type, so
        # the transport hands it over instead of letting the worker sniff the name.
        "media_type_arg": True,
    },
    "pdf.extract": {
        "version": "1",
        "worker": "services/python-workers/document/worker_pdf.py",
        "media_types": {"application/pdf"},
        "call": "path",
    },
    "image.ocr": {
        "version": "1",
        "worker": "services/python-workers/vision/worker_ocr.py",
        "media_types": {"image/png", "image/jpeg", "image/tiff", "image/webp", "image/bmp"},
        "call": "ocr",
    },
}


_IMAGE_SUFFIX = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}


def _run_route(route, source: Path, media_type: str) -> dict:
    """Load the route's worker and extract with its own entry-point shape."""
    spec = importlib.util.spec_from_file_location("route_worker", ROOT / route["worker"])
    if spec is None or spec.loader is None:
        raise Rejected("route worker module is missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if route["call"] == "ocr":
        # Staging stores inputs content-addressed (no extension), while the OCR
        # worker validates the file type. Materialise a route-local view with the
        # suffix the declared media type implies; the original input is untouched
        # and its hash is still verified separately by the caller.
        suffix = _IMAGE_SUFFIX.get(media_type.split(";", 1)[0].strip().lower())
        if suffix is None:
            raise Rejected("unsupported image media type", "AAK-VAL-002")
        view = source.with_name(source.name + suffix)
        if not view.exists():
            with view.open("xb") as handle:
                handle.write(source.read_bytes())
        # OCR keeps its own explicit parameters: language plus the tessdata dir.
        # The repository ships eng.traineddata; an ambient TESSDATA_PREFIX may
        # point elsewhere, so the repository copy wins when it exists. The path is
        # passed in plain form because tesseract cannot open a Windows extended
        # (\\?\) path - canonicalised callers such as the Rust executor would
        # otherwise hand one over and OCR would fail to load its language data.
        tessdata = ROOT / "tools" / "tesseract" / "tessdata"
        tessdata_arg = tessdata if tessdata.is_dir() else None
        if tessdata_arg is not None:
            plain = str(tessdata_arg).replace("\\\\?\\", "")
            tessdata_arg = Path(plain)
        return module.extract(view, "eng", tessdata_arg)
    if route.get("media_type_arg"):
        return module.extract(str(source), media_type.split(";", 1)[0].strip().lower())
    return module.extract(str(source))


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
    if request["schema"] != "archeaxis.worker-request/v1":
        raise Rejected("worker-request/v1 is required", "AAK-PROTO-001")
    if request["type"] != "job_request":
        raise Rejected("job_request type is required")
    request = dict(request)
    for field, minimum in (("attempt", 1), ("deadline_ms", 1), ("protocol_minor", 0)):
        request[field] = integer_value(request[field], minimum)
    route = ROUTES.get(request["capability"])
    if route is None:
        raise Rejected("unsupported capability")
    if request["capability_version"] != route["version"] or request["protocol_minor"] != 0:
        raise Rejected("unsupported capability or protocol version", "AAK-PROTO-001")
    if (not isinstance(request["parameters"], dict)
            or request["parameters"] or not isinstance(request["inputs"], list) or len(request["inputs"]) != 1):
        raise Rejected(f"{request['capability']} v{route['version']} requires one input, integer minor and empty parameters")
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
    allowed_media = route["media_types"]
    if asset["media_type"].split(";", 1)[0].strip().lower() not in allowed_media:
        raise Rejected("unsupported media type for this capability", "AAK-VAL-002")
    source = staging / "input" / digest
    raw, identity = read_regular(source)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise Rejected("input content hash mismatch", "AAK-HASH-001")
    check_deadline()
    result = _run_route(route, source, asset["media_type"])
    reread, current_identity = read_regular(source)
    if current_identity != identity or reread != raw:
        raise Rejected("input changed during extraction", "AAK-HASH-001")
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
                raise Rejected("existing output hash path contains different bytes", "AAK-HASH-001")
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
            raise Rejected("output content changed during write", "AAK-HASH-001")
        outputs.append({"kind": kind, "uri": f"job://output/{digest}", "sha256": hashlib.sha256(actual).hexdigest(),
                        "media_type": media_type, "byte_length": len(actual), "schema": output_schema,
                        "authority_effect": "candidate_or_measurement_only"})
    check_deadline()
    return outputs, {"input_bytes": len(raw)}, result["loss_receipt"].get("losses", [])


def emit(message):
    sys.stdout.buffer.write(json.dumps(message, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def serve_stdio(worker_name: str, capabilities: list[str], staging_root: Path) -> int:
    """R08: one stdio job loop for every route.

    The worker identity and the advertised capabilities are the only per-route
    inputs; the handshake shape, the request validation, the response envelope and
    the error vocabulary are identical, so a PDF or OCR worker reaches the Core
    through exactly the same job/attempt/error machinery as the text worker.
    """
    emit({"schema": "archeaxis.worker-hello/v1", "type": "hello",
          "protocol": {"major": 1, "min_minor": 0, "max_minor": 0},
          "worker": {"name": worker_name, "version": "1"},
          "capabilities": list(capabilities), "schemas": OUTPUT_SCHEMAS})
    request = None
    response = response_for(request)
    try:
        line = sys.stdin.buffer.readline(MAX_LINE_BYTES + 1)
        if not line:
            raise Rejected("request line is empty")
        if len(line) > MAX_LINE_BYTES:
            raise Rejected("request line exceeds 1 MiB", "AAK-VAL-003")
        try:
            request = strict_json(line)
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise Rejected("invalid strict JSON request") from exc
        response = response_for(request)
        # The route table is shared by every worker, so the worker's own declared
        # capability list is what decides: a process may only serve what its
        # handshake advertised, even if another route is registered.
        advertised = request.get("capability") if isinstance(request, dict) else None
        if advertised not in capabilities:
            raise Rejected("unsupported capability")
        outputs, measurements, warnings = execute(request, staging_root)
        response.update(status="succeeded", outputs=outputs, measurements=measurements, warnings=warnings)
    except Rejected as exc:
        response.update(status="rejected", outputs=[], error={"code": exc.code, "message": str(exc), "retryable": False})
    except TimeoutError as exc:
        response.update(status="failed", outputs=[], error={"code": "AAK-WORKER-002", "message": str(exc), "retryable": True})
    except Exception as exc:
        response.update(status="failed", outputs=[], error={"code": "AAK-WORKER-003", "message": str(exc), "retryable": False})
    emit(response)
    return 0 if response["status"] == "succeeded" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-root", type=Path, required=True)
    args = parser.parse_args()
    return serve_stdio("python-worker-text-ndjson", ["text.extract"], args.staging_root)


if __name__ == "__main__":
    raise SystemExit(main())
