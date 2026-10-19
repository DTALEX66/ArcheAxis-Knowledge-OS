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


def test_plan_policy_version_pairs_preserve_legacy_and_reject_partial_or_cross_purpose():
    schema=json.loads((ROOT/'packages/contracts/v2/conversation.schema.json').read_text(encoding='utf8'))
    validator=Draft202012Validator({**schema, '$ref':'#/$defs/ConversationPlanDto'})
    request={'session_id':'session_a','request_id':'request_a','purpose':'companion','material':None,'selection':None,'question':'question','model':None,'max_tokens':128,'timeout_s':5,'preview':False,'confirmed_plan_sha256':None}
    legacy={'schema':'archeaxis.conversation-plan/v1','request':request,'consumer':'archeaxis','session_sequence':0,'context_sha256':'a'*64,'material_proof':None,'restore_epoch':'legacy_epoch','delivery':'BUFFERED','destination':'LOCAL_LOOPBACK_ONLY','destination_candidates':['http://127.0.0.1:1234/v1'],'model_binding':'legacy_owned_local_probe','usage':None,'cost':None}
    assert not list(validator.iter_errors(legacy))
    general={**legacy,'answer_policy':'companion_general','prompt_version':'archeaxis.companion/v1 2026-10-19'}
    assert not list(validator.iter_errors(general))
    grounded=copy.deepcopy(legacy)
    grounded['request'].update(purpose='material_learning',material={'kind':'document','document_id':'document_a','version':1,'content_sha256':'b'*64,'block_id':None})
    grounded.update(answer_policy='grounded',prompt_version='archeaxis.vnext/v1 2026-10-02')
    assert not list(validator.iter_errors(grounded))
    for field in ('answer_policy','prompt_version'):
        broken = copy.deepcopy(general)
        del broken[field]
        assert list(validator.iter_errors(broken))
    for field,bad in [('answer_policy','arbitrary_template'),('prompt_version','unknown'),('prompt_version','archeaxis.vnext/v1 2026-10-02')]:
        broken = copy.deepcopy(general)
        broken[field] = bad
        assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(grounded)
    broken['answer_policy'] = 'companion_general'
    broken['prompt_version'] = 'archeaxis.companion/v1 2026-10-19'
    assert list(validator.iter_errors(broken)), 'material cannot select the general policy'
