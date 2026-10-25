import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.mark.parametrize("rows,located", [([], 0), ([(87.29,88.29,"original tail")],0), ([(0,1,"valid"),(87.29,88.29,"original tail")],1)])
def test_asr_raw_alignment_preserves_text_and_invalid_positions(tmp_path, monkeypatch, rows, located):
    path = Path(__file__).resolve().parents[2] / "services/python-workers/media/worker_transcribe.py"
    spec = importlib.util.spec_from_file_location("alignment_asr", path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    class Model:
        def __init__(self, *args, **kwargs): pass
        def transcribe(self, *args, **kwargs):
            return [types.SimpleNamespace(start=a,end=b,text=t) for a,b,t in rows], types.SimpleNamespace(language="en",duration=83.081,language_probability=1)
    monkeypatch.setitem(sys.modules,"faster_whisper",types.SimpleNamespace(WhisperModel=Model))
    monkeypatch.setattr(worker,"_resolve_model",lambda value:(tmp_path,"test-fixture"))
    source=tmp_path/"controlled.wav"
    source.write_bytes(b"controlled engine output fixture, not actual audio")
    result=worker.extract(str(source),None,"auto","cpu")
    assert result["text"]=="\n".join(t for _,_,t in rows)
    assert len(result["cues"])==located
    assert len(result["raw_cues"])==len(rows)
    if rows and located<len(rows):
        assert result["raw_cues"][-1]["start_ms"]==87290
        assert result["raw_cues"][-1]["end_ms"]==88290
        assert result["alignment_status"]=="partial"
        assert result["alignment_issues"][-1]["location_status"]=="unlocated"
        assert "transcript retained" in result["loss_receipt"]["loss_note"]
        assert "kept empty" not in result["loss_receipt"]["loss_note"]
        if not located:
            assert "all positions unlocated" in result["loss_receipt"]["loss_note"]
    elif not rows:
        assert result["alignment_status"]=="unlocated"
        assert "kept empty" in result["loss_receipt"]["loss_note"]


def test_a_tail_cue_inside_the_declared_vad_pad_is_kept_and_marked(tmp_path, monkeypatch):
    """A real 4.5 s recording yields a segment ending at 4.64 s because VAD pads speech.

    Discarding it left the transcript with text but no usable cue. The pad is declared by
    the engine call, so a cue inside it is kept at its measured position and marked.
    """
    path = Path(__file__).resolve().parents[2] / "services/python-workers/media/worker_transcribe.py"
    spec = importlib.util.spec_from_file_location("alignment_vad_pad", path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)

    class Model:
        def __init__(self, *args, **kwargs): pass
        def transcribe(self, *args, **kwargs):
            return ([types.SimpleNamespace(start=0.0, end=4.64, text="Learning evidence anchor.")],
                    types.SimpleNamespace(language="en", duration=4.5, language_probability=1))

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=Model))
    monkeypatch.setattr(worker, "_resolve_model", lambda value: (tmp_path, "test-fixture"))
    source = tmp_path / "speech.wav"
    source.write_bytes(b"controlled engine output fixture, not actual audio")
    result = worker.extract(str(source), None, "en", "cpu")
    assert result["duration_ms"] == 4500
    assert len(result["cues"]) == 1 and result["cues"][0]["end_beyond_duration_ms"] == 140
    assert result["alignment_issues"] == []
    assert result["alignment_status"] == "complete"
    assert "VAD speech padding" in result["loss_receipt"]["loss_note"]
    assert result["loss_receipt"]["params"]["cue_duration_tolerance_ms"] == worker.VAD_SPEECH_PAD_MS


def test_probe_declares_the_formats_the_decoder_actually_opened(tmp_path):
    path = Path(__file__).resolve().parents[2] / "services/python-workers/media/worker_transcribe.py"
    spec = importlib.util.spec_from_file_location("probe_formats", path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.bin").write_bytes(b"weights")
    report = worker.probe(str(model))
    assert report["capability"] is True
    assert {"wav", "mp3", "m4a", "flac", "ogg", "opus", "mp4", "mov", "webm"} <= set(report["formats"])
