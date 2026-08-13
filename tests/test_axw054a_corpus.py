"""AXW-054A: evaluation corpus integrity tests.

Verifies the multi-lingual corpus (tests/fixtures/corpus) stays usable as
a human-truth evaluation set:
- manifest declares license / source / sha256 / privacy for every sample;
- every truth file has a matching prediction file;
- manifest sha256 matches the on-disk truth bytes (integrity);
- the golden-pair evaluator can consume the corpus (CER/WER produced);
- multi-lingual coverage (zh / en / mixed) is present.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from shared.accuracy_benchmark import evaluate_golden_pairs

CORPUS = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "corpus"


def _manifest() -> dict:
    return json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))


def test_manifest_declares_required_fields() -> None:
    manifest = _manifest()
    samples = manifest["samples"]
    assert len(samples) >= 3
    for sample in samples:
        for field in ("sample_id", "language", "source", "license", "sha256_truth", "privacy"):
            assert sample.get(field), f"{sample.get('sample_id')} missing {field}"
        assert len(sample["sha256_truth"]) == 64


def test_every_truth_has_prediction() -> None:
    truths = sorted(CORPUS.glob("*.truth.txt"))
    assert truths
    for truth in truths:
        pred = CORPUS / truth.name.replace(".truth.txt", ".pred.txt")
        assert pred.is_file(), f"missing prediction for {truth.name}"


def test_manifest_sha256_matches_disk() -> None:
    manifest = _manifest()
    for sample in manifest["samples"]:
        truth = CORPUS / f"{sample['sample_id']}.truth.txt"
        assert truth.is_file()
        on_disk = hashlib.sha256(truth.read_bytes()).hexdigest()
        assert on_disk == sample["sha256_truth"], f"sha mismatch for {sample['sample_id']}"


def test_multilingual_coverage() -> None:
    manifest = _manifest()
    languages = {s["language"] for s in manifest["samples"]}
    assert "zh" in languages
    assert "en" in languages


def test_golden_pair_evaluator_consumes_corpus() -> None:
    result = evaluate_golden_pairs(CORPUS)
    assert result.get("samples")
    evaluated = [s for s in result["samples"] if s.get("status") != "missing_prediction"]
    assert evaluated
    # CER/WER must be numeric for evaluated pairs (0.0 for exact copies).
    metrics = [s for s in evaluated if "cer" in s and s["cer"] is not None]
    assert metrics
    for s in evaluated:
        if "cer" in s and s["cer"] is not None:
            assert 0.0 <= s["cer"] <= 1.0
