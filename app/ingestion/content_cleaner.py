"""Content noise filter — pipeline interference removal (页眉/页脚/页码/水印/版权行).

Converted text from PDFs/OCR carries non-knowledge interference: running
headers (book title on every page), footers (page numbers, ISBN, 版权/印刷行),
watermarks, and repeated boilerplate. This module strips them so the knowledge
stored is the REAL content (user requirement, 2026-08-18).

    clean_text(text)                — full-document cleanup (page-aware)
    repeated_lines(pages)           — running headers/footers across pages
    clean_page(page, noise_lines)   — one-page cleanup
    noise_report(text)              — what was removed (audit)

Deterministic and local; no LLM needed.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

_PAGE_SPLIT = re.compile(r"\n\s*\n|\f")
_PAGE_NUMBER_ONLY = re.compile(r"^\s*[\-–—]?\s*\d{1,4}\s*[\-–—]?\s*$")
_PAGE_LABEL = re.compile(r"^第\s*\d{1,4}\s*页$|^页\s*\d{1,4}$|^page\s*\d{1,4}$|^p\.?\s*\d{1,4}$", re.IGNORECASE)
_ISBN = re.compile(r"(?:ISBN(?:-13)?:?|书\s*号)[\s:：]*[\d\-\sXx]{8,20}", re.IGNORECASE)
_BOILERPLATE = re.compile(
    r"(版\s*次|第\s*[\d一二三四五六七八九十]+\s*版|印\s*次|印刷|出版发行|"
    r"版权所有|翻印必究|如有印装质量问题|责任编辑|装帧设计|版权局|字数|印张)",
    re.IGNORECASE,
)
_WATERMARK = re.compile(r"(仅供学习|仅供参考|测试文档|watermark|sample|draft|preview|试读|电子样书)", re.IGNORECASE)
_MIN_NOISE_REPEATS = 3


class CleanerError(ValueError):
    """Raised when the cleaner receives invalid input."""


def split_pages(text: str) -> list[str]:
    """Split document text into page-like blocks (blank-line or form-feed)."""
    if not isinstance(text, str):
        raise CleanerError("text must be a string")
    return [p.strip() for p in _PAGE_SPLIT.split(text) if p.strip()]


def repeated_lines(pages: list[str], *, min_repeats: int = _MIN_NOISE_REPEATS) -> set[str]:
    """Running headers/footers: lines appearing on >= min_repeats pages."""
    counter: Counter[str] = Counter()
    for page in pages:
        seen: set[str] = set()
        for line in page.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                counter[line] += 1
    return {line for line, count in counter.items() if count >= min_repeats}


def _is_noise_line(line: str, noise_lines: set[str]) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped in noise_lines:
        return True
    if _PAGE_NUMBER_ONLY.match(stripped) or _PAGE_LABEL.match(stripped):
        return True
    if _ISBN.search(stripped):
        return True
    if _BOILERPLATE.search(stripped):
        return True
    if _WATERMARK.search(stripped):
        return True
    return False


def clean_page(page: str, noise_lines: set[str]) -> str:
    """Strip noise lines from one page, keeping real content lines."""
    kept: list[str] = []
    for line in page.splitlines():
        if not _is_noise_line(line, noise_lines):
            kept.append(line)
    return "\n".join(kept).strip()


def clean_text(text: str) -> str:
    """Full-document cleanup: split pages → detect running noise → clean each."""
    if not text.strip():
        return ""
    pages = split_pages(text)
    if len(pages) <= 1:
        # single block: just filter page numbers / ISBN / boilerplate / watermark
        return clean_page(text, set())
    noise = repeated_lines(pages)
    cleaned = [clean_page(page, noise) for page in pages]
    return "\n\n".join(page for page in cleaned if page)


def noise_report(text: str) -> dict[str, Any]:
    """Audit: what noise was detected/removed (for evidence)."""
    before = len(text)
    pages = split_pages(text)
    noise = repeated_lines(pages)
    cleaned = clean_text(text)
    return {
        "before_chars": before,
        "after_chars": len(cleaned),
        "removed_chars": before - len(cleaned),
        "pages": len(pages),
        "running_noise_lines": sorted(noise)[:20],
        "noise_line_count": len(noise),
        "removed_ratio": round((before - len(cleaned)) / max(before, 1), 4),
    }
