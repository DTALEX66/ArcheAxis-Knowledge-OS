from __future__ import annotations

import pytest
from pydantic import ValidationError

KNOWLEDGE_UNIT_SCHEMA_ID = (
    "https://archeaxis.local/contracts/v1/knowledge-unit.schema.json"
)
RELATION_SCHEMA_ID = "https://archeaxis.local/contracts/v1/relation.schema.json"


def _entity_row():
    return {
        "id": "concept-vector-search",
        "entity_type": "concept",
        "properties": {
            "title": "Vector Search",
            "source_record_ids": ["source-001"],
            "confidence": 0.8,
        },
        "graph_name": "knowledge",
        "created_at": "2026-07-15 23:58:00",
    }


def _relation_row():
    return {
        "id": "rel-001",
        "source_id": "concept-vector-search",
        "target_id": "concept-embeddings",
        "relation_type": "depends_on",
        "weight": 0.75,
        "graph_name": "knowledge",
        "created_at": "2026-07-15 23:59:00",
    }


def test_knowledge_unit_and_relation_schemas_are_stable_and_strict():
    from app.contracts.v1 import KnowledgeUnitV1, RelationV1

    assert KnowledgeUnitV1.model_json_schema()["$id"] == KNOWLEDGE_UNIT_SCHEMA_ID
    assert RelationV1.model_json_schema()["$id"] == RELATION_SCHEMA_ID
    with pytest.raises(ValidationError):
        KnowledgeUnitV1(
            schema_version="1.0.0",
            unit_id="unit",
            unit_type="concept",
            properties={},
            graph_name="knowledge",
            created_at="now",
            invented="forbidden",
        )
    with pytest.raises(ValidationError):
        RelationV1(
            schema_version="2.0.0",
            relation_id="rel",
            source_unit_id="a",
            target_unit_id="b",
            relation_type="related",
            weight=1.0,
            graph_name="knowledge",
            created_at="now",
        )


def test_graph_entity_row_round_trips_losslessly():
    from app.adapters.knowledge_graph import from_graph_entity_row, to_graph_entity_row

    row = _entity_row()
    assert to_graph_entity_row(from_graph_entity_row(row)) == row


def test_graph_relation_row_round_trips_losslessly():
    from app.adapters.knowledge_graph import from_graph_relation_row, to_graph_relation_row

    row = _relation_row()
    assert to_graph_relation_row(from_graph_relation_row(row)) == row


def test_graph_rows_reject_unknown_fields_instead_of_silently_dropping_them():
    from app.adapters.knowledge_graph import from_graph_entity_row, from_graph_relation_row
    from app.adapters.taskpack import ContractMappingError

    with pytest.raises(ContractMappingError, match="unmapped graph entity fields"):
        from_graph_entity_row({**_entity_row(), "invented": "forbidden"})
    with pytest.raises(ContractMappingError, match="unmapped graph relation fields"):
        from_graph_relation_row({**_relation_row(), "invented": "forbidden"})


def test_graph_entity_properties_are_isolated_on_both_adapter_boundaries():
    from app.adapters.knowledge_graph import from_graph_entity_row, to_graph_entity_row

    row = _entity_row()
    unit = from_graph_entity_row(row)
    row["properties"]["source_record_ids"].append("source-mutated")
    assert unit.properties["source_record_ids"] == ["source-001"]

    projected = to_graph_entity_row(unit)
    projected["properties"]["source_record_ids"].append("projection-mutated")
    assert unit.properties["source_record_ids"] == ["source-001"]


def test_relation_preserves_direction_and_does_not_invent_inverse_edges():
    from app.adapters.knowledge_graph import from_graph_relation_row

    relation = from_graph_relation_row(_relation_row())
    assert relation.source_unit_id == "concept-vector-search"
    assert relation.target_unit_id == "concept-embeddings"
    assert relation.relation_type == "depends_on"


def test_contracts_facade_exports_knowledge_graph_contracts_and_adapters():
    from app.adapters.knowledge_graph import (
        from_graph_entity_row,
        from_graph_relation_row,
        to_graph_entity_row,
        to_graph_relation_row,
    )
    from app.contracts.v1 import KnowledgeUnitV1, RelationV1
    from app.facades import contracts

    assert contracts.KnowledgeUnitV1 is KnowledgeUnitV1
    assert contracts.RelationV1 is RelationV1
    assert contracts.from_graph_entity_row is from_graph_entity_row
    assert contracts.to_graph_entity_row is to_graph_entity_row
    assert contracts.from_graph_relation_row is from_graph_relation_row
    assert contracts.to_graph_relation_row is to_graph_relation_row
