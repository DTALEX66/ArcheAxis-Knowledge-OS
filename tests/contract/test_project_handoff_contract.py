"""严格schema/共享case；不把合同投影当作实际跨产品投递或原生验收。"""
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[2]

def test_project_handoff_shared_schema_cases():
    schema=json.loads((ROOT/'packages/contracts/v2/project-handoff.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema)
    cases=json.loads((ROOT/'packages/contracts/v2/project-handoff.cases.json').read_text(encoding='utf-8'))
    assert len(cases)==67
    for case in cases:
        assert validator.is_valid(case['value'])==case['schema_valid'],case['name']
        if 'expected_proposal_sha256' in case:
            raw=json.dumps(case['value'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
            assert hashlib.sha256(b'archeaxis.project-handoff/v1\0'+raw).hexdigest()==case['expected_proposal_sha256']

def test_handoff_reuses_observer_identity_reference_and_existing_capability_ids():
    schema=json.loads((ROOT/'packages/contracts/v2/project-handoff.schema.json').read_text(encoding='utf-8'))
    observer=json.loads((ROOT/'packages/contracts/v2/project-observer.schema.json').read_text(encoding='utf-8'))
    for name in ['ProducerIdentity','ConsumerIdentity','ObjectReference']:
        assert schema['$defs'][name]==observer['$defs'][name]
    capability_map=json.loads((ROOT/'config/capability-map.v1.json').read_text(encoding='utf-8'))
    assert schema['$defs']['CapabilityLink']['properties']['capability_id']['enum']==[v['capability_id'] for v in capability_map['capabilities']]
    assert schema['$defs']['CapabilityLink']['properties']['manifest_identity']=={'const':'UNKNOWN'}
