#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext document worker: subtitles SRT/VTT (F12).

Deterministic subtitle parsing that preserves timing: each cue keeps its
media-time anchor (offset_ms + duration_ms). VTT alignment/position tags and
NOTE blocks are stripped with a documented loss note; SRT numeric indexes are
kept as metadata.

Usage:
    python worker_subtitles.py <input.srt|vtt>
Output: {"engine","engine_version","text","structure","loss_receipt"}
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ENGINE = "python-worker-subtitles"
ENGINE_VERSION = "0.1.0"
# R15/F12: the identity advertised in the sidecar handshake for this route.
WORKER_IDENTITY = "python-worker-subtitles-ndjson"

_TIMECODE = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")
_SRT_CLOCK = r"\d+:\d{2}:\d{2}[,.]\d{1,3}"
_SRT_TIMING = re.compile(rf"({_SRT_CLOCK})\s*-->\s*({_SRT_CLOCK})(?:\s+(.*))?")
_VTT_CLOCK = r"(?:[0-9]+:)?[0-9]{2}:[0-9]{2}[,.][0-9]{1,3}"
_VTT_TIMING = re.compile(rf"({_VTT_CLOCK})[ \t]*-->[ \t]*({_VTT_CLOCK})(?:[ \t]+(.*))?")
_MAX_TIMESTAMP_MS = (1 << 53) - 1


def _to_ms(match: re.Match[str]) -> int:
    hours_text, minutes_text, seconds_text = match.groups()[:3]
    hours_text = hours_text.lstrip("0") or "0"
    if len(hours_text) > 10:
        raise ValueError("SRT timestamp exceeds the supported range")
    hours, minutes, seconds = int(hours_text), int(minutes_text), int(seconds_text)
    if minutes >= 60 or seconds >= 60:
        raise ValueError("SRT timestamp has out-of-range minutes or seconds")
    fraction_text = match.group(4)
    fraction = int(fraction_text) * (10 ** (3 - len(fraction_text)))
    milliseconds = ((hours * 60 + minutes) * 60 + seconds) * 1000 + fraction
    if milliseconds > _MAX_TIMESTAMP_MS:
        raise ValueError("SRT timestamp exceeds the supported range")
    return milliseconds


def _vtt_to_ms(timestamp: str) -> int:
    clock, fraction_text = re.split(r"[,.]", timestamp, maxsplit=1)
    parts = clock.split(":")
    if len(parts) == 3:
        hours_text, minutes_text, seconds_text = parts
        hours_text = hours_text.lstrip("0") or "0"
        if len(hours_text) > 10:
            raise ValueError("VTT timestamp exceeds the supported range")
        hours = int(hours_text)
    else:
        hours = 0
        minutes_text, seconds_text = parts
    minutes, seconds = int(minutes_text), int(seconds_text)
    if minutes >= 60 or seconds >= 60:
        raise ValueError("VTT timestamp has out-of-range minutes or seconds")
    fraction = int(fraction_text) * (10 ** (3 - len(fraction_text)))
    milliseconds = ((hours * 60 + minutes) * 60 + seconds) * 1000 + fraction
    if milliseconds > _MAX_TIMESTAMP_MS:
        raise ValueError("VTT timestamp exceeds the supported range")
    return milliseconds


def _parse_srt(text: str) -> list[dict]:
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    cues: list[dict] = []
    for block in blocks:
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        if not re.fullmatch(r"\d+", lines[0].strip()):
            raise ValueError("SRT block must start with a numeric index")
        timing = lines[1] if len(lines) > 1 else ""
        time_match = _SRT_TIMING.fullmatch(timing.strip())
        if not time_match or (time_match.group(3) and "-->" in time_match.group(3)):
            raise ValueError("SRT cue without valid timing")
        start_match = _TIMECODE.fullmatch(time_match.group(1))
        end_match = _TIMECODE.fullmatch(time_match.group(2))
        if start_match is None or end_match is None:
            raise ValueError("SRT cue without valid timing")
        start, end = _to_ms(start_match), _to_ms(end_match)
        if end < start:
            raise ValueError("SRT cue ends before it starts")
        cues.append(
            {
                "index": int(lines[0].strip()),
                "offset_ms": start,
                "duration_ms": end - start,
                "text": "\n".join(lines[2:]),
            }
        )
    return cues


def _parse_vtt(text: str) -> list[dict]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or not re.fullmatch(r"WEBVTT(?:[ \t].*)?", lines[0]):
        raise ValueError("VTT file must start with a WEBVTT header")
    blocks: list[list[str]] = []
    block: list[str] = []
    for line in lines:
        if line:
            block.append(line)
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)

    # The first block is the header and any legacy header metadata. A timing
    # line there indicates a missing separator, so do not drop it as metadata.
    if not blocks or any("-->" in line for line in blocks[0][1:]):
        raise ValueError("VTT header must be separated from cues by a blank line")
    cues: list[dict] = []
    for block in blocks[1:]:
        first_line = block[0]
        first = first_line.strip()
        is_note = first_line == "NOTE" or first_line.startswith(("NOTE ", "NOTE\t"))
        if is_note and "-->" in first_line:
            raise ValueError("VTT non-cue block contains an ambiguous timing line")
        is_noncue_heading = is_note or re.fullmatch(r"(?:STYLE|REGION)[ \t]*", first_line) is not None
        if is_noncue_heading and (len(block) == 1 or "-->" not in block[1]):
            if any("-->" in line for line in block[1:]):
                raise ValueError("VTT non-cue block contains an ambiguous timing line")
            continue
        # NOTE/STYLE/REGION can also be cue identifiers when the next line is
        # a timing line. Otherwise their blocks are omitted in the loss receipt.
        timing_index = 0 if "-->" in first else 1
        if timing_index >= len(block):
            raise ValueError("VTT cue without valid timing")
        timing = block[timing_index].strip()
        match = _VTT_TIMING.fullmatch(timing)
        if not match or (match.group(3) and "-->" in match.group(3)):
            raise ValueError("VTT cue without valid timing")
        start, end = _vtt_to_ms(match.group(1)), _vtt_to_ms(match.group(2))
        if end < start:
            raise ValueError("VTT cue ends before it starts")
        payload = block[timing_index + 1:]
        if any("-->" in line for line in payload):
            raise ValueError("VTT cues must be separated by a blank line")
        # Inline tags are intentionally omitted; an empty payload still has a
        # meaningful timing anchor and must not disappear from the projection.
        cleaned = [re.sub(r"<[^>]+>", "", line) for line in payload]
        cues.append({"index": len(cues) + 1, "offset_ms": start, "duration_ms": end - start,
                     "text": "\n".join(cleaned)})
    return cues


def extract(path: str) -> dict:
    suffix = Path(path).suffix.lower()
    try:
        text = Path(path).read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"subtitle file is not valid UTF-8: {exc}") from exc
    if suffix == ".srt":
        cues = _parse_srt(text)
    elif suffix == ".vtt":
        cues = _parse_vtt(text)
    else:
        raise ValueError(f"unsupported subtitle extension: {suffix}")
    if not cues:
        raise ValueError("no cues parsed (empty or malformed subtitle file)")

    projection = "".join(f"{cue['text']}\n" for cue in cues)
    structure = []
    offset = 0
    for cue in cues:
        start = offset
        offset += len(cue["text"]) + 1
        structure.append(
            {
                "kind": "cue",
                "path": [f"cue-{cue['index']}"],
                "char_start": start,
                "char_end": start + len(cue["text"]),
                "offset_ms": cue["offset_ms"],
                "duration_ms": cue["duration_ms"],
            }
        )
    if suffix == ".srt":
        loss_note = ("cue timings preserved as anchors; SRT timing suffixes and whitespace-only "
                     "payload lines are not preserved")
    else:
        loss_note = "cue timings preserved as anchors; VTT inline tags stripped; NOTE blocks dropped"
        loss_note += ("; VTT header metadata, cue identifiers, STYLE/REGION blocks and cue timing settings "
                      "such as line, position and align are not preserved; "
                      "VTT character references remain encoded")
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": projection,
        "structure": structure,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"cues": len(cues)},
            "loss_note": loss_note,
        },
    }


def main() -> int:
    # R15/F12: the same wiring as the canvas worker - this worker existed without a route.
    if "--staging-root" in sys.argv:
        import argparse
        import importlib.util

        # The shared transport sits beside this worker's own category directory, in a
        # source checkout (`services/python-workers/transport/`) and in a staged runtime
        # (`workers/transport/`) alike, so both are tried from this file's location. A
        # fixed parents[3] plus a `services/python-workers/` suffix was correct only for
        # the source layout and left a staged worker unable to start.
        _transport_candidates = (
            Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py",
            Path(__file__).resolve().parents[2] / "services" / "python-workers" / "transport" / "text_ndjson.py",
        )
        _transport = next((p for p in _transport_candidates if p.is_file()), _transport_candidates[0])
        spec = importlib.util.spec_from_file_location("subtitles_transport", _transport)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        sidecar = argparse.ArgumentParser(description=__doc__)
        sidecar.add_argument("--staging-root", type=Path, required=True)
        sidecar.add_argument("--artifact-root", type=Path, default=None)
        args = sidecar.parse_args()
        return transport.serve_stdio(
            WORKER_IDENTITY, ["subtitles.structure"], args.staging_root, args.artifact_root
        )

    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_subtitles.py <input.srt|vtt>"}))
        return 2
    try:
        out = extract(sys.argv[1])
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
