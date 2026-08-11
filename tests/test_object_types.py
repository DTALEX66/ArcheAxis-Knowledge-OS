"""Tests for shared.object_types (unified typed-object registry).

Covers built-in schemas, custom type registration with inheritance,
validation (required/type/choices/defaults), and schema queries.
"""

from __future__ import annotations

from shared.object_types import (
    BUILTIN_TYPES,
    get_property_schema,
    get_type,
    list_types,
    register_type,
    validate,
)


def test_builtin_types_present() -> None:
    for name in ("document", "card", "review", "mistake", "machine_knowledge"):
        assert name in BUILTIN_TYPES, name
    assert BUILTIN_TYPES["card"]["parent"] == "document"


def test_get_type_builtin() -> None:
    tdef = get_type("card")
    assert tdef["table"] == "kb_cards"
    assert "review_status" in tdef["properties"]


def test_get_type_unknown_returns_placeholder() -> None:
    tdef = get_type("nonexistent")
    assert tdef["properties"] == {}
    assert tdef["table"] == ""


def test_register_custom_type_inherits() -> None:
    register_type("course", parent="document", properties={"instructor": {"type": "str"}})
    tdef = get_type("course")
    # inherits document's properties
    assert "title" in tdef["properties"]
    assert "content" in tdef["properties"]
    # adds custom property
    assert "instructor" in tdef["properties"]
    assert tdef["parent"] == "document"
    assert tdef["table"] == "kb_courses"


def test_register_custom_table_override() -> None:
    register_type("person", parent="document", table="people", properties={"age": {"type": "int"}})
    assert get_type("person")["table"] == "people"


def test_list_types_contains_builtin_and_custom() -> None:
    register_type("project", parent="document", properties={"deadline": {"type": "str"}})
    types = list_types()
    names = [t["name"] for t in types]
    assert "document" in names
    assert "card" in names
    assert "project" in names
    proj = next(t for t in types if t["name"] == "project")
    assert proj["builtin"] is False
    doc = next(t for t in types if t["name"] == "document")
    assert doc["builtin"] is True


def test_validate_valid_document() -> None:
    result = validate("document", {"title": "T", "content": "C"})
    assert result["valid"] is True
    assert result["errors"] == []
    # defaults applied for source/tags
    assert result["defaults_applied"]["source"] == "unknown"


def test_validate_missing_required() -> None:
    result = validate("document", {"title": "T"})
    assert result["valid"] is False
    assert any("content" in e for e in result["errors"])


def test_validate_type_mismatch() -> None:
    register_type("task", parent="document", properties={"priority": {"type": "int", "default": 1}})
    result = validate("task", {"title": "T", "content": "C", "priority": "high"})
    assert result["valid"] is False
    assert any("priority" in e for e in result["errors"])


def test_validate_choices() -> None:
    bad = validate("card", {"title": "T", "content": "C", "review_status": "invalid_status"})
    assert bad["valid"] is False
    good = validate("card", {"title": "T", "content": "C", "review_status": "mastered"})
    assert good["valid"] is True


def test_validate_list_type() -> None:
    bad = validate("document", {"title": "T", "content": "C", "tags": "not-a-list"})
    assert bad["valid"] is False


def test_get_property_schema() -> None:
    schema = get_property_schema("card")
    assert schema["type"] == "card"
    assert schema["table"] == "kb_cards"
    assert "review_status" in schema["properties"]
    # choices carried through for UI form rendering
    assert schema["properties"]["review_status"]["choices"] == ["draft", "reviewing", "mastered", "struggling"]


def test_validate_unknown_type() -> None:
    result = validate("ghost", {"anything": 1})
    assert result["valid"] is True  # no schema → nothing to enforce
