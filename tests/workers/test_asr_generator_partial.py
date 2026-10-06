import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def worker(tmp_path, monkeypatch, first):
    path = (
        Path(__file__).resolve().parents[2] / "services/python-workers/media/worker_transcribe.py"
    )
    spec = importlib.util.spec_from_file_location("partial_asr", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def segments():
        if first:
            yield SimpleNamespace(start=0, end=1, text="original yielded text")
        raise RuntimeError("do not expose underlying engine message")

    class Model:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, *args, **kwargs):
            return segments(), SimpleNamespace(duration=4, language="en", language_probability=1)

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Model))
    monkeypatch.setattr(module, "_model_dir", lambda value: tmp_path)
    source = tmp_path / "controlled.wav"
    source.write_bytes(b"synthetic engine output fixture")
    return module, source


def test_yield_then_failure_keeps_text_raw_and_independent_alignment(tmp_path, monkeypatch):
    module, source = worker(tmp_path, monkeypatch, True)
    result = module.extract(str(source), None, "auto", "cpu")
    assert result["text"] == "original yielded text"
    assert result["raw_cues"] == [{"start_ms": 0, "end_ms": 1000, "text": "original yielded text"}]
    assert result["cues"][0]["raw_index"] == 0
    assert result["processing_status"] == "partial"
    assert result["alignment_status"] == "complete"
    assert result["processing_error"] == {
        "stage": "segment_iteration",
        "error_type": "RuntimeError",
    }
    assert "unprocessed remainder unknown" in result["loss_receipt"]["loss_note"]
    assert "do not expose" not in str(result)


def test_no_yield_failure_is_nonzero_and_never_silence(tmp_path, monkeypatch, capsys):
    module, source = worker(tmp_path, monkeypatch, False)
    with pytest.raises(RuntimeError, match="before any usable result"):
        module.extract(str(source), None, "auto", "cpu")
    monkeypatch.setattr(sys, "argv", ["worker_transcribe.py", str(source)])
    assert module.main() == 1
    output = capsys.readouterr().out
    assert "before any usable result" in output
    assert "do not expose" not in output and "no speech" not in output
