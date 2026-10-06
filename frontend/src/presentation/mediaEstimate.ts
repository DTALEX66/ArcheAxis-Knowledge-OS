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

export interface SplitProgress {
  status: string;
  expected: number;
  present: number;
  missing: number[];
  resumed: number[];
}

/**
 * What a split run actually finished, read from the job's own loss receipt.
 *
 * The receipt is the only place this may come from: the number of windows a recording needs is
 * decided by the worker from the file's real duration, so a count computed here would be a second,
 * disagreeing opinion. `null` means the receipt carried no split record at all — not that nothing
 * ran.
 */
export function splitProgressOf(loss: Record<string, unknown>): SplitProgress | null {
  return splitProgressFromWorkerOutput((loss as { params?: { worker_output?: unknown } }).params?.worker_output);
}

/** The same reading, from an already-extracted worker output (the transcription proof's pipeline). */
export function splitProgressFromWorkerOutput(output: unknown): SplitProgress | null {
  const windows = (output as { windows?: unknown } | null | undefined)?.windows;
  if (!windows || typeof windows !== "object" || Array.isArray(windows)) return null;
  const value = windows as Record<string, unknown>;
  const count = (input: unknown): number[] =>
    Array.isArray(input) && input.every(item => Number.isSafeInteger(item)) ? (input as number[]) : [];
  if (!Number.isSafeInteger(value.windows_expected) || !Number.isSafeInteger(value.windows_present)) return null;
  return {
    status: String(value.status ?? "unknown"),
    expected: Number(value.windows_expected),
    present: Number(value.windows_present),
    missing: count(value.windows_missing),
    resumed: count(value.windows_resumed),
  };
}

export function describeSplit(progress: SplitProgress): string {
  const { status, expected, present, missing, resumed } = progress;
  const reused = resumed.length ? `，其中本次复用了 ${resumed.length} 段` : "";
  if (status === "complete") return `分段全部完成（${present} / ${expected} 段${reused}）。`;
  return `分段尚未全部完成（${present} / ${expected} 段${resumed.length ? `，复用了 ${resumed.length} 段` : ""}；未完成段 ${missing.length ? missing.join("、") : "未提供"}）；正文只包含已完成分段，未完成部分没有被省略记录。`;
}

export function formatEstimate(milliseconds: number): string {
  const totalSeconds = Math.round(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0 ? `约 ${minutes} 分 ${seconds} 秒` : `约 ${seconds} 秒`;
}
