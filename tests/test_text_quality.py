"""Tests for shared.text_quality (ADS-001/002: JiWER + RapidFuzz absorption)."""

from shared.text_quality import alignment_similarity, cer, find_disagreement_spans, wer


class TestCerWer:
    def test_cer_identical(self) -> None:
        assert cer("hello", "hello") == 0.0

    def test_cer_single_substitution(self) -> None:
        assert cer("hello", "hallo") > 0.0

    def test_wer_identical(self) -> None:
        assert wer("hello world", "hello world") == 0.0

    def test_wer_one_error(self) -> None:
        assert wer("hello world", "hello") > 0.0

    def test_both_empty(self) -> None:
        assert cer("", "") == 0.0
        assert wer("", "") == 0.0


class TestAlignment:
    def test_similarity_identical(self) -> None:
        assert alignment_similarity("abc def", "def abc") > 0.9

    def test_similarity_different(self) -> None:
        assert alignment_similarity("hello", "zzzzz") < 0.5


class TestDisagreementSpans:
    def test_no_disagreement(self) -> None:
        spans = find_disagreement_spans("hello world", "hello world")
        assert spans == []

    def test_finds_disagreement(self) -> None:
        spans = find_disagreement_spans("hello world", "zzzzz zzzzz", threshold=0.3)
        assert len(spans) > 0
        for s in spans:
            assert "start" in s
            assert "end" in s
            assert "truth_slice" in s
            assert "pred_slice" in s
