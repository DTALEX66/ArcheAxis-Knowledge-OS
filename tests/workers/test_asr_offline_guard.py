"""Offline ASR guard: synthetic local assets and a constructor sentinel only."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = Path(
    os.environ.get(
        "ASR_GUARD_WORKER", str(ROOT / "services/python-workers/media/worker_transcribe.py")
    )
)


class ConstructorReachedError(Exception):
    pass


@pytest.fixture
def rig(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("asr_offline_guard_candidate", WORKER)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    calls = []

    def constructor(*args, **kwargs):
        calls.append((args, kwargs))
        raise ConstructorReachedError

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=constructor))
    model = tmp_path / "faster-whisper-base"
    model.mkdir()
    for asset in ("model.bin", "config.json", "tokenizer.json"):
        (model / asset).write_bytes(b"{}")
    source = tmp_path / "input.wav"
    source.write_bytes(b"synthetic; decoder must never run")
    decoder = SimpleNamespace(duration_ms=lambda _: 1000)
    monkeypatch.setattr(worker, "_decode_engine", lambda _: {"kind": "pyav"})
    monkeypatch.setattr(worker, "_media_decode", lambda: decoder)
    plan = {"windows": [{"index": 0, "start_ms": 0, "end_ms": 1000}]}
    windows = SimpleNamespace(
        run_windows=lambda plan, per_window, *_: per_window(plan["windows"][0])
    )
    monkeypatch.setattr(worker, "_window_module", lambda: windows)
    monkeypatch.setattr(
        worker, "_plan_module", lambda: SimpleNamespace(plan_windows=lambda _: plan, OVERHEAD_MS=0)
    )

    def invoke(mode):
        if mode == "whole":
            return worker.extract(str(source), str(model), "auto", "cpu")
        if mode == "windowed":
            return worker.extract_windowed(
                str(source), str(model), "auto", "cpu", plan, None, work_dir=str(tmp_path / "work")
            )
        return worker.extract_split(
            str(source), str(model), "auto", "cpu", None, work_dir=str(tmp_path / "work")
        )

    return worker, model, calls, invoke


@pytest.mark.parametrize("mode", ["whole", "windowed", "split"])
@pytest.mark.parametrize("asset", ["model.bin", "config.json", "tokenizer.json"])
def test_missing_asset_fails_before_any_constructor(rig, mode, asset):
    _, model, calls, invoke = rig
    (model / asset).unlink()
    with pytest.raises(ValueError, match=asset.replace(".", r"\.")):
        invoke(mode)
    assert calls == []


@pytest.mark.parametrize("mode", ["whole", "windowed", "split"])
@pytest.mark.parametrize("invalid", ["empty", "directory"])
def test_invalid_tokenizer_fails_before_any_constructor(rig, mode, invalid):
    _, model, calls, invoke = rig
    tokenizer = model / "tokenizer.json"
    tokenizer.unlink()
    if invalid == "empty":
        tokenizer.write_bytes(b"")
    else:
        tokenizer.mkdir()
    with pytest.raises(ValueError, match="tokenizer"):
        invoke(mode)
    assert calls == []


@pytest.mark.parametrize("mode", ["whole", "windowed", "split"])
def test_complete_local_assets_keep_cpu_int8_and_disable_model_download(rig, mode):
    _, model, calls, invoke = rig
    assert not (model / "preprocessor_config.json").exists(), (
        "optional feature config remains optional"
    )
    with pytest.raises(ConstructorReachedError):
        invoke(mode)
    assert calls == [
        ((str(model),), {"device": "cpu", "compute_type": "int8", "local_files_only": True})
    ]


def test_incomplete_explicit_or_override_does_not_fall_back(rig, monkeypatch):
    worker, model, calls, _ = rig
    (model / "tokenizer.json").unlink()
    monkeypatch.setenv("ARCHEAXIS_ASR_MODEL_DIR", str(model))
    monkeypatch.setattr(worker, "_bundled_model_dirs", lambda: pytest.fail("must not fall back"))
    for explicit in (str(model), None):
        with pytest.raises(ValueError, match="tokenizer"):
            worker._resolve_model(explicit)
    assert calls == []


def test_probe_rejects_incomplete_assets_without_constructor(rig):
    worker, model, calls, _ = rig
    (model / "tokenizer.json").unlink()
    result = worker.probe(str(model))
    assert result["capability"] is False and "tokenizer" in result["reason"]
    assert calls == []
