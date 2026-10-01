"""Per-format matrix: what a real staged runtime converts, format by format.

Round 4 proved the joined path for one format (canvas). This generalises it, because a
single format cannot show whether the route declaration, the launcher, the Core
dispatcher and each worker all agree for *every* capability a candidate ships.

One real runtime root is built once, its profile's routes come from the stager's own
`present_routes`, and the Core is started through the launcher's own `load_profile` and
`start`. Every input is copied into the staged tree under `data/inputs/` before the Core
starts, so each job reads a real file inside the runtime rather than reaching back into
the checkout for a fixture.

    kind            input                          engine
    text            golden text anchor             python-worker-text
    pdf             golden journey evidence        python-worker-pdf
    image           golden screenshot (OCR)        python-worker-ocr
    office          golden docx / xlsx / pptx      python-worker-office
    html            golden web anchor              python-worker-html
    canvas          golden learning evidence       python-worker-canvas
    subtitles       sample srt                     python-worker-subtitles
    archive         generated zip of real files    python-worker-archive
    media           golden wav / mp4               python-worker-media

The run reports one verdict per entry and never promotes a failure to a pass. Engines
that need a model this host does not serve are absent from the matrix on purpose rather
than reported as passing.
"""

from __future__ import annotations

import base64
import contextlib
import importlib.util
import json
import os
import shutil
import sys
import time
import uuid
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "fixtures" / "golden"
LAUNCHER = REPO / "scripts" / "release" / "backend_launcher.py"
STAGER = REPO / "scripts" / "release" / "stage_backend_runtime.py"
VERIFIER = REPO / "scripts" / "release" / "verify_backend_capabilities.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


launcher = _load("launcher_matrix", LAUNCHER)
stager = _load("stager_matrix", STAGER)
core_client = _load("core_client_matrix", REPO / "shared" / "core_client.py")
verifier = _load("verifier_matrix", VERIFIER)

# (label, job kind, staged input name, source path or None for a generated input, language)
GOLDEN_MATRIX: list[tuple[str, str, str, Path | None, str]] = [
    ("text/txt", "text", "golden-text-anchor.txt", GOLDEN / "golden-text-anchor.txt", ""),
    ("pdf", "pdf", "golden-journey-evidence.pdf", GOLDEN / "golden-journey-evidence.pdf", ""),
    ("image/ocr", "image", "golden-screenshot-ocr.png", GOLDEN / "golden-screenshot-ocr.png", "eng"),
    ("office/docx", "office", "golden-docx-anchor.docx", GOLDEN / "golden-docx-anchor.docx", ""),
    ("office/xlsx", "office", "golden-xlsx-anchor.xlsx", GOLDEN / "golden-xlsx-anchor.xlsx", ""),
    ("office/pptx", "office", "golden-pptx-anchor.pptx", GOLDEN / "golden-pptx-anchor.pptx", ""),
    ("html", "html", "golden-web-anchor.html", GOLDEN / "golden-web-anchor.html", ""),
    ("canvas", "canvas", "learning-evidence.canvas", GOLDEN / "learning-evidence.canvas", ""),
    (
        "subtitles",
        "subtitles",
        "sample.srt",
        REPO / "tests" / "fixtures" / "vnext" / "documents" / "sample.srt",
        "",
    ),
    ("archive", "archive", "bundle.zip", None, ""),
    ("media/wav", "media", "golden-audio-anchor.wav", GOLDEN / "golden-audio-anchor.wav", ""),
    ("media/mp4", "media", "golden-video-anchor.mp4", GOLDEN / "golden-video-anchor.mp4", ""),
]

# Real-material mode: the same route set, sourced from a real learning library instead of
# the repository's synthetic fixtures. Set ARCHEAXIS_REAL_MATERIAL_ROOT to enable it; the
# probe then picks one real file per route and records its origin and sha256, so the
# receipt names the actual content that was converted.
MATERIAL_ROOT_ENV = "ARCHEAXIS_REAL_MATERIAL_ROOT"
MAX_MATERIAL_BYTES = int(os.environ.get("ARCHEAXIS_REAL_MAX_BYTES", str(4 * 1024 * 1024)))
# Vault tool state and machine-generated transcripts are not learning content.
SKIP_DIR_PARTS = {".obsidian", ".git", ".smart-env", ".copilot", "node_modules", "__pycache__"}
SKIP_NAME_TOKENS = tuple(part for part in
                         os.environ.get("ARCHEAXIS_REAL_EXCLUDE", "ASR").split(",") if part)

# label -> (job kind, candidate suffixes, language)
MATERIAL_ROUTES: dict[str, tuple[str, tuple[str, ...], str]] = {
    "text/md": ("text", (".md",), ""),
    "text/csv": ("text", (".csv",), ""),
    "text/json": ("text", (".json",), ""),
    "pdf": ("pdf", (".pdf",), ""),
    "image/ocr": ("image", (".png",), "chi_sim"),
    "office/docx": ("office", (".docx",), ""),
    "html": ("html", (".html",), ""),
    "canvas": ("canvas", (".canvas",), ""),
    "media/mp4": ("media", (".mp4",), ""),
}


def material_root() -> Path | None:
    raw = os.environ.get(MATERIAL_ROOT_ENV, "").strip()
    if not raw:
        return None
    root = Path(raw)
    return root if root.is_dir() else None


def usable_material(path: Path) -> bool:
    if any(part in SKIP_DIR_PARTS for part in path.parts):
        return False
    return not any(token and token in path.name for token in SKIP_NAME_TOKENS)


def pick_material(root: Path, suffixes: tuple[str, ...]) -> Path | None:
    """The smallest usable real file with one of these suffixes."""
    best: tuple[int, Path] | None = None
    for suffix in suffixes:
        for path in root.rglob(f"*{suffix}"):
            with contextlib.suppress(OSError):
                size = path.stat().st_size
                if 0 < size <= MAX_MATERIAL_BYTES and usable_material(path):
                    if best is None or size < best[0]:
                        best = (size, path)
    return best[1] if best else None


def build_matrix() -> tuple[list[tuple[str, str, str, Path | None, str]], Path | None]:
    """The route list and the material root in use, golden or real."""
    root = material_root()
    if root is None:
        return GOLDEN_MATRIX, None
    matrix: list[tuple[str, str, str, Path | None, str]] = []
    for label, (kind, suffixes, language) in MATERIAL_ROUTES.items():
        source = pick_material(root, suffixes)
        if source is None:
            continue
        matrix.append((label, kind, source.name, source, language))
    return matrix, root


def build_generated_input(destination: Path) -> None:
    """A real zip of real repository files, so the archive route reads a real container."""
    sources = [
        REPO / "tests" / "fixtures" / "golden" / "golden-text-anchor.txt",
        REPO / "tests" / "fixtures" / "golden" / "golden-web-anchor.html",
    ]
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as bundle:
        for source in sources:
            bundle.write(source, source.name)


def build_staged_tree(root: Path, core_binary: Path, runtime_python: Path,
                      matrix: list[tuple[str, str, str, Path | None, str]]) -> Path:
    """A runtime root: core/, workers/, data/inputs, profile.

    The profile's `python` is the runtime's own interpreter, named by absolute path, which
    is how a staged runtime works: the workers run under the interpreter the runtime
    ships, not under whatever started the probe. That interpreter must already carry the
    engines the format workers import - a standard-library-only interpreter reports
    `pdf engine missing`, `xlsx engine missing` and `pptx engine missing`, which is a
    packaging condition rather than a product defect.
    """
    (root / "core").mkdir(parents=True, exist_ok=True)
    shutil.copy2(core_binary, root / "core" / "archeaxis-api.exe")
    shutil.copytree(REPO / "services" / "python-workers", root / "workers",
                    ignore=shutil.ignore_patterns("__pycache__"))
    # The declared external-capability manifest travels with the runtime: resolving an
    # engine to its declared path is impossible without it, which showed up as
    # "tesseract binary not found on PATH" for a staged OCR job even though the engine is
    # installed and declared.
    manifest = REPO / "config" / "environment" / "capability-requirements.yaml"
    if manifest.is_file():
        (root / "config" / "environment").mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest, root / "config" / "environment" / manifest.name)
    inputs = root / "data" / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    for _label, _kind, name, source, _language in matrix:
        if source is None:
            build_generated_input(inputs / name)
        elif source.is_file():
            shutil.copy2(source, inputs / name)

    profile = {
        "schema": stager.PROFILE_SCHEMA,
        "python": str(runtime_python),
        "script": stager.TEXT_WORKER_RELATIVE,
        "staging": "data/worker-staging",
        "routes": stager.present_routes(root),
    }
    (root / "worker-profile.json").write_text(
        json.dumps(profile, indent=2) + "\n", encoding="utf-8", newline="\n")
    return root / "worker-profile.json"


def run_job(base: str, token: str, kind: str, staged_input: Path, labelled: str) -> dict:
    payload = staged_input.read_bytes()
    status, imported = core_client.call(
        base, "POST", "/api/v1/imports", token,
        core_client.import_request(staged_input.name, payload))
    source_id = imported.get("source_id") if isinstance(imported, dict) else None
    record: dict = {
        "case": labelled, "kind": kind, "input": staged_input.name,
        "bytes": len(payload), "import_status": status, "source_id": source_id,
    }
    if not 200 <= status < 300 or not source_id:
        record["verdict"] = "IMPORT_REFUSED"
        record["body"] = imported
        return record

    job_id = f"matrix-{kind}-{uuid.uuid4().hex[:8]}"
    status, queued = core_client.call(base, "POST", "/api/v1/jobs", token,
                                      {"job_id": job_id, "kind": kind, "input_ref": source_id})
    record["enqueue_status"] = status
    if not 200 <= status < 300:
        record["verdict"] = "ENQUEUE_REFUSED"
        record["body"] = queued
        return record

    status, started = core_client.call(
        base, "POST", f"/api/v1/jobs/{job_id}/executions", token,
        {"deadline_ms": 120000}, extra_headers={"idempotency-key": job_id})
    record["execute_status"] = status

    state, final = None, None
    for _ in range(200):
        _, final = core_client.call(base, "GET", f"/api/v1/jobs/{job_id}", token)
        state = final.get("state") if isinstance(final, dict) else None
        if state in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(0.25)
    record["job_state"] = state
    if isinstance(final, dict) and final.get("error"):
        record["error"] = str(final["error"])[:2000]

    if state == "succeeded":
        status, output = core_client.call(
            base, "GET", f"/api/v1/jobs/{job_id}/outputs/text", token)
        record["output_status"] = status
        if isinstance(output, dict):
            text = str(output.get("content") or output.get("text") or "")
            record["output_chars"] = len(text)
        status, quality = core_client.call(base, "GET", f"/api/v1/jobs/{job_id}/quality", token)
        if isinstance(quality, dict):
            record["engine"] = quality.get("engine")
            record["covered"] = quality.get("covered")
            record["total"] = quality.get("total")
        record["verdict"] = "CONVERTED"
    elif state == "failed":
        record["verdict"] = "FAILED_AT_ROUTE"
    else:
        record["verdict"] = "UNSETTLED"
    return record


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")
    core_binary = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    runtime_python = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if core_binary is None or not core_binary.is_file():
        print(json.dumps({"ok": False, "blocked": "pass the built Core binary as argv[1]"}))
        return 2
    if runtime_python is None or not runtime_python.is_file():
        print(json.dumps({
            "ok": False,
            "blocked": "pass the provisioned runtime python.exe as argv[2]",
        }))
        return 2

    matrix, material = build_matrix()
    if not matrix:
        print(json.dumps({"ok": False, "blocked": "no inputs selected",
                          "material_root": os.environ.get(MATERIAL_ROOT_ENV, "")}))
        return 2

    root = REPO / ".project-local" / "runs" / "staged-matrix"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    profile_path = build_staged_tree(root, core_binary, runtime_python, matrix)
    inputs = root / "data" / "inputs"

    # Readiness first: whether each route the profile declares is actually usable on the
    # interpreter it names. Reported alongside the job results so a failure can be
    # attributed to the route or to the packaging rather than guessed at.
    readiness = verifier.verify(root, runtime_python, None, None)

    receipt: dict = {
        "ok": False,
        "staged_root": str(root),
        "core_binary": str(core_binary),
        "runtime_python": str(runtime_python),
        "evidence_level": "REAL_STAGED_RUNTIME",
        "input_source": "real_material" if material else "repository_golden_corpus",
        "material_root": str(material) if material else "",
        "declared_routes": json.loads(profile_path.read_text(encoding="utf-8")).get("routes", []),
        "readiness": {
            "ok": readiness.get("ok"),
            "summary": readiness.get("summary"),
            "not_ready": [
                {"capability": entry["capability"],
                 "launch": entry["launch"].get("reason"),
                 "engine": entry["engine"]}
                for entry in readiness.get("capabilities", [])
                if not entry.get("ok")
            ],
        },
        "external_engine_root": launcher.os.environ.get("ARCHEAXIS_EXTERNAL_ROOT", ""),
        "results": [],
    }
    receipt["readiness_ok"] = bool(readiness.get("ok"))

    launcher.ROOT = root
    child, base, _start_receipt, tokens = launcher.start(root / "data", 0)
    token = launcher.credential(tokens, "human")["x-archeaxis-launch-token"]
    try:
        status, version = core_client.call(base, "GET", "/api/v1/system/version", token)
        receipt["system_version_status"] = status
        receipt["system_version"] = version if isinstance(version, dict) else str(version)
        for labelled, kind, name, source, _language in matrix:
            staged_input = inputs / name
            if not staged_input.is_file():
                receipt["results"].append({
                    "case": labelled, "kind": kind, "input": name,
                    "verdict": "INPUT_ABSENT", "note": "source file not present",
                })
                continue
            record = run_job(base, token, kind, staged_input, labelled)
            if source is not None:
                record["origin"] = str(source)
            receipt["results"].append(record)
    finally:
        launcher.stop(child)

    counts: dict[str, int] = {}
    for record in receipt["results"]:
        counts[record["verdict"]] = counts.get(record["verdict"], 0) + 1
    receipt["verdict_counts"] = counts
    receipt["converted"] = [r["case"] for r in receipt["results"] if r["verdict"] == "CONVERTED"]
    receipt["not_converted"] = [r["case"] for r in receipt["results"] if r["verdict"] != "CONVERTED"]

    # `ok` is the acceptance verdict, not "the probe finished": every declared route must
    # be ready on the runtime and every selected case must convert. A probe that merely
    # completed while cases failed would otherwise read as a pass.
    all_converted = not receipt["not_converted"] and bool(receipt["results"])
    receipt["accepted"] = bool(receipt["readiness_ok"]) and all_converted
    receipt["ok"] = receipt["accepted"]
    receipt["verdict_reason"] = (
        "ready and every case converted" if receipt["accepted"]
        else "; ".join(filter(None, [
            "" if receipt["readiness_ok"] else "declared routes are not all ready",
            "" if all_converted else f"cases not converted: {receipt['not_converted']}",
        ]))
    )
    out = root / "staged-format-matrix.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in
                      ("ok", "accepted", "verdict_reason", "evidence_level",
                       "input_source", "readiness_ok", "readiness", "verdict_counts",
                       "converted", "not_converted", "declared_routes")},
                     ensure_ascii=False, indent=2))
    print(f"\nreceipt: {out}")
    return 0 if receipt["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
