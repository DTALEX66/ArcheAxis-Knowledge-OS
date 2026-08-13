"""AXW-054B: comparative metrics tests.

Verifies:
- rates carry Wilson 95% CI and sample size;
- empty samples are explicitly unverified (never confident 0%);
- citation coverage / correctness / refusal / retention / transfer
  aggregate correctly;
- latency and resource summaries are computed with n.
"""

from __future__ import annotations

from shared.answer_metrics import (
    citation_coverage,
    correctness,
    full_report,
    latency_ms,
    learning_retention,
    refusal_rate,
    resource_usage,
    transfer_rate,
    wilson_interval,
)


def test_wilson_interval_known_values() -> None:
    # 0/10 → CI low 0; 10/10 → CI high 1; 5/10 → wide symmetric-ish CI.
    zero = wilson_interval(0, 10)
    assert zero["rate"] == 0.0
    assert zero["ci_low"] == 0.0
    assert zero["n"] == 10
    all_ = wilson_interval(10, 10)
    assert all_["rate"] == 1.0
    assert all_["ci_high"] == 1.0
    half = wilson_interval(5, 10)
    assert 0.1 <= half["ci_low"] < 0.5 < half["ci_high"] <= 0.9


def test_empty_samples_are_unverified() -> None:
    assert correctness([])["status"] == "unverified_no_truth"
    assert refusal_rate([])["status"] == "unverified_no_verdicts"
    assert learning_retention([])["status"] == "unverified_no_reviews"
    assert transfer_rate([])["status"] == "unverified_no_transfer"
    assert latency_ms([])["status"] == "unverified_no_samples"
    assert resource_usage([])["status"] == "unverified_no_samples"
    assert citation_coverage([])["status"] == "unverified_no_answers"
    assert correctness([])["rate"] is None


def test_citation_coverage_counts_grounded_claims() -> None:
    verdicts = [
        {"status": "success", "answer": {"claims": [{"anchor_id": "a"}, {"anchor_id": "b"}]}},
        {"status": "success", "answer": {"claims": [{"anchor_id": "c"}]}},
        {"status": "refused", "answer": None},
    ]
    result = citation_coverage(verdicts)
    assert result["n"] == 3
    assert result["rate"] == 1.0


def test_refusal_rate_counts_non_success() -> None:
    verdicts = [
        {"status": "success"},
        {"status": "refused"},
        {"status": "stale"},
        {"status": "conflict"},
        {"status": "success"},
    ]
    result = refusal_rate(verdicts)
    assert result["n"] == 5
    assert result["rate"] == 0.6
    assert 0.0 < result["ci_low"] < result["rate"] < result["ci_high"] < 1.0


def test_correctness_retention_transfer() -> None:
    assert correctness([True, True, False])["rate"] == round(2 / 3, 6)
    assert learning_retention([True, True, True, True])["rate"] == 1.0
    assert transfer_rate([False, False])["rate"] == 0.0


def test_latency_and_resource_summaries() -> None:
    lat = latency_ms([100.0, 200.0, 300.0])
    assert lat["n"] == 3
    assert lat["mean_ms"] == 200.0
    assert lat["p50_ms"] == 200.0
    assert lat["p95_ms"] == 300.0
    mem = resource_usage([10.0, 20.0])
    assert mem["mean_mb"] == 15.0
    assert mem["peak_mb"] == 20.0


def test_full_report_aggregates_all() -> None:
    report = full_report(
        verdicts=[{"status": "success", "answer": {"claims": [{}]}}, {"status": "refused"}],
        truth_results=[True, False, True],
        retention_results=[True, True],
        transfer_results=[False],
        durations_ms=[50.0, 60.0],
        memory_mb=[30.0],
    )
    assert report["citation_coverage"]["n"] == 1
    assert report["refusal_rate"]["rate"] == 0.5
    assert report["correctness"]["rate"] == round(2 / 3, 6)
    assert report["learning_retention"]["rate"] == 1.0
    assert report["transfer_rate"]["rate"] == 0.0
    assert report["latency"]["n"] == 2
    assert report["resource"]["n"] == 1
