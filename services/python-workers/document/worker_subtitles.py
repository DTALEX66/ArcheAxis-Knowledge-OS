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

_TIMECODE = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")


def _to_ms(match: re.Match[str]) -> int:
    hours, minutes, seconds, fraction = (int(g) for g in match.groups())
    fraction = fraction * (10 ** (3 - len(str(fraction))))
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + fraction


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
        time_match = re.search(r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})", timing)
        if not time_match:
            raise ValueError(f"SRT cue without valid timing: {lines[0].strip()}")
        start = _to_ms(_TIMECODE.search(time_match.group(1)) or _TIMECODE.match("0:00:00,000"))
        end = _to_ms(_TIMECODE.search(time_match.group(2)) or _TIMECODE.match("0:00:00,000"))
        cues.append(
            {
                "index": int(lines[0].strip()),
                "offset_ms": start,
                "duration_ms": max(0, end - start),
                "text": "\n".join(lines[2:]),
            }
        )
    return cues


def _parse_vtt(text: str) -> list[dict]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or not lines[0].strip().startswith("WEBVTT"):
        raise ValueError("VTT file must start with a WEBVTT header")
    cues: list[dict] = []
    current_time: tuple[int, int] | None = None
    current_text: list[str] = []
    index = 0

    def flush() -> None:
        nonlocal current_time, current_text, index
        if current_time is not None and current_text:
            index += 1
            offset, duration = current_time
            cues.append(
                {
                    "index": index,
                    "offset_ms": offset,
                    "duration_ms": duration,
                    "text": "\n".join(current_text),
                }
            )
        current_time = None
        current_text = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("NOTE"):
            if stripped == "":
                flush()
            continue
        if "-->" in stripped:
            flush()
            match = re.search(
                r"(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})", stripped
            )
            if not match:
                # optional leading cue index line before timing handled by caller loop
                continue
            start = _to_ms(_TIMECODE.search(match.group(1)) or _TIMECODE.match("0:00:00,000"))
            end = _to_ms(_TIMECODE.search(match.group(2)) or _TIMECODE.match("0:00:00,000"))
            current_time = (start, max(0, end - start))
            continue
        if current_time is not None:
            # strip VTT inline settings tags like <00:00:01.000> or <c.color>
            cleaned = re.sub(r"<[^>]+>", "", line)
            current_text.append(cleaned.rstrip())
    flush()
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
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": projection,
        "structure": structure,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"cues": len(cues)},
            "loss_note": "cue timings preserved as anchors; VTT inline tags stripped; NOTE blocks dropped",
        },
    }


def main() -> int:
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
