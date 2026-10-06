"""Bounded window planning for long audio/video transcription.

The Core refuses any job whose deadline exceeds 300_000 ms, and a single decode of a
long recording cannot finish inside that bound on CPU. Rather than raise the bound, the
work is planned as windows small enough that each one is *estimated* to finish well
inside it, so progress is resumable and a stall costs one window instead of the whole
recording.

This module is deliberately pure: it holds the declared policy and the arithmetic, and
nothing else, so the same numbers can be asserted from the worker tests and mirrored by
the interface that shows the estimate to the user. It never inspects a file and never
calls an engine.

Policy values are measured, not invented:

* ``overhead_ms`` covers process start plus model load before the first segment;
* ``realtime_factor`` is the wall-clock seconds per audio second. The 83 s sample video
  finished 83 s of audio in about 105 s of compute (factor ~1.27), while a 12 minute
  recording did not finish within 301 s (factor > 0.42 over that duration and rising).
  2.0 is the declared ceiling for estimation so a window is never *expected* to overrun.

A window's estimate is ``overhead_ms + window_audio_ms * realtime_factor`` and is
guaranteed to be ``<= ceiling_ms`` by construction; the planner raises instead of
returning a plan that could exceed it.
"""

from __future__ import annotations

CEILING_MS = 300_000
OVERHEAD_MS = 20_000
REALTIME_FACTOR = 2.0


def window_audio_ms(
    *,
    ceiling_ms: int = CEILING_MS,
    overhead_ms: int = OVERHEAD_MS,
    realtime_factor: float = REALTIME_FACTOR,
) -> int:
    """Audio length whose estimated wall clock still fits the ceiling."""
    if ceiling_ms <= 0:
        raise ValueError("ceiling_ms must be positive")
    if overhead_ms < 0:
        raise ValueError("overhead_ms must not be negative")
    if realtime_factor <= 0:
        raise ValueError("realtime_factor must be positive")
    budget = ceiling_ms - overhead_ms
    if budget <= 0:
        raise ValueError("overhead_ms leaves no budget inside ceiling_ms")
    span = int(budget / realtime_factor)
    if span <= 0:
        raise ValueError("policy yields a zero-length window")
    return span


def plan_windows(
    duration_ms: int,
    *,
    ceiling_ms: int = CEILING_MS,
    overhead_ms: int = OVERHEAD_MS,
    realtime_factor: float = REALTIME_FACTOR,
) -> dict:
    """Windows covering ``[0, duration_ms)`` with per-window estimates inside the ceiling.

    ``recommended`` is ``"whole"`` only when the whole recording is itself expected to
    finish inside the ceiling; otherwise the caller must offer the split path, and the
    interface is expected to say why.
    """
    if not isinstance(duration_ms, int) or isinstance(duration_ms, bool):
        raise ValueError("duration_ms must be an integer")
    if duration_ms <= 0:
        raise ValueError("duration_ms must be positive")
    span = window_audio_ms(ceiling_ms=ceiling_ms, overhead_ms=overhead_ms, realtime_factor=realtime_factor)
    windows = []
    start = 0
    while start < duration_ms:
        end = min(start + span, duration_ms)
        audio_ms = end - start
        windows.append({
            "index": len(windows),
            "start_ms": start,
            "end_ms": end,
            "audio_ms": audio_ms,
            "estimated_ms": int(overhead_ms + audio_ms * realtime_factor),
        })
        start = end
    whole_estimated_ms = int(overhead_ms + duration_ms * realtime_factor)
    for window in windows:
        if window["estimated_ms"] > ceiling_ms:
            raise ValueError("window estimate exceeds the ceiling")
    return {
        "windows": windows,
        "windows_total": len(windows),
        "window_audio_ms": span,
        "whole_estimated_ms": whole_estimated_ms,
        "whole_exceeds_ceiling": whole_estimated_ms > ceiling_ms,
        "recommended": "whole" if whole_estimated_ms <= ceiling_ms else "split",
        "policy": {
            "ceiling_ms": ceiling_ms,
            "overhead_ms": overhead_ms,
            "realtime_factor": realtime_factor,
        },
    }
