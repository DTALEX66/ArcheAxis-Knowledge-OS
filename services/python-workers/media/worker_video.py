#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext media worker: video decoding and bounded local analysis.

Extracts from a video container, via the system ffmpeg binary:

- a 16 kHz mono WAV of the audio track (for the ASR lane),
- sampled keyframes (JPEG) with their media-time offsets,
- a coverage manifest of every extracted artifact (sha256 + ms offset).

The media.video product job also transcribes the full extracted audio and
describes up to three sampled frames through the existing local vision adapter.
Each stage records its own status; sampling never claims continuous visual
coverage. The standalone CLI below remains a decoding/artifact interface.

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
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

ENGINE = "python-worker-video"
ENGINE_VERSION = "0.1.0"

SUPPORTED = {".mp4", ".mov", ".mkv", ".webm"}


def _declared_path(name: str) -> str | None:
    """The declared external path for *name*, or None when nothing is declared.

    Delegates to `tool_paths.declared`, which loads the shared module from this worker's
    own tree. Only a missing declaration becomes None; a manifest that exists but cannot
    be read raises, because reporting that as "not declared" is how a missing parser turns
    into "engine not installed".
    """
    module_path = Path(__file__).resolve().parent.parent / "tool_paths.py"
    if not module_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("worker_tool_paths", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.declared(name, __file__)


def _ffmpeg() -> str:
    declared = _declared_path("ffmpeg")
    if declared:
        return declared
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("ffmpeg binary not found (video engine unavailable)")
    return binary


def probe() -> dict:
    # A probe reports whether the engine is available; it must not crash when it is not.
    # Resolution can also fail because the declaration itself cannot be read, and that is a
    # different answer from "ffmpeg is absent" - so it is reported, not swallowed and not
    # raised. The fail-closed reading belongs to extraction, where a wrong answer costs a
    # conversion rather than a diagnostic.
    try:
        binary = _declared_path("ffmpeg") or shutil.which("ffmpeg")
    except Exception as exc:  # noqa: BLE001 - a probe reports, it does not raise
        return {"capability": False, "reason": f"{type(exc).__name__}: {exc}",
                "engine": ENGINE, "resolution_failed": True}
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


def _probe_duration(binary: str, input_path: Path, timeout_s: float = 60) -> int:
    probe = Path(binary).with_name("ffprobe.exe" if Path(binary).suffix.lower() == ".exe" else "ffprobe")
    if probe.is_file():
        result = subprocess.run(
            [str(probe), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(input_path)],
            capture_output=True, text=True, encoding="utf-8", timeout=timeout_s,
        )
        if result.returncode != 0:
            raise ValueError("video duration probe failed")
        duration = Decimal(json.loads(result.stdout)["format"]["duration"])
        if not duration.is_finite() or duration <= 0:
            raise ValueError("video duration unavailable")
        return int(duration * 1000)
    out = subprocess.run(
        [binary, "-i", str(input_path)],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout_s,
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


def _remaining(deadline: float | None, maximum: float) -> float:
    remaining = maximum if deadline is None else min(maximum, deadline - time.monotonic())
    if remaining <= 0:
        raise TimeoutError("video job budget exhausted")
    return remaining


def _run_asr(audio_path: str, model_path: str | None, language: str, device: str, timeout_s: float) -> dict:
    command = [sys.executable, "-B", str(Path(__file__).with_name("worker_transcribe.py")), audio_path, "--language", language, "--device", device]
    if model_path:
        command.extend(["--model-dir", model_path])
    child_env = os.environ.copy()
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=timeout_s, env=child_env)
    if result.returncode:
        raise RuntimeError("ASR subprocess failed")
    if len(result.stdout.encode("utf-8")) > 8 * 1024 * 1024:
        raise ValueError("ASR output limit exceeded")
    value = json.loads(result.stdout)
    if not isinstance(value, dict) or not isinstance(value.get("text"), str) or not isinstance(value.get("cues"), list):
        raise ValueError("ASR output invalid")
    return value


def extract(input_path: Path, out_dir: Path, frame_interval_ms: int, max_frames: int, *, deadline: float | None = None, known_duration_ms: int | None = None) -> dict:
    binary = _ffmpeg()
    if not input_path.is_file():
        raise ValueError(f"input video file not found: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"unsupported video extension: {input_path.suffix}")
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_wav = out_dir / "audio-16k-mono.wav"
    decode_errors = []
    try:
        audio_proc = subprocess.run(
            [
                binary, "-y", "-i", str(input_path),
                "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                str(audio_wav),
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=_remaining(deadline, 600),
        )
        audio_available = audio_proc.returncode == 0 and audio_wav.is_file()
        if not audio_available:
            decode_errors.append({"stage": "audio", "reason": "audio_track_unavailable_or_decode_failed"})
    except (subprocess.TimeoutExpired, TimeoutError):
        audio_available = False
        decode_errors.append({"stage": "audio", "reason": "audio_decode_timeout"})

    duration_ms = known_duration_ms if known_duration_ms is not None else _probe_duration(binary, input_path, _remaining(deadline, 60))

    timestamps_ms: list[int] = []
    if duration_ms > 0:
        timestamps_ms = list(range(0, duration_ms, frame_interval_ms))
        if not timestamps_ms or timestamps_ms[-1] != duration_ms - 1:
            timestamps_ms.append(max(0, duration_ms - 1))
    else:
        timestamps_ms = list(range(0, frame_interval_ms * max_frames, frame_interval_ms))
    timestamps_ms = timestamps_ms[:max_frames]

    frame_errors: list[dict] = []
    frames: list[dict] = []
    for frame_index, offset_ms in enumerate(timestamps_ms):
        frame_path = out_dir / f"frame-{frame_index:03d}-{offset_ms}ms.jpg"
        try:
            frame_proc = subprocess.run(
                [
                    binary, "-y", "-ss", f"{offset_ms / 1000:.3f}", "-i", str(input_path),
                    "-frames:v", "1", "-q:v", "3", str(frame_path),
                ],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=_remaining(deadline, 120),
            )
        except (subprocess.TimeoutExpired, TimeoutError):
            frame_errors.append({"sampling_seek_requested_ms": offset_ms, "reason": "frame_decode_timeout"})
            continue
        if frame_proc.returncode != 0 or not frame_path.is_file():
            frame_errors.append({"sampling_seek_requested_ms": offset_ms, "reason": "frame_decode_failed"})
            continue
        frames.append({"offset_ms": offset_ms, "sampling_seek_requested_ms": offset_ms, "actual_pts_ms": None, "timing_precision": "approximate", "path": str(frame_path), "sha256": _sha256(frame_path)})

    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "duration_ms": duration_ms,
        "audio_wav": {"path": str(audio_wav), "sha256": _sha256(audio_wav)} if audio_available else None,
        "frame_errors": frame_errors,
        "decode_errors": decode_errors,
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
                ("audio extracted as 16 kHz mono WAV for the ASR lane; frames are " if audio_available else "audio unavailable or decode failed; frames are ") +
                f"sampled keyframes ({len(frames)} captured); audio success does "
                "not imply video understanding; OCR/subtitle/VL alignment are "
                "separate lanes"
            ),
        },
    }


def _load_worker(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Existing worker is missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_job(path: Path, out_dir: Path, model_path: str | None, language: str, device: str, *, request_deadline: float | None = None) -> dict:
    """Bounded sampled VL remains independent of the full audio transcript."""
    started = time.monotonic()
    deadline = min(started + 270, request_deadline - 10) if request_deadline is not None else started + 270
    source_sha = _sha256(path)
    # Three uniformly spaced requests, not a claim of continuous understanding.
    duration = _probe_duration(_ffmpeg(), path, _remaining(deadline, 60))
    if duration <= 0:
        raise ValueError("Decoded video duration is unavailable")
    interval = max(1, duration // 3)
    decoded = extract(path, out_dir, frame_interval_ms=interval, max_frames=3, deadline=deadline, known_duration_ms=duration)
    stages = {"decode": {"state": "partial" if decoded["frame_errors"] or decoded.get("decode_errors") or not decoded["frames"] else "succeeded"}}
    transcript = {"text": "", "cues": [], "raw_cues": [], "alignment_issues": [], "alignment_status": "unlocated", "loss_receipt": None}
    if decoded["audio_wav"]:
        try:
            transcript = _run_asr(decoded["audio_wav"]["path"], model_path, language, device, _remaining(deadline, 240))
            stages["asr"] = {"state": "partial" if transcript.get("processing_status") == "partial" or transcript.get("alignment_issues") or not transcript["text"] else "succeeded", "reason": "asr_processing_interrupted" if transcript.get("processing_status") == "partial" else "empty_transcript" if not transcript["text"] else None, "processing_error": transcript.get("processing_error")}
        except Exception as exc:
            stages["asr"] = {"state": "failed", "reason": "asr_failed", "error_type": type(exc).__name__}
    else:
        stages["asr"] = {"state": "failed", "reason": "audio_track_unavailable_or_decode_failed"}
    valid_cues = []
    issues = list(transcript.get("alignment_issues", []))
    for cue in transcript["cues"]:
        if 0 <= cue["start_ms"] < cue["end_ms"] <= duration:
            valid_cues.append(cue)
        else:
            issues.append({"index": cue.get("raw_index"), "start_ms": cue["start_ms"], "end_ms": cue["end_ms"], "reason": "out_of_video_duration", "location_status": "unlocated"})
    caption = _load_worker("video_caption", Path(__file__).parent.parent / "vision" / "worker_caption.py")
    # Reuse the existing product LM Studio defaults; overrides are job-process
    # configuration, never a machine-wide model/provider change.
    endpoint = os.environ.get("ARCHEAXIS_CAPTION_ENDPOINT", "").strip() or caption.OPENAI_BASE
    model = os.environ.get("ARCHEAXIS_CAPTION_MODEL", "").strip() or caption.OPENAI_MODEL
    protocol = os.environ.get("ARCHEAXIS_CAPTION_PROTOCOL", "").strip() or "openai"
    parts = urlsplit(endpoint)
    configured = bool(model.strip()) and protocol == "openai" and parts.scheme == "http" and parts.hostname in {"127.0.0.1", "localhost", "::1"} and not parts.username and not parts.password and not parts.query and not parts.fragment
    visual = []
    if not configured:
        stages["visual"] = {"state": "failed", "reason": "invalid_local_visual_configuration"}
    else:
        for frame in decoded["frames"]:
            item = {"source_sha256": source_sha, "frame_sha256": frame["sha256"], "sampling_seek_requested_ms": frame["sampling_seek_requested_ms"], "actual_pts_ms": None, "timing_precision": "approximate"}
            try:
                remaining = deadline - time.monotonic()
                if remaining < 5:
                    raise TimeoutError("sample budget exhausted")
                image = Path(frame["path"])
                if _sha256(image) != frame["sha256"]:
                    raise ValueError("frame identity mismatch")
                result = caption.describe(image, model=model, timeout_s=min(30, int(remaining)), require_identity=True,
                    endpoint_override={"base": endpoint.rstrip("/"), "protocol": protocol, "model": model, "discovered": False})
                if _sha256(image) != frame["sha256"] or _sha256(path) != source_sha:
                    raise ValueError("input identity changed")
                item.update(state="partial" if result["engine_receipt"].get("completion_state") == "partial" else "succeeded",
                    description=result["description"], engine_receipt=result["engine_receipt"])
                if item["state"] == "partial":
                    item["reason"] = "model_output_truncated"
            except Exception as exc:
                item.update(state="failed", reason="visual_sample_failed", error_type=type(exc).__name__)
            visual.append(item)
        stages["visual"] = {"state": "succeeded" if visual and all(item["state"] == "succeeded" for item in visual) else "partial" if any(item["state"] in {"succeeded", "partial"} for item in visual) else "failed"}
    if _sha256(path) != source_sha:
        raise ValueError("video source identity changed")
    pipeline = "succeeded" if all(stage["state"] == "succeeded" for stage in stages.values()) and not issues else "partial"
    return {"engine": ENGINE, "engine_version": ENGINE_VERSION, "text": transcript["text"], "cues": valid_cues,
            "raw_cues": transcript.get("raw_cues", transcript["cues"]), "alignment_issues": issues,
            "alignment_status": "partial" if issues else transcript.get("alignment_status", "unlocated"),
            "duration_ms": duration, "source_sha256": source_sha, "frames": decoded["frames"], "visual_results": visual,
            "audio_wav": decoded["audio_wav"], "pipeline_state": pipeline, "stages": stages,
            "loss_receipt": {"engine": ENGINE, "engine_version": ENGINE_VERSION,
                "params": {"video_decode": decoded["loss_receipt"], "decode_errors": decoded.get("decode_errors", []), "frame_errors": decoded["frame_errors"], "asr": transcript["loss_receipt"], "sampling": {"max_frames": 3, "requested_interval_ms": interval, "total_job_budget_seconds": 270, "visual_timeout_seconds": 30, "continuous_coverage": False, "unsampled_regions": "all intervals between sampled still frames; no continuous visual analysis", "actual_pts_available": False}},
                "loss_note": "Audio transcript preserved independently, including raw unlocated cues. At most three requested-seek still frames; actual frame PTS unavailable, timing approximate. Unsampled intervals have not been visually analyzed. Stage failures and empty audio results are retained; successful job storage is not full multimedia success."}}


def main() -> int:
    if "--staging-root" in sys.argv:
        transport_path = Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py"
        spec = importlib.util.spec_from_file_location("video_transport", transport_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Transport is missing")
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--staging-root", type=Path, required=True)
        parser.add_argument("--artifact-root", type=Path, required=True)
        args = parser.parse_args()
        return transport.serve_stdio("python-worker-video-ndjson", ["media.video"], args.staging_root, args.artifact_root)
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
