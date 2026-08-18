"""Tests for the temporal knowledge graph (Graphiti absorption)."""
from __future__ import annotations

import pytest

from app.memory.temporal_graph import (
    active_facts,
    add_fact,
    conflict_report,
    fact_history,
    record_contradiction,
    resolve_current,
    supersede_fact,
    TemporalGraphError,
)


def test_add_and_active(tmp_path):
    db = tmp_path / "tg.sqlite"
    f = add_fact(db, statement="Photoshop 2025 supports UXP",
                 entity="photoshop", predicate="supports", object="uxp",
                 source="adobe-docs", valid_from="2025-01-01T00:00:00+00:00")
    assert f.version == 1 and f.is_current
    assert len(active_facts(db)) == 1


def test_supersede_creates_version_chain(tmp_path):
    db = tmp_path / "tg.sqlite"
    f1 = add_fact(db, statement="Photoshop 2025 supports UXP",
                  entity="photoshop", predicate="supports", object="uxp",
                  source="adobe-docs", valid_from="2025-01-01T00:00:00+00:00")
    f2 = supersede_fact(db, fact_id=f1.fact_id, statement="Photoshop 2027 changed UXP API",
                        source="adobe-docs-2027", valid_to=None)
    assert f2.version == 2
    assert f2.supersedes == f1.fact_id
    history = fact_history(db, entity="photoshop", predicate="supports")
    assert [h.version for h in history] == [1, 2]
    assert history[0].status == "superseded"
    current = resolve_current(db, entity="photoshop", predicate="supports")
    assert current is not None and current.version == 2


def test_expiry_removes_from_active(tmp_path):
    db = tmp_path / "tg.sqlite"
    add_fact(db, statement="old api", entity="api", predicate="works", object="yes",
             source="s", valid_from="2020-01-01T00:00:00+00:00",
             valid_to="2024-12-31T00:00:00+00:00")
    active = active_facts(db, as_of="2026-08-18T00:00:00+00:00")
    assert active == []
    # historical query still sees it before expiry
    old = active_facts(db, as_of="2023-06-01T00:00:00+00:00")
    assert len(old) == 1


def test_contradiction_marks_both(tmp_path):
    db = tmp_path / "tg.sqlite"
    a = add_fact(db, statement="x is true", entity="x", predicate="is", object="true", source="s1")
    b = add_fact(db, statement="x is false", entity="x", predicate="is", object="false", source="s2")
    record_contradiction(db, a.fact_id, b.fact_id)
    report = conflict_report(db, entity="x", predicate="is")
    assert report["contradiction_edges"]
    assert resolve_current(db, entity="x", predicate="is") is None  # both contested


def test_cannot_supersede_contradicted(tmp_path):
    db = tmp_path / "tg.sqlite"
    a = add_fact(db, statement="a", entity="e", predicate="p", object="1", source="s")
    b = add_fact(db, statement="b", entity="e2", predicate="p2", object="2", source="s")
    record_contradiction(db, a.fact_id, b.fact_id)
    with pytest.raises(TemporalGraphError, match="only active"):
        supersede_fact(db, fact_id=a.fact_id, statement="c", source="s")


def test_validation(tmp_path):
    db = tmp_path / "tg.sqlite"
    with pytest.raises(TemporalGraphError):
        add_fact(db, statement="", entity="e", predicate="p", object="o", source="s")
    with pytest.raises(TemporalGraphError):
        add_fact(db, statement="x", entity="e", predicate="p", object="o", source="s", confidence=2.0)
