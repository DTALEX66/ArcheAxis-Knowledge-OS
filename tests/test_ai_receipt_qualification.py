"""Synthetic receipt-only checks; no actual model or Owner qualification."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ai_binding', ROOT/'scripts/probes/aaos01_ai_receipt_qualification.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
IDENTITIES = helper.declared_identities((ROOT/'services/python-workers/machine/worker_machine_answer.py').read_text(),
                                      [{'protocol':'openai','base':'http://127.0.0.1:1234/v1'}])

def fixture(retest=False, asset=False):
    knowledge = {'knowledge_id':'kid', 'body':'中文采用正文\n尾行。', 'status':'accepted'}
    grant = {'document_id':'grant', 'version':1, 'content_sha256':'a'*64, 'purpose':'exact purpose'}
    request = {'knowledge_id':'kid', 'question':'问题?', 'context_grant':grant, 'context_sha256':helper.digest(knowledge['body'])}
    answer = {**IDENTITIES[0], 'answer':'Synthetic test response, never actual inference'}
    doc = {'schema':'archeaxis.machine-answer/v1','authority':'candidate','knowledge_id':'kid',
           'question':'问题?','answer_id':'answer1','answer':answer,'request':request}
    task = {'task_id':'answer1','scope':'runtime.answer','outcome':'unmeasured','knowledge_version':'kid@v1',
            'model_version':answer['model'],'retest_of':None}
    prior = None
    packet_json = None
    if asset:
        packet = {'asset':{'document_id':'asset1','version':2,'content_sha256':'b'*64},'grant':{'document_id':'asset-grant','version':1,'content_sha256':'c'*64},
                  'items':[{'snapshot':{'document_id':'asset1','version':2},'body':'材料正文'}]}
        packet_json = json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        request['asset_context_grant'] = {'request_id':'asset-request'}
        request['knowledge_context_sha256'] = helper.digest(knowledge['body'])
        request['asset_context'] = {'schema':'archeaxis.machine-asset-context/v1','consumer':'local-machine',
                                    'operation':'retest' if retest else 'answer',
                                    'asset':packet['asset'],'grant':packet['grant'],'packet_sha256':helper.digest(packet_json)}
        combined = 'CANONICAL_KNOWLEDGE:\n'+knowledge['body']+'\n\nAI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n'+packet_json
        request['context_sha256'] = helper.digest(combined)
    if retest:
        previous = {'question':'问题?', 'answer_id':'old-answer','knowledge_id':'kid'}
        prior = {'task_id':'evaluation1','scope':'runtime.evaluation.failed','outcome':'failed','conditions':json.dumps(previous)}
        frozen = {'retest_of':'evaluation1','knowledge_id':'kid','question':'问题?','max_tokens':2048,'context_grant':grant}
        if asset:
            frozen['asset_context_grant'] = request['asset_context_grant']
        execution = {'schema':'archeaxis.machine-retest-execution/v1','request':frozen,
                     **{key:request[key] for key in ('context_sha256','knowledge_context_sha256','asset_context') if key in request}}
        doc.update(schema='archeaxis.machine-retest/v1',retest_task_id='answer1',retest_of='evaluation1',
                   prior={'conditions':previous},request=frozen,execution_request=execution)
        task.update(scope='runtime.retest',retest_of='evaluation1')
    task['conditions'] = json.dumps(doc, ensure_ascii=False)
    return task,knowledge,'问题?',grant,IDENTITIES,prior,packet_json

def check(value, retest=False, packet=True):
    task,knowledge,question,grant,identities,prior,packet_json=value
    return helper.validate(task,knowledge,question,grant,identities,scope='runtime.retest' if retest else 'runtime.answer',
                           prior_failed_task=prior,asset_packet_json=packet_json if packet else None)

@pytest.mark.parametrize('retest,asset',[(False,False),(False,True),(True,False),(True,True)])
def test_current_bindings_only_never_prove_model_execution(retest,asset):
    result = check(fixture(retest,asset),retest)
    assert result['status']=='RECEIPT_BINDINGS_VALIDATED'
    assert result['actual_model_execution']=='NOT_PROVEN_BY_RECEIPT_HELPER'
    assert result['owner_acceptance'] is False and result['model_accuracy']=='UNMEASURED'

def test_historical_retest_without_execution_hash_is_unverified():
    value=fixture(True)
    doc=json.loads(value[0]['conditions']);del doc['execution_request'];value[0]['conditions']=json.dumps(doc)
    assert check(value,True)['reason']=='MISSING_EXECUTION_CONTEXT_BINDING'

def test_generic_evaluation_scope_cannot_substitute_persisted_failed_task():
    value=fixture(True)
    value[5]['scope']='runtime.evaluation'
    with pytest.raises(helper.BindingError,match='Persisted failed evaluation'):
        check(value,True)

def test_adopted_correction_retest_binds_new_exact_body_and_immutable_id():
    value=fixture(True)
    task,knowledge,question,grant,_,prior,_=value
    knowledge.update(knowledge_id='adopted',body='已采用的中文纠正正文\n保留换行。')
    task['knowledge_version']='adopted@v1'
    previous={'question':question,'knowledge_id':'original','correction':{'correction_candidate_id':'adopted'}}
    prior['conditions']=json.dumps(previous)
    doc=json.loads(task['conditions'])
    doc.update(knowledge_id='adopted',prior={'conditions':previous})
    doc['request']['knowledge_id']='adopted'
    doc['execution_request']['request']=doc['request']
    doc['execution_request']['context_sha256']=helper.digest(knowledge['body'])
    task['conditions']=json.dumps(doc)
    assert check(value,True)['status']=='RECEIPT_BINDINGS_VALIDATED'
    knowledge['body']='旧正文'
    with pytest.raises(helper.BindingError,match='context SHA'):
        check(value,True)

def test_asset_context_without_exact_packet_is_unverified():
    result=check(fixture(True,True),True,False)
    assert result['status']=='UNVERIFIED' and result['reason']=='EXACT_CORE_ASSET_PACKET_NOT_EXPOSED'

@pytest.mark.parametrize('damage',['stub','undeclared_model','undeclared_endpoint','wrong_version','wrong_id','body',
                                   'wrong_context','missing_context','wrong_request','typed_conditions','wrong_schema','grant_bool'])
def test_invalid_or_missing_fields_never_validate(damage):
    value=fixture();task,knowledge,_,grant,*_=value;doc=json.loads(task['conditions'])
    if damage=='stub':doc['answer']['model']='local-stub'
    elif damage=='undeclared_model':doc['answer']['model']='different-real-name'
    elif damage=='undeclared_endpoint':doc['answer']['endpoint']='http://127.0.0.1:9999/v1'
    elif damage=='wrong_version':task['knowledge_version']='kid@v2'
    elif damage=='wrong_id':doc['knowledge_id']='other'
    elif damage=='body':knowledge['body']+='修改'
    elif damage=='wrong_context':doc['request']['context_sha256']='0'*64
    elif damage=='missing_context':del doc['request']['context_sha256']
    elif damage=='wrong_request':doc['request']['knowledge_id']='other'
    elif damage=='wrong_schema':doc['schema']='unknown'
    elif damage=='grant_bool':grant['version']=True;doc['request']['context_grant']['version']=True
    task['conditions']=doc if damage=='typed_conditions' else json.dumps(doc)
    with pytest.raises(helper.BindingError):check(value)

@pytest.mark.parametrize('damage',['prior_task','prior_snapshot','knowledge_sha','combined_sha'])
def test_retest_actual_lineage_and_two_separate_context_hashes(damage):
    value=fixture(True,True);doc=json.loads(value[0]['conditions'])
    if damage=='prior_task':value[5]['task_id']='other'
    elif damage=='prior_snapshot':doc['prior']['conditions']['question']='other'
    elif damage=='knowledge_sha':doc['execution_request']['knowledge_context_sha256']=doc['execution_request']['context_sha256']
    else:doc['execution_request']['context_sha256']=helper.digest(value[1]['body'])
    value[0]['conditions']=json.dumps(doc)
    with pytest.raises(helper.BindingError):check(value,True)

def test_declarations_require_current_worker_and_local_lane_not_adapter_stub():
    source=(ROOT/'services/python-workers/machine/worker_machine_answer.py').read_text()
    for lanes in ([],[{'protocol':'openai','base':'https://example.invalid/v1'}]):
        with pytest.raises(helper.BindingError):helper.declared_identities(source,lanes)
    with pytest.raises(helper.BindingError):
        helper.declared_identities(source.replace('qwen3.5-4b','local-stub'),[{'protocol':'openai','base':'http://127.0.0.1:1234/v1'}])
