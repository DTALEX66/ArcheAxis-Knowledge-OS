/**
 * Performance monitoring tests
 */
import { describe, expect, it, beforeEach } from "vitest";
import {
  PerformanceMonitor,
  visibilityAdapter,
  meetsBaseline,
  qualityProfiles,
  type PerformanceMetric,
} from "../runtime/performance";

describe("Performance Monitoring", () => {
  let monitor: PerformanceMonitor;

  beforeEach(() => {
    monitor = new PerformanceMonitor();
  });

  it("records performance metrics", () => {
    const metric: PerformanceMetric = {
      component: "TestComponent",
      operation: "render",
      duration_ms: 15,
      timestamp: Date.now(),
    };

    monitor.record(metric);
    expect(monitor.getComponentMetrics("TestComponent")).toHaveLength(1);
  });

  it("calculates average render time", () => {
    monitor.record({
      component: "TestComponent",
      operation: "render",
      duration_ms: 10,
      timestamp: Date.now(),
    });
    monitor.record({
      component: "TestComponent",
      operation: "render",
      duration_ms: 20,
      timestamp: Date.now(),
    });

    expect(monitor.getAverageRenderTime("TestComponent")).toBe(15);
  });

  it("limits metrics storage", () => {
    // Record more than max metrics
    for (let i = 0; i < 1100; i++) {
      monitor.record({
        component: "Test",
        operation: "render",
        duration_ms: 10,
        timestamp: Date.now(),
      });
    }

    expect(monitor.getAllMetrics().length).toBeLessThanOrEqual(1000);
  });

  it("exports metrics as JSON", () => {
    monitor.record({
      component: "Test",
      operation: "render",
      duration_ms: 10,
      timestamp: Date.now(),
    });

    const exported = monitor.export();
    expect(JSON.parse(exported)).toHaveLength(1);
  });

  it("clears all metrics", () => {
    monitor.record({
      component: "Test",
      operation: "render",
      duration_ms: 10,
      timestamp: Date.now(),
    });
    monitor.clear();

    expect(monitor.getAllMetrics()).toHaveLength(0);
  });
});

describe("Visibility Lifecycle", () => {
  it("tracks visibility state", () => {
    expect(visibilityAdapter.getState()).toBe("visible");
  });

  it("determines if component should render", () => {
    expect(visibilityAdapter.shouldRender()).toBe(true);
  });

  it("allows subscribing to visibility changes", () => {
    let callCount = 0;
    const unsubscribe = visibilityAdapter.subscribe(() => {
      callCount++;
    });

    expect(typeof unsubscribe).toBe("function");
    unsubscribe();
    expect(callCount).toBe(0); // No visibility change during test
  });
});

describe("Performance Baselines", () => {
  it("checks if metric meets baseline", () => {
    const goodMetric: PerformanceMetric = {
      component: "Fast",
      operation: "render",
      duration_ms: 15,
      timestamp: Date.now(),
    };

    expect(meetsBaseline(goodMetric, "good")).toBe(true);
  });

  it("detects slow metrics", () => {
    const slowMetric: PerformanceMetric = {
      component: "Slow",
      operation: "render",
      duration_ms: 50,
      timestamp: Date.now(),
    };

    expect(meetsBaseline(slowMetric, "good")).toBe(false);
    expect(meetsBaseline(slowMetric, "acceptable")).toBe(false);
  });
});

describe("Quality Profiles", () => {
  it("defines quality levels", () => {
    expect(qualityProfiles.high.maxFPS).toBe(60);
    expect(qualityProfiles.medium.maxFPS).toBe(30);
    expect(qualityProfiles.low.maxFPS).toBe(15);
  });

  it("configures transitions per quality", () => {
    expect(qualityProfiles.high.enableTransitions).toBe(true);
    expect(qualityProfiles.low.enableTransitions).toBe(false);
  });
});
