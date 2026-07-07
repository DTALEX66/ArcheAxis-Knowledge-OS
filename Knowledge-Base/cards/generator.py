"""Card generator from documents — converts ingested documents into knowledge cards.

P2-1: provides a simple heuristic-based generator for creating cards from
document content.  Designed to be lightweight and runnable locally without LLM.
"""

from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from cards import KnowledgeCard  # noqa: E402


def generate_from_markdown(
    content: str,
    source_doc_id: str = "",
    max_cards: int = 10,
) -> list[KnowledgeCard]:
    """Generate knowledge cards from markdown content.

    Splits on headings (##, ###) and creates one card per section.
    """
    cards = []
    # Split on markdown headings
    sections = re.split(r"\n(?=#{2,3}\s)", content)
    count = 0

    for section in sections:
        if count >= max_cards:
            break
        section = section.strip()
        if not section or len(section) < 30:
            continue

        # Extract title from the first heading
        title_match = re.match(r"^#{2,3}\s+(.+)$", section, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else f"Card {count + 1}"

        card = KnowledgeCard(
            card_id=f"card_{uuid.uuid4().hex[:12]}",
            title=title[:120],
            content=section[:2000],
            source_ids=[source_doc_id] if source_doc_id else [],
            tags=[],
        )
        cards.append(card)
        count += 1

    return cards


def generate_qa_cards(
    qa_pairs: list[dict[str, str]],
    source_doc_id: str = "",
) -> list[KnowledgeCard]:
    """Generate cards from Q&A pairs.

    Args:
        qa_pairs: list of {question, answer} dicts.
    """
    cards = []
    for qa in qa_pairs:
        card = KnowledgeCard(
            card_id=f"card_{uuid.uuid4().hex[:12]}",
            title=qa.get("question", "")[:120],
            content=f"**Q:** {qa.get('question', '')}\n\n**A:** {qa.get('answer', '')}",
            source_ids=[source_doc_id] if source_doc_id else [],
            tags=["qa"],
        )
        cards.append(card)
    return cards
