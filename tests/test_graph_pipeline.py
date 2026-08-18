"""Tests for the ECL knowledge-graph pipeline (Cognee absorption)."""
from __future__ import annotations

import pytest

from app.knowledge.graph_pipeline import (
    GraphPipelineError,
    cognify,
    extract,
    load,
    run_pipeline,
)


def test_extract_entities_and_relations():
    result = extract("Photoshop 支持 UXP；InDesign 依赖 Photoshop",
                     glossary={"Photoshop": "software", "UXP": "technology"})
    assert "Photoshop" in result.entities
    assert result.entities["UXP"] == "technology"
    assert ("Photoshop", "supports", "UXP") in result.relations
    assert ("InDesign", "requires", "Photoshop") in result.relations
    assert result.provenance


def test_extract_empty_rejected():
    with pytest.raises(GraphPipelineError):
        extract("   ")


def test_cognify_dedupes_edges():
    raw = extract("A 支持 B；A 支持 B；C 属于 D")
    cleaned = cognify(raw)
    assert cleaned.relation_count() == 2  # duplicate A-B edge removed


def test_load_into_store():
    class FakeStore:
        def __init__(self):
            self.entities = []
            self.relations = []

        def add_entity(self, entity_id, entity_type, props):
            self.entities.append((entity_id, entity_type))

        def add_relation(self, source, target, relation, weight):
            self.relations.append((source, relation, target))

    store = FakeStore()
    result = extract("X 支持 Y", glossary={"X": "a", "Y": "b"})
    receipt = load(cognify(result), store)
    assert receipt["entities"] == 2
    assert receipt["relations"] == 1
    assert store.entities == [("X", "a"), ("Y", "b")]


def test_run_pipeline_full():
    class FakeStore:
        def add_entity(self, *args): pass
        def add_relation(self, *args): pass

    out = run_pipeline("A 支持 B；B 依赖 C", FakeStore())
    assert out["receipt"]["relations"] == 2
    assert out["provenance"]
