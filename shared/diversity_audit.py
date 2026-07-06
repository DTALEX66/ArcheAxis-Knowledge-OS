"""Content diversity analyzer — adapted from Obsidian-Assistance v5 course_diversity_audit.

Analyzes KB content for modality diversity (images, tables, mermaid, code, callouts)
and provides a diversity health score.

Adapted from: scripts/v5/course_diversity_audit.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import select_all  # noqa: E402

# Modality detection patterns
MODALITY_PATTERNS: dict[str, re.Pattern] = {
    "images": re.compile(r"!\[\[|!\[[^\]]*\]\(|\.png|\.jpg|\.webp", re.IGNORECASE),
    "tables": re.compile(r"^\s*\|.+\|\s*$", re.MULTILINE),
    "mermaid": re.compile(r"```mermaid"),
    "code": re.compile(r"```(?!mermaid|dataview)"),
    "dataview": re.compile(r"```dataview"),
    "tasks": re.compile(r"^\s*- \[[ xX]\]", re.MULTILINE),
    "callouts": re.compile(r"^> \[![A-Za-z]", re.MULTILINE),
    "wikilinks": re.compile(r"\[\[[^\]]+\]\]"),
    "headings": re.compile(r"^#{1,4}\s", re.MULTILINE),
    "lists": re.compile(r"^\s*[-*+]\s", re.MULTILINE),
    "blockquotes": re.compile(r"^>\s", re.MULTILINE),
    "math": re.compile(r"\$\$|\$[^$]+\$"),
}


def analyze_diversity(doc_id: str) -> dict[str, Any]:
    """Analyze content modality diversity for a document or card.

    Returns:
        {doc_id, modalities: {type: count}, diversity_score, status}.
    """
    from shared.storage import select_one

    doc = select_one("kb_documents", doc_id)
    if not doc:
        doc = select_one("kb_cards", doc_id)
    if not doc:
        return {"error": "not found"}

    content = doc.get("content", "")
    modalities: dict[str, int] = {}
    for name, pattern in MODALITY_PATTERNS.items():
        count = len(pattern.findall(content))
        if count > 0:
            modalities[name] = count

    # Diversity score: number of distinct modalities present
    distinct = len(modalities)
    if distinct >= 6:
        score = 100
        status = "rich"
    elif distinct >= 4:
        score = 70
        status = "good"
    elif distinct >= 2:
        score = 40
        status = "basic"
    else:
        score = 10
        status = "text_only"

    suggestions = []
    if "images" not in modalities:
        suggestions.append("Add visual elements (images, diagrams)")
    if "tables" not in modalities:
        suggestions.append("Add structured data tables")
    if "mermaid" not in modalities:
        suggestions.append("Add Mermaid diagrams for processes")
    if "code" not in modalities:
        suggestions.append("Add code examples where relevant")

    return {
        "doc_id": doc_id,
        "title": doc.get("title", "")[:60],
        "modalities": modalities,
        "distinct_modalities": distinct,
        "diversity_score": score,
        "status": status,
        "suggestions": suggestions[:3],
    }


def diversity_radar(limit: int = 20) -> list[dict[str, Any]]:
    """Scan all documents and rank by diversity score.

    Returns list sorted by diversity (richest first).
    """
    docs = select_all("kb_documents", limit=100)
    cards = select_all("kb_cards", limit=100)
    all_items = list(docs) + list(cards)

    results = []
    for item in all_items:
        iid = item.get("id") or item.get("card_id", "")
        if not iid:
            continue
        analysis = analyze_diversity(iid)
        if "error" not in analysis:
            results.append(analysis)

    results.sort(key=lambda r: r["diversity_score"], reverse=True)
    return results[:limit]
