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
import contextlib
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


def filesystem_path(path: Path) -> Path:
    """Use extended Windows paths only at file IO boundaries, after validation."""
    absolute = os.path.abspath(path)
    if os.name == "nt" and len(absolute) >= 248 and not absolute.startswith("\\\\?\\"):
        return Path("\\\\?\\" + absolute)
    return path


_SCRIPT = Path(__file__).absolute()
_BUNDLE_ROOT = _SCRIPT.parents[2]
if (_BUNDLE_ROOT / "workers").is_dir():
    # A Green candidate relocates this transport to ``workers/transport``.
    # Keep the source checkout layout working while resolving bundled workers
    # from the candidate root when the script is portable.
    ROOT = _BUNDLE_ROOT
    WORKER_ROOT = ROOT / "workers"
else:
    ROOT = _SCRIPT.parents[3]
    WORKER_ROOT = ROOT / "services" / "python-workers"
MAX_LINE_BYTES = 1024 * 1024
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_SAFE_INTEGER = 2**53 - 1
OUTPUT_SCHEMAS = ["archeaxis.text/v1", "archeaxis.document-structure/v1", "archeaxis.loss-receipt/v1"]


OCR_LANG_ENV = "ARCHEAXIS_OCR_LANG"
OCR_TESSDATA_ENV = "ARCHEAXIS_OCR_TESSDATA"


class Rejected(ValueError):
    def __init__(self, message, code="AAK-VAL-001"):
        super().__init__(message)
        self.code = code


def _declared_tool_path(name: str) -> Path | None:
    """The declared external path for a capability, or None.

    Uses the same resolver the workers use, so the transport stops guessing where
    language data lives. A manifest that cannot be read raises rather than reading as
    "nothing declared".
    """
    tool_paths = _SCRIPT.parent.parent / "tool_paths.py"
    if not tool_paths.is_file():
        return None
    spec = importlib.util.spec_from_file_location("transport_tool_paths", tool_paths)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    resolved = module.declared_path(name)
    return Path(resolved) if resolved else None


def _ocr_language() -> str:
    """The language the OCR route reads.

    `ARCHEAXIS_OCR_LANG` selects it, defaulting to `eng`. It used to be hardcoded, which
    meant a Chinese page was handed the English model and read as noise - the language is
    a property of the material, not of the route.
    """
    return os.environ.get(OCR_LANG_ENV, "").strip() or "eng"


def _ocr_tessdata(language: str) -> Path | None:
    """Language data for this language, preferring one that can actually serve it.

    Order: an explicit `ARCHEAXIS_OCR_TESSDATA`, the repository's bundled copy, then the
    declared `tesseract-languages` entry. A candidate counts only if it holds the
    requested language, so a directory of unrelated languages is not mistaken for usable.
    The path is handed over in plain form because tesseract cannot open a Windows extended
    (\\\\?\\\\) path, which a canonicalising caller such as the Rust executor would
    otherwise supply.
    """
    candidates: list[Path] = []
    configured = os.environ.get(OCR_TESSDATA_ENV, "").strip()
    if configured:
        candidates.append(Path(configured))
    candidates.append(ROOT / "tools" / "tesseract" / "tessdata")
    declared = _declared_tool_path("tesseract-languages")
    if declared is not None:
        candidates.extend([declared, declared / "tessdata"])
    for candidate in candidates:
        with contextlib.suppress(OSError):
            if (candidate / f"{language}.traineddata").is_file():
                return Path(str(candidate).replace("\\\\?\\", ""))
    return None


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
            info = filesystem_path(part).lstat()
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
    before = filesystem_path(path).lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise Rejected("staging asset must be a regular file with exactly one link")
    if before.st_size > MAX_INPUT_BYTES:
        raise Rejected("staging asset exceeds byte limit", "AAK-VAL-003")
    with filesystem_path(path).open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_nlink) != (before.st_dev, before.st_ino, 1):
            raise Rejected("staging asset identity changed while opening")
        raw = handle.read(MAX_INPUT_BYTES + 1)
        after = os.fstat(handle.fileno())
    safe_path(path)
    current = filesystem_path(path).lstat()
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
            "application/x-ndjson",
            "application/yaml",
            "text/x-yaml",
            "application/toml",
            "application/epub+zip",
            "message/rfc822",
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
        # R15/F06: the PDF worker renders text-less pages so the OCR route has a real
        # image to read; it writes them into this directory inside the transfer area.
        "artifact_dir": "ocr",
        "artifact_kwarg": "ocr_dir",
    },
    "image.ocr": {
        "version": "1",
        "worker": "services/python-workers/vision/worker_ocr.py",
        "media_types": {"image/png", "image/jpeg", "image/tiff", "image/webp", "image/bmp"},
        "call": "ocr",
    },
    # R15/F15: a container is binary, so it has its own route and its own worker; the
    # projection is an inventory listing rather than a decode of the bytes.
    "archive.inventory": {
        "version": "1",
        "worker": "services/python-workers/document/worker_archive.py",
        "media_types": {"application/zip"},
        "call": "path",
        # R15/F15: the archive worker can offer its members to the Core as sources, so
        # it is told where durable transfer files may be written.
        "artifact_dir": "members",
        "artifact_kwarg": "member_dir",
    },
    # R15/F10-F11: audio and video are binary; the probe reads header structure only.
    "media.probe": {
        "version": "1",
        "worker": "services/python-workers/document/worker_media.py",
        "media_types": {"video/mp4", "audio/wav"},
        "call": "path",
    },
    # The pack requires real audio before final closure. The ASR engine, its model and its
    # path resolution were all real and verified, but nothing declared the capability, so
    # no Core job could reach it. Audio formats are named here that the probe route
    # deliberately does not guess at, because this route has a reader for them.
    "media.transcribe": {
        "version": "1",
        "worker": "services/python-workers/media/worker_transcribe.py",
        "media_types": {
            "audio/mpeg",
            "audio/mp4",
            "audio/x-m4a",
            "audio/flac",
            "audio/ogg",
            "audio/opus",
            "audio/wav",
            "audio/x-wav",
        },
        "call": "transcribe",
    },
    # R15/F07-F09: an Office package is a ZIP of XML parts; this route reaches the
    # worker that already read them since the 2026-09-05 slice but had no route.
    "office.structure": {
        "version": "1",
        "worker": "services/python-workers/document/worker_office.py",
        "media_types": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        "call": "path",
        # this worker dispatches on the file suffix, so it needs a suffixed view
        "suffix_by_media": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        },
    },
    # R15/F12: the canvas and subtitle workers existed unreachable too; each produces
    # real structure, so each gets its own capability and media type.
    "canvas.structure": {
        "version": "1",
        "worker": "services/python-workers/document/worker_canvas.py",
        "media_types": {"application/json"},
        "call": "path",
        # this worker predates the unified contract: it returns its own node anchors and
        # a receipt without coverage, so the transport adapts its output (and keeps the
        # worker's own structure as a fact under params.worker_structure)
        "contract_adapter": True,
    },
    "subtitles.structure": {
        "version": "1",
        "worker": "services/python-workers/document/worker_subtitles.py",
        "media_types": {"application/x-subrip", "text/vtt"},
        "call": "path",
        # the worker picks its parser by suffix, and staging has no extension
        "suffix_by_media": {"application/x-subrip": ".srt", "text/vtt": ".vtt"},
    },
    # R15/F02: a saved HTML snapshot gets its own route through the worker that has read
    # HTML since an earlier slice but had no route pointing at it.
    "html.structure": {
        "version": "1",
        "worker": "services/python-workers/web/worker_html.py",
        "media_types": {"text/html", "application/xhtml+xml"},
        "call": "path",
        "contract_adapter": True,
    },
    # R15/F04: a figure description is model output; the route exists so the description
    # is a labelled candidate, and a missing model fails the job by name.
    "image.caption": {
        "version": "1",
        "worker": "services/python-workers/vision/worker_caption.py",
        "media_types": {"image/png", "image/jpeg", "image/tiff", "image/webp", "image/bmp"},
        "call": "path",
        # the worker validates the image suffix and staging has no extension
        "suffix_by_media": {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/tiff": ".tiff",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
        },
    },
    # G4's machine answer worker has **no route here on purpose**. A route in this table is validated
    # against the job protocol, and that protocol requires `parameters` to be empty, so there is no
    # way to carry the question the worker needs. Declaring a route here would be a route that fails
    # its own validation. What the worker needs is a Core route that accepts a question, which does
    # not exist yet, and inventing a route that cannot run would be worse than saying so.
}


_IMAGE_SUFFIX = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}

# The ASR worker hands the path to its engine, which selects a decoder by suffix, so the
# content-addressed staged name needs a route-local view carrying the real extension.
_AUDIO_SUFFIX = {
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/flac": ".flac",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}

# R15/F07-F09 + F12: a worker that dispatches on the file suffix cannot read staging's
# content-addressed names (no extension), so each such route declares the suffix its
# media type implies and the transport materialises a route-local view for it.


def _materialise_view(source: Path, suffix: str) -> Path:
    """A route-local copy carrying the suffix the route's worker expects.

    The original staged input is untouched and its hash is still verified separately by
    the caller; this only gives a suffix-dispatching worker the name it needs.
    """
    view = source.with_name(source.name + suffix)
    safe_path(view, missing=True)
    if not filesystem_path(view).exists():
        with filesystem_path(view).open("xb") as handle:
            handle.write(filesystem_path(source).read_bytes())
    return view


def _as_route_contract(result: dict, route_capability: str) -> dict:
    """Give a worker's own output the shape the route contract requires.

    The Office worker predates the unified job contract: it returns its engine's own
    structure (paragraph or page anchors) and a receipt without coverage. The Core
    requires canonical line anchors over the projected text plus covered/total/coverage,
    so the transport derives them here and keeps the worker's own structure in
    `params.worker_structure` as a fact. The loss list says who derived what, because a
    reader must be able to tell the worker's measurement from the transport's.
    """
    text = result.get("text")
    if not isinstance(text, str):
        raise Rejected(f"{route_capability} produced no projected text", "AAK-WORK-002")
    lines = text.splitlines(keepends=True)
    anchors: list[dict] = []
    offset = 0
    for index, line in enumerate(lines, start=1):
        anchors.append(
            {"kind": "line", "path": [f"line-{index}"], "char_start": offset, "char_end": offset + len(line)}
        )
        offset += len(line)
    receipt = dict(result.get("loss_receipt") or {})
    params = dict(receipt.get("params") or {})
    worker_structure = result.get("structure")
    if worker_structure is not None and "worker_structure" not in params:
        params["worker_structure"] = worker_structure
        params["worker_structure_note"] = (
            "the worker's own structure is kept here as a fact; the structure the route contract carries is "
            "derived from the projected text"
        )
    # Any other top-level key the worker returned is kept too: the canvas worker reports
    # edges and references beside its structure, and dropping them here would be a
    # silent loss introduced by the adapter rather than by the engine.
    contract_keys = {"engine", "engine_version", "text", "structure", "loss_receipt"}
    extra = {key: value for key, value in result.items() if key not in contract_keys}
    if extra:
        params.setdefault("worker_output", {}).update(extra)
        params["worker_output_note"] = (
            "additional fields the worker returned are preserved verbatim here instead of being dropped"
        )
    params.setdefault("coverage_unit", "line anchors")
    losses = list(receipt.get("losses") or [])
    losses.append(
        "line anchors and coverage were derived by the transport from the worker's projected text; "
        "the worker's own structure is kept under params.worker_structure"
    )
    receipt.update(
        params=params,
        losses=losses,
        covered=len(anchors),
        total=len(lines),
        coverage=1.0,
    )
    receipt.setdefault("loss_note", "; ".join(losses))
    return {**result, "structure": anchors, "loss_receipt": receipt}


def _run_route(route, source: Path, media_type: str, artifact_root: Path | None = None) -> dict:
    """Load the route's worker and extract with its own entry-point shape."""
    relative_worker = Path(route["worker"])
    if relative_worker.parts[:2] == ("services", "python-workers"):
        relative_worker = Path(*relative_worker.parts[2:])
    spec = importlib.util.spec_from_file_location("route_worker", filesystem_path(WORKER_ROOT / relative_worker))
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
        view = _materialise_view(source, suffix)
        # OCR keeps its own explicit parameters: language plus the tessdata dir. The
        # language comes from the caller's configuration rather than being hardcoded, and
        # the directory is one that actually holds that language.
        language = _ocr_language()
        return module.extract(filesystem_path(view), language, _ocr_tessdata(language))
    if route["call"] == "transcribe":
        # The ASR worker dispatches on the suffix, and it takes its model directory and
        # language as arguments. Both default to the worker's own resolution - the declared
        # model and language detection - so the transport passes them only when an operator
        # has configured them, rather than inventing a default here.
        suffix = _AUDIO_SUFFIX.get(media_type.split(";", 1)[0].strip().lower())
        view = source
        if suffix is not None:
            view = _materialise_view(source, suffix)
        kwargs: dict = {}
        model_dir = os.environ.get("ARCHEAXIS_ASR_MODEL_DIR", "").strip()
        kwargs["model_path"] = model_dir or None
        # Default to detection: the language is a property of the recording, so the
        # transport does not pin one unless an operator has.
        kwargs["language"] = os.environ.get("ARCHEAXIS_ASR_LANG", "").strip() or "auto"
        kwargs["device"] = os.environ.get("ARCHEAXIS_ASR_DEVICE", "").strip() or "cpu"
        return _as_route_contract(module.extract(str(filesystem_path(view)), **kwargs),
                                  route.get("capability", "route"))
    if route.get("suffix_by_media"):
        suffix = route["suffix_by_media"].get(media_type.split(";", 1)[0].strip().lower())
        if suffix is None:
            raise Rejected("unsupported media type for this capability", "AAK-VAL-002")
        # the worker's own structure is kept as a fact while the route contract carries
        # canonical line anchors, so both the worker's view and the contract hold
        return _as_route_contract(
            module.extract(str(filesystem_path(_materialise_view(source, suffix)))), route.get("capability", "route")
        )
    if route.get("artifact_dir"):
        # R15/F06+F15: the attempt directory is temporary, so durable transfer files
        # (rendered PDF pages, extracted container members) go to the artifact root the
        # Core owns and verifies later by digest. Without one, the worker declares
        # nothing and writes nothing.
        if artifact_root is None:
            return module.extract(str(filesystem_path(source)))
        target = safe_path(artifact_root / route["artifact_dir"], missing=True)
        return module.extract(str(filesystem_path(source)), **{route.get("artifact_kwarg", "artifact_dir"): filesystem_path(target)})
    if route.get("media_type_arg"):
        return module.extract(str(filesystem_path(source)), media_type.split(";", 1)[0].strip().lower())
    if route.get("contract_adapter"):
        return _as_route_contract(module.extract(str(filesystem_path(source))), route.get("capability", "route"))
    return module.extract(str(filesystem_path(source)))


def execute(request, staging: Path, artifact_root: Path | None = None):
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
    if not filesystem_path(staging).is_dir():
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
    result = _run_route(route, source, asset["media_type"], artifact_root)
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
    filesystem_path(output_dir).mkdir(exist_ok=True)
    prepared = []
    # Check every pre-existing object before producing any new artifact.
    for kind, output_schema, media_type, data in artifacts:
        digest = hashlib.sha256(data).hexdigest()
        path = safe_path(output_dir / digest, missing=True)
        if filesystem_path(path).exists():
            previous, _ = read_regular(path)
            if previous != data:
                raise Rejected("existing output hash path contains different bytes", "AAK-HASH-001")
        prepared.append((kind, output_schema, media_type, data, digest, path))
    outputs = []
    for kind, output_schema, media_type, data, digest, path in prepared:
        check_deadline()
        safe_path(path, missing=True)
        if not filesystem_path(path).exists():
            with filesystem_path(path).open("xb") as handle:
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


def serve_stdio(worker_name: str, capabilities: list[str], staging_root: Path, artifact_root: Path | None = None) -> int:
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
        outputs, measurements, warnings = execute(request, staging_root, artifact_root)
        response.update(status="succeeded", outputs=outputs, measurements=measurements, warnings=warnings)
    except Rejected as exc:
        response.update(status="rejected", outputs=[], error={"code": exc.code, "message": str(exc), "retryable": False})
    except TimeoutError as exc:
        response.update(status="failed", outputs=[], error={"code": "AAK-WORKER-002", "message": str(exc), "retryable": True})
    except Exception as exc:
        response.update(status="failed", outputs=[], error={"code": "AAK-WORKER-003", "message": str(exc).replace("\\\\?\\", ""), "retryable": False})
    emit(response)
    return 0 if response["status"] == "succeeded" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-root", type=Path, required=True)
    # accepted for every route so one launch shape works for all of them; only a
    # route that declares an artifact directory writes anything there
    parser.add_argument("--artifact-root", type=Path, default=None)
    args = parser.parse_args()
    return serve_stdio("python-worker-text-ndjson", ["text.extract"], args.staging_root, args.artifact_root)


if __name__ == "__main__":
    raise SystemExit(main())
