"""ASR model resolution stays aligned with the shared model library."""

from __future__ import annotations

from pathlib import Path

from app.ingestion import asr_adapter


def test_sense_voice_uses_shared_model_library(monkeypatch, tmp_path: Path) -> None:
    shared = tmp_path / "Model library"
    model = shared / "sherpa-onnx" / "sense-voice"
    model.mkdir(parents=True)
    (model / "model.int8.onnx").write_bytes(b"fixture")
    (model / "tokens.txt").write_text("fixture", encoding="utf-8")
    monkeypatch.delenv("ARCHEAXIS_SENSE_VOICE_MODEL_DIR", raising=False)
    monkeypatch.setenv("ARCHEAXIS_MODEL_LIBRARY_DIR", str(shared))
    monkeypatch.delenv("ARCHEAXIS_RUN_ROOT", raising=False)

    assert asr_adapter._sense_voice_dir() == model


def test_explicit_sense_voice_path_wins(monkeypatch, tmp_path: Path) -> None:
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("ARCHEAXIS_SENSE_VOICE_MODEL_DIR", str(explicit))
    monkeypatch.setenv("ARCHEAXIS_MODEL_LIBRARY_DIR", str(tmp_path / "shared"))

    assert asr_adapter._sense_voice_dir() == explicit
