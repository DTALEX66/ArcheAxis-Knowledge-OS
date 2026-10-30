"""Counterexamples for the owned-ID shared mapping launcher; no VM in unit tests."""
import hashlib
import json
import subprocess
import uuid
from pathlib import Path

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
