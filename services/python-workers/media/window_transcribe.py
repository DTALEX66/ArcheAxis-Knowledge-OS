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

import json
import os
import re
from pathlib import Path

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


def run_windows(plan: dict, per_window, staging: Path | None = None) -> dict:
    """Run a window plan, resuming windows that already succeeded.

    The Core caps a job at 300 s, so a long recording is expected to take several invocations.
    That makes two behaviours load-bearing:

    * a window that already succeeded on a previous invocation is reused, so work is not repeated
      and the total cost falls as the run advances;
    * a window that failed is *not* cached as done — it is attempted again, because caching a
      failure would make a transient engine problem permanent.

    A failure inside ``per_window`` is recorded as that window failing and the remaining windows are
    still attempted: one bad window must not discard the rest of the recording. Results are written
    per window so a run that is killed mid-way keeps everything already finished.
    """
    windows = list(plan.get("windows") or [])
    if not windows:
        raise ValueError("plan carries no windows")
    expected = int(plan.get("windows_total") or len(windows))
    if expected != len(windows):
        raise ValueError("plan windows_total disagrees with the window list")
    if staging is not None:
        staging = Path(staging)
        staging.mkdir(parents=True, exist_ok=True)

    collected: list[dict] = []
    resumed: list[int] = []
    for window in windows:
        index = int(window["index"])
        cached = staging / f"window-{index:04d}.json" if staging is not None else None
        record = None
        if cached is not None and cached.is_file():
            try:
                stored = json.loads(cached.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                stored = None
            if isinstance(stored, dict) and stored.get("status") == "succeeded":
                record = stored
                resumed.append(index)
        if record is None:
            try:
                produced = per_window(window)
                # Keep everything the window produced, not just the three fields the merge needs: a
                # resumed window has to look exactly like a freshly produced one, and the caller's
                # envelope is built from the first successful window's receipt.
                record = {**produced,
                          "status": str(produced.get("status") or "failed"),
                          "cues": list(produced.get("cues") or []),
                          "text": str(produced.get("text") or "")}
            except Exception as exc:  # one window must not discard the recording
                record = {"status": "failed", "cues": [], "text": "",
                          "error": f"{type(exc).__name__}: {exc}"}
            if cached is not None and record["status"] == "succeeded":
                temporary = cached.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
                os.replace(temporary, cached)
        collected.append({"index": index, "start_ms": int(window["start_ms"]), "end_ms": int(window["end_ms"]),
                          **record})

    merged = merge_windows(collected, expected_total=expected)
    merged["windows_resumed"] = resumed
    merged["staging"] = str(staging) if staging is not None else None
    # The full per-window records travel with the merge: the caller's receipt is built from a window's
    # own canonical output, and a resumed run has to expose exactly what a fresh run would.
    merged["windows_detail"] = collected
    return merged


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
