"""Candidate-only LearningArtifact projection from reviewed Knowledge units."""
from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.v1 import LearningArtifactV1
from shared import knowledge_governance_migration


class KnowledgeLearningArtifactApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: str = Field(min_length=1)
    unit_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


def _artifact_id(approval_id: str) -> str:
    return "knowledge-learning-artifact_" + sha256(approval_id.encode()).hexdigest()[:24]


def create_candidate_learning_artifact(
    approval: KnowledgeLearningArtifactApproval, *, db_path: str | Path
) -> LearningArtifactV1:
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT artifact_json FROM knowledge_candidate_learning_artifacts_v1 WHERE approval_id=?",
                (approval.approval_id,),
            ).fetchone()
            if existing is not None:
                connection.commit()
                return LearningArtifactV1.model_validate_json(existing["artifact_json"])
            row = connection.execute(
                "SELECT properties_json, provenance_json FROM knowledge_candidate_units_v1 WHERE id=? AND unit_type='research_claim' AND lifecycle_status='candidate'",
                (approval.unit_id,),
            ).fetchone()
            if row is None:
                raise ValueError("learning artifact requires an active candidate research_claim")
            properties = json.loads(row["properties_json"])
            provenance = json.loads(row["provenance_json"])
            artifact = LearningArtifactV1(
                schema_version="1.0.0", artifact_id=_artifact_id(approval.approval_id),
                artifact_type="enhancement_bundle",
                source_record_ids=list(properties["source_ids"]),
                summary={"knowledge_unit_id": approval.unit_id, "statement": properties["statement"], "provenance": provenance},
                cards=[{"front": properties["statement"], "back": "Review the cited evidence and explain the claim.", "source_unit_id": approval.unit_id}],
                quality={"reviewer_id": approval.reviewer_id, "approval_id": approval.approval_id, "requires_card_review": True},
                status="candidate", provenance_status="server_verified", requires_human_review=True,
                created_at=approval.reviewed_at,
            )
            connection.execute(
                "INSERT INTO knowledge_candidate_learning_artifacts_v1 VALUES (?, ?, ?, ?, ?, ?, 'candidate', ?)",
                (artifact.artifact_id, approval.unit_id, approval.approval_id, approval.reviewer_id, approval.rationale, artifact.model_dump_json(), approval.reviewed_at),
            )
            connection.commit()
            return artifact
        except Exception:
            connection.rollback()
            raise


def approve_artifact_cards(
    artifact_id: str, *, command_id: str, reviewer_id: str, reviewed_at: str, db_path: str | Path
) -> list[dict[str, str]]:
    """Atomically persist an append-only approval receipt and project reviewed cards."""
    if not command_id:
        raise ValueError("learning approval requires command_id")
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing_event = connection.execute(
                "SELECT artifact_id, reviewer_id FROM learning_approval_events_v1 WHERE command_id=?",
                (command_id,),
            ).fetchone()
            if existing_event is not None and tuple(str(value) for value in existing_event) != (
                artifact_id,
                reviewer_id,
            ):
                raise RuntimeError("learning approval command id conflicts with an existing receipt")
            row = connection.execute(
                "SELECT artifact_json, status FROM knowledge_candidate_learning_artifacts_v1 WHERE id=?",
                (artifact_id,),
            ).fetchone()
            if row is None:
                raise ValueError("artifact approval requires an existing candidate")
            artifact = LearningArtifactV1.model_validate_json(row["artifact_json"])
            if artifact.provenance_status != "server_verified":
                raise ValueError("artifact card projection requires server_verified provenance")
            if existing_event is None:
                event_id = "learning_approval_" + sha256(command_id.encode()).hexdigest()[:24]
                connection.execute(
                    "INSERT INTO learning_approval_events_v1 "
                    "(id, artifact_id, command_id, reviewer_id, decision, rationale, reviewed_at, created_at) "
                    "VALUES (?, ?, ?, ?, 'approved', 'explicit learning approval', ?, ?)",
                    (event_id, artifact_id, command_id, reviewer_id, reviewed_at, reviewed_at),
                )
            projected: list[dict[str, str]] = []
            for index, card in enumerate(artifact.cards):
                card_id = f"{artifact_id}-card-{index}"
                title, content = str(card["front"]), str(card["back"])
                connection.execute(
                    "INSERT OR IGNORE INTO kb_cards(id, title, content, source_ids_json, tags_json, review_status, created_at) VALUES (?, ?, ?, ?, '[]', 'draft', ?)",
                    (card_id, title, content, json.dumps(artifact.source_record_ids), reviewed_at),
                )
                projected.append({"id": card_id, "review_status": "draft"})
            connection.commit()
            return projected
        except Exception:
            connection.rollback()
            raise
