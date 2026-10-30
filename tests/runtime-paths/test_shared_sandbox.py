"""Counterexamples for the owned-ID shared mapping launcher; no VM in unit tests."""
import hashlib
import json
import subprocess
import uuid
from pathlib import Path, PureWindowsPath

import pytest

from scripts.runtime import shared_sandbox as subject


@pytest.fixture
def prepared(tmp_path):
    root = tmp_path / 'project space & 中文'
    dev = root / '.project-local'
    stage = dev / 'runs/source/retained'
    files = [(subject.inputs.ENTRY, b'fixture guest'),
             (str(subject.inputs.GUEST_FOLDERS['AAOSInstall'] / 'fixture.exe'), b'not an executable'),
             (str(subject.inputs.GUEST_FOLDERS['AAOSTools'] / 'pwsh.exe'), b'not PowerShell')]
    rows = []
    for guest, data in files:
        folder, relative = subject.inputs.member(guest)
        path = stage / folder / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        rows.append({'path': guest, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    manifest = stage / 'input/inputs.json'
    manifest.write_text(json.dumps({'approval': 'ROOT_REVIEWED_FOR_THIS_FRESH_RUN',
                                   'scope': 'SYNTHETIC_NEVER_EXECUTED', 'files': rows}), encoding='utf-8')
    key = hashlib.sha256(str(root).casefold().encode()).hexdigest()[:10]
    run = dev / 'runs' / key / 'probe'
    artifacts = run / 'artifacts'
    artifacts.mkdir(parents=True)
    (run / 'run-metadata.json').write_text(json.dumps({'owner': 'ArcheAxis-Knowledge-OS',
        'worktree_root': str(root), 'run_id': run.name}), encoding='utf-8')
    paths = {'root': root, 'dev': dev, 'run': run, 'artifacts': artifacts}
    return paths, subject.prepare(paths, stage, hashlib.sha256(manifest.read_bytes()).hexdigest())


class FakeCli:
    def __init__(self, plan, mode='ok'):
        self.plan, self.mode = plan, mode
        self.environments, self.calls = set(), []
        self.unrelated = str(uuid.uuid4())

    def __call__(self, args):
        self.calls.append(args)
        if args[0] == 'list':
            return {'WindowsSandboxEnvironments': [{'Id': key} for key in self.environments]}
        own = args[args.index('--id') + 1]
        assert own == self.plan['sandbox_id']
        if args[0] == 'start':
            self.environments.add(own)
            if self.mode == 'concurrent':
                self.environments.add(self.unrelated)
            if self.mode == 'start-timeout':
                raise subprocess.TimeoutExpired('synthetic start', 1)
        elif args[0] == 'exec':
            if self.mode == 'exec-failure':
                raise ValueError('synthetic exec failure')
            result = {'schema': 'aaos.shared-sandbox-guest-probe/v1', 'nonce': self.plan['nonce'],
                'manifest_sha256': self.plan['source_manifest_sha256'],
                'status': 'PASS_READONLY_HANDLES_OUTPUT_WRITE_AND_INPUT_IDENTITIES',
                'context': 'SYSTEM_MAPPING_PROBE_ONLY', 'members_verified': self.plan['members'],
                'readonly': [{'path': path, 'write_open_access_denied': True} for path in self.plan['binding']['probes']]}
            if self.mode == 'stale-proof':
                result['nonce'] = 'old-nonce'
            if self.mode == 'write-allowed':
                result['readonly'][0]['write_open_access_denied'] = False
            output = Path(self.plan['output'])
            (output / 'shared-probe.json').write_text(json.dumps(result), encoding='utf-8')
            (output / 'shared-probe-marker.txt').write_bytes(('aaos-shared-probe:' + self.plan['nonce']).encode())
        elif args[0] == 'stop':
            if self.mode == 'stop-failure':
                raise ValueError('synthetic stop failure')
            self.environments.remove(own)
        return {'Id': own}


@pytest.mark.parametrize('mode', ['ok', 'concurrent'])
def test_real_checks_are_required_and_only_the_requested_id_is_stopped(prepared, mode):
    paths, plan = prepared
    cli = FakeCli(plan, mode)
    result = subject.execute(paths, plan, cli)
    assert result['status'] == 'PASS_REAL_OFFLINE_SHARED_MAPPING_PROBE_ONLY'
    assert result['payload_bytes_copied'] == 0
    assert result['product_lifecycle'] == 'NOT_EXECUTED'
    assert len([args for args in cli.calls if args[0] == 'start']) == 1
    assert len([args for args in cli.calls if args[0] == 'stop']) == 1
    assert cli.environments == ({cli.unrelated} if mode == 'concurrent' else set())
    with pytest.raises(ValueError, match='replayed'):
        subject.execute(paths, plan, cli)


@pytest.mark.parametrize('mode', ['start-timeout', 'exec-failure', 'stale-proof', 'write-allowed', 'stop-failure'])
def test_partial_start_guest_failures_and_failed_stop_are_not_promoted(prepared, mode):
    paths, plan = prepared
    cli = FakeCli(plan, mode)
    result = subject.execute(paths, plan, cli, pause=lambda _: None)
    assert result['status'] == 'FAIL_OR_INCOMPLETE'
    assert len([args for args in cli.calls if args[0] == 'start']) == 1
    assert len([args for args in cli.calls if args[0] == 'stop']) == 1
    assert result.get('error') or result.get('cleanup_or_reverification_error')


def test_existing_environment_is_preserved_without_a_start_intent(prepared):
    paths, plan = prepared
    cli = FakeCli(plan)
    cli.environments.add(cli.unrelated)
    with pytest.raises(ValueError, match='Existing sandbox'):
        subject.execute(paths, plan, cli)
    assert not (paths['artifacts'] / 'shared-sandbox-start-intent.json').exists()
    assert all(args[0] == 'list' for args in cli.calls)


def test_unexpected_verifier_exception_never_saves_a_passing_execution(prepared, monkeypatch):
    paths, plan = prepared
    cli = FakeCli(plan)
    def fail(_):
        raise RuntimeError('Unexpected verifier fault')
    monkeypatch.setattr(subject, 'verify_guest', fail)
    with pytest.raises(RuntimeError, match='Unexpected'):
        subject.execute(paths, plan, cli)
    receipt = subject.inputs.read_manifest(paths['artifacts'] / 'shared-sandbox-execution.json')
    assert receipt['status'] == 'FAIL_OR_INCOMPLETE'
    assert cli.environments == set()


@pytest.mark.parametrize('change', ['config', 'output', 'command', 'template', 'run-metadata'])
def test_changed_mappings_commands_and_nonempty_outputs_fail_before_os_calls(prepared, change):
    paths, plan = prepared
    if change == 'config':
        config = Path(plan['config'])
        config.write_bytes(config.read_bytes().replace(b'<ReadOnly>true', b'<ReadOnly>false', 1))
        plan['config_identity'] = subject.inputs.identity(config)
    elif change == 'output':
        (Path(plan['output']) / 'unowned.txt').write_bytes(b'preserve')
    elif change == 'command':
        plan['command'] += ' wrong'
    elif change == 'run-metadata':
        (paths['run'] / 'run-metadata.json').write_bytes(b'changed ownership')
    else:
        plan['guest_template']['sha256'] = '0' * 64
    (paths['artifacts'] / 'shared-sandbox-plan.json').write_text(json.dumps(plan), encoding='utf-8')
    with pytest.raises(ValueError):
        subject.execute(paths, plan, lambda _: pytest.fail('No OS call allowed'))
    assert not (paths['artifacts'] / 'shared-sandbox-start-intent.json').exists()


def test_private_declaration_rechecked_before_binding_or_declared_payload(prepared, monkeypatch):
    paths, plan = prepared
    manifest = Path(plan['stage']) / 'input/inputs.json'
    data = json.loads(manifest.read_text(encoding='utf-8'))
    data['files'].append({'path': str(subject.inputs.GUEST_FOLDERS['AAOSInput'] / 'repo/.mimosa/state'),
                         'bytes': 1, 'sha256': '0' * 64})
    manifest.write_text(json.dumps(data), encoding='utf-8')
    plan['source_manifest_sha256'] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    (paths['artifacts'] / 'shared-sandbox-plan.json').write_text(json.dumps(plan), encoding='utf-8')
    original_identity = subject.inputs.identity

    def guard(path):
        assert path.name == 'inputs.json', 'Declared payload was inspected before rejecting private material'
        return original_identity(path)

    monkeypatch.setattr(subject.inputs, 'identity', guard)
    monkeypatch.setattr(subject, 'probe_binding', lambda *_: pytest.fail('Binding must not run'))
    with pytest.raises(ValueError, match='Private'):
        subject.execute(paths, plan, lambda _: pytest.fail('No OS call allowed'))


@pytest.mark.parametrize('change', ['none', 'plan-root-drift', 'post-guest-input-drift'])
def test_split_roots_are_bound_to_the_plan_and_reverified_after_stop(prepared, change):
    paths, old_plan = prepared
    stage = Path(old_plan['stage'])
    retained = paths['dev'] / 'runs/shared/retained'
    retained.mkdir(parents=True)
    for name in ('package', 'tools'):
        (stage / name).rename(retained / name)
    document = subject.inputs.read_manifest(stage / 'input/inputs.json')
    document['source_roots'] = {name: str(stage / name if name == 'input' else retained / name)
                                for name in subject.inputs.ROOTS.values()}
    manifest = stage / 'input/inputs.json'
    manifest.write_text(json.dumps(document), encoding='utf-8')
    run = paths['run'].with_name('split-retry')
    artifacts = run / 'artifacts'
    artifacts.mkdir(parents=True)
    (run / 'run-metadata.json').write_text(json.dumps({'owner': 'ArcheAxis-Knowledge-OS',
        'worktree_root': str(paths['root']), 'run_id': run.name}), encoding='utf-8')
    split_paths = {**paths, 'run': run, 'artifacts': artifacts}
    plan = subject.prepare(split_paths, stage, subject.inputs.identity(manifest)['sha256'])
    if change == 'plan-root-drift':
        plan['source_roots']['tools'] = str(stage / 'tools')
        (artifacts / 'shared-sandbox-plan.json').write_text(json.dumps(plan), encoding='utf-8')
        with pytest.raises(ValueError, match='mapping/command/template'):
            subject.execute(split_paths, plan, lambda _: pytest.fail('No OS call allowed'))
        return
    cli = FakeCli(plan)
    def invoke(args):
        value = cli(args)
        if args[0] == 'exec' and change == 'post-guest-input-drift':
            (retained / 'tools/pwsh.exe').write_bytes(b'changed after guest proof')
        return value
    result = subject.execute(split_paths, plan, invoke)
    assert result['status'] == ('PASS_REAL_OFFLINE_SHARED_MAPPING_PROBE_ONLY' if change == 'none' else 'FAIL_OR_INCOMPLETE')
    assert cli.environments == set(), 'The owned sandbox must still be stopped'
    if change != 'none':
        assert result.get('cleanup_or_reverification_error')


@pytest.mark.parametrize('change', ['identity', 'boolean', 'ambiguous'])
def test_lifecycle_receipt_must_be_unique_complete_and_match_the_candidate(prepared, change):
    _, plan = prepared
    output = Path(plan['output'])
    (output / 'guest-terminal.json').write_text(json.dumps({'status': 'VERIFIER_RETURNED_REQUIRES_LIFECYCLE_RECEIPT_REVIEW',
        'verifier_invoked': True, 'error': None}), encoding='utf-8')
    plan['expected_lifecycle'] = {'installer_sha256': 'a' * 64, 'core_sha256': 'b' * 64}
    receipt = {'schema': 'archeaxis/installed-lifecycle-receipt/v1',
        'qualification_scope': 'LOCAL_MIXED_CORE_INSTALLED_LIFECYCLE',
        'same_installer_scope': 'SAME_INSTALLER_SAME_VERSION_REINSTALL_DATA_PRESERVATION',
        'pyc_growth': 0, **plan['expected_lifecycle']}
    for key in ['complete_lifecycle_verified', 'graceful_shutdown', 'forced_tree_cleanup',
                'clean_uninstall', 'uninstall_retains_data', 'reinstall_readback']:
        receipt[key] = True
    if change == 'identity':
        receipt['core_sha256'] = 'c' * 64
    if change == 'boolean':
        receipt['reinstall_readback'] = False
    for _ in range(2 if change == 'ambiguous' else 1):
        directory = output / uuid.uuid4().hex
        directory.mkdir()
        (directory / 'lifecycle-receipt.json').write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError, match='identity|predicates|Exactly one'):
        subject.verify_lifecycle(plan)


@pytest.mark.parametrize('change', ['none', 'wrong-candidate', 'wrong-source', 'harness-failed',
                                  'canonical-drift', 'missing-restart', 'malformed-ui', 'journey-escape', 'metadata-drift'])
def test_conflict_requires_actual_canonical_receipts_source_candidate_and_restart(prepared, change):
    _, plan = prepared
    output = Path(plan['output'])
    empty = hashlib.sha256(b'').hexdigest()
    expected = {'harness_commit': 'a' * 40, 'harness_tree': 'b' * 40,
                'host_sha256': 'c' * 64, 'installer_sha256': 'd' * 64, 'core_sha256': 'e' * 64}
    plan['expected_conflict'] = expected
    source = {'commit': expected['harness_commit'], 'patch_sha256': empty}
    guest_repo = str(subject.inputs.GUEST_FOLDERS['AAOSOutput'] / 'repo')
    key = hashlib.sha256(guest_repo.casefold().encode()).hexdigest()[:10]
    guest_run = str(subject.inputs.GUEST_FOLDERS['AAOSOutput'] / f'repo/.project-local/runs/{key}/wdconf')
    host_run = output / f'repo/.project-local/runs/{key}/wdconf'
    probe_name = 'webdriver-123456789abc'
    host_probe = host_run.parent / probe_name
    execution = {'status': 'LOCAL_PASS', 'source_consistent': True, 'child_exit_code': 0, 'exit_code': 0,
                 'source_commit': expected['harness_commit'], 'source_commit_after': expected['harness_commit'],
                 'source_tree': expected['harness_tree'], 'source_patch_sha256': empty,
                 'source_patch_sha256_after': empty, 'run_root': guest_run}
    conflict = {'status': 'PASS', 'fixture': {'source': source}, 'initializer_exit': {'stopped': True},
                'launcher': {'core': {'sha256': expected['core_sha256']}},
                'ui_result': {'status': 'PASS', 'installed_ui': 'TRUSTED_WEBDRIVER_CONTROLS',
                              'restart_readback': True, 'source': source, 'final_source': source}}
    body = {'ok': True, 'source_consistent': True,
            'run_root': str(PureWindowsPath(guest_run).parent / probe_name),
            'host': {'sha256': expected['host_sha256']},
            'installer': {'sha256': expected['installer_sha256']}, 'installed_draft_conflict_loop': conflict,
            'owned_identity_collection_verified': True, 'owned_ports_released': True, 'owned_process_cleanup': True,
            'remaining_same_creation_owned_hosts': [], 'remaining_owned_port_listeners': []}
    terminal = {'status': 'CONFLICT_JOURNEY_RECEIPT_COLLECTED', 'verifier_invoked': True, 'error': None, 'harness_exit': 0}
    metadata = {'schema': 'aaos.run-retention/v1', 'owner': 'ArcheAxis-Knowledge-OS',
                'worktree_root': guest_repo, 'run_id': probe_name, 'source_commit': expected['harness_commit'],
                'source_patch_sha256': empty}
    if change == 'wrong-candidate':
        body['host']['sha256'] = 'f' * 64
    elif change == 'wrong-source':
        execution['source_commit'] = 'f' * 40
    elif change == 'harness-failed':
        terminal['harness_exit'] = 1
    elif change == 'missing-restart':
        conflict['ui_result']['restart_readback'] = False
    elif change == 'malformed-ui':
        conflict['ui_result'] = []
    elif change == 'journey-escape':
        body['run_root'] = str(PureWindowsPath(guest_run).parent.parent / probe_name)
    elif change == 'metadata-drift':
        metadata['owner'] = 'other-owner'
    for path, value in [(output / 'guest-terminal.json', terminal),
                        (output / 'conflict-run-execution.json', execution),
                        (output / 'conflict-journey-receipt.json', body),
                        (host_run / 'artifacts/execution.json', execution),
                        (host_probe / 'tmp/journey/receipt.json', body),
                        (host_probe / 'run-metadata.json', metadata)]:
        native = Path(subject.inputs.native(path))
        native.parent.mkdir(parents=True, exist_ok=True)
        native.write_text(json.dumps(value), encoding='utf-8')
    if change == 'canonical-drift':
        Path(subject.inputs.native(host_probe / 'tmp/journey/receipt.json')).write_bytes(b'{}')
    if change == 'none':
        assert subject.verify_conflict(plan)['status'] == 'PASS_TRUSTED_INSTALLED_CONFLICT_AND_RESTART_ONLY'
    else:
        with pytest.raises(ValueError, match='Conflict'):
            subject.verify_conflict(plan)


@pytest.mark.parametrize('mode', ['natural', 'forced', 'unconfirmed', 'force-error', 'wait-error'])
def test_owned_connection_handle_terminal_is_explicit_and_failures_are_retained(tmp_path, monkeypatch, mode):
    class Child:
        pid = 12345
        returncode = None
        def wait(self, timeout):
            if mode == 'wait-error':
                raise RuntimeError('synthetic wait failure')
            if self.returncode is None:
                if mode != 'natural':
                    raise subprocess.TimeoutExpired('synthetic owned connect', timeout)
                self.returncode = 0
            return self.returncode
    child = Child()
    stops = []
    def stop(owned):
        assert owned is child
        stops.append(owned.pid)
        if mode == 'force-error':
            raise RuntimeError('synthetic stop failure')
        if mode != 'unconfirmed':
            owned.returncode = 1
    monkeypatch.setattr(subject.shutil, 'which', lambda _: 'synthetic-wsb.exe')
    monkeypatch.setattr(subject.subprocess, 'Popen', lambda *a, **kw: child)
    monkeypatch.setattr(subject.dev, 'stop_owned_process', stop)
    cli = subject.native_cli(tmp_path)
    assert cli.reap_connections() == []
    cli(['connect', '--id', str(uuid.uuid4()), '--raw'])
    rows = cli.reap_connections()
    assert len(rows) == 1
    row = rows[0]
    assert row['pid'] == child.pid
    assert row['ownership_basis'] == 'RETAINED_POPEN_HANDLE_FROM_THIS_CONNECT'
    assert type(row['launch_observed_at_ns']) is int
    assert row['force_stop_attempted'] == (mode not in {'natural', 'wait-error'})
    assert stops == ([] if mode in {'natural', 'wait-error'} else [child.pid])
    assert row['status'] == ('REAPED_OWNED_HANDLE' if mode in {'natural', 'forced'} else 'UNCONFIRMED')
    assert bool(row['error']) == (mode not in {'natural', 'forced'})
    assert subject.read_object(tmp_path / 'connection-001-terminal.json') == row
    start = subject.read_object(tmp_path / row['start_receipt'])
    assert start['pid'] == row['pid']
    assert start['launch_observed_at_ns'] == row['launch_observed_at_ns']


@pytest.mark.parametrize('connection', ['none', 'reaped', 'unconfirmed', 'exception', 'write-failure'])
def test_environment_absence_does_not_replace_owned_connection_reaping(prepared, connection):
    paths, plan = prepared
    class Cli(FakeCli):
        def reap_connections(self):
            assert plan['sandbox_id'] not in self.environments
            if connection == 'exception':
                raise RuntimeError('synthetic reaper fault')
            if connection == 'none':
                return []
            return [{'status': 'REAPED_OWNED_HANDLE' if connection == 'reaped' else (
                        'TERMINAL_RECEIPT_WRITE_FAILED' if connection == 'write-failure' else 'UNCONFIRMED'),
                     'wait_returncode': 1 if connection == 'reaped' else None,
                     'returncode': 1 if connection == 'reaped' else None}]
    result = subject.execute(paths, plan, Cli(plan), pause=lambda _: None)
    assert result['stop'] == 'OWNED_ID_ABSENT_AFTER_OFFICIAL_STOP'
    saved = subject.read_object(paths['artifacts'] / 'shared-sandbox-execution.json')
    assert saved == result
    if connection in {'none', 'reaped'}:
        assert result['status'] == 'PASS_REAL_OFFLINE_SHARED_MAPPING_PROBE_ONLY'
        assert result['owned_connections'] == ([] if connection == 'none' else [
            {'status': 'REAPED_OWNED_HANDLE', 'wait_returncode': 1, 'returncode': 1}])
    else:
        assert result['status'] == 'FAIL_OR_INCOMPLETE'
        assert result['cleanup_or_reverification_error']


@pytest.mark.parametrize('confirmed', [True, False])
def test_repeated_reaper_reuses_final_owned_handle_result_without_retry(tmp_path, monkeypatch, confirmed):
    class Child:
        pid = 12345
        returncode = None
        waits = 0
        def wait(self, timeout):
            self.waits += 1
            if self.returncode is None:
                raise subprocess.TimeoutExpired('synthetic owned connection', timeout)
            return self.returncode
    child = Child()
    stops = []
    writes = []
    original_write = subject.write_json
    def stop(owned):
        assert owned is child
        stops.append(owned.pid)
        if confirmed:
            owned.returncode = 1
    def record_write(target, value):
        writes.append(target.name)
        original_write(target, value)
    monkeypatch.setattr(subject.shutil, 'which', lambda _: 'synthetic-wsb.exe')
    monkeypatch.setattr(subject.subprocess, 'Popen', lambda *a, **kw: child)
    monkeypatch.setattr(subject.dev, 'stop_owned_process', stop)
    monkeypatch.setattr(subject, 'write_json', record_write)
    cli = subject.native_cli(tmp_path)
    cli(['connect', '--id', str(uuid.uuid4()), '--raw'])
    first = cli.reap_connections()
    before = (child.waits, list(stops), list(writes), json.dumps(first, sort_keys=True))
    assert cli.reap_connections() is first
    assert before == (child.waits, stops, writes, json.dumps(first, sort_keys=True))
    assert len(first) == 1
    assert first[0]['status'] == ('REAPED_OWNED_HANDLE' if confirmed else 'UNCONFIRMED')


def test_terminal_write_failure_still_reaps_later_owned_handles_and_is_not_retried(tmp_path, monkeypatch):
    class Child:
        returncode = 0
        def __init__(self, pid):
            self.pid, self.waits = pid, 0
        def wait(self, timeout):
            self.waits += 1
            return self.returncode
    children = [Child(12345), Child(12346)]
    pending = iter(children)
    attempted = []
    original_write = subject.write_json
    def write(target, value):
        attempted.append(target.name)
        if target.name == 'connection-001-terminal.json':
            raise PermissionError('synthetic terminal write failure')
        original_write(target, value)
    monkeypatch.setattr(subject.shutil, 'which', lambda _: 'synthetic-wsb.exe')
    monkeypatch.setattr(subject.subprocess, 'Popen', lambda *a, **kw: next(pending))
    monkeypatch.setattr(subject, 'write_json', write)
    cli = subject.native_cli(tmp_path)
    for _ in children:
        cli(['connect', '--id', str(uuid.uuid4()), '--raw'])
    rows = cli.reap_connections()
    assert [child.waits for child in children] == [1, 1]
    assert rows[0]['status'] == 'TERMINAL_RECEIPT_WRITE_FAILED'
    assert rows[0]['terminal_receipt_error']['type'] == 'PermissionError'
    assert rows[1]['status'] == 'REAPED_OWNED_HANDLE'
    assert subject.read_object(tmp_path / 'connection-002-terminal.json') == rows[1]
    before = list(attempted)
    assert cli.reap_connections() is rows
    assert attempted == before
    assert [child.waits for child in children] == [1, 1]


@pytest.mark.parametrize('reaper_fails', [False, True])
def test_failed_environment_stop_still_reaps_connections_and_preserves_both_errors(prepared, reaper_fails):
    paths, plan = prepared
    class Cli(FakeCli):
        reaps = 0
        def reap_connections(self):
            self.reaps += 1
            if reaper_fails:
                raise RuntimeError('synthetic additional reaper failure')
            return [{'status': 'REAPED_OWNED_HANDLE', 'wait_returncode': 1, 'returncode': 1}]
    cli = Cli(plan, 'stop-failure')
    result = subject.execute(paths, plan, cli, pause=lambda _: None)
    assert cli.reaps == 1
    assert result['status'] == 'FAIL_OR_INCOMPLETE'
    assert result['cleanup_or_reverification_error']['message'] == 'synthetic stop failure'
    if reaper_fails:
        assert result['owned_connection_reap_error']['message'] == 'synthetic additional reaper failure'
    else:
        assert result['owned_connections'][0]['status'] == 'REAPED_OWNED_HANDLE'
    assert subject.read_object(paths['artifacts'] / 'shared-sandbox-execution.json') == result
