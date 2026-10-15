"""Finite material question DTOs, synthetic schema evidence only."""
import copy
import json
import subprocess
import sys
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2]
def test_material_question_schema_and_generated_dto_are_exact():
    s=json.loads((ROOT/'packages/contracts/v2/material-question.schema.json').read_text())
    v=jsonschema.Draft202012Validator(s)
    body={'request_id':'request_1','material':{'kind':'document','document_id':'doc_1','version':1,'content_sha256':'a'*64,'block_id':None},'selection':None,'question':'question','purpose':'learning','model':None,'max_tokens':128,'timeout_s':5,'preview':True,'confirmed_plan_sha256':None}
    assert not list(v.iter_errors(body))
    for field,bad in [('material',{'kind':'shell','command':'exec'}),('request_id','../other'),('max_tokens',0),('confirmed_plan_sha256','changed')]:
        changed=copy.deepcopy(body);changed[field]=bad;assert list(v.iter_errors(changed))
    for forbidden in ['url','token','context','provider','endpoint']:
        changed=copy.deepcopy(body);changed[forbidden]='synthetic';assert list(v.iter_errors(changed))
    assert subprocess.run([sys.executable,'-B',str(ROOT/'scripts/contracts/generate_material_question.py'),'--check'],cwd=ROOT).returncode==0
