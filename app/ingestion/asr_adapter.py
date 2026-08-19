"""ASR adapter — H2 audio coverage (Model library faster-whisper).

Local speech-to-text via faster-whisper using the shared model library
(D:\All projects\Model library\whisper\<model>). Fail-closed: missing model
or runtime → AdapterResult-like error, never a silent empty transcript.

    resolve_model_dir()      → config/env-driven model directory
    transcribe(audio_path)   → {success, text, language, engine, duration}
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MODEL_DIR = r"D:\All projects\Model library\whisper"
DEFAULT_MODEL_NAME = "faster-whisper-large-v3-turbo"


class AsrError(ValueError):
    """Raised when ASR is unavailable or fails."""


def resolve_model_dir() -> Path:
    """Model directory from config (asr.model_dir) or env, else the shared lib."""
    try:
        from shared.config import config
        configured = str(config.get("asr.model_dir", "") or "").strip()
    except Exception:
        configured = ""
    env_value = os.environ.get("ARCHEAXIS_ASR_MODEL_DIR", "").strip()
    return Path(configured or env_value or DEFAULT_MODEL_DIR)


def transcribe(audio_path: str | Path) -> dict[str, Any]:
    """Transcribe one audio file with faster-whisper (fail-closed).

    Returns {"success": True, "text", "language", "engine", "model"} or raises
    AsrError when the model/runtime is unavailable.
    """
    path = Path(audio_path)
    if not path.is_file():
        raise AsrError(f"audio file not found: {path}")
    model_dir = resolve_model_dir() / DEFAULT_MODEL_NAME
    if not (model_dir / "model.bin").is_file():
        raise AsrError(
            f"whisper model missing at {model_dir} — set ARCHEAXIS_ASR_MODEL_DIR "
            f"or place faster-whisper files in {resolve_model_dir()}"
        )
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:
        raise AsrError("faster-whisper not installed") from exc
    try:
        model = WhisperModel(str(model_dir), device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(path))
        text = "".join(segment.text for segment in segments).strip()
        return {
            "success": True,
            "text": text,
            "language": info.language,
            "engine": f"faster-whisper/{DEFAULT_MODEL_NAME}",
            "model": str(model_dir),
        }
    except Exception as exc:  # noqa: BLE001
        raise AsrError(f"transcription failed: {exc}") from exc



_SENSE_VOICE_DIR = Path(r"D:\All projects\Model library\sherpa-onnx\sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17")


def _read_wav(path: Path):
    """Read a 16-bit PCM wav as float32 mono (no soundfile dependency)."""
    import wave
    import numpy as np
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        frames = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        return sr, frames.astype(np.float32) / 32768.0


def transcribe_sense_voice(audio_path: str | Path) -> dict[str, Any] | None:
    """Fast Chinese ASR via sherpa-onnx + SenseVoice (int8, ~26x faster than
    faster-whisper-large-v3 on CPU). Returns None when model/runtime missing.

    Input must be a 16k mono wav; callers extract via ffmpeg first.
    """
    try:
        import sherpa_onnx  # noqa: F401
    except ImportError:
        return None
    model = _SENSE_VOICE_DIR / "model.int8.onnx"
    tokens = _SENSE_VOICE_DIR / "tokens.txt"
    if not model.is_file() or not tokens.is_file():
        return None
    try:
        rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(model), tokens=str(tokens), num_threads=4)
        sr, samples = _read_wav(Path(audio_path))
        stream = rec.create_stream()
        stream.accept_waveform(sr, samples)
        rec.decode_stream(stream)
        text = stream.result.text.strip()
        if not text:
            return None
        return {"success": True, "text": text, "language": "zh",
                "engine": "sherpa-sense-voice", "model": str(model)}
    except Exception:
        return None
