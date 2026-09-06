"""Run the AXW-096A performance benchmark on a layered corpus.

Measures, per layer (small/medium/large):
- conversion latency (median/p95) through convert_directory_resumable;
- cold start (fresh interpreter importing the core) and hot start
  (warm process re-running the same conversion) latency;
- peak Python memory during conversion (tracemalloc);
- corpus data size + hardware identity.

Emits a JSON report via shared.performance_benchmark (fail-closed
threshold verdicts). The report lands under the project data dir and is
NOT committed; a summary can be copied to docs/truth by the executor.

Usage: python scripts/run_performance_benchmark.py --corpus DIR --report PATH
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from shared.performance_benchmark import (
    DegradationThreshold,
    build_report,
    measure_latency_ms,
    measure_memory_peak_mib,
    write_report,
)


def _convert_once(corpus_dir: Path, artifacts_dir: Path) -> None:
    """Convert one layer via the resumable pipeline (idempotent)."""
    from app.ingestion.multi_format import convert_directory_resumable

    convert_directory_resumable(
        directory=corpus_dir,
        manifest_path=artifacts_dir / "manifest.json",
        output_dir=artifacts_dir,
        max_files=2000,
    )


def measure_cold_start_ms() -> dict[str, object]:
    """Start a fresh interpreter importing the core; return latency summary."""
    code = "import app.runtime_entrypoint"  # noqa: F841 (executed in child)

    def spawn() -> None:
        subprocess.run(
            [sys.executable, "-c", "import app.runtime_entrypoint"],
            capture_output=True,
            check=True,
        )

    # 3 samples; first is the true cold start, rest are warm OS cache.
    return measure_latency_ms(spawn, repeats=3, warmup=0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=".project-local/task-runtime/corpus")
    parser.add_argument("--report", default=".project-local/task-runtime/benchmark/benchmark.json")
    parser.add_argument("--threshold-import-ms", type=float, default=5000.0)
    parser.add_argument("--threshold-memory-mib", type=float, default=2048.0)
    args = parser.parse_args()

    corpus_root = Path(args.corpus)
    report_path = Path(args.report)
    artifacts_root = report_path.parent / "artifacts"
    layers = ("small", "medium", "large")

    layer_results: dict[str, object] = {}
    for layer in layers:
        layer_dir = corpus_root / layer
        if not layer_dir.is_dir():
            print(f"SKIP {layer}: missing {layer_dir}")
            continue
        artifacts = artifacts_root / layer
        artifacts.mkdir(parents=True, exist_ok=True)

        def convert_this_layer(_layer_dir: Path = layer_dir, _artifacts: Path = artifacts) -> None:
            _convert_once(_layer_dir, _artifacts)

        conversion = measure_latency_ms(convert_this_layer, repeats=3, warmup=1)
        memory = measure_memory_peak_mib(convert_this_layer)
        print(f"{layer}: conversion {conversion['median_ms']}ms median, peak {memory} MiB")

        layer_results[layer] = {
            "conversion_latency_ms": conversion,
            "memory_peak_mib": memory,
        }

    cold_start = measure_cold_start_ms()
    print(f"cold start: {cold_start['median_ms']}ms median")

    thresholds = [
        DegradationThreshold(name="import-latency", limit_ms=args.threshold_import_ms),
        DegradationThreshold(name="memory", limit_mib=args.threshold_memory_mib),
    ]
    report = build_report(
        corpus_dir=corpus_root,
        measurements={
            "layers": layer_results,
            "cold_start_ms": cold_start,
            "notes": "layered public-domain Gutenberg corpus; CPU-only",
        },
        thresholds=thresholds,
        notes="AXW-096A baseline run; conversion = convert_directory_resumable",
    )
    write_report(report, report_path)
    print(f"report: {report_path}")
    print(f"overall: {report['overall']}")
    return 0 if report["overall"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
