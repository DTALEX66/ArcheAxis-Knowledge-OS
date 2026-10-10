"""Canonical template identity/shape matches the existing frontend registry; no runtime I/O."""
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "packages/contracts/v2/template-binding.schema.json"


def test_template_identity_sets_match_existing_28_discipline_and_three_template_registry():
    schema = json.loads(SOURCE.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    source = (ROOT / "frontend/src/templates/disciplines.ts").read_text(encoding="utf-8")
    ids = re.findall(r'\{id:"([^\"]+)"', source)
    assert schema["properties"]["discipline_id"]["enum"] == [value for value in ids if not value.startswith("T")]
    assert schema["properties"]["template_id"]["enum"] == ["T1", "T2", "T3"]
    assert len(set(schema["properties"]["discipline_id"]["enum"])) == 28


def test_template_shape_allows_incomplete_description_but_not_unknown_metadata_or_unpinned_references():
    schema = json.loads(SOURCE.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    value = {"schema": "archeaxis.template/v1", "template_id": "T1", "discipline_id": "math", "fields": {"status": "unevaluated", "空草稿": ""}, "references": [], "learning_item_key": None}
    assert validator.is_valid(value)
    assert not validator.is_valid({**value, "future_extension": {"raw": "historical-only"}})
    assert not validator.is_valid({key: item for key, item in value.items() if key != "learning_item_key"})
    reference = {"document_id": "doc_actual", "version": 1, "block_id": "真实 块标识", "relation": "", "x": -20.25, "y": 40.5}
    assert validator.is_valid({**value, "references": [reference]})
    assert not validator.is_valid({**value, "references": [{**reference, "version": 0}]})
    assert not validator.is_valid({**value, "references": [{**reference, "x": "20"}]})
    assert not validator.is_valid({**value, "references": [{key: item for key, item in reference.items() if key != "block_id"}]})
    assert not validator.is_valid({**value, "references": [reference] * 101})
