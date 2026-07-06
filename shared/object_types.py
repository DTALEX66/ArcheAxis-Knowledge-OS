"""Unified object type system — absorbed from Tana Supertags + Capacities Objects.

Every KB asset (document, card, review, mistake, MKU) gets a typed schema
with configurable properties, similar to:
- Tana: Supertags define what fields a node has
- Capacities: Objects have Types with Properties
- Anytype: Objects classified by Types with Relations

This provides:
1. Schema registry for all KB object types
2. Property validation and defaults
3. Type inheritance (card extends document)
4. Dynamic property querying (like Capacities queries)

Usage:
    from shared.object_types import register_type, get_type, validate
    register_type("course", parent="document",
                  properties={"instructor": "str", "duration_hours": "int"})
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

# ── Type registry ───────────────────────────────────────

# Built-in types with their schemas
BUILTIN_TYPES: dict[str, dict[str, Any]] = {
    "document": {
        "description": "Base content unit",
        "parent": None,
        "properties": {
            "title": {"type": "str", "required": True},
            "content": {"type": "str", "required": True},
            "source": {"type": "str", "default": "unknown"},
            "tags": {"type": "list", "default": []},
            "created_at": {"type": "str"},
        },
        "table": "kb_documents",
    },
    "card": {
        "description": "Knowledge card for learning/review",
        "parent": "document",
        "properties": {
            "title": {"type": "str", "required": True},
            "content": {"type": "str", "required": True},
            "source_ids": {"type": "list", "default": []},
            "tags": {"type": "list", "default": []},
            "review_status": {"type": "str", "default": "draft",
                              "choices": ["draft", "reviewing", "mastered", "struggling"]},
            "created_at": {"type": "str"},
        },
        "table": "kb_cards",
    },
    "review": {
        "description": "Spaced-repetition review record",
        "parent": None,
        "properties": {
            "card_id": {"type": "str", "required": True},
            "quality": {"type": "int", "required": True, "min": 0, "max": 5},
            "interval_days": {"type": "int", "default": 1},
            "ease_factor": {"type": "float", "default": 2.5},
            "next_review_at": {"type": "str", "required": True},
            "created_at": {"type": "str"},
        },
        "table": "kb_reviews",
    },
    "mistake": {
        "description": "Learning mistake/error record",
        "parent": None,
        "properties": {
            "card_id": {"type": "str", "required": True},
            "error_type": {"type": "str", "default": "recall_failure",
                           "choices": ["recall_failure", "concept_confusion", "application_error"]},
            "detail": {"type": "str", "default": ""},
            "source_topic": {"type": "str", "default": ""},
            "resolved": {"type": "bool", "default": False},
            "created_at": {"type": "str"},
        },
        "table": "kb_mistakes",
    },
    "machine_knowledge": {
        "description": "Machine-consumable knowledge unit",
        "parent": None,
        "properties": {
            "title": {"type": "str", "required": True},
            "content": {"type": "str", "required": True},
            "unit_type": {"type": "str", "default": "rule",
                          "choices": ["rule", "fact", "procedure", "constraint", "pattern"]},
            "tags": {"type": "list", "default": []},
            "confidence": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0},
            "source_type": {"type": "str", "default": "manual"},
            "source_id": {"type": "str", "default": ""},
            "active": {"type": "bool", "default": True},
            "created_at": {"type": "str"},
            "updated_at": {"type": "str"},
        },
        "table": "machine_knowledge_units",
    },
    "context_pack": {
        "description": "Context package for agent execution",
        "parent": None,
        "properties": {
            "goal": {"type": "str", "required": True},
            "sources": {"type": "list", "default": []},
            "evidence": {"type": "list", "default": []},
            "constraints": {"type": "list", "default": []},
            "token_budget": {"type": "int", "default": 4000},
            "created_at": {"type": "str"},
        },
        "table": "kb_context_packs",
    },
    "taskpack": {
        "description": "Task package for execution",
        "parent": None,
        "properties": {
            "goal": {"type": "str", "required": True},
            "steps": {"type": "list", "default": []},
            "allowed_tools": {"type": "list", "default": []},
            "blocked_tools": {"type": "list", "default": []},
            "constraints": {"type": "list", "default": []},
            "success_criteria": {"type": "list", "default": []},
            "risk_level": {"type": "str", "default": "low",
                           "choices": ["low", "medium", "high", "critical"]},
            "created_at": {"type": "str"},
        },
        "table": "kb_taskpacks",
    },
    "daily_note": {
        "description": "Daily journal entry",
        "parent": None,
        "properties": {
            "date": {"type": "str", "required": True},
            "content": {"type": "str", "default": ""},
            "tags": {"type": "list", "default": ["daily-note"]},
            "created_at": {"type": "str"},
            "updated_at": {"type": "str"},
        },
        "table": "daily_notes",
    },
}

# Custom user-registered types
_custom_types: dict[str, dict[str, Any]] = {}


# ── Public API ──────────────────────────────────────────


def register_type(
    name: str,
    parent: str = "document",
    description: str = "",
    properties: dict[str, dict[str, Any]] | None = None,
    table: str = "",
) -> dict[str, Any]:
    """Register a custom object type (like Tana Supertag).

    Args:
        name: type name, e.g. "course", "person", "project".
        parent: base type to inherit from.
        description: human-readable description.
        properties: {field_name: {type, required, default, choices, min, max}}.
        table: SQLite table name (if different from kb_{name}s).

    Returns:
        The registered type definition.
    """
    base = get_type(parent)
    merged_props = dict(base.get("properties", {}))
    if properties:
        merged_props.update(properties)

    type_def = {
        "description": description or f"Custom type: {name}",
        "parent": parent,
        "properties": merged_props,
        "table": table or f"kb_{name}s",
    }
    _custom_types[name] = type_def
    return type_def


def get_type(name: str) -> dict[str, Any]:
    """Get type definition by name."""
    if name in _custom_types:
        return _custom_types[name]
    if name in BUILTIN_TYPES:
        return BUILTIN_TYPES[name]
    return {"description": "Unknown type", "parent": None, "properties": {}, "table": ""}


def list_types() -> list[dict[str, Any]]:
    """List all registered types."""
    result = []
    for name, tdef in {**BUILTIN_TYPES, **_custom_types}.items():
        result.append({
            "name": name,
            "description": tdef["description"],
            "parent": tdef["parent"],
            "property_count": len(tdef["properties"]),
            "table": tdef["table"],
            "builtin": name in BUILTIN_TYPES,
        })
    return result


def validate(obj_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """Validate an object against its type schema.

    Returns:
        {valid: bool, errors: list[str], defaults_applied: dict}.
    """
    tdef = get_type(obj_type)
    props = tdef.get("properties", {})
    errors: list[str] = []
    defaults: dict[str, Any] = {}

    # Check required fields
    for name, spec in props.items():
        if spec.get("required") and name not in data:
            errors.append(f"missing required field: {name}")

    # Apply defaults for missing optional fields
    for name, spec in props.items():
        if name not in data and "default" in spec:
            defaults[name] = spec["default"]

    # Type check
    for name, value in data.items():
        spec = props.get(name)
        if not spec:
            continue
        expected = spec.get("type", "str")
        if expected == "int" and not isinstance(value, int):
            errors.append(f"{name}: expected int, got {type(value).__name__}")
        elif expected == "float" and not isinstance(value, (int, float)):
            errors.append(f"{name}: expected float, got {type(value).__name__}")
        elif expected == "bool" and not isinstance(value, bool):
            errors.append(f"{name}: expected bool, got {type(value).__name__}")
        elif expected == "list" and not isinstance(value, list):
            errors.append(f"{name}: expected list, got {type(value).__name__}")
        elif "choices" in spec and value not in spec["choices"]:
            errors.append(f"{name}: '{value}' not in {spec['choices']}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "defaults_applied": defaults,
    }


def get_property_schema(obj_type: str) -> dict[str, Any]:
    """Return property schema for a type (used by UI to render forms)."""
    tdef = get_type(obj_type)
    return {
        "type": obj_type,
        "description": tdef["description"],
        "parent": tdef["parent"],
        "table": tdef["table"],
        "properties": tdef["properties"],
    }
