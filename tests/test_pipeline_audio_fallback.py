"""Fallback behavior for the audio pipeline when SenseVoice is unavailable."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pipeline" / "pipeline_audio.py"


def _load_module(monkeypatch, tmp_path):
    """Load the module against per-test scratch directories.

    The run root used to be a fixed path inside the ignored development root, which left
    `.project-local/test-fallback-run` behind on every run and tripped the layout contract that
    asserts the development root holds only sanctioned classes.
    """
    monkeypatch.setenv("ARCHEAXIS_PIPELINE_SOURCE_ROOT", str(tmp_path / "source-root"))
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(tmp_path / "run-root"))
    spec = importlib.util.spec_from_file_location("pipeline_audio_fallback", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_fallback_uses_faster_whisper_when_sensevoice_is_empty(monkeypatch, tmp_path) -> None:
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "transcribe_sense_voice", lambda _path: None)
    monkeypatch.setattr(module, "transcribe", lambda _path: {"text": "fallback text", "engine": "whisper"})

    assert module._transcribe_with_fallback("ignored.wav")["text"] == "fallback text"


def test_empty_fallback_is_reported_as_failure(monkeypatch, tmp_path) -> None:
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "transcribe_sense_voice", lambda _path: None)
    monkeypatch.setattr(module, "transcribe", lambda _path: {"text": ""})

    assert module._transcribe_with_fallback("ignored.wav") == {}
