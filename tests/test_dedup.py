"""Tests for dedup service."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.dedup import dedup_service, content_hash, tokenize, jaccard_similarity


class TestContentHash:
    def test_stable_hash(self):
        h1 = content_hash("hello world")
        h2 = content_hash("hello world")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256

    def test_different_content(self):
        h1 = content_hash("hello")
        h2 = content_hash("world")
        assert h1 != h2


class TestTokenize:
    def test_basic_tokenize(self):
        tokens = tokenize("Hello World! Test-case 123")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        assert "case" in tokens
        assert "123" in tokens

    def test_chinese_tokenize(self):
        tokens = tokenize("你好世界 test")
        assert "test" in tokens


class TestJaccard:
    def test_identical(self):
        assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint(self):
        assert jaccard_similarity({"a"}, {"b"}) == 0.0

    def test_partial(self):
        score = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert 0.4 < score < 0.6  # 2/4 = 0.5

    def test_both_empty(self):
        assert jaccard_similarity(set(), set()) == 1.0


class TestDedupService:
    def test_find_by_url_exact(self):
        candidates = [
            {"url": "https://example.com/a", "title": "A"},
            {"url": "https://example.com/b", "title": "B"},
        ]
        result = dedup_service.find_by_url("https://example.com/a", candidates)
        assert result is not None
        assert result["title"] == "A"

    def test_find_by_url_not_found(self):
        candidates = [{"url": "https://example.com/a", "title": "A"}]
        assert dedup_service.find_by_url("https://example.com/x", candidates) is None

    def test_find_by_content_hash(self):
        h = content_hash("test")
        candidates = [{"content_hash": h, "title": "Test"}]
        result = dedup_service.find_by_content_hash(h, candidates)
        assert result is not None

    def test_similar_title_exact_match(self):
        candidates = [{"title": "Machine Learning Tutorial"}]
        result = dedup_service.find_similar_title("Machine Learning Tutorial", candidates)
        assert result is not None

    def test_similar_title_no_match(self):
        candidates = [{"title": "Machine Learning"}, {"title": "Deep Learning"}]
        result = dedup_service.find_similar_title("Quantum Computing", candidates)
        assert result is None
