#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext evaluation worker: recomputable CER/WER (T07).

Compares a prediction text against a gold reference and emits quality-report
rows (packages/contracts/v1/quality-report.schema.json). Every row carries
prediction_ref/gold_ref sha256 so any metric can be recomputed from the
original artifacts; nothing is a bare mean claim.

Metrics (deterministic, dependency-free):
- cer: character error rate over code points (Levenshtein / gold length)
- wer: word error rate over whitespace-separated tokens

Normalization: none by default (raw comparison, loss note records it);
pass --normalize lower to compare casefolded text (documented in params).

Usage:
    python worker_quality.py <prediction.txt> <gold.txt>
        [--sample-id ID] [--run-id ID] [--normalize none|lower]
Output: quality-report.schema.json-compatible envelope
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ENGINE = "python-worker-quality"
ENGINE_VERSION = "0.1.0"


def levenshtein(a: str, b: str) -> int:
    """Plain Levenshtein edit distance over code points."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(
                    current[-1] + 1,  # deletion
                    previous[j] + 1,  # insertion
                    previous[j - 1] + (0 if ca == cb else 1),  # substitution
                )
            )
        previous = current
    return previous[-1]


def _normalize(text: str, mode: str) -> str:
    if mode == "lower":
        return text.casefold()
    return text


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def evaluate(prediction: Path, gold: Path, *, sample_id: str, run_id: str, normalize: str) -> dict:
    gold_raw = _read_text(gold)
    prediction_raw = _read_text(prediction)
    gold_ref = _sha256_file(gold)
    prediction_ref = _sha256_file(prediction)

    rows: list[dict] = []
    if gold_raw.strip() == "":
        rows.append(
            {
                "metric": "cer",
                "sample_id": sample_id,
                "status": "unmeasured",
                "value": None,
                "unit": "error_rate",
                "prediction_ref": {"sha256": prediction_ref, "path": str(prediction)},
                "gold_ref": {"sha256": gold_ref, "path": str(gold)},
                "note": "gold reference is empty; metric not measured (no fake value)",
            }
        )
        rows.append(
            {
                "metric": "wer",
                "sample_id": sample_id,
                "status": "unmeasured",
                "value": None,
                "unit": "error_rate",
                "prediction_ref": {"sha256": prediction_ref, "path": str(prediction)},
                "gold_ref": {"sha256": gold_ref, "path": str(gold)},
                "note": "gold reference is empty; metric not measured (no fake value)",
            }
        )
    else:
        gold_text = _normalize(gold_raw.strip(), normalize)
        prediction_text = _normalize(prediction_raw.strip(), normalize)
        gold_chars = list(gold_text)
        prediction_chars = list(prediction_text)
        cer = levenshtein(prediction_chars, gold_chars) / max(1, len(gold_chars))
        gold_tokens = gold_text.split()
        prediction_tokens = prediction_text.split()
        wer = levenshtein(prediction_tokens, gold_tokens) / max(1, len(gold_tokens))
        rows.append(
            {
                "metric": "cer",
                "sample_id": sample_id,
                "status": "measured",
                "value": round(cer, 6),
                "unit": "error_rate",
                "prediction_ref": {"sha256": prediction_ref, "path": str(prediction)},
                "gold_ref": {"sha256": gold_ref, "path": str(gold)},
                "note": f"code-point Levenshtein / gold length ({len(gold_chars)} chars)",
            }
        )
        rows.append(
            {
                "metric": "wer",
                "sample_id": sample_id,
                "status": "measured",
                "value": round(wer, 6),
                "unit": "error_rate",
                "prediction_ref": {"sha256": prediction_ref, "path": str(prediction)},
                "gold_ref": {"sha256": gold_ref, "path": str(gold)},
                "note": f"token Levenshtein / gold length ({len(gold_tokens)} tokens)",
            }
        )

    return {
        "schema": "archeaxis.quality-report/v1",
        "report_id": f"qr-{run_id}-{sample_id}",
        "run_id": run_id,
        "engine": {"name": ENGINE, "version": ENGINE_VERSION},
        "rows": rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"normalize": normalize, "algorithms": {"cer": "levenshtein-codepoints", "wer": "levenshtein-tokens"}},
            "loss_note": "raw comparison unless --normalize lower; all metrics recomputable from refs",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ArcheAxis quality evaluation worker")
    parser.add_argument("prediction", help="prediction text file")
    parser.add_argument("gold", help="gold reference text file")
    parser.add_argument("--sample-id", default="sample")
    parser.add_argument("--run-id", default="local")
    parser.add_argument("--normalize", choices=["none", "lower"], default="none")
    args = parser.parse_args()

    try:
        out = evaluate(
            Path(args.prediction),
            Path(args.gold),
            sample_id=args.sample_id,
            run_id=args.run_id,
            normalize=args.normalize,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
