"""Tests for the content noise filter (页眉/页脚/页码/水印/版权行)."""
from __future__ import annotations

import pytest

from app.ingestion.content_cleaner import (
    CleanerError,
    clean_text,
    noise_report,
    repeated_lines,
    split_pages,
)

# 3 pages with identical running header + footer noise + boilerplate block
DOC = """牛津通识读本·简明逻辑学
三段论是亚里士多德逻辑的核心。
第 12 页

牛津通识读本·简明逻辑学
演绎推理从一般到特殊。
第 13 页

牛津通识读本·简明逻辑学
逻辑学也研究谬误与悖论。
第 14 页

书号 ISBN 978-7-5447-2983-3 版次 2013年5月第1版 2013年5月第1次印刷
版权所有 翻印必究
"""


def test_split_pages():
    pages = split_pages(DOC)
    assert len(pages) >= 2


def test_detect_running_header():
    pages = split_pages(DOC)
    noise = repeated_lines(pages)
    assert "牛津通识读本·简明逻辑学" in noise
    assert "三段论是亚里士多德逻辑的核心。" not in noise


def test_clean_text_removes_noise_keeps_content():
    cleaned = clean_text(DOC)
    assert "牛津通识读本·简明逻辑学" not in cleaned      # running header removed
    assert "第 12 页" not in cleaned                    # page number removed
    assert "ISBN" not in cleaned                        # ISBN/boilerplate removed
    assert "三段论是亚里士多德逻辑的核心。" in cleaned   # real content kept
    assert "演绎推理从一般到特殊。" in cleaned
    assert "逻辑学也研究谬误与悖论。" in cleaned


def test_clean_single_block_strips_boilerplate():
    text = "正文第一行。\n书号 ISBN 978-7-5447-2983-3 版权所有 翻印必究\n正文继续。"
    cleaned = clean_text(text)
    assert "ISBN" not in cleaned
    assert "正文第一行。" in cleaned


def test_watermark_removed():
    text = "正文。\n仅供学习参考，请勿外传\n继续正文。"
    cleaned = clean_text(text)
    assert "仅供学习" not in cleaned
    assert "继续正文。" in cleaned


def test_noise_report_shape():
    report = noise_report(DOC)
    assert report["removed_chars"] > 0
    assert report["pages"] >= 2
    assert report["noise_line_count"] >= 1
    assert report["before_chars"] > report["after_chars"]


def test_validation():
    with pytest.raises(CleanerError):
        split_pages(123)
    assert clean_text("") == ""
