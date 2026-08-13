"""AXW-054B: comparative answer metrics with confidence intervals.

Aggregates answer-verdict and retrieval-practice outcomes into reportable
metrics. Every metric carries sample size and a Wilson 95% confidence
interval; rates are never reported without their n, and empty samples are
explicitly ``unverified`` (never a confident 0%).

Metrics:
- citation coverage: grounded claims / total claims (per answer)
- correctness: human-truth agreement on grounded answers
- refusal rate: non-success verdicts / total verdicts
- learning retention: retrieval-practice pass rate (delayed recall)
- transfer: migration-question pass rate (teach-back)
- latency / resource: optional duration-ms and memory samples
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

Z95 = 1.959963984540054  # normal quantile for 95% CI


def wilson_interval(successes: int, total: int, z: float = Z95) -> dict[str, float]:
    """Wilson score interval for a proportion (robust for small n)."""
    if total <= 0:
        return {"rate": None, "ci_low": None, "ci_high": None, "n": 0}
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return {
        "rate": round(p, 6),
        "ci_low": round(max(0.0, centre - margin), 6),
        "ci_high": round(min(1.0, centre + margin), 6),
        "n": total,
    }


def _rate(status: str, successes: int, total: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = wilson_interval(successes, total)
    result["status"] = status
    if extra:
        result.update(extra)
    return result


def citation_coverage(verdicts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Grounded claims / total claims across successful answers."""
    grounded = sum(len(v.get("answer", {}).get("claims", [])) for v in verdicts if v.get("status") == "success")
    total = sum(len(v.get("answer", {}).get("claims", [])) for v in verdicts if v.get("answer"))
    if total == 0:
        return {"status": "unverified_no_answers", "rate": None, "ci_low": None, "ci_high": None, "n": 0}
    return _rate("measured", grounded, total)


def correctness(truth_results: Sequence[bool]) -> dict[str, Any]:
    """Human-truth agreement on grounded answers (bool per sample)."""
    if not truth_results:
        return {"status": "unverified_no_truth", "rate": None, "ci_low": None, "ci_high": None, "n": 0}
    return _rate("measured", sum(1 for t in truth_results if t), len(truth_results))


def refusal_rate(verdicts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Non-success verdicts (refused/failed/stale/conflict/forbidden/insufficient)."""
    if not verdicts:
        return {"status": "unverified_no_verdicts", "rate": None, "ci_low": None, "ci_high": None, "n": 0}
    refused = sum(1 for v in verdicts if v.get("status") != "success")
    return _rate("measured", refused, len(verdicts))


def learning_retention(pass_results: Sequence[bool]) -> dict[str, Any]:
    """Delayed-recall pass rate from retrieval practice (human truth)."""
    if not pass_results:
        return {"status": "unverified_no_reviews", "rate": None, "ci_low": None, "ci_high": None, "n": 0}
    return _rate("measured", sum(1 for p in pass_results if p), len(pass_results))


def transfer_rate(transfer_results: Sequence[bool]) -> dict[str, Any]:
    """Migration-question pass rate from teach-back evidence."""
    if not transfer_results:
        return {"status": "unverified_no_transfer", "rate": None, "ci_low": None, "ci_high": None, "n": 0}
    return _rate("measured", sum(1 for t in transfer_results if t), len(transfer_results))


def latency_ms(durations_ms: Sequence[float]) -> dict[str, Any]:
    """Latency summary (mean / p50 / p95) with sample size."""
    if not durations_ms:
        return {"status": "unverified_no_samples", "mean_ms": None, "p50_ms": None, "p95_ms": None, "n": 0}
    ordered = sorted(durations_ms)
    n = len(ordered)
    p50 = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    p95 = ordered[min(n - 1, math.ceil(0.95 * n) - 1)]
    return {
        "status": "measured",
        "mean_ms": round(sum(durations_ms) / n, 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "n": n,
    }


def resource_usage(memory_mb_samples: Sequence[float]) -> dict[str, Any]:
    """Peak/mean memory usage with sample size (CI applies to mean)."""
    if not memory_mb_samples:
        return {"status": "unverified_no_samples", "mean_mb": None, "peak_mb": None, "n": 0}
    return {
        "status": "measured",
        "mean_mb": round(sum(memory_mb_samples) / len(memory_mb_samples), 2),
        "peak_mb": round(max(memory_mb_samples), 2),
        "n": len(memory_mb_samples),
    }


def full_report(
    *,
    verdicts: Sequence[dict[str, Any]] | None = None,
    truth_results: Sequence[bool] | None = None,
    retention_results: Sequence[bool] | None = None,
    transfer_results: Sequence[bool] | None = None,
    durations_ms: Sequence[float] | None = None,
    memory_mb: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Aggregate all AXW-054B metrics into one report."""
    return {
        "citation_coverage": citation_coverage(verdicts or []),
        "correctness": correctness(truth_results or []),
        "refusal_rate": refusal_rate(verdicts or []),
        "learning_retention": learning_retention(retention_results or []),
        "transfer_rate": transfer_rate(transfer_results or []),
        "latency": latency_ms(durations_ms or []),
        "resource": resource_usage(memory_mb or []),
    }
