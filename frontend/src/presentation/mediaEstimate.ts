/**
 * Bounded window planning, mirroring services/python-workers/media/window_plan.py.
 *
 * The Core refuses a job deadline above 300_000 ms, and one decode of a long recording
 * cannot finish inside it on CPU. The interface therefore has to tell the user what the
 * current recording is expected to cost and offer the split path explicitly, instead of
 * starting a whole-file job that will be killed at the ceiling.
 *
 * Keep the constants and the arithmetic identical to the worker module: the user-facing
 * estimate and the worker's actual windowing must not disagree. The numbers are the same
 * measured policy (overhead 20 s, factor 2.0 wall-clock seconds per audio second).
 */
export const MEDIA_CEILING_MS = 300_000;
export const MEDIA_OVERHEAD_MS = 20_000;
export const MEDIA_REALTIME_FACTOR = 2.0;

export interface MediaWindow {
  index: number;
  startMs: number;
  endMs: number;
  audioMs: number;
  estimatedMs: number;
}

export interface MediaEstimate {
  windows: MediaWindow[];
  windowsTotal: number;
  windowAudioMs: number;
  wholeEstimatedMs: number;
  wholeExceedsCeiling: boolean;
  recommended: "whole" | "split";
}

export function windowAudioMs(
  ceilingMs = MEDIA_CEILING_MS,
  overheadMs = MEDIA_OVERHEAD_MS,
  realtimeFactor = MEDIA_REALTIME_FACTOR,
): number {
  if (!Number.isFinite(ceilingMs) || ceilingMs <= 0) throw new Error("ceilingMs must be positive");
  if (!Number.isFinite(overheadMs) || overheadMs < 0) throw new Error("overheadMs must not be negative");
  if (!Number.isFinite(realtimeFactor) || realtimeFactor <= 0) throw new Error("realtimeFactor must be positive");
  const budget = ceilingMs - overheadMs;
  if (budget <= 0) throw new Error("overheadMs leaves no budget inside ceilingMs");
  const span = Math.floor(budget / realtimeFactor);
  if (span <= 0) throw new Error("policy yields a zero-length window");
  return span;
}

export function estimateMediaWork(
  durationMs: number,
  ceilingMs = MEDIA_CEILING_MS,
  overheadMs = MEDIA_OVERHEAD_MS,
  realtimeFactor = MEDIA_REALTIME_FACTOR,
): MediaEstimate {
  if (!Number.isInteger(durationMs) || durationMs <= 0) throw new Error("durationMs must be a positive integer");
  const span = windowAudioMs(ceilingMs, overheadMs, realtimeFactor);
  const windows: MediaWindow[] = [];
  for (let start = 0; start < durationMs;) {
    const end = Math.min(start + span, durationMs);
    windows.push({
      index: windows.length,
      startMs: start,
      endMs: end,
      audioMs: end - start,
      estimatedMs: Math.floor(overheadMs + (end - start) * realtimeFactor),
    });
    start = end;
  }
  const wholeEstimatedMs = Math.floor(overheadMs + durationMs * realtimeFactor);
  for (const window of windows) {
    if (window.estimatedMs > ceilingMs) throw new Error("window estimate exceeds the ceiling");
  }
  return {
    windows,
    windowsTotal: windows.length,
    windowAudioMs: span,
    wholeEstimatedMs,
    wholeExceedsCeiling: wholeEstimatedMs > ceilingMs,
    recommended: wholeEstimatedMs <= ceilingMs ? "whole" : "split",
  };
}

export function formatEstimate(milliseconds: number): string {
  const totalSeconds = Math.round(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0 ? `约 ${minutes} 分 ${seconds} 秒` : `约 ${seconds} 秒`;
}
