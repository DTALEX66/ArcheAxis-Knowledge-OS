import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
RUNS=ROOT/'.project-local/runs/be268a2d33'
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
names=['codex-audit-domain-20261030-v2','codex-audit-api-20261030','codex-audit-cancel-20261030','codex-audit-canvas-unit-20261030','codex-audit-python-20261030','codex-audit-j2-20261030','codex-audit-proof-20261030','codex-audit-realmodel-20261030','codex-audit-evidence-20261030-v3','codex-audit-integrity-20261030-v2','codex-audit-smoke-negative-20261030']
checks=[]
for name in names:
    path=RUNS/name/'artifacts/execution.json'
    e=load(path)
    assert e['source_commit']=='1e78ab9332164bcf1248ff33216d62e5f8b250a0'
    assert e['status']=='LOCAL_PASS' and e['source_consistent'] and e['exit_code']==0
    checks.append({'run':name,'receipt':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'status':e['status'],'source_consistent':e['source_consistent']})
rust_names=names[:4]
rust_passed=sum(sum(int(v) for v in re.findall(r'test result: ok\. (\d+) passed;', (RUNS/n/'logs/execution.log').read_text(encoding='utf-8'))) for n in rust_names)
assert rust_passed==99
ev=load(OUT/'evidence-validation.json')
integrity=load(OUT/'integrity-result.json')
j2=load(RUNS/'codex-audit-j2-20261030/artifacts/public-research-receipt.json')
model=load(RUNS/'codex-audit-realmodel-20261030/artifacts/colearning-real-model/d951a28e0d194207a2cc6fdde425ba3d/receipt.json')
result={'schema':'aaos.codex-independent-zcode-audit/v1','date':'2026-10-30','timezone':'Asia/Shanghai',
        'source_commit':'1e78ab9332164bcf1248ff33216d62e5f8b250a0','overall':'PARTIAL_NOT_UNCONDITIONAL_AUDIT_PASS',
        'engineering_slice':'VERIFIED_WITHIN_REVIEWED_SCOPE','findings':[
            {'id':'F01','priority':'P1','state':'UNVERIFIED_OWNER_WAIVER'},
            {'id':'F02','priority':'P2','state':'FAIL_STRICT_JSON'},
            {'id':'F03','priority':'P2','state':'PARTIAL_STALE_FINAL_STATUS'},
            {'id':'F04','priority':'P2','state':'PARTIAL_STOP_STATUS_COUNT_CONFLICT'},
            {'id':'F05','priority':'P2','state':'PARTIAL_SEMANTIC_VALIDATION_GAP'}],
        'independent_verification':{'rust_passed':rust_passed,'python_passed':141,'python_skipped':1,
            'public_j2':{'status':j2['status'],'ok':j2['ok'],'steps':len(j2['steps']),'evidence_level':j2['evidence_level']},
            'real_model':{'evidence_class':model['evidence_class'],'failed_stage':model['failed_stage'],'receipt':str((RUNS/'codex-audit-realmodel-20261030/artifacts/colearning-real-model/d951a28e0d194207a2cc6fdde425ba3d/receipt.json').relative_to(ROOT))},
            'candidate_members':integrity['candidate_members'], 'sidecars':integrity['sidecars'],
            'baseline_preservation':integrity['baseline_preservation'],
            'explicit_reference_hash_checks':sum('hash_match' in r for r in ev['checks']),
            'explicit_reference_hash_mismatches':ev['counts']['hash_mismatch']},
        'runs':checks,'cloud_ci':'NOT_EXECUTED_BY_OWNER_LOCAL_ONLY_BOUNDARY',
        'fresh_installation':'NOT_EXECUTED_RECEIPTS_REVIEWED_ONLY','real_cloud_inference':'DEFERRED_UNEXECUTED',
        'owner_acceptance':'NOT_EXECUTED','product_code_changed':False,
        'git_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)}
assert not result['git_status']
assert all(s['hash_match'] for s in integrity['sidecars']) and not integrity['candidate_members']['mismatches']
assert not integrity['baseline_preservation']['snapshot_mismatches']
for name in ['审计报告.md','audit_evidence.py','integrity.py','smoke_negative_control.py','finalize.py','evidence-validation.json','integrity-result.json','smoke-negative-control.json']:
    result.setdefault('artifacts',[]).append({'path':name,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()})
(OUT/'audit-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'overall':result['overall'],'verification':result['independent_verification'],'runs':len(checks),'git_clean':not result['git_status']},ensure_ascii=False,indent=2))
