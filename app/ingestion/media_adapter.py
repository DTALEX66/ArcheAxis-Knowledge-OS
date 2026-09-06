"""AXW-023F: structured media transcription adapter (time-anchored blocks).

Transcribes audio/video into time-anchored blocks using faster-whisper
(optional heavy dependency). Each block carries start/end timestamps and
engine + language metadata. When the transcriber is unavailable the
adapter fails closed with a clear error — it never auto-downloads models
and never reports a fake success.

A lightweight fallback path (ffmpeg → 16 kHz mono PCM) is provided via
``prepare_audio`` so callers can wire a custom transcriber; the default
engine stays faster-whisper only when already installed.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

from shared.adapter_contract import AdapterResult


def _is_usable_ffmpeg(candidate: str | Path) -> bool:
    """Return whether a candidate executable can actually start as FFmpeg.

    Scoop shims can remain on PATH after their target directory has moved. A
    file-level ``which`` hit is therefore insufficient on Windows: verify the
    lightweight version command before selecting it for a conversion.
    """
    try:
        completed = subprocess.run(
            [str(candidate), "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and "ffmpeg version" in completed.stdout.casefold()


def resolve_ffmpeg() -> str | None:
    """Find a usable FFmpeg binary, including the configured shared tool root.

    The explicit environment value is preferred.  A PATH candidate is retained
    only after it proves runnable; if a stale shim fails, probe the stable
    Scoop install layout under ``OS_EXTERNAL_CONFIG``.  No download or install
    happens here.
    """
    candidates: list[str] = []
    configured = os.environ.get("FFMPEG_CMD", "").strip()
    if configured:
        candidates.append(configured)
    path_candidate = shutil.which("ffmpeg")
    if path_candidate:
        candidates.append(path_candidate)
    external_root = (
        os.environ.get("OS_EXTERNAL_CONFIG", "").strip()
        or os.environ.get("ARCHEAXIS_EXTERNAL_ROOT", "").strip()
    )
    if external_root:
        root = Path(external_root)
        candidates.extend(
            str(root / relative)
            for relative in (
                Path("10-toolchains") / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe",
                Path("toolchains") / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe",
            )
        )
    seen: set[str] = set()
    for candidate in candidates:
        normalized = os.path.normcase(os.path.abspath(candidate))
        if normalized in seen:
            continue
        seen.add(normalized)
        if Path(candidate).is_file() and _is_usable_ffmpeg(candidate):
            return candidate
    return None


def _is_effectively_silent(wav_path: str | Path, *, min_rms: float = 20.0) -> bool:
    """Reject a wholly silent prepared clip before ASR can hallucinate text.

    This is deliberately a coarse whole-file guard, not voice activity
    detection: normal audio with quiet spans still reaches ASR, while an all
    zero/near-zero PCM clip becomes an explicit degraded outcome.
    """
    try:
        with wave.open(str(wav_path), "rb") as stream:
            if stream.getsampwidth() != 2 or stream.getnchannels() != 1:
                return False
            frames = stream.readframes(stream.getnframes())
    except (OSError, wave.Error):
        return False
    if not frames:
        return True
    sample_count = len(frames) // 2
    if sample_count == 0:
        return True
    total_square = 0
    for offset in range(0, sample_count * 2, 2):
        value = int.from_bytes(frames[offset:offset + 2], byteorder="little", signed=True)
        total_square += value * value
    return (total_square / sample_count) ** 0.5 < min_rms


def _sha256(file_path: str | Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare_audio(file_path: str | Path, work_dir: str | Path) -> Path:
    """Convert media to 16 kHz mono PCM WAV via a resolved FFmpeg binary."""
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg executable not found in PATH. See https://ffmpeg.org/download.html")
    out = Path(work_dir) / f"audio16k-{_sha256(file_path)[:16]}.wav"
    subprocess.run(
        [ffmpeg, "-y", "-i", str(file_path), "-ac", "1", "-ar", "16000", "-f", "wav", str(out)],
        check=True,
        capture_output=True,
        text=True,
    )
    return out


def _transcribe_faster_whisper(path: Path) -> tuple[list[dict[str, Any]], str]:
    from faster_whisper import WhisperModel
    from app.ingestion.asr_adapter import DEFAULT_MODEL_NAME, resolve_model_dir

    model_dir = resolve_model_dir() / DEFAULT_MODEL_NAME
    if not (model_dir / "model.bin").is_file():
        raise RuntimeError(
            "local faster-whisper model missing; configure ARCHEAXIS_ASR_MODEL_DIR "
            f"for {DEFAULT_MODEL_NAME}"
        )
    model = WhisperModel(str(model_dir), device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(path), language=None)
    blocks: list[dict[str, Any]] = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        blocks.append(
            {
                "kind": "transcript",
                "text": text,
                "anchor": {"start_s": round(seg.start, 2), "end_s": round(seg.end, 2)},
            }
        )
    detected_lang = getattr(info, "language", None)
    return blocks, f"faster-whisper/{model_dir.name}({detected_lang or 'auto'})"


def _default_work_dir(file_path: str | Path) -> Path:
    """Keep transient audio outside the source corpus by default."""
    project_root = Path(__file__).resolve().parents[2]
    return project_root / ".project-local" / "task-runtime" / "media" / _sha256(file_path)[:16]


def convert_media(file_path: str | Path, work_dir: str | Path | None = None) -> AdapterResult:
    """Transcribe media into time-anchored blocks.

    Requires faster-whisper (not auto-installed) + ffmpeg. Fails closed
    with clear errors when either is unavailable; no model download is
    ever triggered by this function.
    """
    path = Path(file_path)
    if not path.is_file():
        return AdapterResult(success=False, content="", engine="media-adapter", error="file not found")

    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="media-adapter",
            error="media transcription requires faster-whisper (heavy, optional); install explicitly or use another transcriber.",
        )

    if not resolve_ffmpeg():
        return AdapterResult(
            success=False,
            content="",
            engine="media-adapter",
            error="ffmpeg executable not found in PATH. See https://ffmpeg.org/download.html",
        )

    work = Path(work_dir) if work_dir else _default_work_dir(path)
    work.mkdir(parents=True, exist_ok=True)
    wav: Path | None = None

    try:
        wav = prepare_audio(path, work)
        if _is_effectively_silent(wav):
            return AdapterResult(
                success=False,
                content="",
                engine="media-adapter",
                error="prepared audio contains no detectable signal; no transcript is claimed.",
            )
        blocks, engine_label = _transcribe_faster_whisper(wav)
    except Exception as exc:  # pragma: no cover - heavy optional dependency
        return AdapterResult(
            success=False,
            content="",
            engine="media-adapter",
            error=f"media transcription failed: {exc}",
        )
    finally:
        if wav is not None:
            with contextlib.suppress(OSError):
                wav.unlink()

    if not blocks:
        return AdapterResult(
            success=False,
            content="",
            engine="media-adapter",
            error="media transcription returned no content; treat as degraded.",
        )

    text = "\n".join(b["text"] for b in blocks)
    return AdapterResult(
        success=True,
        content=text,
        engine=engine_label,
        metadata={
            "char_count": len(text),
            "block_count": len(blocks),
            "blocks": blocks,
            "loss_notes": [],
        },
    )


def convert_media_to_run(
    file_path: str | Path,
    db: str | Path,
    source_name: str | None = None,
    version: int = 1,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Transcribe media and persist a ConversionRun; returns run metadata."""
    result = convert_media(file_path, work_dir=work_dir)
    if not result.success:
        raise RuntimeError(result.error or "media transcription failed")

    from app.ingestion.conversion_run import create_conversion_run, store_conversion_run

    raw_sha = _sha256(file_path)
    blocks: list[dict[str, Any]] = result.metadata.get("blocks") or []
    loss = result.metadata.get("loss_notes") or []
    run = create_conversion_run(
        raw_sha256=raw_sha,
        source_name=source_name or Path(file_path).name,
        blocks=blocks,
        engine=result.engine,
        version=version,
    )
    store_conversion_run(db, run)
    return {
        "run_id": run.run_id,
        "document_id": run.document.document_id,
        "block_count": len(blocks),
        "loss_notes": loss,
    }
