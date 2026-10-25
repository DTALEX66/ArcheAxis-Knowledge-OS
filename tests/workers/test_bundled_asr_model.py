"""The packaged model is found inside the runtime, and its absence is named.

`worker_transcribe.py` used to derive its model only from the checkout's parent, the declared
external root or a shared sibling library. None of those exist on an installed machine, so the
probe reported a missing model for a product that could have shipped one. These tests pin the
new first step - the model beside the runtime - and the precedence around it.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/media/worker_transcribe.py"
STAGER = ROOT / "scripts/release/stage_backend_runtime.py"


def load(name: str, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def staged_root(tmp_path):
    """A product-shaped tree: <root>/workers/media/worker_transcribe.py."""
    worker = tmp_path / "workers" / "media" / "worker_transcribe.py"
    worker.parent.mkdir(parents=True)
    worker.write_text("# staged worker placeholder\n", encoding="utf-8")
    return worker


def bundle_model(root, name="faster-whisper-base", marker=True):
    directory = root / "runtime" / "models" / "asr" / name
    directory.mkdir(parents=True)
    if marker:
        (directory / "model.bin").write_bytes(b"synthetic weights")
    (directory / "config.json").write_text("{}", encoding="utf-8")
    (directory / "aaos-model.json").write_text(json.dumps({
        "schema": "archeaxis.asr-model/v1",
        "name": name,
        "license": {"code_license": "MIT", "asset_license": "MIT per the upstream model card"},
    }), encoding="utf-8")
    return directory


def test_the_staged_worker_is_pointed_at_the_bundled_model(tmp_path, monkeypatch):
    worker = load("transcribe_bundled", WORKER)
    staged = staged_root(tmp_path)
    model = bundle_model(tmp_path)
    monkeypatch.setattr(worker, "__file__", str(staged))
    monkeypatch.delenv("ARCHEAXIS_ASR_MODEL_DIR", raising=False)
    resolved, source = worker._resolve_model(None)
    assert resolved.resolve() == model.resolve()
    assert source == "bundled"


def test_the_bundled_model_wins_over_a_machine_level_declaration(tmp_path, monkeypatch):
    worker = load("transcribe_bundled_precedence", WORKER)
    monkeypatch.setattr(worker, "__file__", str(staged_root(tmp_path)))
    monkeypatch.delenv("ARCHEAXIS_ASR_MODEL_DIR", raising=False)
    model = bundle_model(tmp_path)
    monkeypatch.setattr(worker, "_declared_path", lambda name: str(tmp_path / "elsewhere"))
    resolved, source = worker._resolve_model(None)
    assert resolved.resolve() == model.resolve() and source == "bundled"


def test_a_larger_shipped_model_is_preferred_over_a_smaller_one(tmp_path, monkeypatch):
    worker = load("transcribe_bundled_order", WORKER)
    monkeypatch.setattr(worker, "__file__", str(staged_root(tmp_path)))
    bundle_model(tmp_path, "faster-whisper-base")
    larger = bundle_model(tmp_path, "faster-whisper-large-v3-turbo")
    resolved, _ = worker._resolve_model(None)
    assert resolved.resolve() == larger.resolve()


def test_an_explicit_argument_and_override_still_win(tmp_path, monkeypatch):
    worker = load("transcribe_bundled_override", WORKER)
    monkeypatch.setattr(worker, "__file__", str(staged_root(tmp_path)))
    bundle_model(tmp_path)
    chosen = tmp_path / "chosen"
    chosen.mkdir()
    (chosen / "model.bin").write_bytes(b"weights")
    assert worker._resolve_model(str(chosen)) == (chosen, "argument")
    monkeypatch.setenv("ARCHEAXIS_ASR_MODEL_DIR", str(chosen))
    assert worker._resolve_model(None) == (chosen, "override")


def test_a_directory_without_weights_is_not_accepted_as_a_model(tmp_path, monkeypatch):
    worker = load("transcribe_bundled_marker", WORKER)
    monkeypatch.setattr(worker, "__file__", str(staged_root(tmp_path)))
    directory = tmp_path / "runtime" / "models" / "asr" / "faster-whisper-base"
    directory.mkdir(parents=True)
    (directory / "config.json").write_text("{}", encoding="utf-8")
    assert worker._bundled_model_dirs() == [], "a directory without model.bin is not a model"
    monkeypatch.delenv("ARCHEAXIS_ASR_MODEL_DIR", raising=False)
    monkeypatch.setattr(worker, "_declared_path", lambda name: None)
    monkeypatch.setattr(worker, "_root_derived_model_dir", lambda: None)
    monkeypatch.setattr(worker, "DEFAULT_MODEL_DIR", tmp_path / "absent")
    with pytest.raises(ValueError, match="ASR model directory not found"):
        worker._resolve_model(None)


def test_a_missing_model_names_the_product_local_location(tmp_path, monkeypatch):
    worker = load("transcribe_bundled_missing", WORKER)
    monkeypatch.setattr(worker, "__file__", str(staged_root(tmp_path)))
    monkeypatch.delenv("ARCHEAXIS_ASR_MODEL_DIR", raising=False)
    monkeypatch.setattr(worker, "_declared_path", lambda name: None)
    monkeypatch.setattr(worker, "_root_derived_model_dir", lambda: None)
    monkeypatch.setattr(worker, "DEFAULT_MODEL_DIR", tmp_path / "absent")
    with pytest.raises(ValueError) as error:
        worker._resolve_model(None)
    message = str(error.value)
    assert "ASR model directory not found" in message
    assert "runtime" in message and "models" in message, "the failure must name the product-local spot"


def test_the_bundled_layout_is_the_one_packaging_writes():
    """Worker discovery and packaging must agree on one relative path, or the model is orphaned."""
    worker = load("transcribe_bundled_layout", WORKER)
    stager = load("stager_layout", STAGER)
    relative = worker.BUNDLED_MODEL_RELATIVE.as_posix()
    assert relative == stager.ASR_MODEL_ROOT
    assert relative.startswith("runtime/"), "the model must travel with the runtime bundle resource"


def test_the_shipped_identity_is_reported_beside_the_model(tmp_path, monkeypatch):
    worker = load("transcribe_bundled_identity", WORKER)
    monkeypatch.setattr(worker, "__file__", str(staged_root(tmp_path)))
    model = bundle_model(tmp_path)
    identity = worker._model_identity(model)
    assert identity and identity["name"] == "faster-whisper-base"
    assert identity["license"]["code_license"] == "MIT"
