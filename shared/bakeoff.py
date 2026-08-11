"""H2 Recognition provider bake-off framework.

Compares OCR/ASR engines against a fixed fixture corpus.
Measures: CER (with ground truth), resource usage (time), failure rate.

Does NOT report engine confidence as accuracy.
Only computes CER when ground-truth text is available.
"""

from __future__ import annotations

import csv
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "BakeoffResult",
    "EngineUnderTest",
    "run_bakeoff",
    "load_fixtures",
    "report_csv",
    "report_json",
]


@dataclass
class EngineUnderTest:
    name: str
    fn: Callable[[Path], str]  # (file_path) → text
    available: bool = True
    version: str = "unknown"
    notes: str = ""


@dataclass
class BakeoffResult:
    engine: str
    fixture: str
    file_size: int
    cer: float | None = None
    wer: float | None = None
    char_count: int = 0
    duration_ms: float = 0
    success: bool = False
    error: str | None = None


def load_fixtures(fixture_dir: Path, pattern: str = "*.*") -> list[tuple[Path, str | None]]:
    """Load fixture files with optional ground-truth text.

    Each fixture file `sample.png` can have an optional `sample.txt`
    containing ground-truth text for CER/WER computation.
    Returns list of (binary_path, ground_truth_text_or_none).
    """
    fixtures: list[tuple[Path, str | None]] = []
    for f in sorted(fixture_dir.glob(pattern)):
        if f.is_file() and f.suffix.lower() != ".txt":
            gt = fixture_dir / (f.stem + ".txt")
            truth = gt.read_text(encoding="utf-8").strip() if gt.is_file() else None
            fixtures.append((f, truth))
    return fixtures


def run_bakeoff(
    engines: list[EngineUnderTest],
    fixtures: list[tuple[Path, str | None]],
) -> list[BakeoffResult]:
    """Run all engines against all fixtures. CER only when truth available."""
    from shared.text_quality import cer, wer

    results: list[BakeoffResult] = []
    for e in engines:
        if not e.available:
            continue
        for fp, truth in fixtures:
            r = BakeoffResult(
                engine=e.name,
                fixture=fp.name,
                file_size=fp.stat().st_size,
            )
            try:
                t0 = time.perf_counter()
                text = e.fn(fp)
                r.duration_ms = (time.perf_counter() - t0) * 1000
                r.char_count = len(text)
                r.success = True
                if truth:
                    r.cer = round(cer(truth, text), 4)
                    r.wer = round(wer(truth, text), 4)
            except Exception as exc:
                r.error = str(exc)[:200]
            results.append(r)
    return results


def report_csv(results: list[BakeoffResult], path: Path) -> Path:
    """Write bake-off results as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "engine", "fixture", "file_size", "cer", "wer",
                "char_count", "duration_ms", "success", "error",
            ],
        )
        w.writeheader()
        for r in results:
            w.writerow({
                "engine": r.engine,
                "fixture": r.fixture,
                "file_size": r.file_size,
                "cer": r.cer or "",
                "wer": r.wer or "",
                "char_count": r.char_count,
                "duration_ms": round(r.duration_ms, 1),
                "success": r.success,
                "error": r.error or "",
            })
    return path


def report_json(results: list[BakeoffResult], path: Path) -> Path:
    """Write bake-off results as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "engines": sorted({r.engine for r in results}),
        "fixtures": len({r.fixture for r in results}),
        "results": [
            {
                "engine": r.engine,
                "fixture": r.fixture,
                "cer": r.cer,
                "wer": r.wer,
                "duration_ms": round(r.duration_ms, 1),
                "success": r.success,
            }
            for r in results
        ],
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
