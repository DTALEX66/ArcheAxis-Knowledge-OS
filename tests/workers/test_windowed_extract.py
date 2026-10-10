"""Windowed extraction end to end: real ffmpeg cuts the audio, a stubbed model supplies the words.

Nothing here mocks ffmpeg: a three second wav is synthesised with the declared binary and the real
window command runs against it. Only the ASR model is replaced, because the point of these tests is
the windowing contract — which byte range was decoded, where the cues land on the recording, and
whether a second invocation repeats work it already did.
"""

import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2]
WORKER = HERE / "services" / "python-workers" / "media" / "worker_transcribe.py"
ROOT_ENV = ("ARCHEAXIS_EXTERNAL_ROOT", "OS_EXTERNAL_CONFIG")
FFMPEG_DECLARED = Path("10-toolchains/scoop/apps/ffmpeg/current/bin/ffmpeg.exe")


def external_root() -> Path | None:
    for name in ROOT_ENV:
        raw = os.environ.get(name, "").strip()
        if raw and Path(raw).is_absolute():
            return Path(raw)
    return None


def ffmpeg_path() -> Path:
    root = external_root()
    if root is None:
        pytest.skip("no external root in the environment; the declared ffmpeg cannot be located")
    candidate = root / FFMPEG_DECLARED
    if not candidate.is_file():
        pytest.skip(f"declared ffmpeg is not present: {candidate}")
    return candidate


def load_worker():
    spec = importlib.util.spec_from_file_location("windowed_worker", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Segment:
    def __init__(self, start, end, text):
        self.start, self.end, self.text = start, end, text


class _FakeModel:
    """Every window reports a cue at its own local 0.2 s, so the offset is what is under test."""

    calls: list[str] = []

    def __init__(self, *args, **kwargs):
        pass

    def transcribe(self, path, **kwargs):
        type(self).calls.append(str(path))
        return [_Segment(0.2, 0.9, f"window-{len(type(self).calls)}")], types.SimpleNamespace(language="zh", duration=2.0)


def install_fake_model(monkeypatch, worker):
    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = _FakeModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    _FakeModel.calls = []
    return _FakeModel


def synthesise(path: Path, ffmpeg: Path, seconds: float = 3.0) -> None:
    finished = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-nostdin", "-f", "lavfi",
         "-i", f"sine=frequency=440:duration={seconds}", "-ac", "1", "-ar", "16000", "-y", str(path)],
        capture_output=True, text=True)
    assert finished.returncode == 0, finished.stderr[-400:]
    assert path.is_file() and path.stat().st_size > 0


def two_window_plan():
    return {
        "windows": [
            {"index": 0, "start_ms": 0, "end_ms": 1_000, "audio_ms": 1_000, "estimated_ms": 2_000},
            {"index": 1, "start_ms": 1_000, "end_ms": 3_000, "audio_ms": 2_000, "estimated_ms": 4_000},
        ],
        "windows_total": 2,
        "window_audio_ms": 1_000,
        "policy": {"ceiling_ms": 300_000, "overhead_ms": 20_000, "realtime_factor": 2.0},
    }


def test_real_windows_are_cut_and_cues_land_on_the_recording_timeline(tmp_path, monkeypatch):
    ffmpeg = ffmpeg_path()
    worker = load_worker()
    install_fake_model(monkeypatch, worker)
    source = tmp_path / "sample.wav"
    synthesise(source, ffmpeg)

    merged = worker.extract_windowed(str(source), None, "auto", "cpu", two_window_plan(), str(ffmpeg),
                                     staging=str(tmp_path / "staging"), work_dir=str(tmp_path / "work"))
    # The windowed path has to look like an ordinary transcribe receipt, or the Core's route contract
    # cannot accept it: same engine identity, same loss receipt, same duration reference.
    assert merged["engine"] == worker.ENGINE
    assert "loss_receipt" in merged and merged["loss_receipt"]["engine"] == worker.ENGINE
    assert merged["duration_ms"] == 3_000, "duration must be the recording's, not the last window's"
    assert merged["windows"]["status"] == "complete"
    assert merged["windows"]["windows_missing"] == []
    assert [cue["start_ms"] for cue in merged["cues"]] == [200, 1_200]
    assert [cue["end_ms"] for cue in merged["cues"]] == [900, 1_900]
    assert merged["window_identity"]["source"] == str(source)
    assert sorted(path.name for path in (tmp_path / "staging").iterdir()) == [
        "window-0000.json", "window-0001.json"]


def test_a_second_invocation_resumes_and_does_not_decode_again(tmp_path, monkeypatch):
    ffmpeg = ffmpeg_path()
    worker = load_worker()
    fake = install_fake_model(monkeypatch, worker)
    source = tmp_path / "sample.wav"
    synthesise(source, ffmpeg)
    staging = str(tmp_path / "staging")

    first = worker.extract_windowed(str(source), None, "auto", "cpu", two_window_plan(), str(ffmpeg),
                                    staging=staging, work_dir=str(tmp_path / "work"))
    decoded = len(fake.calls)
    assert decoded == 2

    second = worker.extract_windowed(str(source), None, "auto", "cpu", two_window_plan(), str(ffmpeg),
                                     staging=staging, work_dir=str(tmp_path / "work2"))
    assert len(fake.calls) == decoded, "finished windows must not be decoded twice"
    assert second["windows"]["windows_resumed"] == [0, 1]
    assert second["text"] == first["text"]


def test_a_missing_ffmpeg_is_named_rather_than_silently_skipped(tmp_path, monkeypatch):
    worker = load_worker()
    install_fake_model(monkeypatch, worker)
    source = tmp_path / "absent.wav"
    source.write_bytes(b"not audio")
    with pytest.raises(ValueError, match="ffmpeg"):
        worker.extract_windowed(str(source), None, "auto", "cpu", two_window_plan(),
                                str(tmp_path / "no-such-ffmpeg.exe"))
