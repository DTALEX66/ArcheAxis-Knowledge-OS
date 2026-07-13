"""Measured OCR/ASR accuracy against explicit human-labelled golden pairs.

Model confidence, file existence and sampled extraction are never treated as
accuracy. With no truth/prediction pairs the result is explicitly unverified.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path


def edit_distance(left: Sequence[str], right: Sequence[str]) -> int:
    previous = list(range(len(right) + 1))
    for index, left_item in enumerate(left, 1):
        current = [index]
        for offset, right_item in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[offset] + 1,
                    previous[offset - 1] + (left_item != right_item),
                )
            )
        previous = current
    return previous[-1]


def _normalize_characters(text: str) -> str:
    return "".join(text.split())


def _word_tokens(text: str) -> list[str]:
    return text.split()


def evaluate_golden_pairs(golden_dir: str | Path) -> dict:
    """Evaluate ``*.truth.txt``/``*.pred.txt`` pairs with weighted CER/WER."""
    root = Path(golden_dir)
    samples: list[dict] = []
    for truth_path in sorted(root.glob("*.truth.txt")) if root.is_dir() else []:
        stem = truth_path.name.removesuffix(".truth.txt")
        prediction_path = root / f"{stem}.pred.txt"
        if not prediction_path.exists():
            samples.append({"sample": stem, "status": "missing_prediction"})
            continue

        truth_raw = truth_path.read_text(encoding="utf-8", errors="strict")
        prediction_raw = prediction_path.read_text(encoding="utf-8", errors="strict")
        truth = _normalize_characters(truth_raw)
        prediction = _normalize_characters(prediction_raw)
        if not truth:
            samples.append({"sample": stem, "status": "empty_truth"})
            continue

        metadata_path = root / f"{stem}.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        char_distance = edit_distance(truth, prediction)
        words_truth = _word_tokens(truth_raw)
        words_prediction = _word_tokens(prediction_raw)
        word_distance = edit_distance(words_truth, words_prediction) if words_truth else None
        cer = char_distance / len(truth)
        wer = word_distance / len(words_truth) if word_distance is not None else None
        samples.append(
            {
                "sample": stem,
                "kind": metadata.get("kind", "unknown"),
                "status": "measured",
                "truth_chars": len(truth),
                "prediction_chars": len(prediction),
                "edit_distance": char_distance,
                "cer": round(cer, 6),
                "accuracy": round(max(0.0, 1.0 - cer), 6),
                "truth_words": len(words_truth),
                "word_edit_distance": word_distance,
                "wer": round(wer, 6) if wer is not None else None,
            }
        )

    measured = [sample for sample in samples if sample.get("status") == "measured"]
    expected_count = len(samples)
    weighted_distance = sum(sample["edit_distance"] for sample in measured)
    weighted_chars = sum(sample["truth_chars"] for sample in measured)
    aggregate_cer = weighted_distance / weighted_chars if weighted_chars else None
    weighted_word_distance = sum(
        sample["word_edit_distance"] or 0 for sample in measured
    )
    weighted_words = sum(sample["truth_words"] for sample in measured)
    aggregate_wer = weighted_word_distance / weighted_words if weighted_words else None
    coverage = len(measured) / expected_count if expected_count else 0.0
    if measured and len(measured) == expected_count:
        status = "measured_complete"
    elif measured:
        status = "incomplete_partial"
    else:
        status = "unverified_no_golden_pairs"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "human_truth_character_error_rate",
        "status": status,
        "expected_sample_count": expected_count,
        "sample_count": len(measured),
        "coverage": round(coverage, 6),
        "aggregate_cer": round(aggregate_cer, 6) if aggregate_cer is not None else None,
        "aggregate_wer": round(aggregate_wer, 6) if aggregate_wer is not None else None,
        "aggregate_accuracy": (
            round(max(0.0, 1.0 - aggregate_cer), 6) if aggregate_cer is not None else None
        ),
        "samples": samples,
    }
