"""AXW-096A: large-corpus / CPU-only performance benchmark scaffold.

Defines the measurable dimensions required by the baseline (data size,
hardware, cold/hot start, latency, memory, degradation thresholds) and
provides honest measurement helpers. The real large corpus is supplied at
qualification time; this module keeps the *definition* and the
measurement harness stable and testable at small scale.

All measurements are reported with units and sample size; nothing is
extrapolated. Thresholds are explicit and fail-closed: a benchmark run
that crosses a degradation threshold reports ``degraded`` rather than
pretending the result is fine.
"""

from __future__ import annotations

import json
import platform
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BENCHMARK_SCHEMA_VERSION = "v1"


class BenchmarkError(ValueError):
    """Raised when the harness itself is misused (no fabricated metrics)."""


@dataclass
class DegradationThreshold:
    """One explicit pass/fail threshold with a human-readable name."""

    name: str
    limit_ms: float | None = None  # latency upper bound (ms)
    limit_mib: float | None = None  # memory upper bound (MiB)
    limit_ratio: float | None = None  # cold/hot ratio upper bound


@dataclass
class Sample:
    """One measured observation with its unit."""

    value: float
    unit: str
    label: str = ""


def _summarize(values: list[float], unit: str) -> dict[str, Any]:
    if not values:
        return {"count": 0, "unit": unit}
    return {
        "count": len(values),
        "unit": unit,
        "min_ms": round(min(values), 3),
        "median_ms": round(statistics.median(values), 3),
        "mean_ms": round(statistics.mean(values), 3),
        "max_ms": round(max(values), 3),
        "p95_ms": round(sorted(values)[max(0, int(len(values) * 0.95) - 1)], 3),
    }


def measure_latency_ms(fn: Callable[[], Any], *, repeats: int = 5, warmup: int = 1) -> dict[str, Any]:
    """Measure ``fn`` latency; warms up first, then samples ``repeats``."""
    if repeats < 1:
        raise BenchmarkError("repeats must be >= 1")
    if warmup < 0:
        raise BenchmarkError("warmup must be >= 0")
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return _summarize(samples, "ms")


def measure_memory_peak_mib(fn: Callable[[], Any]) -> float:
    """Peak Python memory during ``fn`` via tracemalloc (MiB)."""
    import tracemalloc

    tracemalloc.start()
    try:
        fn()
    finally:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return round(peak / (1024 * 1024), 3)


def hardware_identity() -> dict[str, Any]:
    """Non-secret hardware description for the report header."""
    import os

    cpu_count = os.cpu_count() or 0
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "python": platform.python_version(),
        "cpu_count": cpu_count,
        "machine": platform.machine(),
    }


def corpus_metrics(corpus_dir: str | Path) -> dict[str, Any]:
    """Data-size metrics for a corpus directory (files, bytes, kinds)."""
    root = Path(corpus_dir)
    if not root.is_dir():
        raise BenchmarkError(f"corpus directory not found: {root}")
    files = [p for p in root.rglob("*") if p.is_file()]
    sizes: dict[str, int] = {}
    count_by_suffix: dict[str, int] = {}
    for file_path in files:
        suffix = file_path.suffix.lower() or "(none)"
        count_by_suffix[suffix] = count_by_suffix.get(suffix, 0) + 1
        sizes[suffix] = sizes.get(suffix, 0) + file_path.stat().st_size
    return {
        "file_count": len(files),
        "total_bytes": sum(sizes.values()),
        "total_mib": round(sum(sizes.values()) / (1024 * 1024), 3),
        "by_suffix": {
            suffix: {"count": count_by_suffix[suffix], "bytes": sizes[suffix]}
            for suffix in sorted(count_by_suffix)
        },
    }


def evaluate_thresholds(
    *,
    latency: dict[str, Any] | None = None,
    memory_mib: float | None = None,
    cold_hot_ratio: float | None = None,
    thresholds: list[DegradationThreshold] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate explicit thresholds; every crossed threshold is reported."""
    verdicts: list[dict[str, Any]] = []
    for threshold in thresholds or []:
        exceeded: list[str] = []
        if threshold.limit_ms is not None and latency:
            observed = latency.get("median_ms")
            if observed is not None and observed > threshold.limit_ms:
                exceeded.append(f"median {observed}ms > {threshold.limit_ms}ms")
        if threshold.limit_mib is not None and memory_mib is not None and memory_mib > threshold.limit_mib:
            exceeded.append(f"memory {memory_mib}MiB > {threshold.limit_mib}MiB")
        if threshold.limit_ratio is not None and cold_hot_ratio is not None and cold_hot_ratio > threshold.limit_ratio:
            exceeded.append(f"cold/hot ratio {cold_hot_ratio:.2f} > {threshold.limit_ratio}")
        verdicts.append(
            {
                "name": threshold.name,
                "passed": not exceeded,
                "failures": exceeded,
            }
        )
    return verdicts


def build_report(
    *,
    corpus_dir: str | Path,
    measurements: dict[str, Any],
    thresholds: list[DegradationThreshold] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Assemble the full benchmark report (JSON-serializable)."""
    thresholds = thresholds or []
    verdicts = evaluate_thresholds(
        latency=measurements.get("latency"),
        memory_mib=measurements.get("memory_peak_mib"),
        cold_hot_ratio=measurements.get("cold_hot_ratio"),
        thresholds=thresholds,
    )
    report: dict[str, Any] = {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hardware": hardware_identity(),
        "corpus": corpus_metrics(corpus_dir),
        "measurements": measurements,
        "thresholds": [{"name": t.name, "limit_ms": t.limit_ms, "limit_mib": t.limit_mib, "limit_ratio": t.limit_ratio} for t in thresholds],
        "verdicts": verdicts,
        "overall": "passed" if all(v["passed"] for v in verdicts) else "degraded",
        "notes": notes,
    }
    return report


def write_report(report: dict[str, Any], destination: str | Path) -> Path:
    """Write the report as JSON (the canonical machine-readable form)."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination
