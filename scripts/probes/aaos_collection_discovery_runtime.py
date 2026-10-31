"""Discover saved collections through the actual qualified Core in an independent authored restore.

Preserves the prior collection/reference/research/learning objects. Presence is not
collection schema validity or external-software parity. No model or public queries.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
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
    dev = office.load('collection_discovery_dev', ROOT / 'scripts/runtime/dev.py')
    run = dev.safe_path(Path(os.environ['ARCHEAXIS_RUN_ROOT']))
    paths = dev.layout(ROOT, run.name)
    require(run == paths['run'], 'Foreign run')

    def owned(path):
        path = dev.safe_path(path)
        path.relative_to(paths['dev'] / 'runs')
        return path

    candidate, input_path = owned(args.candidate), owned(args.input_receipt)
    prior = json.loads(input_path.read_text(encoding='utf-8'))
    require(prior['status'] == 'PASS_AUTHORED_COLLECTION_SUBSET' and prior['independent_restore_equal'], 'Unqualified input')
    require(all(x['wait_reaped'] for x in prior['stopped']), 'Prior Core still live')
    manifest = json.loads((candidate / 'candidate-manifest.json').read_text(encoding='utf-8'))
    build_path = owned(Path(manifest['build_receipt']['path']))
    require(sha(build_path.read_bytes()) == manifest['build_receipt']['sha256'], 'Build receipt changed')
    build = json.loads(build_path.read_text(encoding='utf-8'))
    require(build['status'] == 'PASS' and build['source_consistent'], 'Unqualified build')
    names = ['ArcheAxis.exe', 'core/archeaxis-api.exe', 'worker-profile.json', 'backend-runtime-manifest.json']
    before = {n: office.identity(candidate / n) for n in names}
    require(all(v['sha256'] == manifest['files'][n]['sha256'] for n,v in before.items()), 'Candidate hash mismatch')
    require(before['core/archeaxis-api.exe']['sha256'] == build['core_sha256'], 'Wrong Core')
    backup = prior['backup']
    backup_file = owned(Path(prior['workspace']) / 'backups' / backup['filename'])
    require(sha(backup_file.read_bytes()) == backup['sha256'], 'Input backup changed')
    output = paths['artifacts'] / 'collection-discovery-runtime.json'
    require(not output.exists(), 'Choose a new run ID')
    receipt = {'schema':'archeaxis.collection-discovery-runtime/v1','status':'RUNNING',
               'candidate':str(candidate),'candidate_identity':before,'input':office.identity(input_path),
               'input_backup':office.identity(backup_file),'steps':[],'stopped':[],
               'materials':'SYNTHETIC_AUTHORED','execution':'ACTUAL_CORE_HTTP_SQLITE',
               'limits':['Presence is not schema validity or external-platform parity','No native IPC/installed/Green/Owner/CI acceptance','No models/public queries/knowledge approval']}
    launcher = office.load('collection_discovery_launcher', ROOT / 'scripts/release/backend_launcher.py')
    client = office.load('collection_discovery_client', ROOT / 'shared/core_client.py')
    child = None
    base = token = None

    def checkpoint():
        output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

    def call(method,path,body=None,expected=200):
        status,value = client.call(base,method,path,token,body,timeout=45)
        receipt['steps'].append({'method':method,'path':path,'status':status})
        checkpoint()
        require(status == expected,f'{method} {path}: {status}, expected {expected}')
        return value

    def stop():
        nonlocal child
        helper.stop_owned(child,launcher,receipt['stopped'])
        child = None
        checkpoint()

    def restore(backup_path,target):
        target.mkdir(exist_ok=False)
        result = subprocess.run([str(candidate/'core/archeaxis-api.exe'),'--maintenance-restore',str(target/'workspace.sqlite'),str(backup_path)],capture_output=True,text=True,encoding='utf-8',timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        require(result.returncode == 0 and json.loads(result.stdout).get('verified'),'Independent restore failed')
        return {'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}

    def verify_summary(document, present):
        listing = call('GET','/api/v1/documents')
        require(listing['next_cursor'] is None, 'Authored fixture grew beyond this probe page')
        require(all(type(d.get('has_collection')) is bool for d in listing['documents']), 'Unknown presence in new Core')
        summary = next(d for d in listing['documents'] if d['document_id'] == document['document_id'])
        require(summary['has_collection'] is present and summary['version'] == document['version'] and summary['content_sha256'] == document['content_sha256'], 'Presence snapshot mismatch')
        require('editor_json' not in summary and 'text_projection' not in summary, 'Summary exposed a body')
        return listing

    try:
        workspace = paths['artifacts']/'collection-discovery-workspace'
        receipt['input_restore'] = restore(backup_file,workspace)
        receipt['workspace'] = str(workspace)
        child,base,token,_ = helper.hidden_start(office,candidate,workspace,launcher)
        document, target, latest = prior['document'],prior['target'],prior['latest_target']
        doc_path = f"/api/v1/documents/{document['document_id']}"
        target_path = f"/api/v1/documents/{target['document_id']}"
        expected = {doc_path:document,target_path:latest,target_path+'/versions/1':target}
        baseline_paths = [f"/api/v1/documents/{prior['baseline_document_id']}", f"/api/v1/learning/events/{prior['baseline_item_key']}"]
        expected.update({p:call('GET',p) for p in baseline_paths})
        for p,v in expected.items(): require(call('GET',p) == v, 'Input restore changed '+p)
        verify_summary(document,True)
        verify_summary(latest,False)
        for kind,projection in prior['projections'].items():
            p = doc_path+f'/collection?view_id={kind}&version=1&offset=0&limit=20'
            require(call('GET',p) == projection, 'New Core changed existing saved projection')
            expected[p] = projection
        plain = {'type':'doc','attrs':{'foreign':{'keep':True}},'content':[]}
        created = call('POST','/api/v1/documents',{'title':'集合标记变更验证','create_request_id':uuid.uuid4().hex,'editor_json':plain},201)
        created_path = f"/api/v1/documents/{created['document_id']}"
        verify_summary(created,False)
        with_collection = {**plain,'attrs':{**plain['attrs'],'archeaxis_collection':{'schema':'archeaxis.collection/v1','properties':[],'records':[],'views':[{'view_id':'table','name':'Table','kind':'table'}]}}}
        added = call('PUT',created_path+'/draft',{'expected_version':1,'editor_json':with_collection})
        verify_summary(added,True)
        removed = call('PUT',created_path+'/draft',{'expected_version':2,'editor_json':plain})
        listing = verify_summary(removed,False)
        require(call('GET',created_path+'/versions/2') == added, 'Collection history was removed')
        expected.update({created_path:removed,created_path+'/versions/2':added,'/api/v1/documents':listing})
        require(call('GET',doc_path) == document, 'Reads changed existing collection')
        receipt.update(document=document,target=target,latest_target=latest,projections=prior['projections'],document_id=document['document_id'],target_id=target['document_id'],baseline_document_id=prior['baseline_document_id'],baseline_item_key=prior['baseline_item_key'],saved_presence_changes=[False,True,False],historical_collection_preserved=True)
        stop()
        child,base,token,_ = helper.hidden_start(office,candidate,workspace,launcher)
        for p,v in expected.items(): require(call('GET',p) == v, 'Restart changed '+p)
        receipt['restart_equal'] = True
        backup = call('POST','/api/v1/workspace/backups',{},201)
        require(backup['verified'], 'Backup unverified')
        receipt['backup'] = backup
        saved = owned(workspace/'backups'/backup['filename'])
        require(sha(saved.read_bytes()) == backup['sha256'], 'Output backup changed')
        stop()
        restored = paths['artifacts']/'independent-collection-discovery-restore'
        receipt['output_restore'] = restore(saved,restored)
        child,base,token,_ = helper.hidden_start(office,candidate,restored,launcher)
        for p,v in expected.items(): require(call('GET',p) == v, 'Restore changed '+p)
        receipt.update(status='PASS_AUTHORED_DISCOVERY_SUBSET',independent_restore_equal=True,independent_workspace=str(restored),baseline_preserved=True,read_queries_do_not_write=True)
    except Exception as error:
        receipt.update(status='FAIL',error=f'{type(error).__name__}: {error}')
    finally:
        if child is not None:
            try: stop()
            except Exception as error: receipt.update(status='FAIL',cleanup_error=str(error))
        receipt['candidate_unchanged'] = {n:office.identity(candidate/n) for n in names} == before
        if not receipt['candidate_unchanged']: receipt['status'] = 'FAIL'
        checkpoint()
    print(json.dumps({'status':receipt['status'],'calls':len(receipt['steps']),'receipt':str(output)},ensure_ascii=False))
    return 0 if receipt['status'] == 'PASS_AUTHORED_DISCOVERY_SUBSET' else 1


if __name__ == '__main__': raise SystemExit(main())
