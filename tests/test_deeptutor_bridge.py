"""DeepTutor bridge rebuilds projections from canonical truth only."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.contracts.source_anchor_v2 import AnchorV2, SourceObjectV2, TextQuoteSelector
from app.evidence.source_store_v2 import SourceStoreV2
from app.integrations.deeptutor_bridge import DeepTutorBridge
from app.learning.event_store import LearningEvent, append_event
from shared.migration_runner import MigrationOperator


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    runtime = project / ".project-local/task-runtime"
    runtime.mkdir(parents=True)
    db = runtime / "workspace.sqlite"
    db.touch()
    MigrationOperator(db_path=db, backup_dir=runtime / "backups").apply(
        "knowledge-governance.sqlite"
    )
    source_store = SourceStoreV2(db)
    source_store.put_source(
        SourceObjectV2(
            source_id="source-a",
            version=1,
            sha256=hashlib.sha256(b"content").hexdigest(),
            byte_size=7,
            media_type="text/plain",
            rights_status="owned",
            original_retained=True,
            created_at="2026-08-27T00:00:00+00:00",
        )
    )
    source_store.put_anchor(
        AnchorV2(
            anchor_id="anchor-a",
            source_id="source-a",
            source_version=1,
            selector=TextQuoteSelector(exact="content"),
            created_at="2026-08-27T00:01:00+00:00",
        )
    )
    append_event(
        db,
        LearningEvent(
            event_id="event-a",
            learner_id="learner-a",
            node_id="node-a",
            event_type="review",
            payload={"correct": True},
            occurred_at="2026-08-27T00:02:00+00:00",
            idempotency_key="review-a",
            source_system="archeaxis",
        ),
    )
    return project, db


def test_projection_is_rebuildable_after_complete_sidecar_deletion(tmp_path: Path) -> None:
    project, db = _setup(tmp_path)
    bridge = DeepTutorBridge(project_root=project, db_path=db)

    first = bridge.rebuild_projection()
    projection = Path(first["projection_root"])
    assert first["counts"] == {"anchors": 1, "learning_events": 1, "sources": 1}
    assert (projection / "manifest.json").is_file()
    digest = first["digest"]

    shutil.rmtree(projection.parent)
    second = bridge.rebuild_projection()
    assert second["digest"] == digest
    assert Path(second["projection_root"]).is_dir()


def test_inbound_truth_claims_are_rejected_before_persistence(tmp_path: Path) -> None:
    project, db = _setup(tmp_path)
    bridge = DeepTutorBridge(project_root=project, db_path=db)

    with pytest.raises(ValueError, match="forbidden authority fields"):
        bridge.accept_event(
            {
                "event_id": "event-b",
                "learner_id": "learner-a",
                "node_id": "node-a",
                "event_type": "review",
                "idempotency_key": "review-b",
                "verified": True,
            }
        )


def test_allowed_inbound_learning_event_is_candidate_only_and_idempotent(
    tmp_path: Path,
) -> None:
    project, db = _setup(tmp_path)
    bridge = DeepTutorBridge(project_root=project, db_path=db)
    payload = {
        "event_id": "event-b",
        "learner_id": "learner-a",
        "node_id": "node-a",
        "event_type": "quiz_answer",
        "idempotency_key": "quiz-b",
        "outcome": {"correct": False, "question_id": "q-1"},
    }

    first = bridge.accept_event(payload)
    second = bridge.accept_event(payload)
    assert first == second
    assert first["status"] == "candidate"
    assert first["verified"] is False


def test_projection_root_cannot_escape_project_runtime(tmp_path: Path) -> None:
    project, db = _setup(tmp_path)
    with pytest.raises(ValueError, match="project runtime"):
        DeepTutorBridge(project_root=project, db_path=db, projection_root=tmp_path / "outside")
