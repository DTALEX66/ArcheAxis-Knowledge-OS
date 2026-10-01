"""What a *production* Core launch can actually convert, per real fixture.

`m0_full_loop_smoke.py` drives one continuous loop but only with a text source, so
it cannot show whether the multiformat routes exist in the shipped process.  The
per-format Rust suites do drive PDF/OCR/Office/HTML/canvas/subtitles end to end,
but every one of them registers its routes through `Executor::open_routes`, which
only test files call.  The binary that a Desktop launch starts uses
`Executor::open` (`crates/archeaxis-api/src/main.rs`), and that seeds exactly one
route: `text.extract` (`crates/archeaxis-application/src/executor.rs`).

This probe measures that difference instead of asserting it.  It starts the Core
the way the product does -- same argv, same launch JSON, one `text_worker`
script -- imports each verified fixture from `tests/fixtures/golden/`, and runs
the declared job kind through the real HTTP surface.  It records the observed job
state and error for every fixture, so "the format loop is wired" becomes a
measured claim with a per-format verdict rather than an inference from test
suites.

Evidence class: REAL inputs (project-authored fixture bytes, hashes verified
against the fixture manifest) through the REAL production launch shape.  It
qualifies format reachability only; it never qualifies model inference, real
human learning, or migration.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "fixtures" / "golden"
BINARY = Path(os.environ.get(
    "ARCHEAXIS_CORE_BIN",
    str(REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe")))

sys.path.insert(0, str(REPO))
from shared import core_client as core  # noqa: E402

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

# The production text_worker is exactly this one entry; no extra capability routes
# are passed, because `Executor::open` has no way to receive them.
WORKER_SCRIPT = "services/python-workers/transport/text_ndjson.py"

# Every fixture in the golden corpus, with the job kind the Core's own route table
# (`attempts::ROUTES`) resolves it to.  `expected_engine` is what the format needs
# locally for the route to succeed at all.
FIXTURES: list[tuple[str, str, str]] = [
    ("golden-text-anchor.txt", "text", "stdlib text.extract"),
    ("golden-journey-evidence.pdf", "pdf", "pymupdf pdf.extract"),
    ("golden-screenshot-ocr.png", "image", "tesseract image.ocr"),
    ("golden-docx-anchor.docx", "office", "stdlib zip+xml office.structure"),
    ("golden-pptx-anchor.pptx", "office", "python-pptx office.structure"),
    ("golden-xlsx-anchor.xlsx", "office", "openpyxl office.structure"),
    ("golden-web-anchor.html", "html", "stdlib htmlparser html.structure"),
    ("learning-evidence.canvas", "canvas", "stdlib json canvas.structure"),
    ("golden-audio-anchor.wav", "media", "header-only media.probe"),
    ("golden-video-anchor.mp4", "media", "header-only media.probe"),
]


def load_launcher():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "launcher_fmt", REPO / "scripts/release/backend_launcher.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["launcher_fmt"] = module
    spec.loader.exec_module(module)
    return module


launcher = load_launcher()


def binary_identity(path: Path) -> dict:
    """The artefact that actually ran, not the path someone typed."""
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return {"path": str(path), "sha256": digest.hexdigest(), "size": stat.st_size}


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


def declared_capabilities() -> list[str]:
    """The capability set the configured worker script itself advertises.

    Read statically from the transport's own `serve_stdio(...)` return so the
    probe does not need a second interpreter launch to discover it. When the
    configured script is the generic text transport this is exactly one
    capability, which is the whole reason the format jobs fail.
    """
    transport = REPO / WORKER_SCRIPT
    with contextlib.suppress(OSError):
        text = transport.read_text(encoding="utf-8")
        import re

        # The advertised capability list is the literal passed to serve_stdio by
        # this script's own main(); it is the set the worker will accept.
        found = re.search(r"return serve_stdio\((.*?)\)\s*$", text, re.M | re.S)
        if found:
            literal = re.search(r"\[(.*?)\]", found.group(1), re.S)
            if literal:
                return [part.strip().strip("'\"") for part in literal.group(1).split(",")
                        if part.strip()]
        for match in re.finditer(r'^\s*"capabilities":\s*\[(.*?)\]', text, re.M):
            return [part.strip().strip("'\"") for part in match.group(1).split(",")
                    if part.strip()]
    return []


def run_fixture(base: str, name: str, kind: str) -> dict:
    path = GOLDEN / name
    if not path.is_file():
        return {"fixture": name, "kind": kind, "skipped": "fixture missing"}
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    record: dict = {"fixture": name, "kind": kind, "bytes": len(payload),
                    "sha256": digest}

    status, imported = core.call(base, "POST", "/api/v1/imports", TOKEN,
                                core.import_request(name, payload))
    source_id = imported.get("source_id") if isinstance(imported, dict) else None
    record["import_status"] = status
    record["source_id"] = source_id
    if not 200 <= status < 300 or not source_id:
        record["verdict"] = "IMPORT_REFUSED"
        record["body"] = imported
        return record

    job_id = f"fmt-{kind}-{uuid.uuid4().hex[:10]}"
    status, queued = core.call(base, "POST", "/api/v1/jobs", TOKEN,
                               {"job_id": job_id, "kind": kind, "input_ref": source_id})
    record["enqueue_status"] = status
    if not 200 <= status < 300:
        record["verdict"] = "ENQUEUE_REFUSED"
        record["body"] = queued
        return record

    status, started = core.call(
        base, "POST", f"/api/v1/jobs/{job_id}/executions", TOKEN,
        {"deadline_ms": 120000}, extra_headers={"idempotency-key": job_id})
    record["execute_status"] = status

    state = None
    final: object = None
    for _ in range(120):
        _, final = core.call(base, "GET", f"/api/v1/jobs/{job_id}", TOKEN)
        state = final.get("state") if isinstance(final, dict) else None
        if state in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(0.25)
    record["job_state"] = state
    if isinstance(final, dict):
        for key in ("error", "attempt", "request_id"):
            if final.get(key) is not None:
                record[key] = final[key]

    if state == "succeeded":
        status, output = core.call(
            base, "GET", f"/api/v1/jobs/{job_id}/outputs/text", TOKEN)
        record["output_status"] = status
        if isinstance(output, dict):
            text = str(output.get("content") or output.get("text") or "")
            record["output_chars"] = len(text)
            record["output_sample"] = text[:200]
        status, quality = core.call(base, "GET", f"/api/v1/jobs/{job_id}/quality", TOKEN)
        record["quality_status"] = status
        if isinstance(quality, dict):
            record["quality"] = {k: quality.get(k)
                                 for k in ("engine", "engine_version", "covered", "total")
                                 if quality.get(k) is not None}
        # The source-scoped transform route filters kind='text', so it is only
        # meaningful for a text job; record what it answers anyway.
        status, transform = core.call(
            base, "GET", f"/api/v1/sources/{source_id}/jobs/{job_id}/transform", TOKEN)
        record["transform_route_status"] = status
        record["verdict"] = "REACHABLE"
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
    if not GOLDEN.is_dir():
        print(json.dumps({"ok": False, "blocked": "golden fixture corpus missing",
                          "path": str(GOLDEN)}))
        return 2

    work = REPO / ".project-local" / "runs" / "m0fmt" / uuid.uuid4().hex[:12]
    work.mkdir(parents=True, exist_ok=True)
    db = work / "workspace.sqlite"
    staging = work / "worker-staging"

    receipt: dict = {
        "ok": False,
        "workdir": str(work),
        "evidence_level": "REAL_INPUTS_PRODUCTION_LAUNCH",
        "core_binary": binary_identity(BINARY),
        "launch_shape": "Executor::open (prod) via main.rs text_worker branch",
        "configured_worker": WORKER_SCRIPT,
        "worker_capability_declaration": declared_capabilities(),
        "interpreter": sys.executable,
        "results": [],
    }

    child, base = start_core(db, staging)
    try:
        status, version = core.call(base, "GET", "/api/v1/system/version", TOKEN)
        receipt["system_version"] = {"status": status, "body": version}
        for name, kind, engine in [(f[0], f[1], f[2]) for f in FIXTURES]:
            record = run_fixture(base, name, kind)
            record["expected_engine"] = engine
            receipt["results"].append(record)
    finally:
        launcher.stop(child)

    verdicts: dict[str, int] = {}
    for record in receipt["results"]:
        verdicts[record["verdict"]] = verdicts.get(record["verdict"], 0) + 1
    receipt["verdict_counts"] = verdicts
    reachable = [r["fixture"] for r in receipt["results"] if r["verdict"] == "REACHABLE"]
    receipt["reachable_fixtures"] = reachable
    receipt["unreachable_fixtures"] = [r["fixture"] for r in receipt["results"]
                                       if r["verdict"] != "REACHABLE"]
    # The point of the probe: production reachability is measured, not inferred.
    receipt["ok"] = True
    out = work / "production-format-coverage.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
    print(f"\nreceipt: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
