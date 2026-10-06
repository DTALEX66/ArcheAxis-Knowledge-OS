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
    monkeypatch.setattr(worker,"_model_dir",lambda value:tmp_path)
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
