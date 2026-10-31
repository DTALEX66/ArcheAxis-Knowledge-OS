import hashlib, json, os, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
INDEX = ROOT / 'workspace/intake/20261030-zcode-backend-closure/evidence-index.json'
raw = INDEX.read_text(encoding='utf-8')
result = {'head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'original_index_sha256': hashlib.sha256(INDEX.read_bytes()).hexdigest(), 'strict_json': None, 'checks': []}
try:
    data = json.loads(raw)
    result['strict_json'] = 'PASS'
except json.JSONDecodeError as exc:
    result['strict_json'] = {'status':'FAIL','line':exc.lineno,'column':exc.colno,'message':exc.msg}
    # Diagnostic recovery in memory only. The delivered source is never changed.
    repaired, count = raw, 0
    for _ in range(20):
        try:
            data = json.loads(repaired)
            break
        except json.JSONDecodeError as issue:
            if issue.msg != 'Invalid \\escape': raise
            repaired = repaired[:issue.pos] + '\\' + repaired[issue.pos:]
            count += 1
    else: raise RuntimeError('diagnostic recovery limit')
    result['diagnostic_recovery'] = {'invalid_escape_count': count, 'source_unchanged': True}

def check(label, path, expected=None):
    path = Path(path)
    if not path.is_absolute(): path = ROOT / path
    path = path.resolve()
    if not path.is_relative_to(ROOT):
        result['checks'].append({'label':label,'status':'OUTSIDE_SCOPE_NOT_READ','path':str(path)})
        return
    entry={'label':label,'path':str(path),'exists':path.is_file()}
    if entry['exists']:
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
        entry.update(bytes=path.stat().st_size,sha256=h.hexdigest())
        if expected: entry['hash_match']=entry['sha256']==expected
        if path.suffix=='.json' and entry['bytes'] < 3000000:
            try:
                receipt=json.loads(path.read_text(encoding='utf-8-sig'))
                entry['receipt_summary']={k:receipt[k] for k in ('status','ok','evidence_level','qualification_scope','complete_lifecycle_verified','source_commit','source_consistent','child_exit_code','failed_stage') if k in receipt}
            except (json.JSONDecodeError,UnicodeError) as exc: entry['parse_error']=str(exc)
    result['checks'].append(entry)

runs=ROOT / '.project-local/runs/be268a2d33'
for item in data['verification_runs_20261030']['runs']:
    check('original_test:'+item['run'],runs/item['run']/'artifacts/execution.json',item['execution_sha256'])
def walk(node,label='index'):
    if isinstance(node,dict):
        if 'path' in node and isinstance(node['path'],str):
            if node['path'].startswith(('.project-local/','.project-local\\','workspace/')):
                check(label,node['path'],node.get('sha256'))
        for key,val in node.items(): walk(val,label+'.'+key)
    elif isinstance(node,list):
        for i,val in enumerate(node): walk(val,label+f'[{i}]')
walk(data)
for label,relative in data['historical_evidence_cited_not_rebound'].items():
    if relative.startswith('.project-local/'):
        check('historical:'+label,relative.split(' (')[0])
for run in ['zcode-stage-newcore-20261030','zcode-c1-j2-public-20261030','zcode-c1-learning-20261030','zcode-c1-j5-template-20261030','zcode-c1-colearning-smoke-20261030-v2','zclint-test-20261030','zc1r-v9']:
    folder=runs/run
    for path in sorted((folder/'artifacts').glob('*.json')):
        check('campaign:'+run,path)
for pattern in ['zc1i2/sandbox-stop*terminal*.json','zc1c8/sandbox-stop*terminal*.json','zc1c8/output/*.json']:
    for path in runs.glob(pattern):
        if path.stat().st_size < 300000: check('sandbox_aux',path)
result['counts']={'files_checked':len(result['checks']), 'missing':sum(not x.get('exists',False) for x in result['checks']), 'hash_mismatch':sum(x.get('hash_match') is False for x in result['checks'])}
(OUT/'evidence-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2))
for item in result['checks']:
    if not item.get('exists') or item.get('hash_match') is False:
        print(json.dumps(item,ensure_ascii=False))
