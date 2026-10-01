"""Convert REAL user learning material through the real Core, per format route.

`production_format_coverage_smoke.py` measures reachability against the repository's
own synthetic golden corpus.  This probe answers the complementary question: when
the input is a real course library instead of a fixture, what does the shipped
Core actually do?

The material is the Obsidian knowledge base under `ARCHEAXIS_REAL_MATERIAL_ROOT`
(default `D:/All projects/ceshi`): course notes, term cards, course maps and a real
frontend project.  The Core ingests bytes (`POST /api/v1/imports` takes
`content_base64`), so a real file outside the repository can be converted without
copying it into the tree; the receipt records the absolute origin path and the
sha256 of the bytes that were actually sent, so the evidence names its source.

Classification matters: the transport is *real input* (real bytes from a real
library), while whether it qualifies as *real user learning* depends on the file,
so this probe reports the bytes and the outcome and leaves the qualification to the
reader.  It never claims a model was called.

Same production launch shape as the format probe: argv `<core> <db> 0`, one launch
JSON on stdin, one `text_worker` script, no extra capability routes.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BINARY = Path(os.environ.get(
    "ARCHEAXIS_CORE_BIN",
    str(REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe")))
# The material root is an external, Owner-supplied resource, so it is never baked in
# here: this probe reads it from the environment and fails closed when it is absent.
# That is the same rule the product should follow - resolve a declared location
# instead of guessing one (R6 A02: exact paths, no PATH guessing).
MATERIAL_ROOT_ENV = "ARCHEAXIS_REAL_MATERIAL_ROOT"
_raw_root = os.environ.get(MATERIAL_ROOT_ENV, "").strip()
MATERIAL_ROOT = Path(_raw_root) if _raw_root else None
MAX_BYTES = int(os.environ.get("ARCHEAXIS_REAL_MAX_BYTES", str(256 * 1024)))
MIN_BYTES = int(os.environ.get("ARCHEAXIS_REAL_MIN_BYTES", "200"))
# Excluded substrings, comma separated.  The default skips machine-generated
# transcripts so a "real material" claim names human-authored notes rather than
# speech-recognition output that happens to share the .md extension.
EXCLUDE = tuple(part for part in os.environ.get(
    "ARCHEAXIS_REAL_EXCLUDE", "ASR").split(",") if part)
# Vault-internal folders that hold tool state, not learning material.
SKIP_DIRS = {".obsidian", ".git", ".smart-env", ".copilot", "node_modules"}

TOKEN = "c" * 64
MACHINE_TOKEN = "e" * 64
SESSION = "d" * 32
LAUNCH = {
    "launch_token": TOKEN,
    "session_id": SESSION,
    "actor": "human",
    "protocol": "archeaxis.desktop-launch/v2",
    "machine_token": MACHINE_TOKEN,
}
WORKER_SCRIPT = "services/python-workers/transport/text_ndjson.py"

# One representative real file per Core route kind.  Extensions are what the Core's
# own `attempts::resolve_media_type` maps a name to, so the kind must agree with the
# file name or the claim is refused before a worker is ever spawned.
KINDS: list[tuple[str, tuple[str, ...]]] = [
    ("text", (".md", ".txt", ".csv", ".json")),
    ("canvas", (".canvas",)),
    ("html", (".html",)),
    ("pdf", (".pdf",)),
    ("office", (".docx",)),
    ("image", (".png",)),
]


def _load(name: str, path: Path):
    """Load a module by file path (the architecture guard forbids sys.path edits)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


core = _load("core_client_real", REPO / "shared" / "core_client.py")
launcher = _load("launcher_real", REPO / "scripts/release/backend_launcher.py")


def _usable(path: Path) -> bool:
    """A real note: the right size, not tool state, not a machine transcript."""
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if any(token and token in path.name for token in EXCLUDE):
        return False
    return True


def pick(kind: str, exts: tuple[str, ...]) -> Path | None:
    """Smallest usable real file, so the run stays bounded and low-noise."""
    best: tuple[int, Path] | None = None
    for ext in exts:
        for path in MATERIAL_ROOT.rglob(f"*{ext}"):
            with contextlib.suppress(OSError):
                size = path.stat().st_size
                if (MIN_BYTES <= size <= MAX_BYTES and _usable(path)
                        and (best is None or size < best[0])):
                    best = (size, path)
    return best[1] if best else None


def corpus_size() -> dict:
    """How much real material the selection was drawn from, by extension."""
    counts: dict[str, int] = {}
    for path in MATERIAL_ROOT.rglob("*"):
        with contextlib.suppress(OSError):
            if path.is_file() and _usable(path):
                counts[path.suffix.casefold()] = counts.get(path.suffix.casefold(), 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1])[:12])


def start_core(db: Path, staging: Path):
    worker = {
        "python": str(Path(sys.executable).resolve()),
        "script": str((REPO / WORKER_SCRIPT).resolve()),
        "staging": str(staging.resolve()),
    }
    child = launcher.subprocess.Popen(
        [str(BINARY), str(db), "0"],
        stdin=launcher.subprocess.PIPE, stdout=launcher.subprocess.PIPE,
        stderr=launcher.subprocess.PIPE, text=True, encoding="utf-8",
    )
    try:
        child.stdin.write(json.dumps({**LAUNCH, "text_worker": worker}) + "\n")
        child.stdin.flush()
        child.stdin.close()
        return child, launcher.wait_for_readiness(child, 0, 25)
    except BaseException:
        launcher.stop(child)
        raise


def convert(base: str, path: Path, kind: str) -> dict:
    payload = path.read_bytes()
    origin = str(path)
    try:
        shown = str(path.relative_to(MATERIAL_ROOT))
    except ValueError:
        shown = origin
    record: dict = {
        "kind": kind, "origin": origin, "origin_relative": shown,
        "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
    }
    status, imported = core.call(base, "POST", "/api/v1/imports", TOKEN,
                                core.import_request(path.name, payload))
    source_id = imported.get("source_id") if isinstance(imported, dict) else None
    record["import_status"] = status
    record["source_id"] = source_id
    if not 200 <= status < 300 or not source_id:
        record["verdict"] = "IMPORT_REFUSED"
        record["body"] = imported
        return record

    job_id = f"real-{kind}-{uuid.uuid4().hex[:10]}"
    status, queued = core.call(base, "POST", "/api/v1/jobs", TOKEN,
                               {"job_id": job_id, "kind": kind, "input_ref": source_id})
    record["enqueue_status"] = status
    if not 200 <= status < 300:
        record["verdict"] = "ENQUEUE_REFUSED"
        record["body"] = queued
        return record

    status, _ = core.call(
        base, "POST", f"/api/v1/jobs/{job_id}/executions", TOKEN,
        {"deadline_ms": 120000}, extra_headers={"idempotency-key": job_id})
    record["execute_status"] = status

    state, final = None, None
    for _ in range(120):
        _, final = core.call(base, "GET", f"/api/v1/jobs/{job_id}", TOKEN)
        state = final.get("state") if isinstance(final, dict) else None
        if state in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(0.25)
    record["job_state"] = state
    if isinstance(final, dict) and final.get("error"):
        record["error"] = final["error"]

    if state == "succeeded":
        status, output = core.call(
            base, "GET", f"/api/v1/jobs/{job_id}/outputs/text", TOKEN)
        record["output_status"] = status
        if isinstance(output, dict):
            text = str(output.get("content") or output.get("text") or "")
            record["output_chars"] = len(text)
            record["output_head"] = text[:160]
        status, quality = core.call(base, "GET", f"/api/v1/jobs/{job_id}/quality", TOKEN)
        if isinstance(quality, dict):
            record["quality"] = {k: quality.get(k) for k in
                                 ("engine", "engine_version", "covered", "total")
                                 if quality.get(k) is not None}
        record["verdict"] = "CONVERTED"
    elif state == "failed":
        record["verdict"] = "FAILED_AT_ROUTE"
    else:
        record["verdict"] = "UNSETTLED"
    return record


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    if not BINARY.is_file():
        print(json.dumps({"ok": False, "blocked": "core binary not built",
                          "path": str(BINARY)}))
        return 2
    if MATERIAL_ROOT is None or not MATERIAL_ROOT.is_dir():
        print(json.dumps({
            "ok": False,
            "blocked": "material root not configured",
            "env": MATERIAL_ROOT_ENV,
            "value": _raw_root,
            "note": "point this at the real learning-material root to run the probe",
        }, ensure_ascii=False))
        return 2

    work = REPO / ".project-local" / "runs" / "m0real" / uuid.uuid4().hex[:12]
    work.mkdir(parents=True, exist_ok=True)
    receipt: dict = {
        "ok": False,
        "evidence_level": "REAL_INPUT_MATERIAL",
        "material_root": str(MATERIAL_ROOT),
        "max_bytes": MAX_BYTES,
        "min_bytes": MIN_BYTES,
        "excluded_name_tokens": list(EXCLUDE),
        "corpus_real_file_counts": corpus_size(),
        "workdir": str(work),
        "configured_worker": WORKER_SCRIPT,
        "results": [],
    }

    selected: list[tuple[str, Path]] = []
    for kind, exts in KINDS:
        found = pick(kind, exts)
        if found is not None:
            selected.append((kind, found))
    receipt["selected_count"] = len(selected)

    child, base = start_core(work / "workspace.sqlite", work / "worker-staging")
    try:
        status, version = core.call(base, "GET", "/api/v1/system/version", TOKEN)
        receipt["system_version_status"] = status
        for kind, path in selected:
            receipt["results"].append(convert(base, path, kind))
    finally:
        launcher.stop(child)

    counts: dict[str, int] = {}
    for record in receipt["results"]:
        counts[record["verdict"]] = counts.get(record["verdict"], 0) + 1
    receipt["verdict_counts"] = counts
    receipt["converted"] = [r["origin_relative"] for r in receipt["results"]
                            if r["verdict"] == "CONVERTED"]
    receipt["not_converted"] = [r["origin_relative"] for r in receipt["results"]
                                if r["verdict"] != "CONVERTED"]
    receipt["ok"] = True
    out = work / "real-material-conversion.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
    print(f"\nreceipt: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
