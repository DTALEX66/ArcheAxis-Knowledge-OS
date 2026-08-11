"""Direct tests for shared.pipeline.run_pipeline stage composition.

Existing coverage (test_mfx012_legacy_credibility_isolation,
test_phase4_research_github) exercises file/text sources; these tests
pin the full multi-stage contract for a text source with all actions.
"""

from __future__ import annotations

import pytest

from shared.pipeline import run_pipeline


def test_text_pipeline_all_stages(monkeypatch) -> None:
    """text source + extract/tag/summarize/facts/crossref stages all emit."""
    inserted = []

    def fake_insert(table, row):
        inserted.append((table, row))

    monkeypatch.setattr("shared.storage.insert", fake_insert)
    monkeypatch.setattr("shared.storage.fts5_sync", lambda *a, **k: None)
    # vector_search/backlinks run inside real contextlib.suppress — any
    # ImportError there is swallowed, so no stubbing needed.

    text = (
        "Machine learning is a field of artificial intelligence. "
        "Python was created by Guido van Rossum. "
        "FastAPI uses Pydantic for validation. "
        "The heart is part of the circulatory system."
    )
    result = run_pipeline(
        "text",
        text,
        actions=["extract", "tag", "summarize", "facts", "index", "crossref"],
    )
    assert result["source"] == "text"
    assert result["stages"]["extract"]["engine"] == "passthrough"
    assert "tags" in result["stages"]["tag"]
    assert "executive" in result["stages"]["summarize"]
    assert result["stages"]["facts"]["count"] >= 1
    assert result["stages"]["index"]["kb_id"].startswith("doc_")
    assert result["stages"]["crossref"]["classification"] == "legacy_heuristic"
    assert result["stages"]["crossref"]["verified"] is False
    assert result["kb_id"] == result["stages"]["index"]["kb_id"]
    # document actually inserted
    assert inserted[0][0] == "kb_documents"


def test_text_pipeline_minimal_actions(monkeypatch) -> None:
    """Only requested actions run; others absent from stages."""
    result = run_pipeline("text", "Some simple content here.", actions=["tag"])
    assert set(result["stages"].keys()) == {"extract", "tag"}
    assert "summarize" not in result["stages"]
    assert "kb_id" not in result or result["kb_id"] == ""


def test_external_source_auto_ingest_raises() -> None:
    """External sources cannot auto-ingest (governed candidate path)."""
    with pytest.raises(RuntimeError, match="auto-ingest is disabled"):
        run_pipeline("url", "https://example.com", auto_ingest=True)


def test_file_source_requires_approved_roots(monkeypatch) -> None:
    """file source without COGNITIVE_APPROVED_SOURCE_ROOTS is rejected."""
    monkeypatch.delenv("COGNITIVE_APPROVED_SOURCE_ROOTS", raising=False)
    with pytest.raises(RuntimeError, match="COGNITIVE_APPROVED_SOURCE_ROOTS"):
        run_pipeline("file", "C:/tmp/nonexistent.md", auto_ingest=False)


def test_empty_text_returns_before_stages(monkeypatch) -> None:
    """Empty content short-circuits with only the extract stage."""
    result = run_pipeline("text", "")
    assert result["stages"]["extract"]["chars"] == 0
    assert set(result["stages"].keys()) == {"extract"}


def test_evidence_stage_queries_doi_when_present(monkeypatch) -> None:
    """evidence action extracts a DOI from content and queries it."""

    def fake_enrich(doi=None, claim_text=None):
        return {
            "hits": [{"source": "crossref", "id": doi, "title": "t"}],
            "source_count": 1,
        }

    monkeypatch.setattr(
        "shared.cross_reference.enrich_with_public_sources", fake_enrich
    )
    result = run_pipeline(
        "text",
        "Reference: https://doi.org/10.1038/s41586-020-2649-2 abstract",
        actions=["evidence"],
    )
    ev = result["stages"]["evidence"]
    assert ev["classification"] == "public-evidence"
    assert ev["verified"] is False
    assert ev["doi"] == "10.1038/s41586-020-2649-2"
    assert ev["hits"][0]["id"] == "10.1038/s41586-020-2649-2"


def test_evidence_stage_falls_back_to_claim_text_without_doi(monkeypatch) -> None:
    """evidence action uses OpenAlex claim-text search when no DOI present."""

    captured = {}

    def fake_enrich(doi=None, claim_text=None):
        captured["doi"] = doi
        captured["claim_text"] = claim_text
        return {"hits": [], "source_count": 0}

    monkeypatch.setattr(
        "shared.cross_reference.enrich_with_public_sources", fake_enrich
    )
    text = "Deep learning architectures for vision transformers."
    result = run_pipeline("text", text, actions=["evidence"])
    assert captured["doi"] is None
    assert captured["claim_text"] == text[:300]
    assert result["stages"]["evidence"]["classification"] == "public-evidence"
    assert result["stages"]["evidence"]["verified"] is False


def test_evidence_stage_absent_by_default(monkeypatch) -> None:
    """evidence is not in the default actions; stages stay clean."""
    result = run_pipeline("text", "Plain content without actions.")
    assert "evidence" not in result["stages"]
