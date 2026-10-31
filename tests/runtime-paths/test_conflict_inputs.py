"""Real local Git snapshots and private-boundary counterexamples; no VM/network."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.runtime import conflict_inputs as subject


@pytest.fixture
def fixture(tmp_path):
    root = tmp_path / 'project 空间'
    root.mkdir()
    template = tmp_path / 'empty-template'
    template.mkdir()
    subject.git(root, 'init', '--initial-branch=main', '--template=' + str(template))
    for name in subject.HARNESS:
        body = b'.project-local/\n' if name == '.gitignore' else b'# Synthetic harness; not executed\n'
        subject.write(root / name, body)
    subject.write(root / 'unrelated-large-source.txt', b'Not part of the harness\n')
    subject.git(root, 'add', '--', *subject.HARNESS, 'unrelated-large-source.txt')
    tree = subject.git(root, 'write-tree').decode().strip()
    commit = subject.git(root, '-c', 'commit.gpgsign=false', 'commit-tree', tree, data=b'fixture\n').decode().strip()
    subject.git(root, 'update-ref', 'refs/heads/main', commit)
    dev = root / '.project-local'
    original = dev / 'runs/retained/original'
    files = {'package/setup.exe': b'not executable', 'tools/pwsh.exe': b'not PowerShell',
             'input/git/cmd/git.exe': b'not Git', 'input/drivers/driver.exe': b'not a driver',
             'input/guest-local-pinned-lifecycle.ps1': b'# synthetic guest',
             'input/repo/.mimosa/private-state.json': b'synthetic private sentinel'}
    rows = []
    for name, body in files.items():
        subject.write(original / name, body)
        folder, tail = name.split('/', 1)
        guest = next(key for key, value in subject.inputs.ROOTS.items() if value == folder)
        rows.append({'path': str(subject.inputs.GUEST_FOLDERS[guest] / tail),
                     'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
    subject.save(original / 'input/inputs.json', {'scope': 'MIXED_CORE_INSTALLED_CONFLICT_JOURNEY',
        'approval': 'ROOT_REVIEWED_FOR_THIS_FRESH_RUN', 'files': rows})
    pin = subject.inputs.identity(original / 'input/inputs.json')['sha256']
    key = hashlib.sha256(str(root).casefold().encode()).hexdigest()[:10]
    run = dev / 'runs' / key / 'prepare'
    (run / 'artifacts').mkdir(parents=True)
    (run / 'tmp').mkdir()
    subject.save(run / 'run-metadata.json', {'owner': 'ArcheAxis-Knowledge-OS',
        'worktree_root': str(root), 'run_id': run.name})
    return {'root': root, 'dev': dev, 'run': run, 'artifacts': run / 'artifacts', 'tmp': run / 'tmp'}, original, pin, commit


def test_clean_snapshot_never_reads_old_repository_or_copies_shared_payloads(fixture, monkeypatch):
    paths, original, pin, commit = fixture
    identity, inventory = subject.inputs.identity, subject.inputs.inventory
    def guarded_identity(path):
        assert not Path(path).is_relative_to(original / 'input/repo'), 'Old repo contents must stay unread'
        return identity(path)
    def guarded_inventory(path, guest):
        assert Path(path) != original / 'input', 'Do not enumerate the mixed old input root'
        assert not Path(path).is_relative_to(original / 'input/repo')
        return inventory(path, guest)
    monkeypatch.setattr(subject.inputs, 'identity', guarded_identity)
    monkeypatch.setattr(subject.inputs, 'inventory', guarded_inventory)
    result = subject.prepare(paths, original, pin, commit)
    stage = Path(result['stage'])
    assert result['old_repository_read'] is False
    assert result['package_and_powershell_bytes_copied'] == 0
    assert result['launch'] == 'NOT_EXECUTED'
    assert not (stage / 'package').exists() and not (stage / 'tools').exists()
    assert not (stage / 'input/repo/unrelated-large-source.txt').exists()
    harness = result['harness_source']
    assert harness['original_commit'] == commit
    assert harness['snapshot_commit'] != commit
    assert subject.git(stage / 'input/repo', 'status', '--porcelain').strip() == b''
    assert {x['path'] for x in harness['files']} == set(subject.HARNESS)
    with pytest.raises(ValueError, match='Fresh'):
        subject.prepare(paths, original, pin, commit)


@pytest.mark.parametrize('change', ['extra-public', 'changed-tool', 'changed-harness', 'owner', 'wrong-pin'])
def test_changed_sources_ownership_and_incomplete_inventories_are_preserved_as_failures(fixture, change):
    paths, original, pin, commit = fixture
    if change == 'extra-public':
        subject.write(original / 'input/git/unlisted.txt', b'preserve')
    elif change == 'changed-tool':
        (original / 'input/git/cmd/git.exe').write_bytes(b'changed')
    elif change == 'changed-harness':
        (paths['root'] / subject.HARNESS[-1]).write_bytes(b'changed')
    elif change == 'owner':
        (paths['run'] / 'run-metadata.json').write_text('{}', encoding='utf-8')
    else:
        pin = '0' * 64
    before = (original / 'input/inputs.json').read_bytes()
    with pytest.raises(ValueError):
        subject.prepare(paths, original, pin, commit)
    assert (original / 'input/inputs.json').read_bytes() == before
    assert not (paths['artifacts'] / 'clean-conflict-inputs.json').exists()


def test_selected_private_tool_declaration_fails_without_reading_it(fixture):
    _, original, _, _ = fixture
    body = json.loads((original / 'input/inputs.json').read_text(encoding='utf-8'))
    body['files'].append({'path': r'C:\AAOSInput\git\.mimosa\state', 'bytes': 1, 'sha256': 'a' * 64})
    with pytest.raises(ValueError, match='Private'):
        subject.selected(body)
