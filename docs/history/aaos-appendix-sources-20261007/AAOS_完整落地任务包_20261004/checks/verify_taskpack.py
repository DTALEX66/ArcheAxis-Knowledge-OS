#!/usr/bin/env python3
"""Offline, read-only validation of this task package. Does not test AAOS."""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))

def require(condition: bool, message: str):
    if not condition:
        raise ValueError(message)

def validate() -> dict:
    manifest = load('MANIFEST.json')
    expected = {e['path']: e for e in manifest['files']}
    require(len(expected) == len(manifest['files']), 'Duplicate manifest paths')
    actual = set()
    for p in ROOT.rglob('*'):
        require(not p.is_symlink(), f'Symlink is not allowed in package: {p}')
        if p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            if rel not in {'MANIFEST.json', 'SHA256SUMS.txt'}:
                actual.add(rel)
    require(actual == set(expected), f'File set mismatch: missing={set(expected)-actual}; extra={actual-set(expected)}')
    for rel, item in expected.items():
        require(not Path(rel).is_absolute() and '..' not in Path(rel).parts, 'Unsafe manifest path')
        data = (ROOT / rel).read_bytes()
        require(len(data) == item['bytes'], f'Length mismatch: {rel}')
        require(hashlib.sha256(data).hexdigest() == item['sha256'], f'Hash mismatch: {rel}')
        if rel.endswith('.json'):
            json.loads(data.decode('utf-8'))
    tasks = load('registries/tasks.json')['tasks']
    tmap = {x['task_id']: x for x in tasks}
    require(len(tmap) == len(tasks), 'Duplicate task IDs')
    visiting, done = set(), set()
    def visit(tid: str):
        require(tid in tmap, f'Unknown dependency {tid}')
        require(tid not in visiting, f'Cycle at {tid}')
        if tid in done: return
        visiting.add(tid)
        for dep in tmap[tid]['depends_on']: visit(dep)
        visiting.remove(tid); done.add(tid)
    for tid in tmap: visit(tid)
    reqs = load('registries/requirements_trace.json')['requirements']
    require({r['requirement_id'] for r in reqs} == {f'U{i:02}' for i in range(1,13)}, 'U01-U12 not complete')
    for r in reqs:
        require(bool(r['task_ids']), f'Unmapped requirement {r["requirement_id"]}')
        require(all(t in tmap for t in r['task_ids']), 'Unknown requirement task')
    cases = load('checks/acceptance_cases.json')['cases']
    require(len({q['case_id'] for q in cases}) == len(cases), 'Duplicate QA IDs')
    require(all(q['task_id'] in tmap for q in cases), 'Unknown QA task')
    require(all(q['status'] == 'NOT_RUN' and not q['evidence'] for q in cases), 'Package must not preclaim product tests')
    caps = load('registries/capability_map.seed.json')['capabilities']
    require(len({c['seed_key'] for c in caps}) == len(caps), 'Duplicate capability seed')
    require(all(c['runnable'] is False and c['canonical_capability_id'] is None for c in caps), 'Seeds must not act as runtime config')
    platforms = load('registries/knowledge_compatibility.seed.json')['platforms']
    require(all(not p['certificates'] and all(s == 'NOT_RUN' for s in p['direction_results'].values()) for p in platforms), 'Unverified compatibility marked passed')
    source_ids = {s['source_id'] for s in load('registries/sources.json')['sources']}
    for p in ROOT.glob('*.md'):
        refs = set(re.findall(r'\[(S\d{2})\]', p.read_text('utf-8')))
        require(refs <= source_ids, f'Undefined sources in {p.name}: {refs-source_ids}')
    decisions = (ROOT/'05_DSH_16问完整裁决.md').read_text('utf-8')
    for heading in ['A'+str(i) for i in range(1,5)]+['B'+str(i) for i in range(1,8)]+['C'+str(i) for i in range(1,6)]:
        require(f'## {heading}.' in decisions, f'Missing DSH question {heading}')
    sums = {}
    for line in (ROOT/'SHA256SUMS.txt').read_text('utf-8').splitlines():
        digest, rel = line.split('  ',1); sums[rel]=digest
    require(set(sums) == actual | {'MANIFEST.json'}, 'SHA256SUMS file set differs')
    for rel,digest in sums.items():
        require(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest, f'Checksum list mismatch: {rel}')
    return {'status':'PASS','scope':'TASK_PACKAGE_ONLY','product_runtime':'NOT_EXECUTED','file_count':len(expected),'requirements':len(reqs),'work_items':len(tasks),'acceptance_cases':len(cases),'capability_seeds':len(caps),'initial_platform_targets':len(platforms)}

if __name__ == '__main__':
    try:
        result = validate()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status':'FAIL','scope':'TASK_PACKAGE_ONLY','error':str(exc)},ensure_ascii=False,indent=2))
        sys.exit(1)
    print(json.dumps(result,ensure_ascii=False,indent=2))
