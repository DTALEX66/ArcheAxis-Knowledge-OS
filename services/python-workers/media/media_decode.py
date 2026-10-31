#!/usr/bin/env python3
"""Decode audio and still frames with the decoder this runtime actually ships.

The packaged product cannot assume a system `ffmpeg.exe`. The registered declaration names
one under the external configuration root, which exists on the build host and not on an
installed machine, so an installed candidate reported `ffmpeg not found` for a container it
could have decoded: `faster-whisper` already depends on PyAV, and PyAV carries its own
FFmpeg libraries in the runtime (`av`, `av.libs`). This module is that decoder, used when a
declared binary is absent.

What it does, and the limits it states:

* audio is decoded and resampled to 16 kHz mono 16-bit PCM, the front end the ASR engine
  consumes, and a window is cut by sample count so its length is measured, not assumed;
* a still frame is written from a decoded video frame, with the container's own timestamp
  reported when it has one and `unlocated` when it does not;
* every failure is named - an unreadable container, a missing track, an empty window and an
  exhausted budget are different answers and are not collapsed into "decode failed".

It never invents a duration, a timestamp or a sample count.
"""

from __future__ import annotations

import time
import wave
from pathlib import Path

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_BYTES = 2


class DecodeUnavailable(RuntimeError):
    """No decoder is available on this host."""


class DecodeFailure(ValueError):
    """The decoder is available, but this container or track could not be decoded."""


def _av():
    try:
        import av
    except ImportError as exc:
        raise DecodeUnavailable(
            "PyAV (av) is not installed and no declared ffmpeg binary was resolved; "
            "no decoder can open this container") from exc
    return av


def available() -> bool:
    try:
        _av()
    except DecodeUnavailable:
        return False
    return True


def identity() -> dict:
    av = _av()
    return {
        "decoder": "pyav",
        "pyav_version": str(getattr(av, "__version__", "unknown")),
        "ffmpeg_version": str(getattr(av, "ffmpeg_version_info", "unknown")),
    }


def _open(source: str):
    av = _av()
    path = Path(source)
    if not path.is_file():
        raise DecodeFailure(f"media file not found: {path}")
    try:
        return av.open(str(path))
    except Exception as exc:  # noqa: BLE001 - a container this decoder cannot open is a named failure
        raise DecodeFailure(
            f"cannot open media container {path.name}: {type(exc).__name__}: {exc}") from exc


def _first_stream(container, kind: str):
    stream = next((item for item in container.streams if item.type == kind), None)
    if stream is None:
        raise DecodeFailure(f"container has no {kind} track")
    return stream


def _decoded(container, stream, deadline: float | None):
    for frame in container.decode(stream):
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError("decoder budget exhausted")
        yield frame


def _frame_ms(frame) -> float | None:
    """The frame's own presentation time in milliseconds, or None when it has none."""
    stamp = getattr(frame, "time", None)
    return None if stamp is None else float(stamp) * 1000.0


def duration_ms(source: str) -> int:
    """The container's duration in milliseconds, or a named failure when it has none."""
    with _open(source) as container:
        if container.duration:
            return max(0, int(container.duration) // 1000)
        spans = []
        for stream in container.streams:
            if stream.duration is not None and stream.time_base is not None:
                spans.append(float(stream.duration * stream.time_base) * 1000.0)
        if not spans:
            raise DecodeFailure("the container reports no duration")
        return int(round(max(spans)))


def extract_window(source: str, target: str, start_ms: int, end_ms: int | None,
                   deadline: float | None = None) -> dict:
    """Write one bounded span of the audio track as 16 kHz mono 16-bit PCM WAV.

    The cut is made by sample count against the requested span, so a shorter decode is
    reported as a shorter window rather than padded to the length that was asked for. An
    `end_ms` of None means "to the end of the track" and is used by the whole-file path.
    """
    if start_ms < 0 or (end_ms is not None and end_ms <= start_ms):
        raise DecodeFailure("window must be a positive range")
    av = _av()
    wanted_samples = (None if end_ms is None
                      else int(round((end_ms - start_ms) * SAMPLE_RATE / 1000)))
    pcm = bytearray()
    first_stamp_ms: float | None = None
    completed = False
    with _open(source) as container:
        stream = _first_stream(container, "audio")
        if start_ms > 0:
            # Without a named stream the offset is in AV_TIME_BASE units (microseconds).
            container.seek(int(start_ms * 1000))
        resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
        for frame in _decoded(container, stream, deadline):
            stamp = _frame_ms(frame)
            span = 0.0
            sample_rate = getattr(frame, "sample_rate", None)
            samples = getattr(frame, "samples", None)
            if sample_rate and isinstance(samples, int):
                span = samples * 1000.0 / sample_rate
            if stamp is not None and span and stamp + span <= start_ms:
                continue
            pieces = resampler.resample(frame) or []
            for piece in pieces:
                data = piece.to_ndarray().tobytes()
                if first_stamp_ms is None:
                    first_stamp_ms = stamp if stamp is not None else float(start_ms)
                    lead = int(round(max(0.0, start_ms - first_stamp_ms) * SAMPLE_RATE / 1000))
                    data = data[lead * SAMPLE_BYTES:]
                pcm.extend(data)
                if wanted_samples is not None and len(pcm) >= wanted_samples * SAMPLE_BYTES:
                    del pcm[wanted_samples * SAMPLE_BYTES:]
                    completed = True
                    break
            if completed:
                break
        if not completed:
            for piece in resampler.resample(None) or []:
                pcm.extend(piece.to_ndarray().tobytes())
    if not pcm:
        raise DecodeFailure(f"no audio samples decoded for {start_ms}-{end_ms} ms")
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target_path), "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(SAMPLE_BYTES)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(bytes(pcm))
    decoded_ms = int(round(len(pcm) / SAMPLE_BYTES / SAMPLE_RATE * 1000))
    if end_ms is None:
        coverage = (f"decoded {decoded_ms} ms from {start_ms} ms to the end of the audio track; "
                    "the end of the track is the decode's own stop, not a requested one")
    elif decoded_ms < end_ms - start_ms:
        coverage = (f"decoded {decoded_ms} ms of the requested {end_ms - start_ms} ms window; "
                    "the decoded span is shorter than requested and is reported as such")
    else:
        coverage = f"decoded the requested {end_ms - start_ms} ms window by sample count"
    return {
        "path": str(target_path),
        "bytes": len(pcm),
        "sample_rate": SAMPLE_RATE,
        "channels": CHANNELS,
        "decoded_ms": decoded_ms,
        "requested_ms": None if end_ms is None else end_ms - start_ms,
        "decoder": identity(),
        "coverage_note": coverage,
    }


def extract_frame(source: str, at_ms: int, target: str,
                  deadline: float | None = None) -> dict:
    """Write the first decoded video frame at or after *at_ms* as a JPEG still."""
    if at_ms < 0:
        raise DecodeFailure("frame offset must not be negative")
    chosen = None
    with _open(source) as container:
        stream = _first_stream(container, "video")
        if at_ms > 0:
            container.seek(int(at_ms * 1000))
        for frame in _decoded(container, stream, deadline):
            stamp = _frame_ms(frame)
            chosen = (frame, stamp)
            if stamp is not None and stamp >= at_ms:
                break
        if chosen is None:
            raise DecodeFailure(f"no video frame decoded at or after {at_ms} ms")
        frame, stamp = chosen
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        image = frame.to_image()
        image.convert("RGB").save(str(target_path), "JPEG", quality=90)
    return {
        "path": str(target_path),
        "requested_ms": at_ms,
        "actual_pts_ms": None if stamp is None else int(round(stamp)),
        "timing_precision": "container_pts" if stamp is not None else "unlocated",
        "decoder": identity(),
    }
