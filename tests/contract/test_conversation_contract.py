"""Finite session/request/sequence schema; synthetic contract evidence only."""
import copy
import json
import subprocess
import sys
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[2]
def test_conversation_request_is_finite_and_companion_cannot_bypass_material_binding():
    schema=json.loads((ROOT/'packages/contracts/v2/conversation.schema.json').read_text(encoding='utf8'))
    validator=Draft202012Validator(schema)
    request={'session_id':'session_a','request_id':'request_a','purpose':'companion','material':None,'selection':None,'question':'question','model':None,'max_tokens':128,'timeout_s':5,'preview':True,'confirmed_plan_sha256':None}
    assert not list(validator.iter_errors(request))
    for field,bad in [('purpose','agent_runtime'),('session_id','../other'),('max_tokens',0),('question','x'*8193),('purpose','material_learning')]:
        value=copy.deepcopy(request);value[field]=bad;assert list(validator.iter_errors(value))
    for field in ['url','endpoint','token','tool','command','context']:
        value=copy.deepcopy(request);value[field]='SYNTHETIC';assert list(validator.iter_errors(value))
    assert subprocess.run([sys.executable,'-B',str(ROOT/'scripts/contracts/generate_conversation.py'),'--check'],cwd=ROOT).returncode==0
