"""AXW-053: transformation provenance tests.

Verifies:
- transformation records carry source/target/tool/version/loss provenance;
- outputs are candidates by default (unreviewed → not in active set);
- review flips a transformation into the active projection;
- supersede chains preserve history (append-only);
- invalid input fails closed.
"""

from __future__ import annotations

from app.knowledge.transform import (
    TransformError,
    active_transformations,
    provenance_of,
    record_transformation,
    review_transformation,
)


def _mkdb(tmp_path) -> str:
    return str(tmp_path / "transform.sqlite")


def test_record_candidate_by_default(tmp_path) -> None:
    db = _mkdb(tmp_path)
    tr = record_transformation(
        db,
        source_type="learning",
        source_id="card_1",
        target_type="ai_asset",
        target_id="unit_1",
        tool="closed-loop",
        tool_version="1.0.0",
        loss_notes="dropped formatting",
    )
    assert tr.is_candidate is True
    assert tr.loss_notes == "dropped formatting"
    # Unreviewed → excluded from the active projection.
    assert active_transformations(db, target_type="ai_asset") == []


def test_review_flips_into_active_set(tmp_path) -> None:
    db = _mkdb(tmp_path)
    tr = record_transformation(
        db,
        source_type="learning",
        source_id="card_1",
        target_type="ai_asset",
        target_id="unit_1",
        tool="closed-loop",
    )
    review_transformation(db, transform_id=tr.transform_id, reviewer="human1", approved=True)
    active = active_transformations(db, target_type="ai_asset")
    assert len(active) == 1
    assert active[0].reviewer == "human1"
    assert active[0].reviewed is True


def test_supersede_preserves_history(tmp_path) -> None:
    db = _mkdb(tmp_path)
    first = record_transformation(
        db,
        source_type="learning",
        source_id="card_1",
        target_type="ai_asset",
        target_id="unit_1",
        tool="v1-pipeline",
    )
    second = record_transformation(
        db,
        source_type="learning",
        source_id="card_1",
        target_type="ai_asset",
        target_id="unit_1",
        tool="v2-pipeline",
        supersede=first.transform_id,
    )
    review_transformation(db, transform_id=second.transform_id, reviewer="human")
    history = provenance_of(db, target_type="ai_asset", target_id="unit_1")
    assert len(history) == 2  # nothing removed
    by_id = {h.transform_id: h for h in history}
    assert by_id[first.transform_id].superseded_by == second.transform_id
    # Only the reviewed, non-superseded one is active.
    active = active_transformations(db, target_type="ai_asset")
    assert [a.transform_id for a in active] == [second.transform_id]


def test_provenance_records_tool_and_loss(tmp_path) -> None:
    db = _mkdb(tmp_path)
    record_transformation(
        db,
        source_type="knowledge",
        source_id="knowledge_1",
        target_type="lesson",
        target_id="lesson_9",
        tool="transform-cli",
        tool_version="0.3.2",
        loss_notes="dropped citations",
    )
    history = provenance_of(db, target_type="lesson", target_id="lesson_9")
    assert len(history) == 1
    assert history[0].tool == "transform-cli"
    assert history[0].tool_version == "0.3.2"
    assert history[0].loss_notes == "dropped citations"
    assert history[0].source_id == "knowledge_1"


def test_invalid_input_fails_closed(tmp_path) -> None:
    db = _mkdb(tmp_path)
    for kwargs in (
        {"source_type": "banana", "source_id": "s", "target_type": "lesson", "target_id": "t", "tool": "x"},
        {"source_type": "knowledge", "source_id": "", "target_type": "lesson", "target_id": "t", "tool": "x"},
        {"source_type": "knowledge", "source_id": "s", "target_type": "lesson", "target_id": "", "tool": "x"},
        {"source_type": "knowledge", "source_id": "s", "target_type": "lesson", "target_id": "t", "tool": ""},
    ):
        try:
            record_transformation(db, **kwargs)
            raise AssertionError(f"expected TransformError for {kwargs}")
        except TransformError:
            pass
    try:
        review_transformation(db, transform_id="ghost", reviewer="h")
        raise AssertionError("expected TransformError")
    except TransformError as exc:
        assert "not found" in str(exc)
