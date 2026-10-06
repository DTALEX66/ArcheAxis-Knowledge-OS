import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "no_audio",
        "empty_asr",
        "visual_fail",
        "frame_mismatch",
        "not_configured",
        "invalid_cue",
        "asr_timeout",
        "asr_processing_partial",
        "default_local",
        "visual_truncated",
    ],
)
def test_video_stages_preserve_available_results(tmp_path, monkeypatch, mode):
    spec = importlib.util.spec_from_file_location(
        "video",
        Path(__file__).resolve().parents[2] / "services/python-workers/media/worker_video.py",
    )
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video fixture")
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"frame fixture")
    sha = worker._sha256(image)
    decoded = {
        "duration_ms": 83081,
        "audio_wav": None if mode == "no_audio" else {"path": "controlled.wav"},
        "frames": [
            {
                "path": str(image),
                "sha256": "0" * 64 if mode == "frame_mismatch" else sha,
                "offset_ms": 0,
                "sampling_seek_requested_ms": 0,
            }
        ],
        "frame_errors": [],
        "loss_receipt": {},
    }
    monkeypatch.setattr(worker, "_ffmpeg", lambda: "controlled-ffmpeg")
    monkeypatch.setattr(worker, "_probe_duration", lambda *a: 83081)
    monkeypatch.setattr(worker, "extract", lambda *a, **k: decoded)
    cue = {
        "start_ms": 87290 if mode == "invalid_cue" else 0,
        "end_ms": 88290 if mode == "invalid_cue" else 1000,
        "text": "ASR original",
    }

    def asr(*a):
        if mode == "asr_timeout":
            raise TimeoutError("controlled ASR timeout")
        return {
            "text": "" if mode == "empty_asr" else "ASR original",
            "cues": [cue] if mode != "empty_asr" else [],
            "raw_cues": [cue],
            "alignment_issues": [],
            "alignment_status": "complete",
            "processing_status": "partial" if mode == "asr_processing_partial" else "complete",
            "processing_error": {"stage":"segment_iteration","error_type":"RuntimeError"} if mode == "asr_processing_partial" else None,
            "loss_receipt": {},
        }

    def caption(*a, **k):
        if mode == "default_local":
            assert k["model"] == "qwen2.5-vl-7b-instruct"
            assert k["endpoint_override"]["base"] == "http://127.0.0.1:1234/v1"
        if mode == "visual_fail":
            raise RuntimeError("controlled failure")
        return {
            "description": "independent visual output",
            "engine_receipt": {
                "actual_model": "actual-model",
                "requested_model": "requested-model",
                "finish_reason": "stop",
                "completion_state": "partial" if mode == "visual_truncated" else "complete",
            },
        }

    monkeypatch.setattr(worker, "_run_asr", asr)
    monkeypatch.setattr(
        worker,
        "_load_worker",
        lambda name, path: (
            SimpleNamespace(extract=asr)
            if name == "video_asr"
            else SimpleNamespace(describe=caption, OPENAI_BASE="http://127.0.0.1:1234/v1", OPENAI_MODEL="qwen2.5-vl-7b-instruct")
        ),
    )
    monkeypatch.setenv("ARCHEAXIS_CAPTION_ENDPOINT", "http://127.0.0.1:1234/v1")
    monkeypatch.setenv("ARCHEAXIS_CAPTION_PROTOCOL", "openai")
    monkeypatch.setenv(
        "ARCHEAXIS_CAPTION_MODEL", "" if mode == "not_configured" else "requested-model"
    )
    if mode == "not_configured":
        monkeypatch.setenv("ARCHEAXIS_CAPTION_ENDPOINT", "http://example.invalid/v1")
    if mode == "default_local":
        for key in ["ARCHEAXIS_CAPTION_ENDPOINT", "ARCHEAXIS_CAPTION_MODEL", "ARCHEAXIS_CAPTION_PROTOCOL"]:
            monkeypatch.delenv(key)
    result = worker.extract_job(source, tmp_path, None, "auto", "cpu")
    assert result["text"] == (
        "" if mode in {"no_audio", "empty_asr", "asr_timeout"} else "ASR original"
    )
    assert result["source_sha256"] == worker._sha256(source)
    assert result["loss_receipt"]["params"]["sampling"]["continuous_coverage"] is False
    if mode in {"success", "default_local"}:
        assert result["pipeline_state"] == "succeeded"
        item = result["visual_results"][0]
        assert item["frame_sha256"] == sha and item["source_sha256"] == worker._sha256(source)
        assert item["actual_pts_ms"] is None and item["timing_precision"] == "approximate"
        assert item["engine_receipt"]["actual_model"] == "actual-model"
    else:
        assert result["pipeline_state"] == "partial"
    if mode == "asr_processing_partial":
        assert result["stages"]["asr"]["state"] == "partial"
        assert result["stages"]["asr"]["reason"] == "asr_processing_interrupted"
        assert result["stages"]["asr"]["processing_error"] == {"stage":"segment_iteration","error_type":"RuntimeError"}
        assert result["cues"] == [cue]
    if mode in {"frame_mismatch", "visual_fail"}:
        assert result["visual_results"][0]["state"] == "failed"
    if mode == "visual_truncated":
        assert result["visual_results"][0]["state"] == "partial"
        assert result["visual_results"][0]["description"] == "independent visual output"
    if mode == "invalid_cue":
        assert result["cues"] == [] and result["raw_cues"][0]["start_ms"] == 87290
        assert result["alignment_issues"][0]["location_status"] == "unlocated"


def test_asr_subprocess_timeout_is_real_and_bounded(tmp_path, monkeypatch):
    import subprocess
    import time

    spec = importlib.util.spec_from_file_location(
        "video_timeout",
        Path(__file__).resolve().parents[2] / "services/python-workers/media/worker_video.py",
    )
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    monkeypatch.setattr(worker, "__file__", str(tmp_path / "worker_video.py"))
    (tmp_path / "worker_transcribe.py").write_text("import time;time.sleep(10)", encoding="utf-8")
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        worker._run_asr("owned-fixture.wav", None, "auto", "cpu", 0.2)
    assert time.monotonic() - started < 3


@pytest.mark.parametrize("fault", ["audio_timeout", "frame_timeout", "budget_exhausted"])
def test_decode_timeout_returns_existing_artifacts(tmp_path, monkeypatch, fault):
    import subprocess
    import time

    spec = importlib.util.spec_from_file_location(
        "video_decode",
        Path(__file__).resolve().parents[2] / "services/python-workers/media/worker_video.py",
    )
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    source = tmp_path / "test.mp4"
    source.write_bytes(b"owned synthetic video")
    monkeypatch.setattr(worker, "_ffmpeg", lambda: "controlled-ffmpeg")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        audio = "-vn" in command
        if (audio and fault == "audio_timeout") or (not audio and fault == "frame_timeout"):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        Path(command[-1]).write_bytes(b"controlled decoded artifact")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(worker.subprocess, "run", run)
    result = worker.extract(
        source,
        tmp_path / "decoded",
        10000,
        3,
        deadline=time.monotonic() + (-1 if fault == "budget_exhausted" else 20),
        known_duration_ms=30000,
    )
    if fault == "audio_timeout":
        assert result["audio_wav"] is None and len(result["frames"]) == 3
        assert result["decode_errors"][0]["reason"] == "audio_decode_timeout"
    elif fault == "frame_timeout":
        assert result["audio_wav"] is not None and result["frames"] == []
        assert len(result["frame_errors"]) == 3
    else:
        assert not calls and result["audio_wav"] is None
        assert len(result["frame_errors"]) == 3


def test_truncated_visual_response_keeps_available_description(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "caption_partial", Path(__file__).resolve().parents[2] / "services/python-workers/vision/worker_caption.py"
    )
    caption = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(caption)
    image = tmp_path / "controlled.jpg"
    image.write_bytes(b"controlled model response fixture, not image decoding evidence")
    endpoint = {"protocol": "openai", "base": "http://127.0.0.1:1234/v1", "model": "controlled-model"}

    def call(actual_endpoint, model, encoded, timeout, *, receipt=None):
        assert actual_endpoint == endpoint
        receipt.update(actual_model="controlled-model", requested_model=model, finish_reason="length")
        return "available partial description"

    monkeypatch.setattr(caption, "_call", call)
    result = caption.describe(image, require_identity=True, endpoint_override=endpoint)
    assert result["description"] == "available partial description"
    assert result["engine_receipt"]["completion_state"] == "partial"


def test_video_duration_uses_precise_probe_instead_of_rounded_console_duration(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "video_duration", Path(__file__).resolve().parents[2] / "services/python-workers/media/worker_video.py"
    )
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    probe = tmp_path / "ffprobe.exe"
    probe.write_bytes(b"controlled probe identity fixture")

    def run(argv, **kwargs):
        assert argv[0] == str(probe)
        assert "format=duration" in argv
        return SimpleNamespace(returncode=0, stdout='{"format":{"duration":"83.046000"}}')

    monkeypatch.setattr(worker.subprocess, "run", run)
    assert worker._probe_duration(str(tmp_path / "ffmpeg.exe"), tmp_path / "source.mp4") == 83046
