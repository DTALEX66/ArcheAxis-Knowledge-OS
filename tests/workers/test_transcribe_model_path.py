from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/media/worker_transcribe.py"


def _load():
    spec = importlib.util.spec_from_file_location("transcribe_worker_path_test", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_model_root_is_derived_from_checkout_parent():
    module = _load()
    expected = ROOT.parent / "Model library" / "whisper" / "faster-whisper-large-v3-turbo"
    assert expected == module.DEFAULT_MODEL_DIR
    assert "D:/All projects" not in str(module.DEFAULT_MODEL_DIR)


def test_explicit_model_override_remains_supported(tmp_path, monkeypatch):
    module = _load()
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.bin").write_bytes(b"fixture")
    monkeypatch.setenv("ARCHEAXIS_ASR_MODEL_DIR", str(model))
    assert module._model_dir(None) == model
