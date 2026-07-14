from __future__ import annotations

from knowledge_base.cards.generator import generate_from_markdown
from shared.auto_tagger import progressive_summarize
from shared.content_quality import audit_markdown_quality

_CONTENT = """## Evidence-first enhancement
The key rule is that generated summaries and cards remain candidates until human review. [[Known Target]]
"""


def _stable_card(card: dict) -> dict:
    return {key: value for key, value in card.items() if key != "card_id"}


def test_enhancement_facade_is_exported_from_public_package():
    import app.facades as facades
    from app.facades.enhancement import EnhancementArtifact, enhance_artifact

    assert facades.EnhancementArtifact is EnhancementArtifact
    assert facades.enhance_artifact is enhance_artifact


def test_enhancement_facade_builds_candidate_from_real_delegates():
    from app.facades.enhancement import enhance_artifact

    result = enhance_artifact(
        _CONTENT,
        source_doc_id="doc_tp13",
        known_targets={"Known Target"},
    )

    assert result.status == "candidate"
    assert result.summary["layer_4_executive"]
    assert len(result.cards) == 1
    assert result.cards[0]["card_id"].startswith("card_")
    assert result.cards[0]["title"] == "Evidence-first enhancement"
    assert result.cards[0]["source_ids"] == ["doc_tp13"]
    assert result.cards[0]["review_status"] == "draft"
    assert result.quality["status"] == "clean_by_static_rules"
    assert "do not prove" in result.quality["limitations"]


def test_enhancement_facade_preserves_existing_delegate_results():
    from app.facades.enhancement import enhance_artifact

    direct_summary = progressive_summarize(_CONTENT)
    direct_cards = generate_from_markdown(_CONTENT, source_doc_id="doc_tp13")
    direct_quality = audit_markdown_quality(_CONTENT, {"Known Target"})

    result = enhance_artifact(
        _CONTENT,
        source_doc_id="doc_tp13",
        known_targets={"Known Target"},
    )

    assert result.summary == direct_summary
    assert [_stable_card(card) for card in result.cards] == [
        _stable_card(card.to_dict()) for card in direct_cards
    ]
    assert result.quality == direct_quality
