import csv, hashlib, json, os, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
RUNS=ROOT/'.project-local/runs/be268a2d33'
CAND=RUNS/'zcode-assemble-c1-20261030-v8/artifacts/c1'
PACK=RUNS/'zc1n/artifacts/p'
def digest(p):
    with Path(native(p)).open('rb') as s: return hashlib.file_digest(s,'sha256').hexdigest()
def native(p):
    s=str(Path(p).absolute())
    return '\\\\?\\'+s if os.name=='nt' and not s.startswith('\\\\?\\') else s
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
identity=load(PACK/'mixed-core-identity.json')
files=identity['payload']['files']
bad=[]
for name,row in files.items():
    p=Path(native(CAND/name))
    if not p.is_file() or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:
        bad.append(name)
result={'candidate_members':{'count':len(files),'mismatches':bad},'sidecars':[]}
for name,row in identity['proof_sidecars'].items():
    p=PACK/row['path']
    result['sidecars'].append({'name':name,'exists':p.is_file(),'hash_match':p.is_file() and digest(p)==row['sha256']})
frozen=ROOT/'workspace/intake/20261029-stitch-zcode-handoff/ZCODE-仅本地'
caps=list(csv.DictReader((frozen/'04-186项能力归并映射-冻结输入.csv').open(encoding='utf-8-sig',newline='')))
roles=list(csv.DictReader((frozen/'05-22职责归并-冻结输入.csv').open(encoding='utf-8-sig',newline='')))
result['capabilities']={'intents':len(caps),'families':len({r['原能力ID'] for r in caps}),'unique_intents':len({(r['原能力ID'],r['原序号'],r['原文']) for r in caps}),'roles':len(roles),'unique_roles':len({r['原页ID'] for r in roles}),'operation_binding_states':sorted({r['细项后端操作绑定'] for r in caps}),'operation_evidence_states':sorted({r['细项运行证据'] for r in caps})}
protected=['docs/truth/CAPABILITY_ATLAS_V2.yaml','config/capability-map.v1.json','docs/current/AAOS-KNOWLEDGE-COMPATIBILITY-MATRIX.json']
result['protected_sources_unchanged']={p:subprocess.run(['git','diff','--quiet','c4531c1b','HEAD','--',p],cwd=ROOT).returncode==0 for p in protected}
diff=subprocess.check_output(['git','diff','--name-only','b2839075','HEAD','--','crates','services','frontend','src-tauri'],cwd=ROOT,text=True).splitlines()
result['source_changes_after_built_core']=diff
guest=load(RUNS/'zc1c8/output/conflict-journey-receipt.json')
result['guest_receipt_top_keys']=list(guest)
result['guest_execution']=load(RUNS/'zc1c8/output/conflict-run-execution.json')
result['guest_terminal']=load(RUNS/'zc1c8/output/guest-terminal.json')
result['stop_terminal']=load(RUNS/'zc1c8/sandbox-stop-v3-terminal.json')
result['baseline_snapshot_dirs']=[str(p) for p in RUNS.glob('*handoff*/artifacts/baseline-before-handoff')]
baseline=RUNS/'stitch-zcode-handoff-20261029/artifacts/baseline-before-handoff'
manifest=load(baseline/'manifest.json')
result['baseline_preservation']={'files':len(manifest['files']),'snapshot_mismatches':[],'current_missing':[]}
for row in manifest['files']:
    p=baseline/'files'/row['path']
    if not p.is_file() or digest(p)!=row['sha256']:
        result['baseline_preservation']['snapshot_mismatches'].append(row['path'])
    if not (ROOT/row['path']).is_file(): result['baseline_preservation']['current_missing'].append(row['path'])
result['git_status']=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
(OUT/'integrity-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='guest_execution'},ensure_ascii=False,indent=2))
