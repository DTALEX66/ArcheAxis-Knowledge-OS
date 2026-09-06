"""H2 bake-off CLI — run OCR/ASR engine comparison with real fixtures.

Usage:
    uv run python scripts/run_bakeoff.py [--mode ocr|asr|all] [--fixtures DIR] [--out DIR]

Runs every *available* engine (Tesseract eng/chi-sim, RapidOCR, faster-whisper,
...) against the fixture files in --fixtures (default: tests/fixtures/bakeoff/),
computes CER/WER against the matching .txt ground truth when present, and writes
CSV + JSON reports to --out (default: .project-local/task-runtime/bakeoff-results/).

Unavailable engines are listed as skipped — the bake-off never pretends.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from shared.bakeoff import (
    load_fixtures,
    report_csv,
    report_json,
    run_bakeoff,
)
from shared.bakeoff_engines import ASR_ENGINES, OCR_ENGINES


def _fixture_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    default = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "bakeoff"
    if default.is_dir():
        return default
    raise SystemExit(
        f"no fixtures at {default}; pass --fixtures DIR with images/audio + .txt ground truth"
    )


def _pick_engines(mode: str) -> list:
    if mode in ("ocr", "all"):
        return list(OCR_ENGINES) + (ASR_ENGINES if mode == "all" else [])
    return list(ASR_ENGINES)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["ocr", "asr", "all"], default="all")
    parser.add_argument("--fixtures", default=None, help="fixture dir (images/audio + .txt truth)")
    parser.add_argument("--out", default=None, help="report output dir")
    args = parser.parse_args()

    fixtures = _fixture_dir(args.fixtures)
    out_dir = Path(args.out) if args.out else (
        Path(__file__).resolve().parents[1] / ".project-local" / "task-runtime" / "bakeoff-results"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    fixture_list = load_fixtures(fixtures)
    engines = _pick_engines(args.mode)
    available = [e for e in engines if e.available]
    skipped = [e.name for e in engines if not e.available]

    print(f"fixtures: {len(fixture_list)} from {fixtures}")
    print(f"engines:  {', '.join(e.name for e in available)}")
    if skipped:
        print(f"skipped (unavailable): {', '.join(skipped)}")
    if not available:
        print("no available engines — nothing to run")
        return 1
    if not fixture_list:
        print("no fixture files found")
        return 1

    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")
    results = run_bakeoff(available, fixture_list)
    csv_path = report_csv(results, out_dir / f"bakeoff-{args.mode}-{stamp}.csv")
    json_path = report_json(results, out_dir / f"bakeoff-{args.mode}-{stamp}.json")

    print(f"\n{'engine':<18} {'fixture':<28} {'CER':>7} {'WER':>7} {'ms':>10}")
    for r in results:
        cer = f"{r.cer:.4f}" if r.cer is not None else "-"
        wer = f"{r.wer:.4f}" if r.wer is not None else "-"
        ms = f"{r.duration_ms:.1f}" if r.success else f"ERR {r.error[:20]}"
        print(f"{r.engine:<18} {r.fixture:<28} {cer:>7} {wer:>7} {ms:>10}")
    print(f"\nreports: {csv_path}")
    print(f"         {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
