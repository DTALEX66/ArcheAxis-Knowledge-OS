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
