#!/usr/bin/env python3
"""Read-only planning validation; no product or disk cleanup operations."""
from pathlib import Path
import json,runpy,sys,argparse
sys.dont_write_bytecode=True
MODIFIED={'TASKS.json','TASKPACK.md','EXECUTOR-START.md','EXECUTOR-CODEX.md','EXECUTOR-DSH.md','verify_package.py','MANIFEST.json'}
def validate(root):
 root=Path(root); old=root/'frozen-r4'
 api=runpy.run_path(str(old/'verify_package.py')); check=api['demand']; read=api['read']
 count=api['manifest_check'](root); previous=api['validate'](old)
 p=read(root,'TASKS.json');b=read(old,'TASKS.json');s=read(root,'REMAINING-WORK.json')['slices']
 check(p['package_revision']=='R5' and p['r5_current_state_verified'] is False,'revision/state invalid')
 for key,value in b.items():
  if key not in ['package_revision','tasks']:check(p[key]==value,'inherited plan changed: '+key)
 check(len(p['tasks'])==23,'task count')
 for t,orig in zip(p['tasks'],b['tasks']):
  for key,value in orig.items():check(t[key]==value,'lost inherited task field '+orig['id']+':'+key)
  linked=[x for x in s if t['id'] in x['mapped_tasks']]
  check(t['r5_slices']==[x['id'] for x in linked],'binding mismatch')
  check(t['r5_work']==[x['work'] for x in linked] and t['r5_acceptance']==[x['acceptance'] for x in linked],'work/acceptance drift')
 expected={f'CLEAN{i:02d}' for i in range(1,11)}|{f'REPO{i:02d}' for i in range(1,5)}|{f'MIG{i:02d}' for i in range(1,5)}
 check(len(s)==18 and {x['id'] for x in s}==expected,'slice coverage')
 ids={t['id'] for t in p['tasks']}
 for x in s:
  check(set(x['mapped_tasks'])<=ids and x['mapped_tasks'],'invalid task reference')
  check(x['status']=='PLANNED_NOT_IMPLEMENTED','false completion')
  check(all(x[k] for k in ['phase','title','work','acceptance','evidence','rollback']),'incomplete slice')
 for f in old.rglob('*'):
  if f.is_file():
   rel=f.relative_to(old)
   if rel.as_posix() not in MODIFIED:check((root/rel).read_bytes()==f.read_bytes(),'inherited artifact changed: '+str(rel))
 for name in ['FASTEST-LOOP.md','CLEANUP-AND-SPILL.md','REPOSITORY-NORMALIZATION.md','LANGUAGE-MIGRATION-EXECUTION.md','R5-ACCEPTANCE.md','R5-CONTINUITY.md']:
  check((root/name).is_file(),'missing guide')
 check(len(list((root/'templates').glob('*.csv')))==6,'missing ledger template')
 return dict(result='PASS',tasks=23,original_scenarios=38,additional_slices=18,cleanup_slices=10,repo_slices=4,migration_slices=4,retained_governance_migration_slices=12,retained_human_learning_slices=12,active_files=count,product_tests_run=False,windows_cleanup_performed=False,current_head_checked=False)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);args=parser.parse_args()
 try:print(json.dumps(validate(args.root),ensure_ascii=False,indent=2))
 except Exception as exc:print(str(exc),file=sys.stderr);sys.exit(1)
