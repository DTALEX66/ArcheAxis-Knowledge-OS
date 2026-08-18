"""Tests for D4 episode ingestion + auto-expiry (Graphiti absorption)."""
from __future__ import annotations

import pytest

from app.memory.temporal_graph import (
    TemporalGraphError,
    active_facts,
    expire_facts,
    ingest_episode,
)


def test_ingest_episode_batch(tmp_path):
    db = tmp_path / "tg.sqlite"
    facts = ingest_episode(
        db, episode_id="ep-1", source="session-1",
        facts=[
            {"statement": "A 支持 B", "entity": "A", "predicate": "supports", "object": "B"},
            {"statement": "C 依赖 A", "entity": "C", "predicate": "requires", "object": "A"},
        ],
    )
    assert len(facts) == 2
    assert all(f.ingested_at is not None for f in facts)
    assert all("ep-1" in f.source for f in facts)
    assert len(active_facts(db)) == 2


def test_ingest_episode_validation(tmp_path):
    db = tmp_path / "tg.sqlite"
    with pytest.raises(TemporalGraphError, match="episode_id"):
        ingest_episode(db, episode_id="", source="s", facts=[{"statement": "x", "entity": "e", "predicate": "p", "object": "o"}])
    with pytest.raises(TemporalGraphError, match="facts"):
        ingest_episode(db, episode_id="e", source="s", facts=[])


def test_expire_facts_marks_and_hides(tmp_path):
    db = tmp_path / "tg2.sqlite"
    from app.memory.temporal_graph import add_fact
    add_fact(db, statement="旧 API", entity="api", predicate="works", object="yes",
             source="s", valid_from="2020-01-01T00:00:00+00:00",
             valid_to="2024-12-31T00:00:00+00:00")
    count = expire_facts(db, as_of="2026-08-18T00:00:00+00:00")
    assert count == 1
    assert active_facts(db) == []
