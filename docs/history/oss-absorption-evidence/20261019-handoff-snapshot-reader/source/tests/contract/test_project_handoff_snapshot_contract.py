"""本机正文不成为Observer字段；共用正负案例验证严格schema。"""

import json
from pathlib import Path
from urllib.parse import urljoin

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "packages/contracts/v2"


def test_snapshot_shared_cases_preserve_local_human_scope_and_strict_identity():
    schema = json.loads(
        (FOLDER / "project-handoff-snapshot.schema.json").read_text(encoding="utf-8")
    )
    base = json.loads((FOLDER / "project-handoff.schema.json").read_text(encoding="utf-8"))
    cases = json.loads((FOLDER / "project-handoff-snapshot.cases.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    registry = Registry().with_resource(
        urljoin(schema["$id"], "project-handoff.schema.json"), Resource.from_contents(base)
    )
    validator = Draft202012Validator(schema, registry=registry)
    assert len(cases) >= 14
    for case in cases:
        assert validator.is_valid(case["value"]) == case["schema_valid"], case["name"]
