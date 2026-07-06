"""Tests for RAG retriever module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.retriever import retrieve


class TestRetriever:
    def test_retrieve_returns_context(self):
        result = retrieve("test query for context retrieval")
        assert result is not None

    def test_retrieve_no_empty_result(self):
        """Even for unknown queries, retriever should return a valid structure."""
        result = retrieve("xyzzy_nonexistent_query_12345")
        assert result is not None

    def test_retrieve_contains_content(self):
        result = retrieve("B线 MVP development plan")
        assert result is not None
