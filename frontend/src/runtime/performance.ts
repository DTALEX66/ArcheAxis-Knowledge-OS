import { useLayoutEffect, useSyncExternalStore } from "react";

/**
 * Performance monitoring utilities
 * Tracks component render times, lifecycle events, and visibility state
 */

export type PerformanceMetric = {
  component: string;
  operation: "mount" | "update" | "unmount" | "render";
  duration_ms: number;
  timestamp: number;
};

export type VisibilityState = "visible" | "hidden" | "background";

/**
 * Performance monitor for React components
 */
export class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private readonly maxMetrics = 1000;

  /**
   * Record a performance metric
   */
  record(metric: PerformanceMetric): void {
    this.metrics.push(metric);
    if (this.metrics.length > this.maxMetrics) {
      this.metrics.shift();
    }
  }

  /**
   * Get metrics for a specific component
   */
  getComponentMetrics(component: string): PerformanceMetric[] {
    return this.metrics.filter((m) => m.component === component);
  }

  /**
   * Get average render time for a component
   */
  getAverageRenderTime(component: string): number {
    const renders = this.metrics.filter(
      (m) => m.component === component && m.operation === "render"
    );
    if (renders.length === 0) return 0;
    const total = renders.reduce((sum, m) => sum + m.duration_ms, 0);
    return total / renders.length;
  }

  /**
   * Get all metrics
   */
  getAllMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics = [];
  }

  /**
   * Export metrics as JSON
   */
  export(): string {
    return JSON.stringify(this.metrics, null, 2);
  }
}

/**
 * Global performance monitor instance
 */
export const performanceMonitor = new PerformanceMonitor();

/**
 * React hook for measuring component render time
 */
export function usePerformanceMonitor(componentName: string) {
  const startTime = performance.now();
  // Elapsed render-to-commit time includes scheduling; this is not CPU time
  // or React Profiler actualDuration. Layout effects also run in production.
  useLayoutEffect(() => {
    const endTime = performance.now();
    performanceMonitor.record({
      component: componentName,
      operation: "render",
      duration_ms: endTime - startTime,
      timestamp: Date.now(),
    });
  });
}

/**
 * Visibility lifecycle adapter
 * Pauses rendering and updates when component is not visible
 */
export class VisibilityLifecycleAdapter {
  private visibilityState: VisibilityState = "visible";
  private observers: Set<(state: VisibilityState) => void> = new Set();

  private readonly onVisibilityChange = () => this.updateVisibility();

  private updateVisibility(): void {
    const newState: VisibilityState = document.hidden ? "hidden" : "visible";
    if (newState !== this.visibilityState) {
      this.visibilityState = newState;
      this.notifyObservers();
    }
  }

  private notifyObservers(): void {
    this.observers.forEach((callback) => callback(this.visibilityState));
  }

  /**
   * Subscribe to visibility changes
   */
  subscribe(callback: (state: VisibilityState) => void): () => void {
    if (!this.observers.size && typeof document !== "undefined") {
      this.visibilityState = this.getState();
      document.addEventListener("visibilitychange", this.onVisibilityChange);
    }
    this.observers.add(callback);
    return () => {
      this.observers.delete(callback);
      if (!this.observers.size && typeof document !== "undefined") document.removeEventListener("visibilitychange", this.onVisibilityChange);
    };
  }

  /**
   * Get current visibility state
   */
  getState(): VisibilityState {
    return typeof document !== "undefined" && document.hidden ? "hidden" : "visible";
  }

  /**
   * Check if component should render
   */
  shouldRender(): boolean {
    return this.getState() === "visible";
  }
}

/**
 * Global visibility adapter instance
 */
export const visibilityAdapter = new VisibilityLifecycleAdapter();
const subscribeVisibility = (notify: () => void) => visibilityAdapter.subscribe(notify);
const readVisibility = () => visibilityAdapter.getState();
export function useVisibilityState(): VisibilityState {
  return useSyncExternalStore(subscribeVisibility, readVisibility, () => "visible");
}

/**
 * Quality profiles for different performance scenarios
 */
export const qualityProfiles = {
  high: {
    maxFPS: 60,
    animationDuration: 300,
    enableShadows: true,
    enableTransitions: true,
  },
  medium: {
    maxFPS: 30,
    animationDuration: 200,
    enableShadows: false,
    enableTransitions: true,
  },
  low: {
    maxFPS: 15,
    animationDuration: 100,
    enableShadows: false,
    enableTransitions: false,
  },
} as const;

export type QualityProfile = keyof typeof qualityProfiles;

/**
 * Performance baseline thresholds
 */
export const performanceBaselines = {
  mount: {
    good: 50, // ms
    acceptable: 100,
  },
  render: {
    good: 16, // 60fps
    acceptable: 33, // 30fps
  },
  update: {
    good: 16,
    acceptable: 33,
  },
  unmount: {
    good: 10,
    acceptable: 20,
  },
} as const;

/**
 * Check if a metric meets performance baseline
 */
export function meetsBaseline(
  metric: PerformanceMetric,
  threshold: "good" | "acceptable" = "good"
): boolean {
  const baseline = performanceBaselines[metric.operation];
  return metric.duration_ms <= baseline[threshold];
}
