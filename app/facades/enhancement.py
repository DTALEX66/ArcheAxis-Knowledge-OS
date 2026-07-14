"""Public enhancement facade over existing local candidate generators."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from knowledge_base.cards.generator import generate_from_markdown
from shared.auto_tagger import progressive_summarize
from shared.content_quality import audit_markdown_quality


class EnhancementArtifact(BaseModel):
    """Heuristic enhancement output that still requires review."""

    status: Literal["candidate"] = "candidate"
    summary: dict[str, Any]
    cards: list[dict[str, Any]]
    quality: dict[str, Any]


def enhance_artifact(
    content: str,
    *,
    source_doc_id: str = "",
    max_cards: int = 10,
    known_targets: set[str] | None = None,
) -> EnhancementArtifact:
    """Build an in-memory candidate without persistence, network, or LLM calls."""
    summary = progressive_summarize(content)
    cards = [
        card.to_dict()
        for card in generate_from_markdown(
            content,
            source_doc_id=source_doc_id,
            max_cards=max_cards,
        )
    ]
    quality = audit_markdown_quality(content, known_targets=known_targets)
    return EnhancementArtifact(summary=summary, cards=cards, quality=quality)
