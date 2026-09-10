#!/usr/bin/env python3
"""Validate this handoff package, not the implementation of ArcheAxis."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(root: Path, name: str):
    return json.loads((root / name).read_text(encoding='utf-8'),
                      object_pairs_hook=unique_keys)


def verify(root: Path) -> dict:
    manifest = read_json(root, 'MANIFEST.json')
    require(manifest['schema'] == 'archeaxis.package-manifest/v1', 'Manifest schema')
    listed = set()
    for item in manifest['files']:
        name = item['path']
        require(name not in listed, 'Repeated manifest path: ' + name)
        listed.add(name)
        require(Path(name).name == name and name not in ('.', '..', 'MANIFEST.json'),
                'Unsafe manifest path: ' + name)
        path = root / name
        require(not path.is_symlink(), 'Linked package file: ' + name)
        body = path.read_bytes()
        require(len(body) == item['bytes'], 'Size differs: ' + name)
        require(hashlib.sha256(body).hexdigest() == item['sha256'], 'Hash differs: ' + name)
    required = {'TASKPACK.md', 'EXECUTOR-START.md', 'INDEPENDENT-AUDIT.md',
                'LOCAL-CLEANUP.md', 'TASKS.json', 'BLUEPRINT-COVERAGE.json',
                'FORMAT-COVERAGE.json', 'SOURCES.json', 'audit_local_storage.py',
                'verify_package.py', 'PACKAGE-VALIDATION.json',
                'ENHANCEMENT-REVIEW.md', 'ENHANCEMENT-COVERAGE.json', 'SOURCE-ENHANCEMENT.md'}
    require(required <= listed, 'Missing required package files')
    tasks = read_json(root, 'TASKS.json')
    rows = tasks['tasks']
    ids = [row['id'] for row in rows]
    expected = {f'X{i:02}' for i in range(15)} | {'Q00', 'Q01'} | {f'F{i:02}' for i in range(1, 7)}
    require(len(ids) == len(set(ids)) and set(ids) == expected, 'Unexpected task IDs')
    require(tasks['plan_only'] is True and tasks['product_implemented_in_this_turn'] is False,
            'Package must not claim product implementation')
    require(tasks['issued_authorization'] is False, 'Package is not an authorization token')
    require(tasks['automatic_future_activation'] is False, 'Future work must remain deferred')
    by_id = {row['id']: row for row in rows}
    for row in rows:
        require(all(dep in by_id for dep in row['depends_on']), 'Unknown dependency: ' + row['id'])
        require(len(row['depends_on']) == len(set(row['depends_on'])), 'Duplicate dependencies')
        require(row['product_completion_claimed'] is False, 'Unverified completion: ' + row['id'])
        require(bool(row['acceptance']) and bool(row['rollback']), 'Missing acceptance/rollback')
        if row['id'].startswith('F'):
            require(row['status'] == 'DEFERRED_RETAINED', 'Future task was activated')
        else:
            require(row['status'] == 'TODO', 'Initial package status changed')
    pending = set(ids)
    completed = set()
    order = []
    while pending:
        ready = sorted(task for task in pending if set(by_id[task]['depends_on']) <= completed)
        require(bool(ready), 'Cyclic task dependencies')
        order.extend(ready)
        completed.update(ready)
        pending.difference_update(ready)
    # Implementers must be able to finish without waiting for the independent auditor.
    for row in rows:
        if row['id'].startswith('X'):
            require(all(dep.startswith('X') for dep in row['depends_on']),
                    'Executor task depends on an auditor/future task: ' + row['id'])
    require(set(by_id['X14']['depends_on']) == {'X01', 'X02'}, 'Cleanup must be available early')
    require('X14' in by_id['Q01']['depends_on'], 'M1 audit must include cleanup')
    coverage = read_json(root, 'BLUEPRINT-COVERAGE.json')
    expected_counts = {'capabilities': 16, 'long_term_programs': 10,
        'blueprint_governance_tasks': 11, 'canonical_repo_tasks': 39,
        'previous_followup_tasks': 21, 'previous_model_tasks': 20, 'user_requirements': 66}
    for group, count in expected_counts.items():
        entries = coverage[group]
        require(len(entries) == count, 'Coverage count changed: ' + group)
        keys = [(item.get('source', ''), item['id']) for item in entries]
        require(len(keys) == len(set(keys)), 'Duplicate coverage IDs: ' + group)
        for item in entries:
            require(bool(item['mapped_tasks']) and set(item['mapped_tasks']) <= expected,
                    'Unmapped requirement: ' + item['id'])
            if 'preserved' in item:
                require(item['preserved'] is True, 'Requirement deleted: ' + item['id'])
    require({x['id'] for x in coverage['capabilities']} == {f'CAP-{i:04}' for i in range(10, 161, 10)},
            'Capability ID set differs')
    formats = read_json(root, 'FORMAT-COVERAGE.json')['formats']
    require(len(formats) == 16 and {x['format_id'] for x in formats} == {f'F{i:02}' for i in range(1, 17)},
            'Format retention set differs')
    for row in formats:
        require(row['preserved'] is True and row['qualification_state'] == 'NOT_REQUALIFIED',
                'Format was dropped or falsely qualified')
        require(bool(row['mapped_tasks']) and set(row['mapped_tasks']) <= expected, 'Unmapped format')
    sources = read_json(root, 'SOURCES.json')
    require(sources['remote_main_sha'] == tasks['audit_base_sha'], 'Inconsistent audit baseline')
    require(bool(sources['known_limits']), 'Source review limitations missing')
    enhancement = read_json(root, 'ENHANCEMENT-COVERAGE.json')
    require(tasks['plan_id'] == coverage['plan_id'] == enhancement['plan_id'] == manifest['plan_id'],
            'Revision identity mismatch')
    require(enhancement['source_sha256'] == hashlib.sha256((root / 'SOURCE-ENHANCEMENT.md').read_bytes()).hexdigest(),
            'Attachment source hash mismatch')
    entries = enhancement['items']
    require(len(entries) == 11 and {x['id'] for x in entries} == {f'E{i:02}' for i in range(1, 12)},
            'Missing enhancement items')
    user_by_id = {item['id']: item for item in coverage['user_requirements']}
    for row in entries:
        require(row['user_requirement_id'] in user_by_id, 'Unregistered enhancement requirement')
        require(bool(row['mapped_tasks']) and set(row['mapped_tasks']) <= expected, 'Unmapped enhancement')
        require(row['mapped_tasks'] == user_by_id[row['user_requirement_id']]['mapped_tasks'], 'Enhancement mapping conflict')
        require(row['product_implemented'] is False and bool(row['decision']), 'Unqualified enhancement completion')
    e_by_id = {row['id']: row for row in entries}
    require(e_by_id['E09']['mapped_tasks'] == ['F04'], 'Cross-project work must remain deferred')
    require(enhancement['new_task_ids'] == [], 'Enhancement must reuse the existing queue')
    return {'package_checks': 'PASS', 'product_tested': False,
            'task_count': len(rows), 'format_groups': len(formats),
            'enhancement_items': len(entries),
            'coverage_counts': expected_counts, 'valid_dependency_order': order,
            'scope': 'File integrity, dependency graph and registered requirement coverage only; no product or Windows qualification.'}


if __name__ == '__main__':
    try:
        result = verify(Path(__file__).resolve().parent)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('PACKAGE CHECK FAILED: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
