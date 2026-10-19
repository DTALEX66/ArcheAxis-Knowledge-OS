"""Shared synthetic cases; schema checks do not replace real admission/process tests."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT = Path(__file__).resolve().parents[2]

def test_project_observer_shared_contract_cases():
    schema = json.loads((ROOT/'packages/contracts/v2/project-observer.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    cases = json.loads((ROOT/'packages/contracts/v2/project-observer.cases.json').read_text(encoding='utf-8'))
    for case in cases:
        assert validator.is_valid(case['value']) == case['schema_valid'], case['name']
