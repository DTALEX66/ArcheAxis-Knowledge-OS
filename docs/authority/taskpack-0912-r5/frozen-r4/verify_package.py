#!/usr/bin/env python3
"""Read-only R4 planning package validator; Python 3.9+, standard library.
Integrity hashes are not signatures. This does not run product tests.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import runpy
import sys

sys.dont_write_bytecode = True
PLAN = 'AAK-FOLLOWUP-20260908-R3'

def demand(ok, message):
    if not ok:
        raise ValueError(message)

def read(root, name):
    return json.loads((root / name).read_text(encoding='utf-8'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest_check(root, name='MANIFEST.json'):
    demand(root.is_dir() and not root.is_symlink(), 'invalid root')
    manifest = read(root, name)
    demand(manifest['plan_id'] == PLAN, 'manifest plan mismatch')
    seen = set()
    for item in manifest['files']:
        rel = item['path']
        p = PurePosixPath(rel)
        demand(rel not in seen and rel not in ['', '.', name], 'duplicate/invalid path')
        demand(not p.is_absolute() and '..' not in p.parts and str(p) == rel and '\\' not in rel and ':' not in rel, 'unsafe path')
        target = root / rel
        demand(target.is_file() and not target.is_symlink(), 'missing file: ' + rel)
        demand(target.stat().st_size == item['bytes'] and digest(target) == item['sha256'], 'hash/size mismatch: ' + rel)
        seen.add(rel)
    all_paths = list(root.rglob('*'))
    demand(not any(p.is_symlink() for p in all_paths), 'symlink in package')
    actual = {p.relative_to(root).as_posix() for p in all_paths if p.is_file()}
    demand(actual == seen | {name}, 'unlisted or missing files')
    return len(actual)

def dag(items, field):
    by_id = {x['id']: x for x in items}
    demand(len(by_id) == len(items), 'duplicate IDs')
    active, done = set(), set()
    def visit(k):
        demand(k in by_id and k not in active, 'unknown dependency or cycle')
        if k in done:
            return
        active.add(k)
        for dep in by_id[k][field]:
            visit(dep)
        active.remove(k)
        done.add(k)
    for k in by_id:
        visit(k)

def validate(root):
    root = Path(root)
    count = manifest_check(root)
    oldroot = root / 'frozen-r3.1'
    previous = runpy.run_path(str(oldroot / 'verify_package.py'))['validate'](oldroot)
    demand(previous['result'] == 'PASS', 'baseline validation failed')
    old = read(oldroot, 'TASKS.json')
    plan = read(root, 'TASKS.json')
    demand(plan['plan_id'] == PLAN and plan['package_revision'] == 'R4', 'R4 identity mismatch')
    demand(plan['audit_base_sha'] == old['audit_base_sha'] and plan['baseline_date'] == '2026-09-08', 'inherited baseline changed')
    for k in ['issued_authorization', 'product_implemented_in_this_turn', 'automatic_future_activation', 'remote_head_rechecked_in_r4']:
        demand(plan[k] is False, 'false activation/implementation: ' + k)
    demand(plan['plan_only'] is True and plan['decisions'] == old['decisions'], 'planning/history boundary changed')
    tasks = plan['tasks']
    by_id = {t['id']: t for t in tasks}
    ids = set(by_id)
    demand(len(tasks) == 23 and ids == {t['id'] for t in old['tasks']}, 'original task IDs lost')
    for original in old['tasks']:
        current = by_id[original['id']]
        for key, value in original.items():
            demand(current.get(key) == value, 'inherited task changed: ' + original['id'] + ':' + key)
        demand(all(k in current for k in ['r4_work', 'r4_acceptance', 'human_learning_slices', 'r4_acceptance_case_ids']), 'missing R4 task fields')
    dag(tasks, 'depends_on')
    for name in ['FUNCTIONS.json', 'BLUEPRINT-COVERAGE.json', 'FORMAT-COVERAGE.json', 'ENHANCEMENT-COVERAGE.json']:
        demand(read(root, name) == read(oldroot, name), 'lost original coverage: ' + name)
    gov = read(root, 'GOVERNANCE-MIGRATION.json')
    demand(gov['package_revision'] == 'R4' and gov['slices'] == read(oldroot, 'GOVERNANCE-MIGRATION.json')['slices'], 'governance/language migration changed')
    learning = read(root, 'HUMAN-LEARNING.json')['slices']
    hlids = {x['id'] for x in learning}
    demand(len(learning) == 12 and hlids == {f'HL{i:02d}' for i in range(1, 13)}, 'HL slices lost')
    dag(learning, 'depends_on_slices')
    features = {f['id'] for f in read(root, 'FUNCTIONS.json')['features']}
    cases = read(root, 'ACCEPTANCE.json')['scenarios']
    oldcases = read(oldroot, 'ACCEPTANCE.json')['scenarios']
    demand(len(cases) == 38 and cases[:26] == oldcases, 'original acceptance changed')
    caseids = {c['id'] for c in cases}
    demand(len(caseids) == 38 and {c['id'] for c in cases[26:]} == {f'HL-AC-{i:02d}' for i in range(1, 13)}, 'new cases lost')
    for c in cases:
        demand(c['result'] == 'NOT_RUN_IN_THIS_PACKAGE', 'fabricated product result')
        demand(all(c[k] for k in ['fixture', 'procedure', 'expected', 'gates']), 'empty case')
        demand(set(c['gates']) <= {f'G{i:02d}' for i in range(1, 15)}, 'unknown gate')
    for s in learning:
        demand(s['status'] == 'PLANNED_NOT_IMPLEMENTED', 'false HL completion')
        demand(set(s['mapped_tasks']) <= ids and s['mapped_tasks'], 'invalid HL parent')
        demand(set(s['parent_contributions']) == set(s['mapped_tasks']) and all(s['parent_contributions'].values()), 'missing parent contribution')
        demand(set(s['feature_ids']) <= features and set(s['acceptance_case_ids']) <= caseids, 'invalid HL reference')
        demand(all(s[k] for k in ['work', 'deliverable', 'acceptance', 'rollback', 'phase']), 'incomplete HL slice')
    for task in tasks:
        expected = [s['id'] for s in learning if task['id'] in s['mapped_tasks']]
        demand(task['human_learning_slices'] == expected, 'HL task binding mismatch')
        expected_cases = [c for s in learning if task['id'] in s['mapped_tasks'] for c in s['acceptance_case_ids']]
        demand(set(task['r4_acceptance_case_ids']) == set(expected_cases), 'HL case binding mismatch')
    templates = read(root, 'ACTIVITY-TEMPLATES.json')['templates']
    demand(len(templates) == 12 and {t['id'] for t in templates} == {f'T{i:02d}' for i in range(1, 13)}, 'template coverage lost')
    source = (root / 'research-v15/07_训练与评价模板.md').read_text(encoding='utf-8')
    sections = {m.group(1): m.group(3).strip() for m in re.finditer(r'^## (T\d{2})｜([^\n]+)\n(.*?)(?=^## T\d{2}｜|\Z)', source, re.M | re.S)}
    for t in templates:
        demand(t['source_body'] == sections[t['id']], 'template source changed')
        demand(hashlib.sha256(t['source_body'].encode()).hexdigest() == t['source_body_sha256'], 'template hash mismatch')
        expected = [s for s in learning if t['id'] in s['template_ids']]
        demand(t['mapped_slices'] == [s['id'] for s in expected], 'template slice binding mismatch')
        demand(set(t['mapped_tasks']) == {k for s in expected for k in s['mapped_tasks']}, 'template task binding mismatch')
        demand(t['effective_protocol_validated'] is False and t['activation'] == 'ADAPT_AND_VALIDATE_NOT_AUTORUN', 'false template validation')
    adoption = read(root, 'RESEARCH-ADOPTION.json')
    demand(adoption['auto_verified'] is False, 'automatic evidence acceptance')
    data_specs = [('research', '研究', 35), ('methods', '方法', 40), ('domains', '学科', 36), ('resources', '资源', 104)]
    source_by_type = {}
    for key, chinese, n in data_specs:
        raw = read(root, f'research-v15/{chinese}数据.json')
        source_by_type[key] = {r['编号']: r for r in raw}
        demand(len(raw) == n and len(adoption[key]) == n, 'source count mismatch: ' + key)
        demand({r['source_id'] for r in adoption[key]} == set(source_by_type[key]), 'source coverage lost: ' + key)
    for r in adoption['research']:
        original = source_by_type['research'][r['source_id']]
        demand(r['reading_level'] == original['阅读层级'][:2] and r['auto_verified'] is False, 'research qualification changed')
        demand(r['allowed_use'] == ('REFERENCE_ONLY' if r['reading_level'] == 'R0' else 'CONTEXT_BOUND_CANDIDATE'), 'R0/conditional boundary changed')
        demand(r['record_role'] == ('correction' if r['source_id'] in ['R33', 'R34'] else 'study_or_review'), 'correction treated as independent study')
    for key in ['methods', 'domains']:
        for r in adoption[key]:
            original = source_by_type[key][r['source_id']]
            expected = re.findall(r'R\d{2}', original['依据编号'])
            demand(r['research_refs'] == expected, 'research references drifted')
            demand(set(r['research_refs']) <= set(source_by_type['research']), 'unknown study')
            demand(r['runtime_enabled'] is False and set(r['mapped_slices']) <= hlids, 'method/domain auto-activated')
    for r in adoption['resources']:
        demand(r['action'] == 'REGISTER_ONLY' and r['installed'] is False and r['network_permission_granted'] is False, 'resource auto-installed')
    context = read(root, 'CONTEXT-DECISIONS.json')
    demand(len(context['decisions']) == 16 and context['unknowns'], 'continuity omissions')
    demand(context['platform_memory_modified'] is False and context['all_platform_chats_available'] is False, 'false platform completeness claim')
    for c in context['decisions']:
        demand(set(c['mapped_tasks']) <= ids and c['basis_type'] and c['references'], 'invalid context mapping')
    contract = read(root, 'LEARNING-CONTRACT.json')
    demand(contract['status'] == 'SPECIFICATION_NOT_RUNTIME_SCHEMA', 'false contract implementation')
    prov = read(root, 'SOURCE-PROVENANCE.json')
    for item in prov['packaged_sources'] + prov['r4_sources']:
        demand(digest(root / item['path']) == item['sha256'], 'source provenance mismatch: ' + item['path'])
    for field in ['new_full_product_audit_performed', 'product_tests_run_this_turn', 'product_code_modified_or_pushed']:
        demand(prov[field] is False, 'false product claim')
    required = ['CONTEXT-HANDOFF.md', 'SESSION-DECISIONS.md', 'EXECUTOR-START.md', 'EXECUTOR-CODEX.md', 'EXECUTOR-DSH.md', 'AUDITOR-GPT.md', 'TASKPACK.md', 'HUMAN-LEARNING.md', 'CONTRIBUTION-MATRIX.md', 'VALIDATION.md']
    demand(all((root / x).is_file() for x in required), 'missing companion')
    return dict(result='PASS', tasks=23, features=29, scenarios=38, capabilities=16, format_groups=16, enhancements=11, retained_user_requirements=66, governance_migration_slices=12, human_learning_slices=12, templates=12, research_records=35, methods=40, domains=36, resources=104, active_files=count, product_tests_run=False, platform_completeness_verified=False)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.root), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({'result': 'FAIL', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
