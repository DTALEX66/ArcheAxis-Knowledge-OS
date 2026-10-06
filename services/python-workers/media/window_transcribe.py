"""Windowed transcription primitives: duration parsing, window extraction, cue offsetting, merging.

The Core refuses a job deadline above 300_000 ms, so a long recording cannot be transcribed in one
pass on CPU. The plan is to run bounded windows instead — but only the *arithmetic and identity*
live here, so they can be asserted without a model, without ffmpeg and without a Core.

Three rules this module keeps, because each of them is a way the honest answer could rot:

* partial is partial: a window that did not run is reported missing, never silently skipped;
* offsets are global: a cue transcribed in a later window is returned with its position in the
  original recording, so a citation cannot point at the wrong place;
* no window borrows another's text: merging only concatenates what each window actually produced.
"""

from __future__ import annotations

import re

_DURATION = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2})\.(\d{1,3})")


def parse_ffmpeg_duration_ms(stderr_text: str) -> int:
    """Duration in milliseconds from ffmpeg's banner, or a named failure.

    ffmpeg prints `Duration: 00:12:03.42` on stderr when probing an input. Nothing is inferred when
    that line is absent: a default duration would make every downstream offset a guess.
    """
    match = _DURATION.search(stderr_text or "")
    if not match:
        raise ValueError("ffmpeg output carries no Duration line")
    hours, minutes, seconds, fraction = match.groups()
    millis = int(fraction.ljust(3, "0"))
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + millis


def window_command(ffmpeg: str, source: str, start_ms: int, end_ms: int, target: str) -> list[str]:
    """The ffmpeg argv that writes one window as 16 kHz mono wav.

    `-ss`/`-t` before `-i` keep the seek cheap; the sample rate is pinned because the ASR front end
    expects it and a resampling surprise would change the text, not just the timing.
    """
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError("window must be a positive range")
    seconds = (end_ms - start_ms) / 1000
    return [ffmpeg, "-hide_banner", "-nostdin", "-ss", f"{start_ms / 1000:.3f}", "-t", f"{seconds:.3f}",
            "-i", source, "-ac", "1", "-ar", "16000", "-f", "wav", "-y", target]


def offset_cues(cues: list[dict], offset_ms: int) -> list[dict]:
    """Shift a window's cues onto the recording's timeline."""
    if offset_ms < 0:
        raise ValueError("offset_ms must not be negative")
    shifted = []
    for index, cue in enumerate(cues):
        start = int(cue["start_ms"]) + offset_ms
        end = int(cue["end_ms"]) + offset_ms
        if end <= start:
            raise ValueError(f"cue {index} has a non-positive duration after offsetting")
        shifted.append({**cue, "start_ms": start, "end_ms": end})
    return shifted


def merge_windows(windows: list[dict], expected_total: int) -> dict:
    """One transcript from the windows that actually ran, with the gaps stated.

    Each input is `{"index", "start_ms", "end_ms", "status", "cues", "text"}`. `status` is whatever
    the window produced; anything that is not `"succeeded"` is counted as missing and never
    contributes text. `expected_total` is how many windows the plan called for, so a short result
    cannot be presented as the whole recording.
    """
    if expected_total <= 0:
        raise ValueError("expected_total must be positive")
    ordered = sorted(windows, key=lambda window: int(window["index"]))
    cues: list[dict] = []
    parts: list[str] = []
    missing: list[int] = []
    seen: set[int] = set()
    for window in ordered:
        index = int(window["index"])
        if index in seen:
            raise ValueError(f"window {index} reported twice")
        seen.add(index)
        if window.get("status") != "succeeded":
            missing.append(index)
            continue
        cues.extend(offset_cues(list(window.get("cues") or []), int(window["start_ms"])))
        text = str(window.get("text") or "").strip()
        if text:
            parts.append(text)
    status = "complete" if not missing and len(seen) == expected_total else "partial"
    return {
        "status": status,
        "windows_expected": expected_total,
        "windows_present": len(seen),
        "windows_missing": missing,
        "cues": cues,
        "text": "\n".join(parts),
        "note": ("all planned windows produced text" if status == "complete"
                 else "partial: windows " + ", ".join(str(i) for i in missing) + " produced no text" if missing
                 else "partial: fewer windows reported than planned"),
    }
