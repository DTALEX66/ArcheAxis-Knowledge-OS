"""Server-owned orchestration for one governed Cognitive Workspace case."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.knowledge.closed_loop import (
    approve_learning_artifact,
    audit_closed_loop,
    record_practice_evidence,
    start_learning_candidate,
)
from app.knowledge.promotion import (
    ResearchKnowledgeApproval,
    promote_research_package_to_candidates,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def promote_research(*, command_id: str, package_id: str, reviewer_id: str, rationale: str, db_path: str | Path) -> dict:
    receipt = promote_research_package_to_candidates(
        ResearchKnowledgeApproval(
            approval_id=command_id,
            package_id=package_id,
            reviewer_id=reviewer_id,
            decision="approved",
            rationale=rationale,
            reviewed_at=now_utc(),
        ),
        db_path=db_path,
    )
    return {
        "command_id": command_id,
        "promotion_id": receipt.promotion_id,
        "package_id": receipt.package_id,
        "unit_ids": [unit.unit_id for unit in receipt.units],
        "status": receipt.lifecycle_status,
    }


def start_learning(*, command_id: str, unit_id: str, reviewer_id: str, rationale: str, db_path: str | Path) -> dict:
    artifact = start_learning_candidate(
        unit_id=unit_id,
        approval_id=command_id,
        reviewer_id=reviewer_id,
        rationale=rationale,
        reviewed_at=now_utc(),
        db_path=db_path,
    )
    return {"command_id": command_id, "artifact_id": artifact.artifact_id, "status": "candidate"}


def approve_learning(*, command_id: str, artifact_id: str, reviewer_id: str, db_path: str | Path) -> dict:
    card_ids = approve_learning_artifact(
        artifact_id=artifact_id,
        command_id=command_id,
        reviewer_id=reviewer_id,
        reviewed_at=now_utc(),
        db_path=db_path,
    )
    return {"command_id": command_id, "artifact_id": artifact_id, "card_ids": card_ids, "status": "approved"}


def record_practice(*, command_id: str, artifact_id: str, quality: int, db_path: str | Path) -> dict:
    result = record_practice_evidence(
        artifact_id=artifact_id,
        command_id=command_id,
        quality=quality,
        recorded_at=now_utc(),
        db_path=db_path,
    )
    return {
        "command_id": command_id,
        "artifact_id": artifact_id,
        "mastered": result.mastery_signal.is_mastered,
        "machine_candidate_id": result.machine_knowledge.unit_id if result.machine_knowledge else None,
    }


def case_audit(*, artifact_id: str, db_path: str | Path) -> dict:
    return {
        "artifact_id": artifact_id,
        "events": [
            {"event_type": event.event_type, "occurred_at": event.occurred_at}
            for event in audit_closed_loop(artifact_id, db_path=db_path)
        ],
    }
