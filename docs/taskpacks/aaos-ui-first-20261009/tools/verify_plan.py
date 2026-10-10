"""Validate this derived planning delivery; never execute product/source-pack scripts.

Run with the project's existing Python. Default is read-only; --write-receipt
refreshes only VALIDATION.json. Source ZIP CRC and source bytes are checked locally.
"""
from pathlib import Path
import argparse, collections, csv, datetime, hashlib, json, re, zipfile, sys

PLAN=Path(__file__).resolve().parents[1]
ROOT=PLAN.parents[2]

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def csvrows(p): return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-receipt',action='store_true')
    args=parser.parse_args()
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    checks=[];errors=[]
    def check(name,ok,detail):
        checks.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':detail})
        if not ok:errors.append(name)
    t=load(PLAN/'TASKS.json');tasks=t['tasks'];byid={x['id']:x for x in tasks}
    check('task_ids_unique',len(byid)==len(tasks)==28,len(tasks))
    check('dependencies_exist',all(d in byid for x in tasks for d in x['depends_on']),'all declared dependencies')
    check('conditional_dependencies_exist',all(x['task'] in byid and x['depends_on'] in byid and x['condition'] for x in t['conditional_dependencies']),'advanced profiles retain original foundation dependencies')
    done=set();active=set()
    def visit(k):
        if k in active:raise ValueError(k)
        if k in done:return
        active.add(k)
        for d in byid[k]['depends_on']:visit(d)
        active.remove(k);done.add(k)
    try:
        for k in byid:visit(k)
        dag=True
    except (ValueError,KeyError):dag=False
    check('dependency_dag',dag,'no missing/cyclic dependency')
    first=set(t['first_slice_tasks'])
    check('first_slice_dependencies_closed',all(d in first for k in first for d in byid[k]['depends_on']),sorted(first))
    check('all_tasks_have_scope_acceptance_verification',all(x['write_set'] and x['implementation'] and x['acceptance'] and x['verification'] for x in tasks),'28 independently described slices')
    check('implementation_not_executed',all(x['status']=='NOT_EXECUTED' and x['evidence_level']=='NO_EVIDENCE' for x in tasks) and t['implementation_status']=='NOT_EXECUTED','planning is not implementation PASS')
    storage=byid['S01'].get('subtasks',[])
    check('three_storage_subtasks_declared',len(storage)==3 and {x['id'] for x in storage}=={'S01.A','S01.B','S01.C'} and all(x['status']=='NOT_EXECUTED' and x['source_roots'] and x['acceptance'] for x in storage),'whole repo / spillover / history decision, not executed')
    main_prompt=(PLAN/'HANDOFF-EXECUTE.md').read_text(encoding='utf-8-sig')
    storage_prompt=(PLAN/'HANDOFF-STORAGE-CLEANUP.md').read_text(encoding='utf-8-sig')
    check('storage_in_both_handoff_prompts',all(k in main_prompt and k in storage_prompt for k in ['S01.A','S01.B','S01.C','docs/history/','.git/info/exclude','SHA-256','UNRESOLVED']),'full and standalone prompts contain scope and preservation rules')
    check('root_handoff_exact_mirror',digest(ROOT/'AAOS-后续执行交接提示词-20261009.md')==digest(PLAN/'HANDOFF-EXECUTE.md'),'copy/paste root prompt matches canonical delivery')
    pages=csvrows(PLAN/'PAGE-PLAN.csv')
    check('22_pages_exact',sorted(x['页面ID'] for x in pages)==[f'{n:02}' for n in range(1,23)],len(pages))
    check('page_targets_exist',all(k in byid for x in pages for k in x['后续切片'].split(';')),'all page roles mapped')
    req=csvrows(PLAN/'REQUIREMENT-CROSSWALK.csv')
    expected={f'R{n:03}' for n in range(1,50)}|{f'CAP-{n:04}' for n in range(10,161,10)}|{f'Q{n:02}' for n in range(16)}|{f'F{n:02}' for n in range(15)}
    check('96_source_ids_exact',len(req)==96 and {x['包内追踪ID'] for x in req}==expected,len(req))
    check('requirement_targets_exist',all(k in byid for x in req for k in x['后续切片'].split(';')),'no orphan requirement')
    detail=csvrows(PLAN/'DESIGN-DETAIL-CROSSWALK.csv')
    check('186_design_details',len(detail)==186 and len({(x['父CAP'],x['源内顺序']) for x in detail})==186,len(detail))
    check('design_targets_exist',all(k in byid for x in detail for k in x['承接切片'].split(';')),'design text is not approved baseline')
    source=load(PLAN/'SOURCE-REGISTER.json')
    files=source['extracted_members'];member_by_name={x['member']:x for x in files}
    rawreq=next(x for x in files if x['member']=='AAOS_Final_Task_Package_20261009/04_需求与能力保留矩阵.csv')
    original=csvrows(Path(rawreq['file']))
    check('96_original_columns_preserved',all(all(out[k]==row[k] for k in row) for row,out in zip(original,req)) and len(original)==len(req),'no source requirement text rewritten')
    rawdetail=load(Path(member_by_name['AAOS_UI_Frontend_20261009/reference/capability-details.json']['file']))
    detailmap={(x['父CAP'],int(x['源内顺序'])):x['设计细项原文'] for x in detail}
    check('186_original_texts_preserved',all(detailmap[(f'CAP-{parent}',i)]==v for parent,vs in rawdetail.items() for i,v in enumerate(vs,1)),'ordered design detail strings')
    old=load(PLAN/'OLD-TASK-DISPOSITION.json');rows=old['rows']
    check('330_disposition_keys_unique',len(rows)==330 and len({x['key'] for x in rows})==330,len(rows))
    check('old_targets_exist',all(k in byid for x in rows for k in x['planning_targets']),'all historical/new-source tasks have destinations')
    oldpath=next(x for x in source['snapshot'] if x['relative_path']=='docs/current/AAOS-ALL-TASKS-LEDGER-20261001.json' and x['root'].endswith('gov-ui-20261008'))
    original_old=load(Path(oldpath['root'])/oldpath['relative_path'])['task_rows'];outold={x['key']:x for x in rows}
    check('270_original_rows_preserved',len(original_old)==270 and all(all(outold[r['key']][k]==v for k,v in r.items()) for r in original_old),'original requirements/acceptance/evidence/status retained')
    contracts=csvrows(PLAN/'ORIGINAL-CONTRACT-DEPENDENCIES.csv')
    check('31_QF_contracts_preserved',len(contracts)==31 and {x['原任务ID'] for x in contracts}=={f'Q{n:02}' for n in range(16)}|{f'F{n:02}' for n in range(15)} and all(x['原依赖原文'] and x['原交付原文'] and x['原验收原文'] for x in contracts),'original Q/F dependencies, delivery, acceptance')
    frozen=load(PLAN/'FREEZE-REGISTER.json')
    check('logical_freeze_only',frozen['physical_files_moved_or_deleted']==0 and frozen['original_bytes_preserved'],'no source deletion/move as task disposition')
    archfail=[];zipfail=[]
    for a in source['archives']:
        p=Path(a['file'])
        if not p.is_file() or p.stat().st_size!=a['bytes'] or digest(p)!=a['sha256']:archfail.append(p.name);continue
        if p.suffix=='.zip':
            try:
                with zipfile.ZipFile(p) as z:
                    bad=z.testzip()
                    if bad:zipfail.append(p.name+':'+bad)
            except (OSError,zipfile.BadZipFile) as e:zipfail.append(p.name+':'+type(e).__name__)
    check('7_source_archive_hashes',not archfail,archfail or 'all registered files match size/SHA256')
    check('6_source_zip_crc',not zipfail,zipfail or 'all 6 source ZIPs readable; no corrupt member')
    for a in source['archives']:
        name=Path(a['file']).name
        if name not in ['AAOS_最后任务包_20261009.zip','AAOS_补齐材料与分析增量_20261009.zip']:continue
        count=0;fail=[]
        with zipfile.ZipFile(a['file']) as z:
            mf=next(n for n in z.namelist() if n.endswith('/SHA256SUMS.txt'))
            prefix=mf.rsplit('/',1)[0]+'/'
            for line in z.read(mf).decode('utf-8-sig').splitlines():
                m=re.match(r'^([0-9a-fA-F]{64})\s+\*?(.+)$',line)
                if not m:continue
                count+=1;member=m[2].strip()
                if member not in z.namelist():member=prefix+member
                if member not in z.namelist() or hashlib.sha256(z.read(member)).hexdigest()!=m[1].lower():fail.append(member)
        check('internal_sha:'+name,not fail and count==(11 if name.startswith('AAOS_最后') else 17),{'entries':count,'failures':fail})
    extractfail=[x['member'] for x in files if not Path(x['file']).is_file() or digest(Path(x['file']))!=x['sha256']]
    check('62_extracted_source_members',len(files)==62 and not extractfail,extractfail or len(files))
    # Match UI union internal SHA manifest across the four supplemental ZIPs.
    uis=[a for a in source['archives'] if Path(a['file']).name.startswith('AAOS_UI_补交_')]
    union={}
    for a in uis:
        with zipfile.ZipFile(a['file']) as z:
            for n in z.namelist():
                if not n.endswith('/'):
                    data=z.read(n)
                    if n in union and union[n]!=hashlib.sha256(data).hexdigest():raise ValueError('UI duplicate content conflict '+n)
                    union[n]=hashlib.sha256(data).hexdigest()
    mf=Path(member_by_name['AAOS_UI_Frontend_20261009/SHA256SUMS.txt']['file'])
    sha_lines=[]
    for line in mf.read_text(encoding='utf-8-sig').splitlines():
        m=re.match(r'^([0-9a-fA-F]{64})\s+\*?(.+)$',line)
        if m:sha_lines.append((m[1].lower(),m[2].strip()))
    internal_ok=len(sha_lines)==154 and all(union.get('AAOS_UI_Frontend_20261009/'+n)==h or union.get(n)==h for h,n in sha_lines)
    check('UI_union_internal_sha',len(union)==155 and internal_ok,{'union_files':len(union),'sha_entries':len(sha_lines)})
    drift=[]
    for s in source['snapshot']:
        p=Path(s['root'])/s['relative_path']
        if p.is_file()!=s['exists'] or (s['exists'] and digest(p)!=s['sha256']):drift.append(str(p))
    check('protected_source_snapshot_unchanged',not drift,drift or 'all selected Main/writer files unchanged')
    manifest=PLAN/'DELIVERY-MANIFEST.json'
    if manifest.is_file():
        m=load(manifest)
        mismatches=[x['path'] for x in m['files'] if not (PLAN/x['path']).is_file() or digest(PLAN/x['path'])!=x['sha256']]
        # Receipt is intentionally regenerated with --write-receipt; check it in read-only verification.
        if args.write_receipt:mismatches=[x for x in mismatches if x!='VALIDATION.json']
        check('delivery_manifest_hashes',not mismatches,mismatches or len(m['files']))
    end=datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt={'schema':'aaos.planning-validation/1','status':'PASS' if not errors else 'FAIL','evidence_level':'STRUCTURAL_SOURCE_VERIFICATION_ONLY','implementation':'NOT_EXECUTED',
      'start_utc':start,'end_utc':end,'command_argv':[sys.executable,'-B',str(Path(__file__).resolve())]+(['--write-receipt'] if args.write_receipt else []),
      'python_executable':sys.executable,'python_version':sys.version,'baseline_register':'SOURCE-REGISTER.json',
      'checks':checks,'errors':errors,'not_run':['product quick/full gates','UI implementation/runtime','model calls','desktop launch','installation lifecycle','manual/physical DPI/IME','real user learning','cloud CI/quota query','whole-repo volume audit','cleanup/destructive operations']}
    if args.write_receipt:(PLAN/'VALIDATION.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':receipt['status'],'checks':len(checks),'failed':errors,'implementation':'NOT_EXECUTED'},ensure_ascii=False))
    raise SystemExit(0 if not errors else 1)

if __name__=='__main__':main()
