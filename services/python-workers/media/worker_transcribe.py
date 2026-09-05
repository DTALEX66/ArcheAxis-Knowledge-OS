#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext media worker: local ASR transcription (F10).

Formats: WAV / MP3 / M4A / FLAC (decoded through ffmpeg by faster-whisper).

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
import json
import sys
from pathlib import Path

ENGINE = "python-worker-transcribe"
ENGINE_VERSION = "0.1.0"

DEFAULT_MODEL_DIR = "D:/All projects/Model library/whisper/faster-whisper-large-v3-turbo"


def _model_dir(path: str | None) -> Path:
    candidate = Path(path or DEFAULT_MODEL_DIR)
    if not candidate.is_dir():
        raise ValueError(f"ASR model directory not found: {candidate} (set --model-dir)")
    marker = candidate / "model.bin"
    if not marker.is_file():
        raise ValueError(f"ASR model directory has no model.bin: {candidate}")
    return candidate


def probe(model_path: str | None) -> dict:
    """Deterministic capability probe: dependency + model presence."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return {"capability": False, "reason": "faster-whisper not installed", "engine": ENGINE}
    try:
        path = _model_dir(model_path)
    except ValueError as exc:
        return {"capability": False, "reason": str(exc), "engine": ENGINE}
    return {
        "capability": True,
        "engine": ENGINE,
        "model_dir": str(path),
        "model": path.name,
        "formats": ["wav", "mp3", "m4a", "flac"],
        "note": "probe checks dependency and model presence only; quality is measured per run (T07)",
    }


def extract(path: str, model_path: str | None, language: str, device: str) -> dict:
    from faster_whisper import WhisperModel

    model_dir = _model_dir(model_path)
    input_path = Path(path)
    if not input_path.is_file():
        raise ValueError(f"input media file not found: {input_path}")

    model = WhisperModel(str(model_dir), device=device, compute_type="int8")
    segments, info = model.transcribe(
        str(input_path),
        language=None if language == "auto" else language,
        vad_filter=True,
    )
    cues: list[dict] = []
    text_parts: list[str] = []
    for segment in segments:
        cues.append(
            {
                "start_ms": int(segment.start * 1000),
                "end_ms": int(segment.end * 1000),
                "text": segment.text.strip(),
            }
        )
        text_parts.append(segment.text.strip())
    text = "\n".join(part for part in text_parts if part)
    language_code = getattr(info, "language", None) or "unknown"
    duration_ms = int((getattr(info, "duration", 0.0) or 0.0) * 1000)
    loss_note = (
        "no speech segments detected (input may be silence/tone/noise); "
        "transcript kept empty and truthful"
        if not cues
        else f"{len(cues)} segments; VAD filtering applied"
    )
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "language": language_code,
        "language_probability": round(float(getattr(info, "language_probability", 0.0) or 0.0), 4),
        "duration_ms": duration_ms,
        "cues": cues,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "model": model_dir.name,
                "language": language,
                "device": device,
                "compute_type": "int8",
                "vad_filter": True,
            },
            "loss_note": loss_note,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ArcheAxis local ASR worker")
    parser.add_argument("input", nargs="?", help="media file")
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--language", default="auto")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--probe", action="store_true", help="capability probe only")
    args = parser.parse_args()

    if args.probe:
        print(json.dumps(probe(args.model_dir), ensure_ascii=False))
        return 0
    if not args.input:
        print(json.dumps({"error": "usage: worker_transcribe.py <input-file> [options]"}))
        return 2
    try:
        out = extract(args.input, args.model_dir, args.language, args.device)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
