"""AXW-024C: versioned evidence relations and human adjudication tests.

Verifies:
- relations are append-only: superseding never overwrites history;
- active-relations projection excludes superseded versions;
- conflict detection works on the active set;
- adjudication is recorded with reviewer attribution and append-only;
- invalid input fails closed.
"""

from __future__ import annotations

from app.evidence.relations import (
    RelationError,
    active_relations,
    adjudicate,
    has_conflict,
    list_adjudications,
    list_relations,
    record_relation,
)


def _mkdb(tmp_path) -> str:
    return str(tmp_path / "relations.sqlite")


def test_record_and_active_projection(tmp_path) -> None:
    db = _mkdb(tmp_path)
    rel = record_relation(
        db, claim_id="c1", evidence_id="e1", kind="supports", actor="tester", reviewed=True
    )
    assert rel.active is True
    assert list_relations(db, claim_id="c1") == [rel]
    assert active_relations(db, claim_id="c1") == [rel]


def test_supersede_preserves_history(tmp_path) -> None:
    db = _mkdb(tmp_path)
    first = record_relation(
        db, claim_id="c1", evidence_id="e1", kind="supports", actor="tester"
    )
    second = record_relation(
        db,
        claim_id="c1",
        evidence_id="e1",
        kind="refutes",
        actor="reviewer2",
        supersede=first.relation_id,
    )
    history = list_relations(db, claim_id="c1")
    assert len(history) == 2  # nothing silently removed
    by_id = {r.relation_id: r for r in history}
    assert by_id[first.relation_id].superseded_by == second.relation_id
    assert by_id[first.relation_id].active is False
    assert second.active is True
    assert active_relations(db, claim_id="c1") == [second]


def test_cannot_supersede_twice(tmp_path) -> None:
    db = _mkdb(tmp_path)
    first = record_relation(db, claim_id="c1", evidence_id="e1", kind="supports", actor="a")
    record_relation(db, claim_id="c1", evidence_id="e1", kind="refutes", actor="b", supersede=first.relation_id)
    try:
        record_relation(db, claim_id="c1", evidence_id="e1", kind="qualifies", actor="c", supersede=first.relation_id)
        raise AssertionError("expected RelationError")
    except RelationError as exc:
        assert "already superseded" in str(exc)


def test_conflict_detection_on_active_set(tmp_path) -> None:
    db = _mkdb(tmp_path)
    record_relation(db, claim_id="c1", evidence_id="e1", kind="supports", actor="a")
    record_relation(db, claim_id="c1", evidence_id="e2", kind="refutes", actor="b")
    assert has_conflict(db, claim_id="c1") is True
    # Superseding the refutes removes the conflict from the active set.
    active = active_relations(db, claim_id="c1")
    refutes = [r for r in active if r.kind == "refutes"][0]
    record_relation(db, claim_id="c1", evidence_id="e2", kind="qualifies", actor="c", supersede=refutes.relation_id)
    assert has_conflict(db, claim_id="c1") is False


def test_adjudication_append_only_with_reviewer(tmp_path) -> None:
    db = _mkdb(tmp_path)
    first = adjudicate(db, claim_id="c1", decision="support", reviewer="human1", note="checked source A")
    second = adjudicate(db, claim_id="c1", decision="refute", reviewer="human2")
    history = list_adjudications(db, claim_id="c1")
    assert [h["adjudication_id"] for h in history] == [first["adjudication_id"], second["adjudication_id"]]
    assert history[0]["reviewer"] == "human1"
    assert history[0]["note"] == "checked source A"
    assert history[1]["decision"] == "refute"


def test_invalid_input_fails_closed(tmp_path) -> None:
    db = _mkdb(tmp_path)
    for kwargs in (
        {"claim_id": "", "evidence_id": "e1", "kind": "supports", "actor": "a"},
        {"claim_id": "c1", "evidence_id": "", "kind": "supports", "actor": "a"},
        {"claim_id": "c1", "evidence_id": "e1", "kind": "banana", "actor": "a"},
        {"claim_id": "c1", "evidence_id": "e1", "kind": "supports", "actor": ""},
    ):
        try:
            record_relation(db, **kwargs)
            raise AssertionError(f"expected RelationError for {kwargs}")
        except RelationError:
            pass
    try:
        adjudicate(db, claim_id="c1", decision="maybe", reviewer="h")
        raise AssertionError("expected RelationError")
    except RelationError as exc:
        assert "invalid adjudication decision" in str(exc)
