"""Candidate-only Knowledge version graph and conflict review service."""

from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from shared import knowledge_governance_migration


class KnowledgeVersionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=1)
    unit_id: str = Field(min_length=1)
    canonical_key: str = Field(min_length=1)
    parent_version_id: str | None = None
    content: dict[str, object]
    reviewer_id: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


class CandidateKnowledgeVersionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: str
    parent_version_id: str | None
    lifecycle_status: Literal["candidate", "conflict"]
    conflict_review_id: str | None


class KnowledgeVersionDeprecation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


def _stable_id(namespace: str, *parts: str) -> str:
    return f"{namespace}_{sha256(chr(0).join((namespace, *parts)).encode()).hexdigest()[:24]}"


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def register_candidate_knowledge_version(
    proposal: KnowledgeVersionProposal, *, db_path: str | Path
) -> CandidateKnowledgeVersionReceipt:
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database, live_wal=True)
    content_json = _dump(proposal.content)
    fingerprint = sha256(content_json.encode()).hexdigest()
    version_id = _stable_id("knowledge-version", proposal.proposal_id)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT parent_version_id, lifecycle_status, conflict_review_id FROM knowledge_candidate_versions_v1 WHERE id=?",
                (version_id,),
            ).fetchone()
            if existing is not None:
                connection.rollback()
                return CandidateKnowledgeVersionReceipt(
                    version_id=version_id,
                    parent_version_id=existing["parent_version_id"],
                    lifecycle_status=existing["lifecycle_status"],
                    conflict_review_id=existing["conflict_review_id"],
                )
            unit = connection.execute(
                "SELECT promotion_id, package_id, provenance_json FROM knowledge_candidate_units_v1 WHERE id=? AND lifecycle_status='candidate'",
                (proposal.unit_id,),
            ).fetchone()
            if unit is None:
                raise ValueError("version proposal requires an active candidate unit")
            previous = connection.execute(
                "SELECT id, content_fingerprint FROM knowledge_candidate_versions_v1 WHERE canonical_key=? ORDER BY created_at DESC, id DESC LIMIT 1",
                (proposal.canonical_key,),
            ).fetchone()
            if previous is None and proposal.parent_version_id is not None:
                raise ValueError("first version cannot declare a parent")
            if previous is not None and proposal.parent_version_id != previous["id"]:
                raise ValueError("new version must name the latest version as parent")
            conflict_id: str | None = None
            lifecycle = "candidate"
            if previous is not None and previous["content_fingerprint"] != fingerprint:
                lifecycle = "conflict"
                conflict_id = _stable_id("knowledge-conflict", proposal.proposal_id)
                connection.execute(
                    "INSERT INTO knowledge_candidate_conflict_reviews_v1 VALUES (?, ?, ?, ?, 'open', ?, ?)",
                    (conflict_id, proposal.canonical_key, previous["id"], version_id, proposal.reviewer_id, proposal.reviewed_at),
                )
            provenance = {"promotion_id": unit["promotion_id"], "package_id": unit["package_id"], "unit_id": proposal.unit_id, "parent_version_id": proposal.parent_version_id, "reviewer_id": proposal.reviewer_id, "unit_provenance": json.loads(unit["provenance_json"])}
            connection.execute(
                "INSERT INTO knowledge_candidate_versions_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (version_id, proposal.unit_id, proposal.canonical_key, proposal.parent_version_id, content_json, fingerprint, lifecycle, conflict_id, _dump(provenance), proposal.reviewed_at),
            )
            connection.commit()
            return CandidateKnowledgeVersionReceipt(version_id=version_id, parent_version_id=proposal.parent_version_id, lifecycle_status=lifecycle, conflict_review_id=conflict_id)
        except Exception:
            connection.rollback()
            raise


def deprecate_candidate_knowledge_version(
    deprecation: KnowledgeVersionDeprecation, *, db_path: str | Path
) -> None:
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database, live_wal=True)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute(
                "SELECT v.lifecycle_status, v.content_fingerprint, p.id, p.package_id "
                "FROM knowledge_candidate_versions_v1 v "
                "JOIN knowledge_candidate_units_v1 u ON u.id=v.unit_id "
                "JOIN knowledge_candidate_promotions_v1 p ON p.id=u.promotion_id "
                "WHERE v.id=?",
                (deprecation.version_id,),
            ).fetchone()
            if row is None:
                raise ValueError("unknown candidate knowledge version")
            event = connection.execute(
                "SELECT 1 FROM knowledge_candidate_governance_events_v1 WHERE approval_id=?",
                (deprecation.approval_id,),
            ).fetchone()
            if event is None:
                event_id = _stable_id("knowledge-version-deprecation", deprecation.approval_id)
                connection.execute(
                    "INSERT INTO knowledge_candidate_governance_events_v1 VALUES (?, ?, ?, ?, ?, 'deprecated', ?, ?, ?, ?)",
                    (event_id, row["id"], row["package_id"], deprecation.approval_id, deprecation.reviewer_id, deprecation.rationale, deprecation.reviewed_at, row["content_fingerprint"], deprecation.reviewed_at),
                )
            if row["lifecycle_status"] != "deprecated":
                connection.execute(
                    "UPDATE knowledge_candidate_versions_v1 SET lifecycle_status='deprecated' WHERE id=?",
                    (deprecation.version_id,),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
