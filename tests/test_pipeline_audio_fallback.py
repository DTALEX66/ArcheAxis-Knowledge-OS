"""Fallback behavior for the audio pipeline when SenseVoice is unavailable."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pipeline" / "pipeline_audio.py"


def _load_module(monkeypatch):
    monkeypatch.setenv("ARCHEAXIS_PIPELINE_SOURCE_ROOT", str(ROOT / ".project-local"))
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(ROOT / ".project-local" / "test-fallback-run"))
    spec = importlib.util.spec_from_file_location("pipeline_audio_fallback", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_fallback_uses_faster_whisper_when_sensevoice_is_empty(monkeypatch) -> None:
    module = _load_module(monkeypatch)
    monkeypatch.setattr(module, "transcribe_sense_voice", lambda _path: None)
    monkeypatch.setattr(module, "transcribe", lambda _path: {"text": "fallback text", "engine": "whisper"})

    assert module._transcribe_with_fallback("ignored.wav")["text"] == "fallback text"


def test_empty_fallback_is_reported_as_failure(monkeypatch) -> None:
    module = _load_module(monkeypatch)
    monkeypatch.setattr(module, "transcribe_sense_voice", lambda _path: None)
    monkeypatch.setattr(module, "transcribe", lambda _path: {"text": ""})

    assert module._transcribe_with_fallback("ignored.wav") == {}
