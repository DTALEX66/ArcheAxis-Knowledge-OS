"""Tests for H2 audio VAD stub (shared.audio_vad).

Silero VAD requires torch + model download; the stub must behave
honestly when unavailable (empty segments, no crash). The torch path is
exercised via injected fake torch/torchaudio modules so the contract
holds without the heavy dependency installed.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

from shared.audio_vad import is_silero_available, silero_vad_segments


class _FakeWav:
    """Minimal tensor stand-in with shape/methods the VAD path touches."""

    shape = (1, 16000)

    def mean(self, dim=0):
        return self


def _fake_torch_with_hub(load_fn) -> types.ModuleType:
    """Build a minimal torch module whose hub.load calls load_fn."""
    torch = types.ModuleType("torch")
    hub = types.ModuleType("torch.hub")
    hub.load = load_fn
    torch.hub = hub
    return torch


def _install_fake_torch(monkeypatch, load_fn, audio_load):
    torch = _fake_torch_with_hub(load_fn)
    torchaudio = types.ModuleType("torchaudio")
    torchaudio.load = audio_load
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "torchaudio", torchaudio)
    monkeypatch.setattr("shared.audio_vad.is_silero_available", lambda: True)


def test_unavailable_returns_empty_without_torch(monkeypatch) -> None:
    """Without torch the honest contract is an empty segment list."""
    monkeypatch.setattr("shared.audio_vad.is_silero_available", lambda: False)
    segments = silero_vad_segments(Path("missing.wav"))
    assert segments == []


def test_available_contract_delegates_to_silero(monkeypatch) -> None:
    """When available, segments come from Silero get_speech_timestamps."""
    captured: dict[str, object] = {}

    def fake_load(*args, **kwargs):
        captured["source"] = args[0]
        captured["trust_repo"] = kwargs.get("trust_repo")

        def get_speech_timestamps(*_a, **_k):
            return [{"start": 0.0, "end": 1.0}]

        return None, (get_speech_timestamps, None, None, None, None)

    _install_fake_torch(monkeypatch, fake_load, lambda *a, **k: (_FakeWav(), 16000))

    segments = silero_vad_segments("x.wav")
    assert segments == [{"start": 0.0, "end": 1.0}]
    assert captured["source"] == "snakers4/silero-vad"
    assert captured["trust_repo"] is True


def test_audio_read_failure_returns_empty(monkeypatch) -> None:
    """Unreadable audio degrades to empty segments, never a crash."""
    captured: dict[str, object] = {}

    def fake_load(*args, **kwargs):
        captured["source"] = args[0]

        def get_speech_timestamps(*_a, **_k):
            return [{"start": 0.0, "end": 1.0}]

        return None, (get_speech_timestamps, None, None, None, None)

    def broken_load(*_a, **_k):
        raise OSError("simulated unreadable audio")

    _install_fake_torch(monkeypatch, fake_load, broken_load)

    segments = silero_vad_segments("missing.wav")
    assert segments == []
    assert captured["source"] == "snakers4/silero-vad"


def test_is_silero_available_probe_never_raises() -> None:
    """Availability probe degrades to a bool (no crash) in any environment."""
    assert is_silero_available() in (True, False)
