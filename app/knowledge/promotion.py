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


def _before_candidate_relation_write() -> None:
    """Narrow failure-injection seam for transaction regression tests."""


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
    package_id, created_at = graph.package.package_id, graph.package.created_at
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
    return sorted(units, key=lambda unit: unit.unit_id), sorted(relations, key=lambda relation: relation.relation_id)


def _receipt(connection: sqlite3.Connection, approval_id: str) -> ResearchKnowledgePromotionReceipt | None:
    event = connection.execute("SELECT promotion_id, package_id, decision FROM knowledge_candidate_governance_events_v1 WHERE approval_id=?", (approval_id,)).fetchone()
    if event is None:
        return None
    promotion_id = str(event["promotion_id"] or _stable_id("knowledge-promotion", str(event["package_id"])))
    projection = connection.execute("SELECT lifecycle_status FROM knowledge_candidate_promotions_v1 WHERE id=?", (promotion_id,)).fetchone()
    lifecycle = str(projection["lifecycle_status"]) if projection is not None else str(event["decision"])
    units = [KnowledgeUnitV1(schema_version="1.0.0", unit_id=row["id"], unit_type=row["unit_type"], properties={**json.loads(row["properties_json"]), "lifecycle_status": row["lifecycle_status"]}, graph_name=row["graph_name"], created_at=row["created_at"]) for row in connection.execute("SELECT * FROM knowledge_candidate_units_v1 WHERE promotion_id=? ORDER BY id", (promotion_id,))]
    relations = [RelationV1(schema_version="1.0.0", relation_id=row["id"], source_unit_id=row["source_unit_id"], target_unit_id=row["target_unit_id"], relation_type=row["relation_type"], weight=row["weight"], graph_name=row["graph_name"], created_at=row["created_at"]) for row in connection.execute("SELECT * FROM knowledge_candidate_relations_v1 WHERE promotion_id=? ORDER BY id", (promotion_id,))]
    return ResearchKnowledgePromotionReceipt(promotion_id=promotion_id, package_id=str(event["package_id"]), lifecycle_status=lifecycle, units=units, relations=relations)


def _record_event(connection: sqlite3.Connection, approval: ResearchKnowledgeApproval, promotion_id: str | None, fingerprint: str) -> None:
    event_id = _stable_id("knowledge-governance-event", approval.approval_id)
    connection.execute("INSERT INTO knowledge_candidate_governance_events_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (event_id, promotion_id, approval.package_id, approval.approval_id, approval.reviewer_id, approval.decision, approval.rationale, approval.reviewed_at, fingerprint, approval.reviewed_at))


def promote_research_package_to_candidates(approval: ResearchKnowledgeApproval, *, db_path: str | Path) -> ResearchKnowledgePromotionReceipt:
    """Persist governed candidate projections and immutable human decision events."""
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database)
    graph = load_research_package(approval.package_id, db_path=database)
    promotion_id = _stable_id("knowledge-promotion", approval.package_id)
    fingerprint = sha256(json.dumps(graph.model_dump(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = _receipt(connection, approval.approval_id)
            if existing is not None:
                connection.rollback()
                return existing
            projection = connection.execute("SELECT id FROM knowledge_candidate_promotions_v1 WHERE package_id=?", (approval.package_id,)).fetchone()
            if approval.decision == "deprecated":
                if projection is None:
                    raise ValueError("cannot deprecate a package without a candidate projection")
                promotion_id = str(projection["id"])
                _record_event(connection, approval, promotion_id, fingerprint)
                connection.execute("UPDATE knowledge_candidate_promotions_v1 SET lifecycle_status='deprecated' WHERE id=?", (promotion_id,))
                connection.execute("UPDATE knowledge_candidate_units_v1 SET lifecycle_status='deprecated' WHERE promotion_id=?", (promotion_id,))
                connection.execute("UPDATE knowledge_candidate_relations_v1 SET lifecycle_status='deprecated' WHERE promotion_id=?", (promotion_id,))
            elif approval.decision == "rejected":
                _record_event(connection, approval, None, fingerprint)
            else:
                if projection is not None:
                    raise ValueError("package already has a candidate projection")
                units, relations = _candidate_models(graph, promotion_id)
                connection.execute("INSERT INTO knowledge_candidate_promotions_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (promotion_id, approval.package_id, approval.approval_id, approval.reviewer_id, approval.decision, approval.rationale, approval.reviewed_at, fingerprint, "candidate", approval.reviewed_at))
                _record_event(connection, approval, promotion_id, fingerprint)
                for unit in units:
                    connection.execute("INSERT INTO knowledge_candidate_units_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (unit.unit_id, promotion_id, approval.package_id, unit.unit_type, json.dumps(unit.properties, sort_keys=True, separators=(",", ":")), unit.graph_name, "candidate", json.dumps(unit.properties["provenance"], sort_keys=True, separators=(",", ":")), unit.created_at))
                for relation in relations:
                    _before_candidate_relation_write()
                    connection.execute("INSERT INTO knowledge_candidate_relations_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (relation.relation_id, promotion_id, relation.source_unit_id, relation.target_unit_id, relation.relation_type, relation.weight, relation.graph_name, "candidate", json.dumps({"research_package_id": approval.package_id, "approval_id": approval.approval_id}, sort_keys=True), relation.created_at))
            receipt = _receipt(connection, approval.approval_id)
            if receipt is None:
                raise RuntimeError("promotion event receipt missing before commit")
            connection.commit()
            return receipt
        except Exception:
            connection.rollback()
            raise
