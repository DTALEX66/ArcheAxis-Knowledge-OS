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
