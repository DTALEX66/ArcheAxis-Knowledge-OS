"""Saved collection reader probe: authored records, actual qualified Core, isolated restore.

No external-platform/version parity, native-host, installed or Owner acceptance claim.
Uses normal Document APIs only; computed projections must not change saved metadata.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path, PureWindowsPath
import subprocess
import uuid
import aaos01_office_runtime_loop as office
import aaos_public_research_runtime_loop as helper
from aaos_research_learning_runtime import require, sha
ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--input-receipt', type=Path, required=True)
    args = parser.parse_args()
    dev = office.load('collection_reader_dev', ROOT / 'scripts/runtime/dev.py')
    run = dev.safe_path(Path(os.environ['ARCHEAXIS_RUN_ROOT']))
    paths = dev.layout(ROOT, run.name)
    require(run == paths['run'], 'Foreign run')
    def owned(path):
        path = dev.safe_path(path); path.relative_to(paths['dev'] / 'runs'); return path
    candidate = owned(args.candidate)
    prior_path = owned(args.input_receipt)
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    require(prior['status'] == 'PASS_AUTHORED_SCAN_FIXTURES' and prior['independent_restore_equal'], 'Unqualified input')
    manifest = json.loads((candidate / 'candidate-manifest.json').read_text(encoding='utf-8'))
    previous = json.loads((owned(Path(prior['candidate'])) / 'candidate-manifest.json').read_text(encoding='utf-8'))
    require(manifest['files'].keys() == previous['files'].keys() and all(v == previous['files'][n] for n,v in manifest['files'].items() if n != 'ArcheAxis.exe'), 'Backend changed')
    identity_names = ['ArcheAxis.exe','core/archeaxis-api.exe','worker-profile.json','backend-runtime-manifest.json']
    before = {n:office.identity(candidate / n) for n in identity_names}
    require(all(v['sha256'] == manifest['files'][n]['sha256'] for n,v in before.items()), 'Candidate hash mismatch')
    baseline_receipt = json.loads(owned(Path(prior['input']['path'])).read_text(encoding='utf-8'))
    baseline_paths = [f"/api/v1/documents/{baseline_receipt['document_id']}", f"/api/v1/learning/events/{baseline_receipt['item_key']}"]
    backup_file = owned(Path(prior['workspace']) / 'backups' / PureWindowsPath(json.loads(prior['output_restore']['stdout'])['backup']).name)
    output = paths['artifacts'] / 'collection-reader-runtime.json'
    require(not output.exists(), 'Choose a new run ID')
    receipt = {'schema':'archeaxis.collection-reader-runtime/v1','status':'RUNNING','steps':[],'stopped':[],
               'candidate':str(candidate),'candidate_identity':before,'input':office.identity(prior_path),
               'input_backup':office.identity(backup_file),'baseline_document_id':baseline_receipt['document_id'],'baseline_item_key':baseline_receipt['item_key'],
               'materials':'SYNTHETIC_AUTHORED','execution':'ACTUAL_CORE_HTTP_SQLITE',
               'limits':['No external software/version parity or full market inventory','No native host/installed/Owner acceptance','No models/public queries/knowledge approval']}
    launcher = office.load('collection_reader_launcher', ROOT / 'scripts/release/backend_launcher.py')
    client = office.load('collection_reader_client', ROOT / 'shared/core_client.py')
    child = None; base = token = None
    def checkpoint(): output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(method,path,body=None,expected=200):
        status,value = client.call(base,method,path,token,body,timeout=45)
        receipt['steps'].append({'method':method,'path':path,'status':status});checkpoint()
        require(status == expected,f'{method} {path}: {status}, expected {expected}');return value
    def stop():
        nonlocal child
        helper.stop_owned(child,launcher,receipt['stopped']);child=None;checkpoint()
    def restore(backup,target):
        target.mkdir(exist_ok=False)
        result = subprocess.run([str(candidate/'core/archeaxis-api.exe'),'--maintenance-restore',str(target/'workspace.sqlite'),str(backup)],capture_output=True,text=True,encoding='utf-8',timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        require(result.returncode == 0 and json.loads(result.stdout).get('verified'),'Independent restore failed')
        return {'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
    def editor(text,attrs=None):
        return {'type':'doc','attrs':attrs or {},'content':[{'type':'paragraph','content':[{'type':'text','text':text}]}]}
    try:
        workspace = paths['artifacts']/'collection-workspace'
        receipt['input_restore']=restore(backup_file,workspace);receipt['workspace']=str(workspace)
        child,base,token,_=helper.hidden_start(office,candidate,workspace,launcher)
        baseline={p:call('GET',p) for p in baseline_paths}
        target=call('POST','/api/v1/documents',{'title':'集合固定版本原文','create_request_id':uuid.uuid4().hex,'editor_json':editor('固定版本一：不可被新版替换。')},201)
        target_path=f"/api/v1/documents/{target['document_id']}"
        engine='archeaxis.bounded-formula/v1'
        definition={'schema':'archeaxis.collection/v1','properties':[
            {'property_id':'name','name':'名称','kind':'text'},{'property_id':'score','name':'数量','kind':'number'},
            {'property_id':'state','name':'状态','kind':'select','options':['待整理','已整理']},{'property_id':'day','name':'日期','kind':'date'},
            {'property_id':'double','name':'双倍数量','kind':'formula','formula':{'dialect':engine,'engine_version':engine,'expression':{'op':'multiply','left':{'op':'property','key':'score'},'right':{'op':'literal','value':2}},'dependencies':['score'],'output_type':'number','original_expression':'score * 2','source_payload':{'authored':True}}}],
            'records':[{'record_id':f'authored_{i:02}','reference':{'kind':'document','document_id':target['document_id'],'version':1},'values':{'name':f'资料条目 {i:02}','score':i,'state':'待整理' if i%2==0 else '已整理','day':f'2026-10-{22+i%3:02}'}} for i in reversed(range(26))],
            'views':[{'view_id':k,'name':n,'kind':k,'sort':[{'property_id':'score','descending':False}],**({'group_by':'state'} if k=='board' else {'date_property':'day'} if k=='calendar' else {})} for k,n in [('table','表格'),('list','列表'),('board','看板'),('calendar','日历'),('gallery','画廊')]],'source_payload':{'foreign':{'keep':[1,2,3]}}}
        definition['views'].append({'view_id':'filtered','name':'数量大于20','kind':'list','filter':{'op':'greater_than','property_id':'score','value':20},'sort':[{'property_id':'score','descending':False}]})
        document=call('POST','/api/v1/documents',{'title':'保存版集合阅读验证','create_request_id':uuid.uuid4().hex,'editor_json':editor('集合读取使用保存版本；正文与外来字段继续保全。',{'archeaxis_collection':definition,'foreign':{'keep':True}})},201)
        path=f"/api/v1/documents/{document['document_id']}"
        newer=call('PUT',target_path+'/draft',{'expected_version':1,'editor_json':editor('新版二：不应出现在固定版本一引用中。')})
        require(newer['version']==2 and call('GET',target_path+'/versions/1')==target,'Fixed version changed')
        expected={**baseline,path:document,target_path:newer,target_path+'/versions/1':target}
        projections={}
        for kind in ['table','list','board','calendar','gallery','filtered']:
            qpath=path+f'/collection?view_id={kind}&version=1&offset=0&limit=20'
            projection=call('GET',qpath);projections[kind]=projection;expected[qpath]=projection
            start=21 if kind=='filtered' else 0;total=5 if kind=='filtered' else 26
            require(projection['total']==total and [r['values']['score'] for r in projection['items']]==list(range(start,min(26,start+20))),'Filter/sort/page differs')
            require(projection['content_sha256']==document['content_sha256'] and projection['version']==1,'Snapshot differs')
            require(all(r['values']['double']==r['values']['score']*2 and not r['formula_errors'] and r['reference']['version']==1 for r in projection['items']),'Formula/reference differs')
            if kind!='filtered':
                second_path=path+f'/collection?view_id={kind}&version=1&offset=20&limit=20'
                second=call('GET',second_path);expected[second_path]=second
                require([r['values']['score'] for r in second['items']]==list(range(20,26)) and second['next_offset'] is None,'Second page differs')
        require(call('GET',path)==document,'Projection wrote metadata')
        receipt.update(document=document,target=target,latest_target=newer,projections=projections,document_id=document['document_id'],target_id=target['document_id'])
        stop();child,base,token,_=helper.hidden_start(office,candidate,workspace,launcher)
        for p,v in expected.items(): require(call('GET',p)==v,'Restart changed '+p)
        receipt['restart_equal']=True
        backup=call('POST','/api/v1/workspace/backups',{},201)
        require(backup['verified'],'Unverified backup');receipt['backup']=backup
        saved=owned(workspace/'backups'/backup['filename']);require(sha(saved.read_bytes())==backup['sha256'],'Backup hash differs')
        stop();restored=paths['artifacts']/'independent-collection-restore';receipt['output_restore']=restore(saved,restored)
        child,base,token,_=helper.hidden_start(office,candidate,restored,launcher)
        for p,v in expected.items(): require(call('GET',p)==v,'Restore changed '+p)
        receipt.update(status='PASS_AUTHORED_COLLECTION_SUBSET',independent_restore_equal=True,independent_workspace=str(restored),read_queries_do_not_write=True,baseline_preserved=True)
    except Exception as error: receipt.update(status='FAIL',error=f'{type(error).__name__}: {error}')
    finally:
        if child is not None:
            try: stop()
            except Exception as error: receipt.update(status='FAIL',cleanup_error=str(error))
        receipt['candidate_unchanged']={n:office.identity(candidate/n) for n in identity_names}==before
        if not receipt['candidate_unchanged']: receipt['status']='FAIL'
        checkpoint()
    print(json.dumps({'status':receipt['status'],'calls':len(receipt['steps']),'receipt':str(output)},ensure_ascii=False))
    return 0 if receipt['status']=='PASS_AUTHORED_COLLECTION_SUBSET' else 1

if __name__=='__main__': raise SystemExit(main())
