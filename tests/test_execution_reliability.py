"""Synthetic-owned Git fixtures; never inspect the live checkout's private state."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

TARGET = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def dev():
    return load('fixture_dev', TARGET / 'scripts/runtime/dev.py')


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'owned-source'
    root.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}

    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], env=env,
                              check=True, capture_output=True)

    git('init', '-q')
    (root / 'source.py').write_text('fixture = 1\n', encoding='utf-8')
    git('add', 'source.py')
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
    return root, git


def test_private_tracked_path_is_refused_before_binary_diff(dev, repo, monkeypatch):
    root, git = repo
    state = root / '.hilo/state.json'
    state.parent.mkdir()
    state.write_text('{"synthetic":"not authorized as source"}', encoding='utf-8')
    git('add', '.hilo/state.json')
    real_git = dev.git

    def protected_git(root, *args):
        if '--binary' in args:
            pytest.fail('binary diff attempted before rejecting tracked private path')
        return real_git(root, *args)

    monkeypatch.setattr(dev, 'git', protected_git)
    with pytest.raises(ValueError, match='protected source'):
        dev.worktree_identity(root)


@pytest.mark.parametrize('source', ['worktree', 'index', 'head'])
@pytest.mark.parametrize('name', ['assets/donor/.hilo/storage.json', 'test-results.log'])
def test_conventions_refuse_protected_paths_before_content(repo, monkeypatch, source, name):
    from scripts import check_repository_conventions as scanner

    root, git = repo
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'owned synthetic state, never scanned')
    git('add', name)
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '-qm', 'synthetic protected path')
    real_read = Path.read_bytes

    def guarded_read(path):
        if path == target:
            pytest.fail('protected worktree body was read')
        return real_read(path)

    def no_blob_read(*_args, **_kwargs):
        pytest.fail('blob content requested before protected path rejection')

    monkeypatch.setattr(Path, 'read_bytes', guarded_read)
    monkeypatch.setattr(scanner, '_read_git_blobs', no_blob_read)
    issues = scanner.scan_git_repository(root, source=source)
    assert [(item.code, item.path) for item in issues] == [('protected-source-path', name)]


@pytest.mark.parametrize('name', ['assets/donor/.hilo/storage.json', 'test-results.log'])
def test_removed_runtime_content_is_excluded_from_source_diff(dev, repo, monkeypatch, name):
    root, git = repo
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'owned synthetic old runtime')
    git('add', name)
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '-qm', 'synthetic old runtime')
    git('rm', '--cached', name)
    # Ignore locally retained runtime, just as the project does after untracking.
    (root / '.git/info/exclude').write_text(name + '\n', encoding='utf-8')
    real_git = dev.git

    def guarded_git(root, *args):
        result = real_git(root, *args)
        if '--binary' in args:
            assert name not in result
            assert 'owned synthetic old runtime' not in result
        return result

    monkeypatch.setattr(dev, 'git', guarded_git)
    assert dev.worktree_identity(root)[0] is False


def test_untracked_hilo_changes_never_open_or_invalidate_source(dev, repo, monkeypatch):
    root, _ = repo
    before = dev.worktree_identity(root)
    state = root / '.hilo/state.json'
    state.parent.mkdir()
    state.write_text('{"synthetic":1}', encoding='utf-8')
    real_open = Path.open

    def no_private_open(path, *args, **kwargs):
        if '.hilo' in path.parts:
            pytest.fail('private runtime body was opened')
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', no_private_open)
    assert dev.worktree_identity(root) == before


def test_public_source_change_still_changes_identity(dev, repo):
    root, _ = repo
    before = dev.worktree_identity(root)
    (root / 'source.py').write_text('fixture = 2\n', encoding='utf-8')
    assert dev.worktree_identity(root) != before


def test_tracked_symlink_refused_without_opening_target(dev, repo, monkeypatch):
    root, git = repo
    target = root.parent / 'owned-synthetic-target.txt'
    target.write_text('synthetic target', encoding='utf-8')
    link = root / 'linked.py'
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip('local symlink privilege unavailable')
    git('add', 'linked.py')
    with pytest.raises(ValueError, match='linked'):
        dev.worktree_identity(root)


def test_existing_mock_git_contract_still_rejects_untracked_link_before_diff(dev, repo, monkeypatch):
    root, _ = repo
    # Preserve the existing junction test's two metadata return values. A third
    # Git call (binary diff) must never happen once safe_path rejects the link.
    replies = iter(['', 'linked/source.txt'])
    monkeypatch.setattr(dev, 'git', lambda *_a: next(replies))

    def refuse(path):
        if 'linked' in path.parts:
            raise ValueError('linked path is not a development root')
        return path

    monkeypatch.setattr(dev, 'safe_path', refuse)
    with pytest.raises(ValueError, match='linked'):
        dev.worktree_identity(root)


def test_existing_private_env_refusal_is_preserved(dev, repo):
    root, _ = repo
    (root / '.env.local').write_text('synthetic fixture only', encoding='utf-8')
    with pytest.raises(ValueError, match='protected source'):
        dev.worktree_identity(root)


def runner_fixture(tmp_path, monkeypatch):
    runner = load('fixture_local_verify', TARGET / 'scripts/ci/local_verify.py')
    paths = {key: tmp_path / key for key in ('tmp', 'build', 'artifacts', 'logs', 'run')}
    for path in paths.values():
        path.mkdir()
    monkeypatch.setattr(runner.dev, 'layout', lambda *_: paths)
    monkeypatch.setattr(runner.dev, 'prepare', lambda *_: {})
    monkeypatch.setattr(runner, 'source_snapshot', lambda *_: {'head': 'fixture'})
    monkeypatch.setattr(sys, 'argv', ['local_verify.py', '--profile', 'quick', '--preflight'])
    return runner, paths


def test_initial_snapshot_failure_releases_only_owned_lock(tmp_path, monkeypatch):
    runner, paths = runner_fixture(tmp_path, monkeypatch)

    def failure(*_):
        raise RuntimeError('synthetic snapshot refused')

    monkeypatch.setattr(runner, 'source_snapshot', failure)
    with pytest.raises(RuntimeError, match='synthetic snapshot'):
        runner.main()
    assert not (paths['build'] / 'local-ci.lock').exists()


def test_existing_lock_is_not_removed(tmp_path, monkeypatch):
    runner, paths = runner_fixture(tmp_path, monkeypatch)
    lock = paths['build'] / 'local-ci.lock'
    lock.write_text('owned-by-other-fixture', encoding='utf-8')
    with pytest.raises(FileExistsError):
        runner.main()
    assert lock.read_text(encoding='utf-8') == 'owned-by-other-fixture'


def mock_checks(runner, monkeypatch):
    class Child:
        def __init__(self, *_args, **_kwargs):
            self.stdout = io.StringIO('')

        def wait(self):
            return 0

        def poll(self):
            return 0

    monkeypatch.setattr(runner.subprocess, 'Popen', Child)
    monkeypatch.setattr(runner.subprocess, 'run', lambda *_a, **_k: SimpleNamespace(returncode=0, stdout='', stderr=''))


def test_receipt_failure_still_releases_owned_lock(tmp_path, monkeypatch):
    runner, paths = runner_fixture(tmp_path, monkeypatch)
    mock_checks(runner, monkeypatch)
    real_write = Path.write_text

    def write(path, *args, **kwargs):
        if path.name == 'local-ci.json':
            raise OSError('synthetic receipt unavailable')
        return real_write(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'write_text', write)
    with pytest.raises(OSError, match='synthetic receipt'):
        runner.main()
    assert not (paths['build'] / 'local-ci.lock').exists()


@pytest.mark.parametrize('source', ['worktree', 'index', 'head'])
def test_convention_source_is_explicit_and_other_checks_are_worktree(tmp_path, monkeypatch, source):
    runner, paths = runner_fixture(tmp_path, monkeypatch)
    mock_checks(runner, monkeypatch)
    monkeypatch.setattr(runner.dev, 'git', lambda *_a: '')
    monkeypatch.setattr(sys, 'argv', ['local_verify.py', '--profile', 'quick', '--preflight', '--conventions-source', source])
    assert runner.main() == 0
    receipt = json.loads((paths['artifacts'] / 'local-ci.json').read_text(encoding='utf-8'))
    conventions = next(x for x in receipt['checks'] if x['name'] == 'conventions')
    assert conventions['command'][-1] == source
    assert conventions['source'] == source
    assert receipt['other_checks_source'] == 'worktree'
    assert receipt['head_qualification'].startswith('NOT_CLAIMED')


def test_head_selection_refuses_dirty_tracked_worktree_before_checks(tmp_path, monkeypatch):
    runner, paths = runner_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(runner.dev, 'git', lambda *_a: 'source.py\0')
    monkeypatch.setattr(sys, 'argv', ['local_verify.py', '--profile', 'quick', '--preflight', '--conventions-source', 'head'])
    assert runner.main() == 1
    receipt = json.loads((paths['artifacts'] / 'local-ci.json').read_text(encoding='utf-8'))
    assert receipt['status'] == 'FAIL'
    assert [x['name'] for x in receipt['checks']] == ['head-worktree-alignment']
    assert not (paths['build'] / 'local-ci.lock').exists()


@pytest.fixture
def lock_context():
    target = TARGET / 'scripts/ci/local_verify.py'
    spec = importlib.util.spec_from_file_location('lock_fixture_runner', target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.owned_local_ci_lock


def test_replaced_lock_belongs_to_replacement_owner(tmp_path, lock_context):
    lock = tmp_path / 'local-ci.lock'
    replacement = tmp_path / 'replacement-owned.lock'
    replacement.write_bytes(b'foreign synthetic owner')
    with lock_context(lock):
        assert lock.exists()
        os.replace(replacement, lock)
    assert lock.read_bytes() == b'foreign synthetic owner'


def test_disappeared_lock_does_not_mask_body_failure(tmp_path, lock_context):
    lock = tmp_path / 'local-ci.lock'
    with pytest.raises(RuntimeError, match='original synthetic failure'):
        with lock_context(lock):
            lock.unlink()
            raise RuntimeError('original synthetic failure')
    assert not lock.exists()


def test_unchanged_owned_lock_is_released_on_error(tmp_path, lock_context):
    lock = tmp_path / 'local-ci.lock'
    with pytest.raises(RuntimeError, match='original synthetic failure'):
        with lock_context(lock):
            raise RuntimeError('original synthetic failure')
    assert not lock.exists()


def test_preexisting_foreign_lock_is_never_claimed(tmp_path, lock_context):
    lock = tmp_path / 'local-ci.lock'
    lock.write_bytes(b'foreign synthetic owner')
    with pytest.raises(FileExistsError):
        with lock_context(lock):
            pytest.fail('existing lock was claimed')
    assert lock.read_bytes() == b'foreign synthetic owner'
