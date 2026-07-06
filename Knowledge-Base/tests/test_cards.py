"""Tests for Knowledge-Base cards module."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

import pytest
from cards import KnowledgeCard


class TestKnowledgeCard:
    def test_card_creation(self):
        card = KnowledgeCard(
            card_id="card_001",
            title="Test Card",
            content="Test content for knowledge card",
            source_ids=["src_1", "src_2"],
            tags=["test", "knowledge"],
        )
        assert card.card_id == "card_001"
        assert card.title == "Test Card"
        assert len(card.source_ids) == 2
        assert card.tags == ["test", "knowledge"]

    def test_card_to_dict(self):
        card = KnowledgeCard(
            card_id="card_002",
            title="Dict Test",
            content="Testing to_dict serialization",
        )
        d = card.to_dict()
        assert d["card_id"] == "card_002"
        assert d["title"] == "Dict Test"
        assert d["source_ids"] == []
        assert d["tags"] == []
        assert "content" in d

    def test_card_missing_title(self):
        """KnowledgeCard has defaults, so empty init is allowed and fields default to ''."""
        card = KnowledgeCard()
        assert card.card_id == ""
        assert card.title == ""

    def test_card_empty_content_allowed(self):
        """Empty content should be allowed (draft cards)."""
        card = KnowledgeCard(card_id="card_004", title="Draft", content="")
        assert card.content == ""
