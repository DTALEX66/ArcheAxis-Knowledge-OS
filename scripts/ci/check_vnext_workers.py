#!/usr/bin/env python3
"""vNext capability-worker smoke gate (workers-vnext).

Runs against the real worker entrypoints in services/python-workers:

- every worker module compiles;
- worker_extract returns the JSON envelope contract on a real file
  (engine/engine_version/text/loss_receipt; BOM stripped);
- a missing input exits non-zero with {"error": ...} — never a fake success.

The protocol envelope is defined in
packages/contracts/v1/worker-protocol.schema.json.
"""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKERS = ROOT / "services" / "python-workers"
WORKER_EXTRACT = WORKERS / "worker_extract.py"

ENVELOPE_KEYS = ("engine", "engine_version", "text", "loss_receipt")

WORKER_MATRIX = {
    "document/worker_text.py": {"fixture": "sample.md", "keys": ("engine", "text", "structure", "loss_receipt")},
    "document/worker_canvas.py": {"fixture": "sample.canvas", "keys": ("engine", "text", "structure", "edges", "references", "loss_receipt")},
    "document/worker_subtitles.py": {"fixture": "sample.srt", "keys": ("engine", "text", "structure", "loss_receipt")},
    "web/worker_html.py": {"fixture": "sample-page.html", "keys": ("engine", "text", "title", "links", "structure", "loss_receipt")},
}


def _run(entrypoint: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    import os

    child_env = dict(os.environ)
    child_env.setdefault("PYTHONUTF8", "1")
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run(
        [sys.executable, str(entrypoint), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=child_env,
        timeout=60,
    )


def _run_worker(args: list[str], *, text: str | None = None) -> subprocess.CompletedProcess[str]:
    return _run(WORKER_EXTRACT, args)


def _run_matrix_worker(relative: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return _run(WORKERS / relative, args)


def main() -> int:
    failures: list[str] = []
    if not WORKER_EXTRACT.is_file():
        print(f"ERROR: worker entrypoint missing: {WORKER_EXTRACT}")
        return 1

    modules = sorted(WORKERS.glob("*.py"))
    for module in modules:
        try:
            py_compile.compile(str(module), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"{module.name}: compile failed: {exc}")

    with tempfile.TemporaryDirectory() as tmp:
        sample = Path(tmp) / "sample.txt"
        sample.write_bytes("\ufeffBOM-marked 原件内容 hello\n".encode("utf-8"))
        ok = _run_worker([str(sample)])
        if ok.returncode != 0:
            failures.append(f"worker_extract exit {ok.returncode}: {ok.stderr.strip()[:300]}")
        else:
            try:
                envelope = json.loads(ok.stdout.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError) as exc:
                failures.append(f"worker_extract stdout not a JSON envelope: {exc}")
                envelope = {}
            for key in ENVELOPE_KEYS:
                if key not in envelope:
                    failures.append(f"worker_extract envelope missing key: {key}")
            if envelope.get("text") != "BOM-marked 原件内容 hello\n":
                failures.append(
                    f"worker_extract text mismatch (BOM must be stripped): {envelope.get('text')!r}"
                )
            if not isinstance(envelope.get("loss_receipt"), dict):
                failures.append("worker_extract loss_receipt must be an object")

    missing = _run_worker([str(Path(tmp) / "does-not-exist.txt")])
    if missing.returncode == 0:
        failures.append("worker_extract succeeded on a missing file (must fail)")
    else:
        try:
            error_payload = json.loads(
                (missing.stdout or missing.stderr).strip().splitlines()[-1]
            )
        except (json.JSONDecodeError, IndexError):
            error_payload = {}
        if "error" not in error_payload:
            failures.append(
                "worker failure output must carry an error payload, "
                f"got: {(missing.stdout or missing.stderr).strip()[:200]!r}"
            )

    fixtures = ROOT / "tests" / "fixtures" / "vnext" / "documents"
    for relative, spec in WORKER_MATRIX.items():
        entrypoint = WORKERS / relative
        try:
            py_compile.compile(str(entrypoint), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"{relative}: compile failed: {exc}")
            continue
        fixture = fixtures / spec["fixture"]
        if not fixture.is_file():
            failures.append(f"{relative}: fixture missing: {fixture.name}")
            continue
        run = _run_matrix_worker(relative, [str(fixture)])
        if run.returncode != 0:
            failures.append(f"{relative} exit {run.returncode}: {run.stderr.strip()[:300]}")
            continue
        try:
            envelope = json.loads(run.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as exc:
            failures.append(f"{relative} stdout not a JSON envelope: {exc}")
            continue
        for key in spec["keys"]:
            if key not in envelope:
                failures.append(f"{relative} envelope missing key: {key}")
        if relative == "document/worker_canvas.py":
            edges = envelope.get("edges")
            if not isinstance(edges, list) or len(edges) != 2:
                failures.append(f"{relative} must preserve both canvas edges verbatim")
            if not envelope.get("text"):
                failures.append(f"{relative} text projection must not be empty")
            references = envelope.get("references")
            if not isinstance(references, list) or len(references) != 2:
                failures.append(f"{relative} must surface file/link nodes as references")
            edge_ids = {e.get("id") for e in edges}
            if not {"e1", "e2"} <= edge_ids:
                failures.append(f"{relative} edge ids must survive verbatim")
        if relative == "web/worker_html.py":
            title = envelope.get("title")
            if "托卡马克" not in str(title):
                failures.append(f"{relative} must extract the document title")
            text = envelope.get("text", "")
            if "1e20" not in text or "script" in text.lower():
                failures.append(f"{relative} must keep body numbers and drop scripts")
            links = envelope.get("links")
            if not isinstance(links, list) or len(links) != 2:
                failures.append(f"{relative} must keep both href links")
            structure = envelope.get("structure")
            if not isinstance(structure, list) or len(structure) < 4:
                failures.append(f"{relative} must emit paragraph/list block anchors")

        if relative == "document/worker_subtitles.py":
            structure = envelope.get("structure")
            if not isinstance(structure, list) or len(structure) != 3:
                failures.append(f"{relative} must parse three cues with time anchors")
            first = structure[0] if isinstance(structure, list) and structure else {}
            if first.get("offset_ms") != 1000 or first.get("duration_ms") != 2500:
                failures.append(f"{relative} first cue timing anchors wrong: {first}")

    # VTT path: same worker, WEBVTT fixture, timing preserved, tags stripped.
    vtt = fixtures / "sample.vtt"
    if vtt.is_file():
        vtt_run = _run_matrix_worker("document/worker_subtitles.py", [str(vtt)])
        if vtt_run.returncode != 0:
            failures.append(f"worker_subtitles(vtt) exit {vtt_run.returncode}: {vtt_run.stderr.strip()[:300]}")
        else:
            try:
                envelope = json.loads(vtt_run.stdout.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError) as exc:
                failures.append(f"worker_subtitles(vtt) invalid envelope: {exc}")
                envelope = {}
            structure = envelope.get("structure")
            if not isinstance(structure, list) or len(structure) != 3:
                failures.append("worker_subtitles(vtt) must parse three cues")
            if "<v" in envelope.get("text", ""):
                failures.append("worker_subtitles(vtt) must strip inline voice tags")
            first = structure[0] if isinstance(structure, list) and structure else {}
            if first.get("offset_ms") != 1000 or first.get("duration_ms") != 2500:
                failures.append(f"worker_subtitles(vtt) first cue timing anchors wrong: {first}")
    else:
        failures.append("missing VTT fixture: sample.vtt")

    # Media worker (F10): compile + probe + failure contracts. Real inference
    # is NOT run in CI (no model artifacts on runners); local verification is
    # recorded in the T06 slice receipt with a truthful capability note.
    media_worker = WORKERS / "media" / "worker_transcribe.py"
    try:
        py_compile.compile(str(media_worker), doraise=True)
    except py_compile.PyCompileError as exc:
        failures.append(f"media/worker_transcribe.py: compile failed: {exc}")
    else:
        probe_run = _run_matrix_worker("media/worker_transcribe.py", ["--probe", "--model-dir", "/nonexistent"])
        if probe_run.returncode != 0:
            failures.append(f"media probe exit {probe_run.returncode}: {probe_run.stderr.strip()[:200]}")
        else:
            try:
                probe_payload = json.loads(probe_run.stdout.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError) as exc:
                failures.append(f"media probe invalid payload: {exc}")
                probe_payload = {}
            if probe_payload.get("capability") is not False:
                failures.append("media probe must report capability=false for a missing model dir")
        bad_run = _run_matrix_worker("media/worker_transcribe.py", ["/nonexistent-input.wav"])
        if bad_run.returncode == 0:
            failures.append("media worker succeeded on a missing input file (must fail)")
        else:
            tail = (bad_run.stdout or bad_run.stderr).strip().splitlines()[-1] if (bad_run.stdout or bad_run.stderr).strip() else ""
            if "error" not in tail:
                failures.append("media worker failure must carry an error payload")

    # Evaluation worker (T07): recomputable CER/WER metrics (stdlib only).
    quality_worker = WORKERS / "evaluation" / "worker_quality.py"
    try:
        py_compile.compile(str(quality_worker), doraise=True)
    except py_compile.PyCompileError as exc:
        failures.append(f"evaluation/worker_quality.py: compile failed: {exc}")
    else:
        with tempfile.TemporaryDirectory() as qtmp:
            gold_path = Path(qtmp) / "gold.txt"
            pred_path = Path(qtmp) / "pred.txt"
            gold_path.write_text("the quick brown fox jumps over the lazy dog", encoding="utf-8")
            pred_path.write_text("the quick brown fox jumps over the lazy cat", encoding="utf-8")
            run1 = _run_matrix_worker("evaluation/worker_quality.py", [str(pred_path), str(gold_path), "--sample-id", "en_001", "--run-id", "gate"])
            if run1.returncode != 0:
                failures.append(f"quality worker exit {run1.returncode}: {run1.stderr.strip()[:200]}")
            else:
                try:
                    report = json.loads(run1.stdout.strip().splitlines()[-1])
                except (json.JSONDecodeError, IndexError) as exc:
                    failures.append(f"quality worker invalid report: {exc}")
                    report = {}
                rows = {row.get("metric"): row for row in report.get("rows", [])}
                if "cer" not in rows or "wer" not in rows:
                    failures.append("quality worker must emit cer and wer rows")
                else:
                    if rows["cer"].get("status") != "measured" or not isinstance(rows["cer"].get("value"), (int, float)):
                        failures.append("quality worker cer must be measured with a value")
                    if not (0.0 <= rows["cer"]["value"] <= 1.0):
                        failures.append(f"quality worker cer out of range: {rows['cer']['value']}")
                    if not (0.0 < rows["wer"]["value"] <= 1.0):
                        failures.append(f"quality worker wer must reflect the single-token substitution: {rows['wer']['value']}")
                    if not rows["cer"]["prediction_ref"]["sha256"] or not rows["cer"]["gold_ref"]["sha256"]:
                        failures.append("quality worker must carry prediction/gold sha256 refs")
            empty_gold = Path(qtmp) / "empty.txt"
            empty_gold.write_text("", encoding="utf-8")
            run2 = _run_matrix_worker("evaluation/worker_quality.py", [str(pred_path), str(empty_gold), "--sample-id", "en_002", "--run-id", "gate"])
            if run2.returncode != 0:
                failures.append(f"quality worker(empty gold) exit {run2.returncode}")
            else:
                try:
                    report2 = json.loads(run2.stdout.strip().splitlines()[-1])
                except (json.JSONDecodeError, IndexError):
                    report2 = {}
                cer_row = next((row for row in report2.get("rows", []) if row.get("metric") == "cer"), {})
                if cer_row.get("status") != "unmeasured" or cer_row.get("value") is not None:
                    failures.append("quality worker must report unmeasured with null value for empty gold")
            run3 = _run_matrix_worker("evaluation/worker_quality.py", [str(Path(qtmp) / "missing.txt"), str(gold_path)])
            if run3.returncode == 0:
                failures.append("quality worker succeeded on a missing prediction file (must fail)")

    # Canvas negative: broken edge reference must be rejected with an error payload.
    broken = fixtures / "broken-edge.canvas"
    if broken.is_file():
        neg = _run_matrix_worker("document/worker_canvas.py", [str(broken)])
        if neg.returncode == 0:
            failures.append("worker_canvas accepted a canvas with an unknown edge node")
        else:
            tail = (neg.stdout or neg.stderr).strip().splitlines()[-1] if (neg.stdout or neg.stderr).strip() else ""
            if "error" not in tail:
                failures.append("worker_canvas failure must carry an error payload")
    else:
        failures.append("missing negative canvas fixture: broken-edge.canvas")

    if failures:
        print("workers-vnext check failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("workers-vnext check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
