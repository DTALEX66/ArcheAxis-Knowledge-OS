"""Content deduplication service for IR + KB.

Adapted from Star-Trails-Log dedup service.
Generalized for Cognitive-Loop-OS: supports URL, title, and content-hash
deduplication across KB documents, research notes, intake cards, etc.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence


def content_hash(text: str) -> str:
    """Produce a stable SHA-256 fingerprint for text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase word set for similarity comparison."""
    return set(re.findall(r"\w+", text.lower()))


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Jaccard similarity coefficient."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class DedupService:
    """Content deduplication — works on dict rows (title, url, content_hash).

    Designed to work with records from shared.storage (dict/Row proxies)
    or any dict-like input. No direct SQL dependency — callers provide
    the records to compare against.
    """

    # ── URL-based ──

    @staticmethod
    def find_by_url(url: str, candidates: Sequence[dict], url_key: str = "url") -> dict | None:
        """Find a candidate record with the same URL."""
        if not url:
            return None
        for row in candidates:
            if row.get(url_key) == url:
                return row
        return None

    # ── Content-hash-based ──

    @staticmethod
    def find_by_content_hash(
        hash_val: str, candidates: Sequence[dict], hash_key: str = "content_hash"
    ) -> dict | None:
        """Find a candidate record with the same content hash."""
        if not hash_val:
            return None
        for row in candidates:
            if row.get(hash_key) == hash_val:
                return row
        return None

    # ── Title similarity ──

    def find_similar_title(
        self,
        title: str,
        candidates: Sequence[dict],
        title_key: str = "title",
        threshold: float = 0.6,
    ) -> dict | None:
        """Find a record with a similar title using Jaccard word overlap.

        Also catches exact match and containment shortcuts.
        Returns the best match or None.
        """
        title_lower = title.lower()
        title_words = tokenize(title)
        best_score = 0.0
        best_row: dict | None = None

        for row in candidates:
            candidate = (row.get(title_key) or "").lower()
            if not candidate:
                continue
            # exact match shortcut
            if candidate == title_lower:
                return row
            # containment
            if (
                len(candidate) > 3
                and len(title_lower) > 3
                and (candidate in title_lower or title_lower in candidate)
            ):
                return row
            # Jaccard word overlap
            candidate_words = tokenize(candidate)
            score = jaccard_similarity(title_words, candidate_words)
            if score > best_score and score >= threshold:
                best_score = score
                best_row = row

        return best_row


dedup_service = DedupService()
