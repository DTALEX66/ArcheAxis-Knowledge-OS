"""本地preview的实际Draft202012合同；不出网解析引用，语义由Rust共同案例检查。"""
import json
from pathlib import Path
from urllib.parse import urljoin

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages/contracts/v2"
BASE = json.loads((CONTRACTS / "project-handoff.schema.json").read_text())
SCHEMA = json.loads((CONTRACTS / "project-handoff-preview.schema.json").read_text())
CASES = json.loads((CONTRACTS / "project-handoff-preview.cases.json").read_text())


def test_preview_shared_cases_have_strict_schema_and_preserve_negative_controls():
    Draft202012Validator.check_schema(SCHEMA)
    registry = Registry().with_resource(
        urljoin(SCHEMA["$id"], "project-handoff.schema.json"), Resource.from_contents(BASE)
    )
    validator = Draft202012Validator(SCHEMA, registry=registry)
    assert any(case["schema_valid"] for case in CASES)
    assert any(not case["schema_valid"] for case in CASES)
    for case in CASES:
        assert validator.is_valid(case["value"]) == case["schema_valid"], case["name"]
