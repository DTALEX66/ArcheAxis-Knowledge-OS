"""AXW-096A: performance benchmark scaffold tests.

Verifies:
- latency sampling returns units, counts and percentiles;
- memory peak is measured via tracemalloc;
- corpus metrics report files, bytes and kinds;
- thresholds evaluate honestly and degrade on crossing;
- reports assemble with hardware/corpus/verdicts and are JSON-writable.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from shared.performance_benchmark import (
    BenchmarkError,
    DegradationThreshold,
    build_report,
    corpus_metrics,
    evaluate_thresholds,
    measure_latency_ms,
    measure_memory_peak_mib,
    write_report,
)


def test_measure_latency_ms() -> None:
    result = measure_latency_ms(lambda: time.sleep(0.001), repeats=3, warmup=1)
    assert result["count"] == 3
    assert result["unit"] == "ms"
    assert result["min_ms"] >= 0
    assert result["median_ms"] >= result["min_ms"]
    assert result["max_ms"] >= result["median_ms"]
    assert result["p95_ms"] >= result["min_ms"]


def test_measure_latency_rejects_bad_args() -> None:
    with pytest.raises(BenchmarkError):
        measure_latency_ms(lambda: None, repeats=0)
    with pytest.raises(BenchmarkError):
        measure_latency_ms(lambda: None, warmup=-1)


def test_measure_memory_peak_mib() -> None:
    def allocate() -> None:
        _ = bytes(1024 * 1024)  # ~1 MiB transient

    peak = measure_memory_peak_mib(allocate)
    assert peak >= 0.5  # at least the allocation shows up


def test_corpus_metrics(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("x" * 1000, encoding="utf-8")
    (tmp_path / "b.bin").write_bytes(b"\x00" * 500)

    metrics = corpus_metrics(tmp_path)
    assert metrics["file_count"] == 2
    assert metrics["total_bytes"] == 1500
    assert metrics["by_suffix"][".md"]["count"] == 1
    assert metrics["by_suffix"][".bin"]["bytes"] == 500


def test_corpus_metrics_rejects_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkError, match="corpus directory not found"):
        corpus_metrics(tmp_path / "nope")


def test_thresholds_pass_and_degrade() -> None:
    thresholds = [
        DegradationThreshold(name="import-latency", limit_ms=100),
        DegradationThreshold(name="memory", limit_mib=512),
        DegradationThreshold(name="cold-hot", limit_ratio=10.0),
    ]
    verdicts = evaluate_thresholds(
        latency={"median_ms": 50},
        memory_mib=256,
        cold_hot_ratio=3.0,
        thresholds=thresholds,
    )
    assert all(v["passed"] for v in verdicts)

    verdicts = evaluate_thresholds(
        latency={"median_ms": 500},
        memory_mib=2048,
        cold_hot_ratio=25.0,
        thresholds=thresholds,
    )
    assert [v["name"] for v in verdicts if not v["passed"]] == [
        "import-latency",
        "memory",
        "cold-hot",
    ]


def test_build_report_and_write(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "x.md").write_text("y", encoding="utf-8")

    report = build_report(
        corpus_dir=corpus,
        measurements={"latency": {"count": 1, "unit": "ms", "median_ms": 10}},
        thresholds=[DegradationThreshold(name="t", limit_ms=100)],
    )
    assert report["schema_version"] == "v1"
    assert report["hardware"]["cpu_count"] >= 1
    assert report["corpus"]["file_count"] == 1
    assert report["overall"] == "passed"
    assert report["verdicts"][0]["passed"] is True

    report_path = write_report(report, tmp_path / "out" / "benchmark.json")
    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert loaded["overall"] == "passed"
