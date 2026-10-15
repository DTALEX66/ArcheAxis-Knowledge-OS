"""Recorded Core/real-worker text, DOCX and malformed-DOCX responses.

These controlled-input fixtures qualify wire shape only. Runtime evidence lives
in file_format_qualification.rs; native editing and roundtrip remain unverified.
"""
import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'packages/contracts/v1/file-format-qualification.schema.json').read_text(encoding='utf-8'))
FIXTURES = json.loads((Path(__file__).with_name('fixtures') / 'file-format-qualification.json').read_text(encoding='utf-8'))
VALIDATOR = Draft202012Validator(SCHEMA)


@pytest.mark.parametrize('case', FIXTURES['samples'], ids=['text', 'docx', 'malformed-docx'])
def test_recorded_worker_responses_match_the_wire_contract(case):
    Draft202012Validator.check_schema(SCHEMA)
    VALIDATOR.validate(case)
    assert case['operations']['edit']['status'] == 'UNVERIFIED'
    assert case['operations']['roundtrip']['status'] == 'UNVERIFIED'


@pytest.mark.parametrize('operation', ['store', 'preview', 'extract', 'edit', 'export', 'roundtrip'])
def test_each_operation_requires_its_own_qualification(operation):
    payload = deepcopy(FIXTURES['samples'][0])
    del payload['operations'][operation]
    errors = list(VALIDATOR.iter_errors(payload))
    assert any(error.validator == 'required' and list(error.absolute_path) == ['operations'] for error in errors)


@pytest.mark.parametrize(('path', 'value'), [
    (['operations', 'edit', 'status'], 'LOSSLESS'),
    (['operations', 'extract', 'qualification_version'], 2),
    (['attempt'], True),
    (['source_revision'], 'unknown'),
    (['qualification_evidence'], 'ASSUMED'),
    (['loss', 'reported_count'], -1),
    (['outputs'], [{}] * 51),
])
def test_single_field_negatives_are_rejected_at_the_changed_field(path, value):
    payload = deepcopy(FIXTURES['samples'][0])
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    assert any(list(error.absolute_path) == path for error in VALIDATOR.iter_errors(payload))


def test_failed_conversion_keeps_loss_unknown_in_recorded_response():
    failed = FIXTURES['samples'][2]
    assert failed['execution_succeeded'] is False
    assert failed['operations']['extract']['status'] == 'FAILED'
    assert failed['loss']['status'] == 'unknown'
    assert failed['loss']['reported_count'] is None
