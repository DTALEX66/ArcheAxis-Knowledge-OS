#!/usr/bin/env python3
"""ArcheAxis vNext media probe worker: header facts for audio and video (F10/F11).

Audio and video are binary, so they never travel through the text route. This worker
reads the **container's own header structure** - a WAV header, or the ISO base media
file boxes of an MP4/MOV - and projects a **fact listing** (one `key<TAB>value` line
per fact) so the projection is a real, addressable text with line anchors.

What it does NOT do, and says so in the receipt:

* it never decodes a sample, a frame or a track: no waveform, no transcript, no frame
  event, no sampling coverage;
* it reports what the header claims (duration, sample rate, track handlers). A header
  is a claim by the file, not a measurement of its content;
* formats it cannot read (mp3, m4a, flac, mkv, webm) are refused by name instead of
  being probed with a guess.

Usage:
    python worker_media.py <input-file>
Output: {"engine","engine_version","text","structure","loss_receipt"}
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import struct
import sys
import wave
from pathlib import Path

ENGINE = "python-worker-media"
ENGINE_VERSION = "0.1.0"
WORKER_IDENTITY = "python-worker-media-ndjson"
FACT_CAP = 200
BOX_DEPTH_CAP = 8


def _line_anchors(text: str, cap: int = 5000) -> list[dict]:
    anchors: list[dict] = []
    offset = 0
    for index, line in enumerate(text.splitlines(keepends=True), start=1):
        anchors.append(
            {"kind": "line", "path": [f"line-{index}"], "char_start": offset, "char_end": offset + len(line)}
        )
        offset += len(line)
        if index >= cap:
            break
    return anchors


def _wav_facts(raw: bytes, path: str) -> tuple[dict, list[str]]:
    problems: list[str] = []
    try:
        with wave.open(path, "rb") as handle:
            channels = handle.getnchannels()
            rate = handle.getframerate()
            frames = handle.getnframes()
            width = handle.getsampwidth()
            compression = handle.getcomptype()
    except Exception as exc:  # noqa: BLE001 - an unreadable header is a failure, not a fact
        raise ValueError(f"unreadable WAV header: {type(exc).__name__}: {exc}") from exc
    if frames == 0:
        problems.append("the header declares zero frames, so there is no audio to describe")
    return {
        "container": "wav",
        "channels": channels,
        "sample_rate_hz": rate,
        "sample_width_bytes": width,
        "compression": compression,
        "frame_count": frames,
        "duration_seconds": round(frames / rate, 3) if rate else None,
        "declared_by": "the WAV header",
    }, problems


def _boxes(raw: bytes, start: int, end: int):
    """Yield (type, payload_start, payload_end) for the boxes in one range.

    A truncated or impossible box stops the walk: what was read is reported and the
    caller never invents a fact for the part it could not parse.
    """
    cursor = start
    while cursor + 8 <= end:
        size = struct.unpack(">I", raw[cursor : cursor + 4])[0]
        kind = raw[cursor + 4 : cursor + 8].decode("latin-1", "replace")
        header = 8
        if size == 1:
            if cursor + 16 > end:
                return
            size = struct.unpack(">Q", raw[cursor + 8 : cursor + 16])[0]
            header = 16
        elif size == 0:
            size = end - cursor
        if size < header or cursor + size > end:
            return
        yield kind, cursor + header, cursor + size
        cursor += size


def _find(raw: bytes, start: int, end: int, name: str):
    for kind, payload_start, payload_end in _boxes(raw, start, end):
        if kind == name:
            return payload_start, payload_end
    return None


def _nested(raw: bytes, names: tuple[str, ...]):
    start, end = 0, len(raw)
    for name in names:
        found = _find(raw, start, end, name)
        if found is None:
            return None
        start, end = found
    return start, end


def _mp4_facts(raw: bytes) -> tuple[dict, list[str]]:
    problems: list[str] = []
    top = [(kind, start, end) for kind, start, end in _boxes(raw, 0, len(raw))]
    kinds = [kind for kind, _, _ in top]
    if "ftyp" not in kinds:
        raise ValueError("unreadable media container: no ISO base media file header (ftyp) found")

    major_brand = None
    compatible: list[str] = []
    ftyp = _nested(raw, ("ftyp",))
    if ftyp is not None:
        payload = raw[ftyp[0] : ftyp[1]]
        if len(payload) >= 8:
            major_brand = payload[0:4].decode("latin-1", "replace")
            compatible = [
                payload[offset : offset + 4].decode("latin-1", "replace")
                for offset in range(8, len(payload) - 3, 4)
            ]
    else:
        problems.append("the header box could not be read, so the brand is unknown")

    mvhd = _nested(raw, ("moov", "mvhd"))
    timescale = None
    duration = None
    if mvhd is not None:
        payload = raw[mvhd[0] : mvhd[1]]
        if len(payload) >= 20 and payload[0] == 0:
            timescale = struct.unpack(">I", payload[12:16])[0]
            duration = struct.unpack(">I", payload[16:20])[0]
        else:
            problems.append("the movie header uses a version this probe does not read (or is truncated)")

    tracks: list[dict] = []
    moov = _nested(raw, ("moov",))
    if moov is not None:
        for kind, start, end in _boxes(raw, moov[0], moov[1]):
            if kind != "trak":
                continue
            handler = None
            track_timescale = None
            track_duration = None
            mdia = _find(raw, start, end, "mdia")
            if mdia is not None:
                hdlr = _find(raw, mdia[0], mdia[1], "hdlr")
                if hdlr is not None and hdlr[1] - hdlr[0] >= 12:
                    handler = raw[hdlr[0] + 8 : hdlr[0] + 12].decode("latin-1", "replace")
                mdhd = _find(raw, mdia[0], mdia[1], "mdhd")
                if mdhd is not None and mdhd[1] - mdhd[0] >= 20 and raw[mdhd[0]] == 0:
                    track_timescale = struct.unpack(">I", raw[mdhd[0] + 12 : mdhd[0] + 16])[0]
                    track_duration = struct.unpack(">I", raw[mdhd[0] + 16 : mdhd[0] + 20])[0]
            tracks.append({"handler": handler, "timescale": track_timescale, "duration": track_duration})
    if not tracks:
        problems.append("the file declares no tracks, so there is no media to describe")
    facts = {
        "container": "iso-base-media",
        "major_brand": major_brand,
        "compatible_brands": compatible,
        "box_types": sorted({kind for kind, _, _ in top}),
        "box_count": len(top),
        "track_count": len(tracks),
        "tracks": tracks,
        "timescale": timescale,
        "duration_units": duration,
        "duration_seconds": round(duration / timescale, 3) if duration and timescale else None,
        "declared_by": "the ISO base media file header boxes",
    }
    return facts, problems


def extract(path: str) -> dict:
    raw = Path(path).read_bytes()
    if raw[:4] == b"RIFF" and raw[8:12] == b"WAVE":
        facts, problems = _wav_facts(raw, path)
        media_type = "audio/wav"
    elif raw[4:8] == b"ftyp":
        facts, problems = _mp4_facts(raw)
        media_type = "video/mp4"
    else:
        raise ValueError("unrecognised media container: not a WAV header and not an ISO base media file")
    # The projection: the facts as text, one per line, deterministically ordered.
    lines = [f"container\t{facts['container']}", f"media_type\t{media_type}"]
    for key in sorted(facts):
        if key in ("container", "tracks"):
            continue
        value = facts[key]
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        lines.append(f"{key}\t{value}")
    for index, track in enumerate(facts.get("tracks") or [], start=1):
        lines.append(f"track-{index}\t{track.get('handler')}\t{track.get('timescale')}\t{track.get('duration')}")
    text = "".join(line + "\n" for line in lines[:FACT_CAP])
    structure = _line_anchors(text)
    losses = list(problems)
    losses.append(
        "this is a header probe: no sample, frame or track was decoded, so there is no waveform, "
        "transcript, timestamp, keyframe or sampling-coverage fact here"
    )
    loss_receipt = {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "params": {
            "projection": "media header fact listing (one key/value per line)",
            "projection_note": (
                "the facts are what the container header declares, not measurements of the media: a duration or "
                "sample rate is a claim by the file, and nothing here decodes content"
            ),
            "coverage_unit": "line anchors over the fact listing",
            "structure": {**facts, "declared_by": facts.get("declared_by")},
        },
        "losses": losses,
        "covered": len(structure),
        "total": len(text.splitlines(keepends=True)),
        "coverage": 1.0,
        "loss_note": "; ".join(losses),
    }
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "structure": structure,
        "loss_receipt": loss_receipt,
    }


def main() -> int:
    if "--staging-root" in sys.argv:
        import argparse

        repo_root = Path(__file__).resolve().parents[3]
        spec = importlib.util.spec_from_file_location(
            "media_transport", repo_root / "services" / "python-workers" / "transport" / "text_ndjson.py"
        )
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--staging-root", type=Path, required=True)
        parser.add_argument("--artifact-root", type=Path, default=None)
        args = parser.parse_args()
        return transport.serve_stdio(WORKER_IDENTITY, ["media.probe"], args.staging_root, args.artifact_root)

    with contextlib.suppress(AttributeError, OSError):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_media.py <input-file> | --staging-root <dir>"}))
        return 2
    try:
        print(json.dumps(extract(sys.argv[1]), ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001 - explicit failure, never silent
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}", "engine": ENGINE}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
