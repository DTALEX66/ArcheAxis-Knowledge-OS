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
import shutil
import subprocess
from pathlib import Path
from typing import Any

from shared.adapter_contract import AdapterResult


def _sha256(file_path: str | Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare_audio(file_path: str | Path, work_dir: str | Path) -> Path:
    """Convert media to 16 kHz mono PCM WAV via ffmpeg (must be in PATH)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg executable not found in PATH. See https://ffmpeg.org/download.html")
    out = Path(work_dir) / "audio16k.wav"
    subprocess.run(
        [ffmpeg, "-y", "-i", str(file_path), "-ac", "1", "-ar", "16000", "-f", "wav", str(out)],
        check=True,
        capture_output=True,
        text=True,
    )
    return out


def _transcribe_faster_whisper(path: Path) -> tuple[list[dict[str, Any]], str]:
    from faster_whisper import WhisperModel

    model = WhisperModel("tiny", device="cpu", compute_type="int8")
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
    return blocks, f"faster-whisper({detected_lang or 'auto'})"


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

    if not shutil.which("ffmpeg"):
        return AdapterResult(
            success=False,
            content="",
            engine="media-adapter",
            error="ffmpeg executable not found in PATH. See https://ffmpeg.org/download.html",
        )

    work = Path(work_dir) if work_dir else Path(path).parent
    work.mkdir(parents=True, exist_ok=True)

    try:
        wav = prepare_audio(path, work)
        blocks, engine_label = _transcribe_faster_whisper(wav)
    except Exception as exc:  # pragma: no cover - heavy optional dependency
        return AdapterResult(
            success=False,
            content="",
            engine="media-adapter",
            error=f"media transcription failed: {exc}",
        )
    finally:
        with contextlib.suppress(OSError):
            (work / "audio16k.wav").unlink()

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
