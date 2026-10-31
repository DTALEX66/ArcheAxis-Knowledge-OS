"""Real decoding through the decoder the runtime ships.

The installed product has no system ffmpeg, so `worker_video` and `worker_transcribe` must
decode with PyAV (the runtime's own FFmpeg libraries). These tests open the project-owned
golden MP4 and assert measured facts - a real duration, a 16 kHz mono WAV, a frame with the
container's own timestamp, and cues that keep their position on the recording timeline.
"""

from __future__ import annotations

import importlib.util
import types
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / "services/python-workers/media"
GOLDEN = ROOT / "tests/fixtures/golden/golden-video-anchor.mp4"

pytestmark = pytest.mark.skipif(
    not GOLDEN.is_file(), reason="the project-owned golden MP4 fixture is not present")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def decoder():
    module = load("pyav_decoder_under_test", MEDIA / "media_decode.py")
    if not module.available():
        pytest.skip("PyAV is not installed in this test interpreter")
    return module


def test_the_golden_container_duration_is_measured(decoder):
    duration = decoder.duration_ms(str(GOLDEN))
    assert 2000 <= duration <= 4000, duration


def test_audio_is_decoded_to_the_front_end_the_engine_consumes(decoder, tmp_path):
    target = tmp_path / "audio.wav"
    record = decoder.extract_window(str(GOLDEN), str(target), 0, None)
    with wave.open(str(target), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == 16000
        frames = handle.getnframes()
    assert frames > 16000, "more than one second of audio must have been decoded"
    assert record["decoded_ms"] == int(round(frames / 16))
    assert record["decoder"]["decoder"] == "pyav"


def test_a_bounded_window_is_cut_by_sample_count(decoder, tmp_path):
    target = tmp_path / "window.wav"
    record = decoder.extract_window(str(GOLDEN), str(target), 1000, 2000)
    assert record["requested_ms"] == 1000
    assert record["decoded_ms"] == 1000
    assert target.stat().st_size == 32000 + 44, "1000 ms of 16 kHz mono 16-bit PCM plus a WAV header"


def test_a_frame_carries_the_container_timestamp_not_a_guess(decoder, tmp_path):
    target = tmp_path / "frame.jpg"
    record = decoder.extract_frame(str(GOLDEN), 1000, str(target))
    assert target.is_file() and target.stat().st_size > 0
    assert record["timing_precision"] == "container_pts"
    assert 1000 <= record["actual_pts_ms"] <= 1100, record["actual_pts_ms"]


def test_a_named_failure_when_no_decoder_can_open_the_input(decoder, tmp_path):
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"not a container")
    with pytest.raises(ValueError, match="cannot open media container"):
        decoder.duration_ms(str(broken))


def test_video_worker_decodes_without_any_ffmpeg_binary(monkeypatch, tmp_path):
    worker = load("video_without_ffmpeg", MEDIA / "worker_video.py")
    if not worker._media_decode().available():
        pytest.skip("PyAV is not installed in this test interpreter")
    monkeypatch.setattr(worker, "_ffmpeg", lambda: (_ for _ in ()).throw(
        RuntimeError("ffmpeg binary not found (video engine unavailable)")))
    source = tmp_path / "golden.mp4"
    source.write_bytes(GOLDEN.read_bytes())
    result = worker.extract(source, tmp_path / "out", frame_interval_ms=1000, max_frames=3)
    assert result["loss_receipt"]["params"]["decoder"] == "pyav"
    assert result["audio_wav"] is not None, result["decode_errors"]
    assert 2000 <= result["duration_ms"] <= 4000
    assert result["frames"], result["frame_errors"]
    for frame in result["frames"]:
        assert frame["timing_precision"] == "container_pts"
        assert frame["actual_pts_ms"] is not None and Path(frame["path"]).is_file()


def test_video_worker_names_the_gap_when_neither_decoder_exists(monkeypatch):
    worker = load("video_no_decoder", MEDIA / "worker_video.py")
    monkeypatch.setattr(worker, "_ffmpeg", lambda: (_ for _ in ()).throw(RuntimeError("no ffmpeg")))
    stub = types.SimpleNamespace(available=lambda: False)
    monkeypatch.setattr(worker, "_media_decode", lambda: stub)
    with pytest.raises(RuntimeError, match="no decoder available"):
        worker._decode_engine()


class _Segment:
    def __init__(self, start, end, text):
        self.start, self.end, self.text = start, end, text


class _FakeModel:
    calls: list[str] = []

    def __init__(self, *args, **kwargs):
        pass

    def transcribe(self, path, **kwargs):
        type(self).calls.append(str(path))
        return [_Segment(0.1, 0.4, f"window-{len(type(self).calls)}")], types.SimpleNamespace(
            language="en", duration=1.0)


def test_windows_are_cut_by_the_bundled_decoder_and_cues_keep_their_offsets(monkeypatch, tmp_path):
    worker = load("transcribe_without_ffmpeg", MEDIA / "worker_transcribe.py")
    if not worker._media_decode().available():
        pytest.skip("PyAV is not installed in this test interpreter")
    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = _FakeModel
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", fake)
    _FakeModel.calls = []
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.bin").write_bytes(b"weights")
    (model / "config.json").write_text("{}", encoding="utf-8")
    (model / "tokenizer.json").write_text("{}", encoding="utf-8")
    plan = {
        "windows": [
            {"index": 0, "start_ms": 0, "end_ms": 1000, "audio_ms": 1000, "estimated_ms": 2000},
            {"index": 1, "start_ms": 1000, "end_ms": 2500, "audio_ms": 1500, "estimated_ms": 3000},
        ],
        "windows_total": 2,
        "window_audio_ms": 1000,
        "policy": {"ceiling_ms": 300_000, "overhead_ms": 20_000, "realtime_factor": 2.0},
    }
    merged = worker.extract_windowed(
        str(GOLDEN), str(model), "auto", "cpu", plan, None,
        staging=str(tmp_path / "staging"), work_dir=str(tmp_path / "work"))
    assert merged["windows"]["status"] == "complete"
    assert merged["window_identity"]["decoder"] == "pyav"
    assert [cue["start_ms"] for cue in merged["cues"]] == [100, 1100]
    assert sorted(path.name for path in (tmp_path / "staging").iterdir()) == [
        "window-0000.json", "window-0001.json"]
