"""ASR adapter — H2 audio coverage (Model library faster-whisper).

Local speech-to-text via faster-whisper using the shared model library
(Model library/whisper/<model>). Fail-closed: missing model
or runtime → AdapterResult-like error, never a silent empty transcript.

    resolve_model_dir()      → config/env-driven model directory
    transcribe(audio_path)   → {success, text, language, engine, duration}
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# A shared model library is optional and must be selected explicitly through
# configuration or ARCHEAXIS_ASR_MODEL_DIR. Keep the fallback project-local so
# this module never captures a developer-machine path in the release build.
DEFAULT_MODEL_DIR = Path("models") / "whisper"
DEFAULT_MODEL_NAME = "faster-whisper-large-v3-turbo"


class AsrError(ValueError):
    """Raised when ASR is unavailable or fails."""


def resolve_model_dir() -> Path:
    """Model directory from config/env, shared library, or project-local fallback."""
    try:
        from shared.config import config
        configured = str(config.get("asr.model_dir", "") or "").strip()
    except Exception:
        configured = ""
    env_value = os.environ.get("ARCHEAXIS_ASR_MODEL_DIR", "").strip()
    if configured or env_value:
        return Path(configured or env_value)

    model_library = os.environ.get("ARCHEAXIS_MODEL_LIBRARY_DIR", "").strip()
    if model_library:
        return Path(model_library) / "whisper"

    external_root = (
        os.environ.get("OS_EXTERNAL_CONFIG", "").strip()
        or os.environ.get("ARCHEAXIS_EXTERNAL_ROOT", "").strip()
    )
    if external_root:
        sibling_library = Path(external_root).parent / "Model library" / "whisper"
        if sibling_library.is_dir():
            return sibling_library

    for ancestor in Path(__file__).resolve().parents:
        sibling_library = ancestor.parent / "Model library" / "whisper"
        if sibling_library.is_dir():
            return sibling_library
    return DEFAULT_MODEL_DIR


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



def _sense_voice_dir() -> Path:
    """Return an explicitly configured SenseVoice model location.

    An absent configuration deliberately resolves inside project runtime data,
    where the subsequent model-file check fails closed.
    """
    configured = os.environ.get("ARCHEAXIS_SENSE_VOICE_MODEL_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path(".hermes") / "task-runtime" / "models" / "sense-voice"


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
    model_dir = _sense_voice_dir()
    model = model_dir / "model.int8.onnx"
    tokens = model_dir / "tokens.txt"
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
