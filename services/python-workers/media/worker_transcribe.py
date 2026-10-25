#!/usr/bin/env python3
"""ArcheAxis vNext media worker: local ASR transcription (F10).

Formats: WAV / MP3 / M4A / FLAC / OGG / OPUS (decoded by faster-whisper/PyAV).

Isolation boundary: this worker NEVER opens the vNext database. It probes
the local model capability, transcribes with segment-level timestamps, and
prints a single JSON envelope on stdout. Silence/absence of speech is a
truthful empty transcript with an explicit loss note — never a fake
success. Missing model/dependency/file produce a non-zero exit with an
error payload.

Provenance: behaviour distilled from the legacy ASR pipeline
(app/ingestion/asr_adapter.py semantics) without importing legacy code.

Usage:
    python worker_transcribe.py <input-file> [--model-dir DIR]
                                          [--language auto] [--device cpu]
    python worker_transcribe.py --probe [--model-dir DIR]

Output:
    {"engine","engine_version","text","language","language_probability",
     "duration_ms","cues":[{"start_ms","end_ms","text"}],"loss_receipt"}
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

ENGINE = "python-worker-transcribe"
ENGINE_VERSION = "0.1.0"
WORKER_IDENTITY = "python-worker-transcribe-ndjson"
CAPABILITY = "media.transcribe"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_DIR = PROJECT_ROOT.parent / "Model library" / "whisper" / "faster-whisper-large-v3-turbo"

# The model a packaged product ships beside its own interpreter. `stage_backend_runtime.py`
# copies it to `runtime/models/asr/<name>/`, which travels with the `runtime/` bundle
# resource, so an installed machine needs no model library, no environment variable and no
# download. Preference order is quality-first: a build that ships a larger model uses it,
# and a build that ships only `base` uses that.
BUNDLED_MODEL_RELATIVE = Path("runtime") / "models" / "asr"
BUNDLED_MODEL_PREFERENCE = (
    "faster-whisper-large-v3-turbo",
    "faster-whisper-small",
    "faster-whisper-base",
    "faster-whisper-tiny",
)
MODEL_IDENTITY_FILE = "aaos-model.json"

# faster-whisper pads each detected speech chunk by this many milliseconds on both sides
# (`VadOptions.speech_pad_ms`). The trailing pad is what makes a final segment's end reach
# past the container's own duration; a cue ending inside this declared pad is a real cue,
# not an invented position, so it is kept and marked rather than discarded.
VAD_SPEECH_PAD_MS = 400



def _load_tool_paths():
    """The shared resolver, loaded from this worker's own tree.

    Failing to load it is not the same as failing to read a declaration, so the two are
    kept apart: this returns None when the module is not there, while `declared()` below
    lets a manifest that exists but cannot be read raise. A broad `except` around both -
    which this once had - reported an unreadable manifest as "nothing declared", the
    failure mode the resolver was changed to stop making.
    """
    module_path = Path(__file__).resolve().parent.parent / "tool_paths.py"
    if not module_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("worker_tool_paths", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _declared_path(name: str) -> str | None:
    """The declared external path for a model, or None when nothing is declared.

    R6 A02 requires a model resolver over exact paths. `DEFAULT_MODEL_DIR` derives the
    model library from the checkout's parent, which is correct only for the canonical
    layout: in a worktree it resolves to an absent sibling and the probe reported the
    model missing while it was present on disk.

    Only a missing declaration becomes None; a manifest that exists but cannot be read
    raises, because reporting that as "not declared" sends someone looking for a model
    that is present.
    """
    module = _load_tool_paths()
    return None if module is None else module.declared(name, __file__)


def _root_derived_model_dir() -> Path | None:
    """The model library that sits beside the declared external root.

    `DEFAULT_MODEL_DIR` assumes the model library is beside the *checkout's parent*,
    which is true only for the canonical layout: in a worktree it points at an absent
    sibling. The declared external root is stable across checkout shapes, and the
    shared model library is its sibling - the same relationship the existing
    `app/ingestion/asr_adapter.py` and `media_adapter.py` rely on.
    """
    module = _load_tool_paths()
    if module is None:
        return None
    try:
        root = module._external_root()
    except Exception:  # noqa: BLE001
        return None
    if root is None:
        return None
    for base in (root.parent, root):
        candidate = base / "Model library" / "whisper" / "faster-whisper-large-v3-turbo"
        if candidate.is_dir():
            return candidate
    return None


def _bundled_model_dirs() -> list[Path]:
    """Model directories shipped with this runtime, best first.

    The runtime root is derived from the worker's own file, so both layouts resolve: a staged
    product (`<root>/workers/media/worker_transcribe.py` -> `<root>/runtime/models/asr`) and
    the source tree (`services/python-workers/media/` -> an absent `services/runtime`).
    """
    root = Path(__file__).resolve().parents[2] / BUNDLED_MODEL_RELATIVE
    if not root.is_dir():
        return []
    order = {name: index for index, name in enumerate(BUNDLED_MODEL_PREFERENCE)}
    found = [path for path in root.iterdir()
             if path.is_dir() and (path / "model.bin").is_file()]
    return sorted(found, key=lambda path: (order.get(path.name, len(order)), path.name))


def _model_identity(directory: Path) -> dict | None:
    """The identity the packaging step wrote beside a bundled model, when one is there."""
    record = directory / MODEL_IDENTITY_FILE
    if not record.is_file():
        return None
    try:
        document = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return document if isinstance(document, dict) else None


def _resolve_model(path: str | None) -> tuple[Path, str]:
    """The model directory and where it came from.

    Precedence: explicit argument, operator override, the model shipped in this product, the
    declaration, the declared sibling library, then the layout-derived default. The bundled
    model is tried before any machine-level declaration so an installed build does not depend
    on a shared library that belongs to the build host.
    """
    candidate: Path | None = Path(path) if path else None
    source = "argument"
    if candidate is None:
        override = os.environ.get("ARCHEAXIS_ASR_MODEL_DIR", "").strip()
        if override:
            candidate = Path(override)
            source = "override"
    if candidate is None:
        bundled = _bundled_model_dirs()
        if bundled:
            candidate = bundled[0]
            source = "bundled"
    if candidate is None:
        declared_model = _declared_path("faster-whisper-large-v3-turbo")
        if declared_model:
            candidate = Path(declared_model)
            source = "declaration"
    if candidate is None:
        candidate = _root_derived_model_dir()
        source = "sibling_library"
    if candidate is None:
        candidate = DEFAULT_MODEL_DIR
        source = "layout_default"
    if not candidate.is_dir():
        raise ValueError(
            f"ASR model directory not found: {candidate} (set --model-dir; product-local "
            f"location consulted: {Path(__file__).resolve().parents[2] / BUNDLED_MODEL_RELATIVE})")
    marker = candidate / "model.bin"
    if not marker.is_file():
        raise ValueError(f"ASR model directory has no model.bin: {candidate}")
    return candidate, source


def _model_dir(path: str | None) -> Path:
    return _resolve_model(path)[0]


def probe(model_path: str | None) -> dict:
    """Deterministic capability probe: dependency + model presence + shipped identity."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return {"capability": False, "reason": "faster-whisper not installed", "engine": ENGINE}
    try:
        path, source = _resolve_model(model_path)
    except ValueError as exc:
        return {"capability": False, "reason": str(exc), "engine": ENGINE}
    identity = _model_identity(path)
    return {
        "capability": True,
        "engine": ENGINE,
        "model_dir": str(path),
        "model": path.name,
        "model_source": source,
        "model_identity": identity,
        "decoder": _decoder_report(),
        "formats": ["wav", "mp3", "m4a", "flac", "ogg", "opus", "mp4", "mov", "webm"],
        "note": "probe checks dependency and model presence only; quality is measured per run (T07)",
    }


def _media_decode():
    """The bundled PyAV decoder, loaded beside this worker (workers run as plain scripts)."""
    spec = importlib.util.spec_from_file_location(
        "transcribe_media_decode", Path(__file__).resolve().with_name("media_decode.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("media_decode.py is missing beside this worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decoder_report() -> dict:
    """Which decoder this invocation would use, stated as a capability rather than a guess."""
    declared = None
    try:
        declared = _declared_path("ffmpeg")
    except Exception:  # noqa: BLE001 - a probe reports a resolution fault, it does not raise
        declared = None
    if declared and Path(declared).is_file():
        return {"kind": "ffmpeg", "path": declared}
    try:
        return _media_decode().identity()
    except Exception as exc:  # noqa: BLE001
        return {"kind": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}


def _decode_engine(ffmpeg: str | None) -> dict:
    """The decoder this run will actually use, or a named failure.

    A declared binary always wins. When there is none - the installed product has no system
    ffmpeg - the runtime's own PyAV decoder is used; it is the decoder `faster-whisper`
    already depends on, so nothing is fetched or installed at run time.
    """
    if ffmpeg and Path(ffmpeg).is_file():
        return {"kind": "ffmpeg", "binary": str(ffmpeg)}
    module = _media_decode()
    if module.available():
        return {"kind": "pyav", **module.identity()}
    raise ValueError(
        f"no decoder available: declared ffmpeg does not exist ({ffmpeg!r}) and PyAV is not "
        "installed in this runtime")


def _segment_cues(model, path: str, language: str, word_timestamps: bool = False):
    """One decode pass: the raw cues, their text, the decode info and any mid-iteration error.

    Shared by the whole-file and per-window paths so a window cannot drift from the canonical
    behaviour. Returns exactly what the original inline loop produced.
    """
    segments, info = model.transcribe(
        str(path),
        language=None if language == "auto" else language,
        vad_filter=True,
        vad_parameters={"speech_pad_ms": VAD_SPEECH_PAD_MS},
        word_timestamps=word_timestamps,
    )
    raw_cues: list[dict] = []
    text_parts: list[str] = []
    processing_error = None
    try:
        for segment in segments:
            raw_cues.append(
                {
                    "start_ms": int(segment.start * 1000),
                    "end_ms": int(segment.end * 1000),
                    "text": segment.text.strip(),
                    # Word timings are reported only when they were asked for: alignment is an
                    # extra pass, and a cue that has none says so rather than being padded.
                    **({"words": [
                        {"start_ms": int(word.start * 1000), "end_ms": int(word.end * 1000),
                         "text": (word.word or "").strip()}
                        for word in (getattr(segment, "words", None) or [])]}
                       if word_timestamps else {}),
                }
            )
            text_parts.append(segment.text.strip())
    except Exception as exc:
        if not raw_cues:
            raise RuntimeError("ASR segment iteration failed before any usable result") from exc
        processing_error = {"stage": "segment_iteration", "error_type": type(exc).__name__}
    return raw_cues, text_parts, info, processing_error


def extract(path: str, model_path: str | None, language: str, device: str,
            word_timestamps: bool = False) -> dict:
    from faster_whisper import WhisperModel

    model_dir, model_source = _resolve_model(model_path)
    input_path = Path(path)
    if not input_path.is_file():
        raise ValueError(f"input media file not found: {input_path}")

    model = WhisperModel(str(model_dir), device=device, compute_type="int8")
    raw_cues, text_parts, info, processing_error = _segment_cues(
        model, path, language, word_timestamps)
    processing_status = "partial" if processing_error else "complete"
    text = "\n".join(part for part in text_parts if part)
    language_code = getattr(info, "language", None) or "unknown"
    duration_ms = int((getattr(info, "duration", 0.0) or 0.0) * 1000)
    cues: list[dict] = []
    alignment_issues: list[dict] = []
    tolerated: list[int] = []
    for index, cue in enumerate(raw_cues):
        start, end = cue["start_ms"], cue["end_ms"]
        if not (0 <= start < end <= duration_ms + VAD_SPEECH_PAD_MS):
            alignment_issues.append({"index": index, "start_ms": start, "end_ms": end,
                                     "reason": "invalid_or_out_of_duration", "location_status": "unlocated"})
        else:
            # A cue that ends past the container's duration but inside the declared VAD pad is
            # kept at its measured position: the export is marked, not silently clipped.
            beyond = max(0, end - duration_ms)
            if beyond:
                tolerated.append(index)
                cues.append({**cue, "raw_index": index, "end_beyond_duration_ms": beyond})
            else:
                cues.append({**cue, "raw_index": index})
    alignment_status = "partial" if alignment_issues else ("complete" if cues else "unlocated")
    loss_note = (
        "no speech segments detected (input may be silence/tone/noise); "
        "transcript kept empty and truthful"
        if not raw_cues
        else (f"{len(raw_cues)} raw segments; all positions unlocated; original transcript retained; VAD filtering applied" if not cues else f"{len(raw_cues)} raw segments; {len(cues)} valid located segments; original transcript retained; VAD filtering applied"
              + (f"; {len(tolerated)} cue end(s) reach up to {VAD_SPEECH_PAD_MS} ms past the container duration "
                 "(VAD speech padding), kept un-clamped and marked end_beyond_duration_ms"
                 if tolerated else ""))
    )
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "language": language_code,
        "language_probability": round(float(getattr(info, "language_probability", 0.0) or 0.0), 4),
        "duration_ms": duration_ms,
        "cues": cues,
        "raw_cues": raw_cues,
        "alignment_issues": alignment_issues,
        "alignment_status": alignment_status,
        "processing_status": processing_status,
        "processing_error": processing_error,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "model": model_dir.name,
                "model_source": model_source,
                "model_identity": _model_identity(model_dir),
                "language": language,
                "device": device,
                "compute_type": "int8",
                "vad_filter": True,
                "vad_speech_pad_ms": VAD_SPEECH_PAD_MS,
                "cue_duration_tolerance_ms": VAD_SPEECH_PAD_MS,
                # The receipt states the granularity actually produced, so a request for word
                # timings that the model could not satisfy stays visible instead of looking met.
                "word_timings_requested": word_timestamps,
                "word_timings_produced": any(cue.get("words") for cue in raw_cues),
            },
            "loss_note": ("ASR processing interrupted; yielded original text/raw cues retained; unprocessed remainder unknown; " if processing_error else "") + loss_note + (f"; {len(alignment_issues)} raw cues have invalid/out-of-duration positions; original text/raw_cues retained without clamping" if alignment_issues else ""),
        },
    }


def _window_module():
    """The window arithmetic and resume rules, loaded from this worker's own directory."""
    import importlib.util

    path = Path(__file__).resolve().parent / "window_transcribe.py"
    spec = importlib.util.spec_from_file_location("transcribe_windows", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("window_transcribe.py is missing beside this worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_windowed(path: str, model_path: str | None, language: str, device: str, plan: dict,
                     ffmpeg: str | None, staging: str | None = None, work_dir: str | None = None,
                     budget_ms: int | None = None,
                     word_timestamps: bool = False) -> dict:
    """Transcribe one bounded window of the recording, resuming windows already finished.

    The Core caps a job at 300 s, so the caller drives successive invocations. `window_transcribe`
    owns the plan arithmetic, the resume rules and the merge; this function owns the two things it
    cannot: cutting the window with a decoder and running the model on it. The offsets come from the
    window's own start, so a citation always points into the recording.

    The decoder is the declared ffmpeg binary when it exists, and the runtime's own PyAV decoder
    when it does not - the installed product ships no system binary, and a window it cannot cut
    would otherwise make every long recording untranscribable.
    """
    import tempfile

    from faster_whisper import WhisperModel

    windows = _window_module()
    input_path = Path(path)
    if not input_path.is_file():
        raise ValueError(f"input media file not found: {input_path}")
    engine = _decode_engine(ffmpeg)

    workspace = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="archeaxis-window-"))
    workspace.mkdir(parents=True, exist_ok=True)
    # Loaded on first real window: an invocation that only resumes finished windows must not pay for
    # a model it never uses.
    loaded: list = []

    def per_window(window):
        if not loaded:
            loaded.append(WhisperModel(str(_model_dir(model_path)), device=device, compute_type="int8"))
        target = workspace / f"window-{int(window['index']):04d}.wav"
        if engine["kind"] == "ffmpeg":
            import subprocess

            command = windows.window_command(str(engine["binary"]), str(input_path),
                                             int(window["start_ms"]), int(window["end_ms"]), str(target))
            finished = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            if finished.returncode != 0 or not target.is_file():
                raise RuntimeError(f"ffmpeg failed for window {window['index']}: {finished.stderr[-200:]}")
            window_decode = {"kind": "ffmpeg"}
        else:
            window_decode = _media_decode().extract_window(
                str(input_path), str(target), int(window["start_ms"]), int(window["end_ms"]))
            if not target.is_file():
                raise RuntimeError(f"decoder produced no audio for window {window['index']}")
        # The canonical whole-file receipt is produced for the window's own wav, so a window cannot
        # invent its own vocabulary: same engine, same loss receipt, same alignment rules.
        receipt = extract(str(target), model_path, language, device,
                          word_timestamps=word_timestamps)
        # Cues stay local to the window: merge_windows owns the offset onto the recording timeline,
        # and applying it here as well shifted every later window twice.
        return {"status": "succeeded", "cues": receipt["cues"], "text": receipt["text"],
                "receipt": receipt, "window_decode": window_decode}

    merged = windows.run_windows(plan, per_window, staging, budget_ms)
    produced = next((item for item in merged["windows_detail"] if item.get("receipt")), None) if \
        merged.get("windows_detail") else None
    if produced is None:
        raise RuntimeError("no window produced a receipt; nothing to report")
    envelope = dict(produced["receipt"])
    windows_planned = list(plan.get("windows") or [])
    envelope.update(
        text=merged["text"],
        cues=merged["cues"],
        raw_cues=merged["cues"],
        # Each window enforced its own range while decoding, so nothing here is silently dropped;
        # what the caller must see instead is which windows were missing from the recording.
        alignment_issues=[],
        alignment_status=("complete" if merged["status"] == "complete" else "partial"),
        processing_status=("complete" if merged["status"] == "complete" else "partial"),
        # The recording's duration, not the last decoded window's, so downstream offsets stay valid.
        duration_ms=(int(windows_planned[-1]["end_ms"]) if windows_planned else envelope["duration_ms"]),
        windows={key: merged[key] for key in
                 ("status", "windows_expected", "windows_present", "windows_missing", "windows_resumed", "note")},
        window_identity={"source": str(input_path),
                         "window_audio_ms": int(plan.get("window_audio_ms") or 0),
                         "policy": plan.get("policy"),
                         "decoder": engine["kind"]},
    )
    return envelope


def _plan_module():
    """The declared window policy and its arithmetic, loaded from this worker's own directory."""
    import importlib.util

    path = Path(__file__).resolve().parent / "window_plan.py"
    spec = importlib.util.spec_from_file_location("transcribe_window_plan", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("window_plan.py is missing beside this worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_split(path: str, model_path: str | None, language: str, device: str,
                  ffmpeg: str | None, staging: str | None = None,
                  remaining_ms: int | None = None,
                  work_dir: str | None = None,
                  word_timestamps: bool = False) -> dict:
    """Transcribe a recording that cannot fit one job, by splitting it into bounded windows.

    The plan is derived here, from the recording's real duration, rather than accepted from the
    caller: the number that decides how many windows a file needs is the file's own length, and a
    plan sent over the wire could drop audio by leaving a gap between two windows while still
    looking well-formed. Only the *choice* to split rides the request.

    Each invocation runs as many windows as the job's own budget allows and reports the rest as
    not attempted, so a long recording advances across invocations instead of being killed
    mid-decode with no statement about what was finished.
    """
    windows = _window_module()
    planner = _plan_module()
    engine = _decode_engine(ffmpeg)
    if not Path(path).is_file():
        raise ValueError(f"input media file not found: {path}")
    if engine["kind"] == "ffmpeg":
        duration_ms = windows.probe_duration_ms(str(engine["binary"]), str(path))
    else:
        # No declared binary: the runtime's own decoder measures the container it will decode.
        duration_ms = _media_decode().duration_ms(str(path))
    plan = planner.plan_windows(duration_ms)
    # Opening the input, loading the model and writing the first window all happen outside the
    # per-window estimate, so that declared overhead is held back from the job's remaining time.
    budget_ms = None if remaining_ms is None else max(0, int(remaining_ms) - planner.OVERHEAD_MS)
    envelope = extract_windowed(path, model_path, language, device, plan, ffmpeg, staging, work_dir,
                               budget_ms, word_timestamps)
    envelope["split"] = {
        "duration_ms": duration_ms,
        "window_audio_ms": plan["window_audio_ms"],
        "windows_total": plan["windows_total"],
        "whole_exceeds_ceiling": plan["whole_exceeds_ceiling"],
        "policy": plan["policy"],
    }
    return envelope


def main() -> int:
    # The sidecar branch first, before the CLI parser: the Core spawns a worker with
    # `--staging-root` and speaks the NDJSON protocol on stdio. Without this mode the
    # engine was real, verified and completely unreachable from any Core job - which is
    # what tests/test_worker_route_coverage.py now exists to catch.
    if "--staging-root" in sys.argv:
        _transport_candidates = (
            Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py",
            Path(__file__).resolve().parents[2] / "services" / "python-workers" / "transport" / "text_ndjson.py",
        )
        _transport = next((p for p in _transport_candidates if p.is_file()),
                          _transport_candidates[0])
        spec = importlib.util.spec_from_file_location("transcribe_transport", _transport)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--staging-root", type=Path, required=True)
        parser.add_argument("--artifact-root", type=Path, default=None)
        args = parser.parse_args()
        return transport.serve_stdio(WORKER_IDENTITY, [CAPABILITY], args.staging_root,
                                     args.artifact_root)

    parser = argparse.ArgumentParser(description="ArcheAxis local ASR worker")
    parser.add_argument("input", nargs="?", help="media file")
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--language", default="auto")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--probe", action="store_true", help="capability probe only")
    parser.add_argument("--window-plan", default=None,
                        help="JSON window plan from window_plan.plan_windows(); runs one bounded window per invocation")
    parser.add_argument("--ffmpeg", default=None, help="declared ffmpeg path used to cut a window")
    parser.add_argument("--window-staging", default=None,
                        help="directory holding finished windows so a later invocation resumes instead of repeating")
    parser.add_argument("--word-timestamps", action="store_true",
                        help="also align word-level timings (an extra pass; asked for, not assumed)")
    parser.add_argument("--split", action="store_true",
                        help="plan the windows from the recording's own duration and transcribe what this invocation's budget allows")
    parser.add_argument("--budget-ms", type=int, default=None,
                        help="wall-clock budget for this invocation; windows that do not fit are reported not attempted")
    args = parser.parse_args()

    if args.probe:
        print(json.dumps(probe(args.model_dir), ensure_ascii=False))
        return 0
    if not args.input:
        print(json.dumps({"error": "usage: worker_transcribe.py <input-file> [options]"}))
        return 2
    if args.split:
        if not args.ffmpeg and not _media_decode().available():
            print(json.dumps({"error": "--split requires --ffmpeg or the bundled PyAV decoder"},
                             ensure_ascii=False))
            return 2
        try:
            out = extract_split(args.input, args.model_dir, args.language, args.device, args.ffmpeg,
                                args.window_staging, args.budget_ms, word_timestamps=args.word_timestamps)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if args.window_plan:
        if not args.ffmpeg and not _media_decode().available():
            print(json.dumps({"error": "--window-plan requires --ffmpeg or the bundled PyAV decoder"},
                             ensure_ascii=False))
            return 2
        try:
            out = extract_windowed(args.input, args.model_dir, args.language, args.device,
                                   json.loads(Path(args.window_plan).read_text(encoding="utf-8")),
                                   args.ffmpeg, args.window_staging,
                                   word_timestamps=args.word_timestamps)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(out, ensure_ascii=False))
        return 0
    try:
        out = extract(args.input, args.model_dir, args.language, args.device,
                        word_timestamps=args.word_timestamps)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
