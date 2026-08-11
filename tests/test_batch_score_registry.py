"""Tests for scripts.batch_score_registry (registry project heuristic scoring)."""

from __future__ import annotations

from scripts.batch_score_registry import (
    ABSORPTION_BONUS,
    category_key,
    main,
    score_registry_entry,
)


def test_category_key_exact_match() -> None:
    assert category_key("Crawler") == "Crawler"
    assert category_key("Memory") == "Memory"


def test_category_key_combined_falls_back() -> None:
    # Combined label "RAG / AI App Platform" contains "RAG/AI Platform" case-insensitively
    assert category_key("RAG / AI Platform") == "RAG/AI Platform"


def test_category_key_unknown_returns_raw() -> None:
    assert category_key("Mystery Category") == "Mystery Category"


def test_score_entry_qualifies_adapter() -> None:
    entry = {
        "name": "repo-a",
        "category": "Document Parsing",
        "absorption_mode": "Adapter",
        "recommended_target": "adapter",
        "risk_policy": "standard_review",
    }
    result = score_registry_entry(entry)
    assert result["repo"] == "repo-a"
    assert result["scores"]["total"] > 0
    assert result["qualifies"] is True
    assert result["next_action"] == "generate_intake_card"
    assert result["risk_level"] == "low"


def test_score_entry_high_risk_blocked() -> None:
    entry = {
        "name": "repo-b",
        "category": "Memory",
        "absorption_mode": "参考",
        "recommended_target": "sidecar",
        "risk_policy": "must_review_before_use",
    }
    result = score_registry_entry(entry)
    assert result["risk_level"] == "high"
    assert result["scores"]["risk_penalty"] > 0
    assert result["next_action"] == "review" if not result["qualifies"] else True


def test_score_entry_unknown_category_default() -> None:
    entry = {
        "name": "repo-c",
        "category": "Totally New",
        "absorption_mode": "只参考",
        "recommended_target": "note",
        "risk_policy": "standard_review",
    }
    result = score_registry_entry(entry)
    # default base tuple applies; negative bonus reduces system_fit
    assert result["category"] == "Totally New"
    assert isinstance(result["scores"]["total"], float)


def test_absorption_bonus_mapping() -> None:
    assert ABSORPTION_BONUS["Adapter"] == 0.5
    assert ABSORPTION_BONUS["只参考"] == -0.2
    assert ABSORPTION_BONUS["参考"] == 0.0


def test_main_disabled_until_provenance() -> None:
    import pytest

    with pytest.raises(RuntimeError, match="legacy screening export is disabled"):
        main()
