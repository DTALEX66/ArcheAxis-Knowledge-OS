"""MFX-012 regression tests: legacy credibility heuristic isolation.

Verifies that ``score_credibility`` (a coarse domain/keyword heuristic) is
explicitly classified as ``legacy_heuristic`` and can never be promoted to a
'verified'/'web-verified'/'evidence' state. A trusted domain, the words
'peer-reviewed', or a DOI-shaped substring must NOT make a fact appear
web-verified.
"""

import pytest

from shared.cross_reference import score_credibility


def test_score_credibility_is_classified_legacy_heuristic() -> None:
    res = score_credibility(
        {"title": "x", "content": "y", "url": "https://example.org"}
    )
    assert res["classification"] == "legacy_heuristic"
    assert "verified" not in res or res.get("verified") is not True


def test_trusted_domain_does_not_equal_verified() -> None:
    # A high trust domain + the words 'peer-reviewed' must still be a legacy
    # heuristic, not web verification.
    res = score_credibility(
        {
            "title": "peer-reviewed study",
            "content": "this paper is peer-reviewed and authoritative",
            "url": "https://www.pnas.org/doi/10.1073/pnas.0000000000",
        }
    )
    assert res["classification"] == "legacy_heuristic"
    # Even if the score is high, it is NOT evidence of verification.
    assert res.get("verified", False) is not True


def test_pipeline_crossref_stage_is_not_verified(tmp_path) -> None:
    """run_pipeline 'crossref' stage must flag legacy_heuristic / verified=False."""
    from shared import pipeline

    # Use a text source with the crossref action; avoid network by using
    # 'text' source and skipping auto_ingest.
    out = pipeline.run_pipeline(
        source="text",
        input_data="A peer-reviewed finding published in Nature about gravity.",
        actions=["crossref"],
        auto_ingest=False,
    )
    cross = out.get("stages", {}).get("crossref", {})
    if not cross:
        pytest.skip("crossref stage not produced in this environment (kb_id absent)")
    assert cross.get("classification") == "legacy_heuristic"
    assert cross.get("verified") is False
