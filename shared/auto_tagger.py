"""Auto-tagging engine — zero-dependency NLP keyword extraction + categorization.

Absorbs: automated content tagging systems, Tiago Forte's progressive
summarization, Zettelkasten atomic note detection.

Capabilities:
1. extract_keywords(text) → top N keywords via TF-IDF-like scoring
2. suggest_tags(text) → auto-suggest tags based on content
3. detect_atomicity(text) → check if a note is truly "atomic" (one idea)
4. progressive_summarize(text) → 4-layer summary (full → bold → highlight → executive)

All zero-dependency — uses only Python stdlib + numpy (already installed).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

import numpy as np

# ── Stop words (English + Chinese common) ────────────────

_STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "just", "because", "but", "and", "or", "if", "while",
    "this", "that", "these", "those", "it", "its", "he", "she", "they",
    "them", "we", "you", "i", "me", "my", "your", "our", "his", "her",
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
    "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
    "们", "那", "什么", "怎么", "如果", "因为", "所以", "但是",
    "可以", "这个", "那个", "已经", "还是", "或者", "虽然", "然后",
    "并且", "而且", "不过", "只是", "就是", "的话", "不能", "不要",
}


def _tokenize(text: str) -> list[str]:
    """Tokenize text into words (handles English + basic Chinese segmentation)."""
    # Split on non-word characters, keep only alphabetic + CJK
    tokens = re.findall(r"[a-zA-Z\u4e00-\u9fff]+", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _STOP_WORDS]


# ── Keyword extraction ──────────────────────────────────


def extract_keywords(text: str, top_k: int = 10) -> list[dict[str, Any]]:
    """Extract top keywords using TF-IDF-like scoring.

    Returns:
        List of {keyword, score, count}.
    """
    tokens = _tokenize(text)
    if not tokens:
        return []

    # Term frequency
    tf = Counter(tokens)
    total = len(tokens)

    # Simple TF-IDF: TF * log(N/DF) — approximate with length-based weighting
    keywords = []
    for word, count in tf.most_common(top_k * 2):
        # Score: frequency normalized by word length (longer words = more specific)
        score = (count / total) * (1 + math.log(len(word)))
        keywords.append({"keyword": word, "score": round(score, 4), "count": count})

    keywords.sort(key=lambda k: k["score"], reverse=True)
    return keywords[:top_k]


def suggest_tags(text: str, max_tags: int = 8) -> list[str]:
    """Auto-suggest tags based on content analysis.

    Uses keyword extraction + common knowledge domain patterns.
    """
    keywords = extract_keywords(text, top_k=15)
    tags = [k["keyword"] for k in keywords[:max_tags]]

    # Domain detection
    lower = text.lower()
    domain_signals: dict[str, list[str]] = {
        "machine-learning": ["neural", "training", "model", "gradient", "loss", "accuracy", "dataset"],
        "programming": ["function", "class", "code", "api", "import", "def ", "return"],
        "design": ["color", "layout", "typography", "ui", "ux", "font", "spacing"],
        "psychology": ["cognitive", "behavior", "memory", "learning", "bias", "emotion"],
        "data-science": ["data", "analysis", "visualization", "statistics", "pipeline"],
        "devops": ["docker", "deploy", "ci", "cd", "pipeline", "kubernetes"],
    }

    for domain, signals in domain_signals.items():
        if any(s in lower for s in signals):
            tags.insert(0, domain)

    return list(dict.fromkeys(tags))[:max_tags]  # dedup preserve order


# ── Atomicity detection ─────────────────────────────────


def detect_atomicity(text: str) -> dict[str, Any]:
    """Zettelkasten atomic note check: does this note contain ONE idea?

    Returns:
        {is_atomic, topic_count, suggested_splits, confidence}.
    """
    tokens = _tokenize(text)
    if len(tokens) < 30:
        return {"is_atomic": True, "topic_count": 1, "suggested_splits": [], "confidence": 0.9}

    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]

    # Count distinct topic shifts (via heading analysis)
    headings = re.findall(r"^#{1,4}\s+(.+)", text, re.MULTILINE)
    topic_count = max(1, len(headings))

    # Check for multiple "also", "additionally", "furthermore" signals
    shift_markers = re.findall(
        r"\b(also|additionally|furthermore|moreover|another|separately|secondly|thirdly)\b",
        text.lower(),
    )

    total_topics = topic_count + len(shift_markers)

    if total_topics <= 1:
        status = "atomic"
        confidence = 0.85
    elif total_topics <= 3:
        status = "mostly_atomic"
        confidence = 0.5
    else:
        status = "multi_topic"
        confidence = 0.2

    suggested_splits = []
    if status != "atomic" and headings:
        suggested_splits = [h for h in headings[:5]]

    return {
        "is_atomic": status == "atomic",
        "topic_count": total_topics,
        "status": status,
        "suggested_splits": suggested_splits,
        "confidence": round(confidence, 2),
    }


# ── Progressive summarization ───────────────────────────


def progressive_summarize(text: str) -> dict[str, Any]:
    """Generate 4-layer progressive summary (Tiago Forte method).

    Layer 1: Full text (original)
    Layer 2: Bold passages (sentences with key signals)
    Layer 3: Highlighted (most important sentences)
    Layer 4: Executive summary (1-2 sentence gist)

    Returns:
        Dict with layers 1-4.
    """
    sentences = re.split(r"(?<=[.!?。！？])\s+", text)
    if len(sentences) < 2:
        return {
            "layer_1_full": text,
            "layer_2_bold": text,
            "layer_3_highlight": text,
            "layer_4_executive": text,
        }

    # Layer 2: Bold — sentences with strong signals
    bold_signals = [
        "important", "key", "critical", "essential", "significant",
        "核心", "关键", "重要", "必须", "注意",
        "definition", "defined", "means", "refers",
        "定义", "是指", "称为",
        "therefore", "thus", "consequently", "hence",
        "因此", "所以", "总之",
    ]
    bold_sentences = [
        s for s in sentences
        if any(sig in s.lower() for sig in bold_signals)
    ]

    # Layer 3: Highlight — top 30% by keyword density
    scored = []
    for s in sentences:
        kw = extract_keywords(s, top_k=5)
        score = sum(k["score"] for k in kw)
        scored.append((s, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    highlight_count = max(1, len(sentences) // 3)
    highlighted = [s for s, _ in scored[:highlight_count]]

    # Layer 4: Executive — first + last sentence heuristic
    executive = sentences[0]
    if len(sentences) > 1:
        last = sentences[-1]
        if len(last) > 20 and last != executive:
            executive += " " + last
    if len(executive) > 300:
        executive = executive[:300] + "..."

    return {
        "layer_1_full": text,
        "layer_2_bold": " ".join(bold_sentences[:5]) if bold_sentences else sentences[0],
        "layer_3_highlight": " ".join(highlighted[:3]),
        "layer_4_executive": executive,
    }
