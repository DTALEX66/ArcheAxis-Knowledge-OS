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
