"""Tests for the OCR quality gate (H2 quality gate)."""
from __future__ import annotations

import pytest

from app.ingestion.ocr_gate import OcrGateError, assess, score_ocr


def test_blank_fails():
    verdict = assess("   \n  ")
    assert verdict.verdict == "fail"
    assert verdict.quality.blank


def test_garbage_fails():
    verdict = assess("\x00\x01\x02" * 20)
    assert verdict.verdict == "fail"


def test_short_text_review_or_fail():
    verdict = assess("ok")
    assert verdict.verdict in ("review", "fail")


def test_good_ocr_passes():
    text = ("贝叶斯知识追踪是一种隐马尔可夫模型，用 guess 和 slip 描述噪声。" +
            "掌握度是技能已学习的后验概率。这是足够长的正常文本示例，用于通过质量门禁。")
    verdict = assess(text)
    assert verdict.verdict == "pass"
    assert verdict.quality.char_count > 20


def test_score_metrics_shape():
    q = score_ocr("abc 123 测试")
    assert 0.0 <= q.printable_ratio <= 1.0
    assert q.script_ratio > 0


def test_non_string_rejected():
    with pytest.raises(OcrGateError):
        score_ocr(123)
