#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext media worker: video track/keyframe extraction (F11 partial).

Extracts from a video container, via the system ffmpeg binary:

- a 16 kHz mono WAV of the audio track (for the ASR lane),
- sampled keyframes (JPEG) with their media-time offsets,
- a coverage manifest of every extracted artifact (sha256 + ms offset).

Frame extraction coverage and timing are explicit; audio success never
implies video understanding (per-format acceptance). OCR/VL over frames is
a separate lane. Missing ffmpeg or input surfaces an error payload.

Usage:
    python worker_video.py <input.mp4|mov|mkv|webm> --out-dir <dir>
        [--frame-interval-ms 10000] [--max-frames 24]
Output (stdout JSON envelope):
    {"engine","engine_version","duration_ms","audio_wav","frames":[...],
     "loss_receipt"}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ENGINE = "python-worker-video"
ENGINE_VERSION = "0.1.0"

SUPPORTED = {".mp4", ".mov", ".mkv", ".webm"}


def _ffmpeg() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("ffmpeg binary not found on PATH (video engine unavailable)")
    return binary


def probe() -> dict:
    binary = shutil.which("ffmpeg")
    if not binary:
        return {"capability": False, "reason": "ffmpeg not found", "engine": ENGINE}
    try:
        version = subprocess.run(
            [binary, "-version"], capture_output=True, text=True, timeout=20
        ).stdout.splitlines()[0]
    except Exception:  # noqa: BLE001
        version = "unknown"
    return {
        "capability": True,
        "engine": ENGINE,
        "ffmpeg": binary,
        "version": version,
        "formats": sorted(SUPPORTED),
        "note": "audio WAV + sampled keyframes only; ASR/OCR/VL are separate lanes",
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe_duration(binary: str, input_path: Path) -> int:
    out = subprocess.run(
        [binary, "-i", str(input_path)],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=60,
    )
    stderr = out.stderr
    marker = "Duration:"
    if marker not in stderr:
        return 0
    duration_line = next(line for line in stderr.splitlines() if marker in line)
    time_part = duration_line.split(marker, 1)[1].split(",", 1)[0].strip()
    parts = time_part.split(":")
    hours, minutes, seconds = (float(p) for p in parts[:3])
    return int(((hours * 60 + minutes) * 60 + seconds) * 1000)


def extract(input_path: Path, out_dir: Path, frame_interval_ms: int, max_frames: int) -> dict:
    binary = _ffmpeg()
    if not input_path.is_file():
        raise ValueError(f"input video file not found: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"unsupported video extension: {input_path.suffix}")
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_wav = out_dir / "audio-16k-mono.wav"
    audio_proc = subprocess.run(
        [
            binary, "-y", "-i", str(input_path),
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            str(audio_wav),
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=600,
    )
    if audio_proc.returncode != 0 or not audio_wav.is_file():
        raise RuntimeError(f"ffmpeg audio extraction failed: {audio_proc.stderr[-400:]}")

    duration_ms = _probe_duration(binary, input_path)

    timestamps_ms: list[int] = []
    if duration_ms > 0:
        timestamps_ms = list(range(0, duration_ms, frame_interval_ms))
        if not timestamps_ms or timestamps_ms[-1] != duration_ms - 1:
            timestamps_ms.append(max(0, duration_ms - 1))
    else:
        timestamps_ms = list(range(0, frame_interval_ms * max_frames, frame_interval_ms))
    timestamps_ms = timestamps_ms[:max_frames]

    frames: list[dict] = []
    for frame_index, offset_ms in enumerate(timestamps_ms):
        frame_path = out_dir / f"frame-{frame_index:03d}-{offset_ms}ms.jpg"
        frame_proc = subprocess.run(
            [
                binary, "-y", "-ss", f"{offset_ms / 1000:.3f}", "-i", str(input_path),
                "-frames:v", "1", "-q:v", "3", str(frame_path),
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=120,
        )
        if frame_proc.returncode != 0 or not frame_path.is_file():
            break
        frames.append({"offset_ms": offset_ms, "path": str(frame_path), "sha256": _sha256(frame_path)})

    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "duration_ms": duration_ms,
        "audio_wav": {"path": str(audio_wav), "sha256": _sha256(audio_wav)},
        "frames": frames,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "frame_interval_ms": frame_interval_ms,
                "max_frames": max_frames,
                "ffmpeg": binary,
            },
            "loss_note": (
                "audio extracted as 16 kHz mono WAV for the ASR lane; frames are "
                f"sampled keyframes ({len(frames)} captured); audio success does "
                "not imply video understanding; OCR/subtitle/VL alignment are "
                "separate lanes"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ArcheAxis video extraction worker")
    parser.add_argument("input", nargs="?", help="video file")
    parser.add_argument("--out-dir", required=False)
    parser.add_argument("--frame-interval-ms", type=int, default=10000)
    parser.add_argument("--max-frames", type=int, default=24)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()

    if args.probe:
        print(json.dumps(probe(), ensure_ascii=False))
        return 0
    if not args.input or not args.out_dir:
        print(json.dumps({"error": "usage: worker_video.py <input> --out-dir <dir> [options]"}))
        return 2
    try:
        out = extract(
            Path(args.input),
            Path(args.out_dir),
            args.frame_interval_ms,
            args.max_frames,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
