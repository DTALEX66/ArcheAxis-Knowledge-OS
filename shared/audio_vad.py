"""Audio voice activity detection (H2: Silero VAD integration stub).

Silero VAD: MIT license, small PyTorch model (~26 MB).
Currently registered as unavailable-honest — activates when torch>=1.12
and the model file are present.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["silero_vad_segments", "is_silero_available"]


def is_silero_available() -> bool:
    """Check if Silero VAD model and torch are usable."""
    try:
        import torch  # noqa: F401
        _ = torch.hub.load("snakers4/silero-vad", "silero_vad", trust_repo=True)
        return True
    except Exception:
        return False


def silero_vad_segments(
    audio_path: str | Path,
    sample_rate: int = 16000,
    threshold: float = 0.5,
    min_speech_duration_ms: int = 250,
) -> list[dict[str, float]]:
    """Extract speech segments from an audio file using Silero VAD.

    Returns list of {'start': sec, 'end': sec}. Returns empty list if unavailable.
    """
    if not is_silero_available():
        return []

    import torch

    model, utils = torch.hub.load(
        "snakers4/silero-vad", "silero_vad", trust_repo=True
    )
    (get_speech_timestamps, _, _, _, _) = utils

    wav = _read_audio(audio_path, sample_rate)
    if wav is None:
        return []

    speech_ts = get_speech_timestamps(
        wav, model, threshold=threshold,
        min_speech_duration_ms=min_speech_duration_ms,
        return_seconds=True,
    )
    return speech_ts


def _read_audio(path: str | Path, target_sr: int):
    """Read audio to mono 16kHz tensor. Returns None on failure."""
    try:
        import torch
        import torchaudio

        wav, sr = torchaudio.load(str(path))
        if sr != target_sr:
            resampler = torchaudio.transforms.Resample(sr, target_sr)
            wav = resampler(wav)
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0)
        return wav
    except Exception:
        return None
