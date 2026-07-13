"""Tests for Knowledge-Base context_pack module."""

from knowledge_base.context_pack import build_context_pack


class TestContextPack:
    def test_build_basic_pack(self):
        ctx = build_context_pack(
            goal="Test goal for context pack generation",
            sources=["doc_001", "card_001"],
            constraints=["quarantine first", "no direct write"],
        )
        assert ctx.goal == "Test goal for context pack generation"
        assert len(ctx.sources) == 2
        assert "doc_001" in ctx.sources
        assert "quarantine first" in ctx.constraints
        assert ctx.context_id.startswith("ctx_")

    def test_pack_without_constraints(self):
        ctx = build_context_pack(
            goal="Simple goal",
            sources=["doc_001"],
            constraints=[],
        )
        assert ctx.goal == "Simple goal"
        assert ctx.constraints == []

    def test_pack_token_budget(self):
        ctx = build_context_pack(
            goal="Token budget test",
            sources=["doc_001"],
            constraints=["keep it short"],
        )
        d = ctx.to_dict()
        assert "context_id" in d
        assert "goal" in d
        assert "sources" in d
        assert "constraints" in d
