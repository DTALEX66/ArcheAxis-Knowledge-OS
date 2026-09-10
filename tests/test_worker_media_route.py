"""R15/F10-F11: a media probe that reads headers and never claims to have decoded.

Audio and video are binary, so they get their own route. The probe reads a WAV header or
the ISO base media file boxes of an MP4/MOV and projects a fact listing; the receipt
states that the facts are what the container declares, that nothing was decoded, and
therefore that there is no waveform, transcript, timestamp, keyframe or coverage fact.

Samples are built here (a real WAV through the wave module, a structurally valid MP4
written box by box), so nothing private is involved.
"""

from __future__ import annotations

import importlib.util
import struct
import subprocess
import sys
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "document" / "worker_media.py"
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load("worker_media_under_test", WORKER)
transport = _load("media_transport_under_test", TRANSPORT)


def _box(kind: str, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload) + 8) + kind.encode("ascii") + payload


def _mvhd(timescale: int = 1000, duration: int = 2500) -> bytes:
    payload = struct.pack(">B3s", 0, b"\x00\x00\x00")  # version 0 + flags
    payload += struct.pack(">II", 0, 0)  # creation/modification
    payload += struct.pack(">II", timescale, duration)
    payload += b"\x00" * 80
    return _box("mvhd", payload)


def _trak(handler: bytes, timescale: int, duration: int) -> bytes:
    mdhd = _box("mdhd", struct.pack(">B3sIIII", 0, b"\x00\x00\x00", 0, 0, timescale, duration) + b"\x00\x00\x00\x00")
    hdlr = _box("hdlr", struct.pack(">B3sI", 0, b"\x00\x00\x00", 0) + handler + b"\x00" * 12)
    return _box("trak", _box("mdia", mdhd + hdlr))


def _write_mp4(path: Path) -> None:
    ftyp = _box("ftyp", b"isom" + struct.pack(">I", 512) + b"isomiso2avc1mp41")
    moov = _box("moov", _mvhd() + _trak(b"vide", 1000, 2500) + _trak(b"soun", 48000, 120000))
    path.write_bytes(ftyp + moov)


def _write_wav(path: Path, seconds: float = 0.5, rate: int = 8000) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x01" * 2 * int(rate * seconds))


def _facts(result: dict) -> dict:
    return result["loss_receipt"]["params"]["structure"]


def test_a_real_wav_header_is_reported_with_its_arithmetic(tmp_path: Path):
    sample = tmp_path / "tone.wav"
    _write_wav(sample, seconds=0.5, rate=8000)
    result = worker.extract(str(sample))
    assert result["engine"] == worker.ENGINE
    facts = _facts(result)
    assert facts["container"] == "wav"
    assert facts["channels"] == 2
    assert facts["sample_rate_hz"] == 8000
    assert facts["sample_width_bytes"] == 2
    assert facts["frame_count"] == 4000
    assert facts["duration_seconds"] == 0.5
    assert "WAV header" in facts["declared_by"]

    # the projection is the fact listing, with line anchors covering it
    lines = result["text"].splitlines()
    assert lines[0] == "container\twav"
    assert any(line == "sample_rate_hz\t8000" for line in lines), lines
    assert result["structure"][-1]["char_end"] == len(result["text"])
    assert result["loss_receipt"]["covered"] == result["loss_receipt"]["total"]
    assert result["loss_receipt"]["coverage"] == 1.0


def test_a_structurally_valid_mp4_reports_brand_duration_and_tracks(tmp_path: Path):
    sample = tmp_path / "clip.mp4"
    _write_mp4(sample)
    result = worker.extract(str(sample))
    facts = _facts(result)
    assert facts["container"] == "iso-base-media"
    assert facts["major_brand"] == "isom"
    assert "avc1" in facts["compatible_brands"]
    assert facts["timescale"] == 1000
    assert facts["duration_units"] == 2500
    assert facts["duration_seconds"] == 2.5
    assert facts["track_count"] == 2
    assert [track["handler"] for track in facts["tracks"]] == ["vide", "soun"]
    assert facts["box_types"] == ["ftyp", "moov"]
    lines = result["text"].splitlines()
    assert "track-1\tvide\t1000\t2500" in lines, lines
    assert "track-2\tsoun\t48000\t120000" in lines, lines


def test_the_receipt_says_nothing_was_decoded(tmp_path: Path):
    sample = tmp_path / "tone.wav"
    _write_wav(sample)
    result = worker.extract(str(sample))
    params = result["loss_receipt"]["params"]
    assert params["projection"] == "media header fact listing (one key/value per line)"
    assert "not measurements of the media" in params["projection_note"]
    assert any("no sample, frame or track was decoded" in loss for loss in result["loss_receipt"]["losses"])
    # no accuracy-style claim anywhere
    assert "accuracy" not in str(result["loss_receipt"]).lower()


def test_a_container_the_probe_cannot_read_is_refused_by_name(tmp_path: Path):
    sample = tmp_path / "song.mp3"
    sample.write_bytes(b"ID3\x04\x00\x00 not something this probe reads")
    try:
        worker.extract(str(sample))
    except ValueError as error:
        assert "unrecognised media container" in str(error)
    else:  # pragma: no cover - the refusal is the point
        raise AssertionError("an unreadable media container must not produce a success envelope")


def test_a_wav_header_that_lies_about_its_frames_is_reported_not_guessed(tmp_path: Path):
    sample = tmp_path / "empty.wav"
    with wave.open(str(sample), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"")
    result = worker.extract(str(sample))
    facts = _facts(result)
    assert facts["frame_count"] == 0
    assert facts["duration_seconds"] == 0.0
    assert any("zero frames" in loss for loss in result["loss_receipt"]["losses"])


def test_the_transport_declares_the_media_route_and_its_media_types():
    route = transport.ROUTES["media.probe"]
    assert route["media_types"] == {"video/mp4", "audio/wav"}
    assert route["worker"] == "services/python-workers/document/worker_media.py"
    assert route["call"] == "path"
    # a media file must not be readable through the text route
    assert "audio/wav" not in transport.ROUTES["text.extract"]["media_types"]
    assert "video/mp4" not in transport.ROUTES["text.extract"]["media_types"]


def test_the_worker_prints_exactly_one_envelope_on_stdout(tmp_path: Path):
    sample = tmp_path / "tone.wav"
    _write_wav(sample)
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(WORKER), str(sample)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, f"stdout must be exactly one envelope: {lines[:3]}"
    assert '"engine": "python-worker-media"' in lines[0]
