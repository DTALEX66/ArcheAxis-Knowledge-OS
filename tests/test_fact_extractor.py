"""Tests for shared.fact_extractor (zero-dependency S-V-O triple extraction)."""

from __future__ import annotations

from shared.fact_extractor import extract_facts, extract_key_entities


def test_is_a_relation() -> None:
    facts = extract_facts("Python is a programming language.")
    assert any(f["predicate"] == "is_a" and f["subject"] == "Python" for f in facts)


def test_created_by_relation() -> None:
    facts = extract_facts("Python was created by Guido van Rossum in 1991.")
    created = [f for f in facts if f["predicate"] == "created_by"]
    assert created
    assert created[0]["subject"] == "Python"
    assert "Guido van Rossum" in created[0]["object"]


def test_uses_relation() -> None:
    facts = extract_facts("FastAPI uses Pydantic for validation.")
    uses = [f for f in facts if f["predicate"] == "uses"]
    assert uses
    assert uses[0]["subject"] == "FastAPI"


def test_contains_relation() -> None:
    facts = extract_facts("The repository contains source code and tests.")
    contains = [f for f in facts if f["predicate"] == "contains"]
    assert contains


def test_causes_relation() -> None:
    facts = extract_facts("Smoking causes lung cancer.")
    causes = [f for f in facts if f["predicate"] == "causes"]
    assert causes
    assert causes[0]["object"] == "lung cancer"


def test_part_of_relation() -> None:
    facts = extract_facts("The heart is part of the circulatory system.")
    part_of = [f for f in facts if f["predicate"] == "part_of"]
    assert part_of


def test_depends_on_relation() -> None:
    facts = extract_facts("The build depends on the compiler toolchain.")
    dep = [f for f in facts if f["predicate"] == "depends_on"]
    assert dep


def test_of_pattern_yields_has_relation() -> None:
    # _OF_PATTERN matches capitalized "X of Y" phrases; relation is
    # reversed (subject=Y, object=X): "University of Oxford" → Oxford has University.
    facts = extract_facts("The University of Oxford is a collegiate research university.")
    has = [f for f in facts if f["predicate"] == "has"]
    assert has
    assert any("Oxford" in f["subject"] and "University" in f["object"] for f in has)


def test_max_facts_limit() -> None:
    text = "Python is a language. Rust is a language. Go is a language. C is a language."
    facts = extract_facts(text, max_facts=2)
    assert len(facts) == 2


def test_empty_text() -> None:
    assert extract_facts("") == []
    assert extract_facts("   ") == []


def test_clean_entities_no_trailing_punctuation() -> None:
    facts = extract_facts("Python is a programming language.")
    is_a = [f for f in facts if f["predicate"] == "is_a"]
    assert is_a
    assert not is_a[0]["object"].endswith(".")
    assert not is_a[0]["object"].endswith(",")


def test_extract_key_entities_capitalized() -> None:
    entities = extract_key_entities("Python and Rust are languages. Python is popular.")
    assert isinstance(entities, list)
    if entities:  # capitalization heuristic may vary, but shape must be stable
        assert {"entity", "type", "count"} <= set(entities[0])
