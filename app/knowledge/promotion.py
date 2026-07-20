"""Explicit, candidate-only promotion from persisted Research packages."""

from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.v1 import KnowledgeUnitV1, RelationV1
from shared import knowledge_governance_migration
from shared.research_store import load_research_package


class ResearchKnowledgeApproval(BaseModel):
    """Auditable human decision required before creating Knowledge candidates."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    decision: Literal["approved", "rejected", "deprecated"]
    rationale: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


class ResearchKnowledgePromotionReceipt(BaseModel):
    """Read-back receipt; candidate promotion never asserts verified truth."""

    model_config = ConfigDict(extra="forbid")

    promotion_id: str
    package_id: str
    lifecycle_status: Literal["candidate", "rejected", "deprecated"]
    units: list[KnowledgeUnitV1]
    relations: list[RelationV1]


def _stable_id(namespace: str, *parts: str) -> str:
    value = "\0".join((namespace, *parts)).encode("utf-8")
    return f"{namespace}_{sha256(value).hexdigest()[:24]}"


def _provenance(graph: object, *, source_ids: list[str]) -> dict[str, object]:
    evidence = [item.model_dump() for item in graph.evidence]
    findings = [item.model_dump() for item in graph.findings]
    return {
        "research_package_id": graph.package.package_id,
        "source_ids": source_ids,
        "evidence_ids": [str(item.get("evidence_id", "")) for item in evidence],
        "finding_ids": [str(item.get("finding_id", "")) for item in findings],
        "research_status": graph.package.status,
        "research_provenance_status": graph.package.provenance_status,
        "requires_human_review": True,
    }


def _candidate_models(graph: object, promotion_id: str) -> tuple[list[KnowledgeUnitV1], list[RelationV1]]:
    package_id = graph.package.package_id
    created_at = graph.package.created_at
    units: list[KnowledgeUnitV1] = []
    source_units: dict[str, str] = {}
    for source in graph.sources:
        payload = source.model_dump()
        source_id = str(payload["source_id"])
        unit_id = _stable_id("knowledge-source", package_id, source_id)
        source_units[source_id] = unit_id
        properties = {
            **payload,
            "lifecycle_status": "candidate",
            "research_package_id": package_id,
            "source_id": source_id,
            "provenance": _provenance(graph, source_ids=[source_id]),
        }
        units.append(KnowledgeUnitV1(schema_version="1.0.0", unit_id=unit_id, unit_type="research_source", properties=properties, graph_name="knowledge_candidate", created_at=created_at))
    relations: list[RelationV1] = []
    for claim in graph.claims:
        payload = claim.model_dump()
        claim_id = str(payload["claim_id"])
        source_ids = [str(item) for item in payload["source_record_ids"]]
        unit_id = _stable_id("knowledge-claim", package_id, claim_id)
        properties = {
            **payload,
            "lifecycle_status": "candidate",
            "research_package_id": package_id,
            "source_ids": source_ids,
            "provenance": _provenance(graph, source_ids=source_ids),
        }
        units.append(KnowledgeUnitV1(schema_version="1.0.0", unit_id=unit_id, unit_type="research_claim", properties=properties, graph_name="knowledge_candidate", created_at=created_at))
        for source_id in source_ids:
            source_unit_id = source_units[source_id]
            relation_id = _stable_id("knowledge-relation", promotion_id, source_unit_id, unit_id)
            relations.append(RelationV1(schema_version="1.0.0", relation_id=relation_id, source_unit_id=source_unit_id, target_unit_id=unit_id, relation_type="supports_claim", weight=1.0, graph_name="knowledge_candidate", created_at=created_at))
    return (
        sorted(units, key=lambda unit: unit.unit_id),
        sorted(relations, key=lambda relation: relation.relation_id),
    )


def _receipt(connection: sqlite3.Connection, approval_id: str) -> ResearchKnowledgePromotionReceipt | None:
    row = connection.execute("SELECT id, package_id, lifecycle_status FROM knowledge_candidate_promotions_v1 WHERE approval_id=?", (approval_id,)).fetchone()
    if row is None:
        return None
    units = [KnowledgeUnitV1(schema_version="1.0.0", unit_id=item["id"], unit_type=item["unit_type"], properties=json.loads(item["properties_json"]), graph_name=item["graph_name"], created_at=item["created_at"]) for item in connection.execute("SELECT * FROM knowledge_candidate_units_v1 WHERE promotion_id=? ORDER BY id", (row["id"],))]
    relations = [RelationV1(schema_version="1.0.0", relation_id=item["id"], source_unit_id=item["source_unit_id"], target_unit_id=item["target_unit_id"], relation_type=item["relation_type"], weight=item["weight"], graph_name=item["graph_name"], created_at=item["created_at"]) for item in connection.execute("SELECT * FROM knowledge_candidate_relations_v1 WHERE promotion_id=? ORDER BY id", (row["id"],))]
    return ResearchKnowledgePromotionReceipt(promotion_id=row["id"], package_id=row["package_id"], lifecycle_status=row["lifecycle_status"], units=units, relations=relations)


def promote_research_package_to_candidates(approval: ResearchKnowledgeApproval, *, db_path: str | Path) -> ResearchKnowledgePromotionReceipt:
    """Persist only governed candidate graph projections after an explicit decision."""
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database)
    graph = load_research_package(approval.package_id, db_path=database)
    promotion_id = _stable_id("knowledge-promotion", approval.package_id, approval.approval_id)
    units, relations = _candidate_models(graph, promotion_id) if approval.decision == "approved" else ([], [])
    lifecycle = "candidate" if approval.decision == "approved" else approval.decision
    fingerprint = sha256(json.dumps(graph.model_dump(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = _receipt(connection, approval.approval_id)
            if existing is not None:
                connection.rollback()
                return existing
            connection.execute("INSERT INTO knowledge_candidate_promotions_v1(id, package_id, approval_id, reviewer_id, decision, rationale, reviewed_at, candidate_fingerprint, lifecycle_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (promotion_id, approval.package_id, approval.approval_id, approval.reviewer_id, approval.decision, approval.rationale, approval.reviewed_at, fingerprint, lifecycle, approval.reviewed_at))
            for unit in units:
                connection.execute("INSERT INTO knowledge_candidate_units_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (unit.unit_id, promotion_id, approval.package_id, unit.unit_type, json.dumps(unit.properties, sort_keys=True, separators=(",", ":")), unit.graph_name, "candidate", json.dumps(unit.properties["provenance"], sort_keys=True, separators=(",", ":")), unit.created_at))
            for relation in relations:
                connection.execute("INSERT INTO knowledge_candidate_relations_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (relation.relation_id, promotion_id, relation.source_unit_id, relation.target_unit_id, relation.relation_type, relation.weight, relation.graph_name, "candidate", json.dumps({"research_package_id": approval.package_id, "approval_id": approval.approval_id}, sort_keys=True), relation.created_at))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return ResearchKnowledgePromotionReceipt(promotion_id=promotion_id, package_id=approval.package_id, lifecycle_status=lifecycle, units=units, relations=relations)
