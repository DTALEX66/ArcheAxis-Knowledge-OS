"""The diarization worker must produce a real result or an exact refusal, never a plausible one.

`_unavailable` is the shape that keeps the format matrix honest: empty text, no segments, and the
artifact that is missing named by path. A fabricated `SPK0  0-1000` would look identical to a result
downstream, and a speaker count nobody measured is precisely the claim this repository's rules refuse.
"""
from __future__ import annotations

import importlib.util
import math
import struct
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services" / "python-workers" / "media" / "worker_diarize.py"
spec = importlib.util.spec_from_file_location("worker_diarize", WORKER)
assert spec and spec.loader
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def _wav(path: Path, seconds: float = 1.0, rate: int = 16000, channels: int = 1, width: int = 2) -> Path:
    frames = int(seconds * rate)
    samples = [int(32767 * math.sin(2 * math.pi * 440 * index / rate)) for index in range(frames)]
    payload = struct.pack(f"<{frames * channels}h", *[s for s in samples for _ in range(channels)])
    with wave.open(str(path), "wb") as sink:
        sink.setnchannels(channels)
        sink.setsampwidth(width)
        sink.setframerate(rate)
        sink.writeframes(payload)
    return path


def _library(tmp_path: Path, *, segmentation: bool = True, embedding: bool = True) -> Path:
    directory = tmp_path / "sherpa-onnx" / "speaker-diarization"
    directory.mkdir(parents=True, exist_ok=True)
    if segmentation:
        (directory / worker.SEGMENTATION_FILE).write_bytes(b"onnx")
    if embedding:
        (directory / worker.EMBEDDING_FILE).write_bytes(b"onnx")
    return tmp_path


class _Segment:
    def __init__(self, speaker: int, start: float, end: float) -> None:
        self.speaker, self.start, self.end = speaker, start, end
        self.duration = end - start


class _FakeDiarizer:
    """Records the buffer it was handed so the test can prove nothing was invented."""

    received: list[list[float]] = []
    segments: list[_Segment] = []

    def __init__(self, config: object) -> None:
        self.config = config

    def process(self, samples):
        type(self).received.append(list(samples))

        class _Result:
            num_speakers = len({item.speaker for item in type(self).segments})
            num_segments = len(type(self).segments)

            @staticmethod
            def sort_by_start_time():
                return list(type(self).segments)

        return _Result()


class _FakeSherpa:
    OfflineSpeakerDiarizationConfig = staticmethod(lambda **kwargs: kwargs)
    OfflineSpeakerSegmentationModelConfig = staticmethod(lambda **kwargs: kwargs)
    OfflineSpeakerSegmentationPyannoteModelConfig = staticmethod(lambda **kwargs: kwargs)
    SpeakerEmbeddingExtractorConfig = staticmethod(lambda **kwargs: kwargs)
    FastClusteringConfig = staticmethod(lambda **kwargs: kwargs)
    OfflineSpeakerDiarization = _FakeDiarizer


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    for name in ("ARCHEAXIS_DIARIZATION_MODEL_DIR", "ARCHEAXIS_MODEL_LIBRARY_DIR"):
        monkeypatch.delenv(name, raising=False)
    _FakeDiarizer.received, _FakeDiarizer.segments = [], []


def test_refuses_without_a_declared_library_and_names_both_artifacts(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeSherpa)
    result = worker.diarize("anything.wav")
    assert result["structure"]["state"] == "unavailable"
    assert result["text"] == ""
    assert result["structure"]["segments"] == []
    assert result["loss_receipt"]["params"]["missing_artifacts"] == [
        f"sherpa-onnx/speaker-diarization/{worker.SEGMENTATION_FILE}",
        f"sherpa-onnx/speaker-diarization/{worker.EMBEDDING_FILE}",
    ]
    assert "no diarization was produced" in result["loss_receipt"]["params"]["claim"]


def test_a_missing_runtime_is_named_as_the_gap_not_left_empty(monkeypatch) -> None:
    # The refusal must say which supply is missing, not just that nothing was produced.
    monkeypatch.setitem(sys.modules, "sherpa_onnx", None)
    result = worker.diarize("anything.wav")
    assert result["structure"]["state"] == "unavailable"
    assert result["loss_receipt"]["params"]["reason"] == "sherpa-onnx not installed"
    assert result["loss_receipt"]["params"]["missing_artifacts"] == [
        "python package sherpa-onnx",
        f"sherpa-onnx/speaker-diarization/{worker.SEGMENTATION_FILE}",
        f"sherpa-onnx/speaker-diarization/{worker.EMBEDDING_FILE}",
    ]


def test_names_the_exact_file_when_only_one_model_is_present(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeSherpa)
    library = _library(tmp_path, embedding=False)
    status = worker.probe(str(library))
    assert status["capability"] is False
    assert status["missing_artifacts"] == [str(library / "sherpa-onnx/speaker-diarization" / worker.EMBEDDING_FILE)]
    assert worker.diarize(str(_wav(tmp_path / "a.wav")), str(library))["structure"]["state"] == "unavailable"


def test_a_declared_model_dir_makes_the_refusal_name_paths_not_just_words(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(worker, "_library_root", lambda override: tmp_path)
    paths = worker.model_paths(None)
    assert set(paths) == {"segmentation", "embedding"}
    assert all(str(path).startswith(str(tmp_path)) for path in paths.values()), "the model library is the declared root"


def test_projects_real_segments_and_passes_the_actual_audio_buffer(tmp_path: Path, monkeypatch) -> None:
    library = _library(tmp_path)
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeSherpa)
    _FakeDiarizer.segments = [_Segment(1, 0.0, 0.5), _Segment(0, 0.5, 1.0)]
    audio = _wav(tmp_path / "speech.wav", seconds=1.0)

    result = worker.diarize(str(audio), str(library))

    assert result["structure"]["state"] == "diarized"
    assert result["text"] == "SPK1\t0-500\nSPK0\t500-1000\n"
    assert result["structure"]["num_speakers"] == 2
    assert result["structure"]["segments"][1] == {"speaker": 0, "start": 0.5, "end": 1.0, "duration": 0.5}
    assert result["structure"]["models"]["segmentation"].endswith(worker.SEGMENTATION_FILE)
    assert len(_FakeDiarizer.received[0]) == 16000, "the buffer handed over is the file's own frames"
    assert result["loss_receipt"]["params"]["boundaries_only"] is True


def test_a_wav_the_diarizer_cannot_consume_is_refused_by_name(tmp_path: Path, monkeypatch) -> None:
    library = _library(tmp_path)
    monkeypatch.setitem(sys.modules, "sherpa_onnx", _FakeSherpa)
    for seconds, rate, channels, expected in (
        (1.0, 8000, 1, "8000 Hz"),
        (1.0, 16000, 2, "2 channels"),
    ):
        result = worker.diarize(str(_wav(tmp_path / f"x{rate}{channels}.wav", seconds, rate, channels)), str(library))
        assert result["structure"]["state"] == "unavailable"
        assert expected in result["loss_receipt"]["params"]["reason"], result["loss_receipt"]
        assert _FakeDiarizer.received == [], "a refused file must never reach the model"


def test_a_job_refusal_names_the_missing_artefacts_instead_of_settling_empty(tmp_path, monkeypatch) -> None:
    # The Core launches the worker through `extract`, where an empty result cannot be returned:
    # silence would read as "a recording with no speakers" rather than as nothing being supplied.
    with pytest.raises(RuntimeError) as raised:
        worker.extract(str(_wav(tmp_path / "a.wav")))
    message = str(raised.value)
    assert worker.SEGMENTATION_FILE in message and worker.EMBEDDING_FILE in message, message
