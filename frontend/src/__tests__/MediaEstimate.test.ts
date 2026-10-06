import { describe, expect, it } from "vitest";
import { estimateMediaWork, formatEstimate, windowAudioMs, MEDIA_CEILING_MS } from "../presentation/mediaEstimate";

// Hand-computed from the declared policy (ceiling 300s, overhead 20s, factor 2.0 -> 140s per window),
// kept in step with services/python-workers/media/window_plan.py so the shown estimate and the
// worker's windowing cannot disagree.
describe("media estimate", () => {
  it("uses a 140 second window under the declared policy", () => {
    expect(windowAudioMs()).toBe(140_000);
  });

  it("treats the 83 second sample as one whole job", () => {
    const plan = estimateMediaWork(83_000);
    expect(plan.windowsTotal).toBe(1);
    expect(plan.recommended).toBe("whole");
    expect(plan.wholeEstimatedMs).toBe(186_000);
    expect(plan.windows[0]).toEqual({ index: 0, startMs: 0, endMs: 83_000, audioMs: 83_000, estimatedMs: 186_000 });
  });

  it("tells the user a 12 minute recording needs six windows and cannot finish whole", () => {
    const plan = estimateMediaWork(720_000);
    expect(plan.windowsTotal).toBe(6);
    expect(plan.recommended).toBe("split");
    expect(plan.wholeExceedsCeiling).toBe(true);
    expect(plan.wholeEstimatedMs).toBe(1_460_000);
    expect(plan.windows.map((window) => window.audioMs)).toEqual([140_000, 140_000, 140_000, 140_000, 140_000, 20_000]);
  });

  it("never promises a window longer than the ceiling allows", () => {
    const plan = estimateMediaWork(3_600_000);
    expect(plan.windowsTotal).toBe(26);
    for (const window of plan.windows) expect(window.estimatedMs).toBeLessThanOrEqual(MEDIA_CEILING_MS);
  });

  it("covers the recording exactly once with no gap or overlap", () => {
    const plan = estimateMediaWork(1_000_000);
    let cursor = 0;
    for (const window of plan.windows) {
      expect(window.startMs).toBe(cursor);
      cursor = window.endMs;
    }
    expect(cursor).toBe(1_000_000);
  });

  it("refuses a duration it cannot plan", () => {
    for (const duration of [0, -1, 1.5, Number.NaN]) expect(() => estimateMediaWork(duration)).toThrow();
  });

  it("renders the estimate in minutes and seconds", () => {
    expect(formatEstimate(186_000)).toBe("约 3 分 6 秒");
    expect(formatEstimate(20_000)).toBe("约 20 秒");
  });
});
