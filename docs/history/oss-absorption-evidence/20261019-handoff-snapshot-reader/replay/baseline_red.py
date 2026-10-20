"""前轮严格绑定的owned Core无snapshot路由；原问题负控制，非新源码资格。"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
binding=json.loads((ROOT/'.project-local/audits/implementation-continuation-20261019/native-owned-binding.json').read_text(encoding='utf-8'))
core=ROOT/binding['core_path']
assert hashlib.sha256(core.read_bytes()).hexdigest()==binding['core_sha256']
db=OUT/'baseline-owned.sqlite'
assert not db.exists()
token='a'*64
process=subprocess.Popen([str(core),str(db),'0'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
record=dict(pid=process.pid,created_at=datetime.now(timezone.utc).isoformat(),command=[str(core),str(db),'0'],cwd=str(ROOT),core_sha256=binding['core_sha256'])
def call(path,body=None):
    request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=None if body is None else json.dumps(body).encode(),headers={'x-archeaxis-launch-token':token,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=4) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as error:return error.code,None
try:
    process.stdin.write((json.dumps(dict(protocol='archeaxis.desktop-launch/v2',actor='human',launch_token=token,machine_token='b'*64,session_id='c'*32))+'\n').encode());process.stdin.close()
    # 此exact owned Core有界首行ready，输出不写凭据/正文。
    line=process.stdout.readline().decode();assert '127.0.0.1:' in line
    port=int(line.split('127.0.0.1:')[1].strip());record['port']=port
    status,workspace=call('/api/v1/workspace/ui-state');assert status==200
    status,document=call('/api/v1/documents',dict(create_request_id='snapshot-baseline',title='SYNTHETIC',editor_json=dict(type='doc',content=[])));assert status in (200,201)
    now=int(time.time()*1000)
    proposal=dict(schema='archeaxis.project-handoff/v1',protocol='archeaxis.project-observer/v1',idempotency_key='1'*32,producer=dict(namespace='archeaxis',workspace_id=workspace['workspace_id'],restore_epoch=workspace['restore_epoch']),consumer=dict(namespace='work-lab',instance_id='2'*32),created_at_ms=now,expires_at_ms=now+30000,authority='PREPARATION_ONLY',payload=dict(kind='context',source=dict(reference={key:document[key] for key in ('document_id','version','content_sha256')},selection=dict(kind='whole_object'),selection_qualification='UNVERIFIED'),purpose='research',authorization_scope='REFERENCE_METADATA_ONLY'))
    status,_=call('/api/v1/project-handoff/snapshot',proposal);record['actual_status']=status;record['required_status']=200
    print('required fixed-reference snapshot HTTP200; observed HTTP'+str(status),flush=True)
    assert status==200,'EXPECTED_RED: previous exact owned Core has no fixed snapshot reader'
finally:
    process.kill();process.wait(timeout=5);record['owned_process_exited']=process.poll() is not None
    (OUT/'baseline-red-process.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
