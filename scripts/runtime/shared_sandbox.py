"""Qualify shared read-only mappings and retained same-version lifecycle inputs.

Installation occurs only in the explicit lifecycle guest; never in the host.
No product inference, payload copy, ACL or global configuration change.
Each execution allocates a fresh ID/output and stops only that ID through the OS CLI.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path, PureWindowsPath
from xml.etree import ElementTree as ET

if __package__:
    from . import dev, sandbox_inputs as inputs, conflict_inputs, native_inputs
else:
    import dev
    import sandbox_inputs as inputs
    import conflict_inputs
    import native_inputs


def write_json(path: Path, value: dict) -> None:
    inputs.contained(path, path.parents[1])
    with open(inputs.native(path), 'x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def read_object(path: Path) -> dict:
    body = inputs.read_manifest(path)
    if not isinstance(body, dict):
        raise ValueError('Receipt must be a JSON object')
    return body


def nested(body: dict, *names: str) -> dict:
    for name in names:
        body = body.get(name)
        if not isinstance(body, dict):
            raise ValueError('Conflict receipt object missing or malformed')
    return body


def inventory(cli) -> set[str]:
    body = cli(['list', '--raw'])
    if not isinstance(body, dict) or not isinstance(body.get('WindowsSandboxEnvironments'), list):
        raise ValueError('Unknown official sandbox inventory')
    values = []
    for entry in body['WindowsSandboxEnvironments']:
        if not isinstance(entry, dict) or not isinstance(entry.get('Id'), str):
            raise ValueError('Unknown sandbox identity')
        values.append(str(uuid.UUID(entry['Id'])))
    if len(set(values)) != len(values):
        raise ValueError('Ambiguous sandbox identities')
    return set(values)


def native_cli(artifacts: Path):
    executable = shutil.which('wsb.exe')
    if os.name != 'nt' or not executable:
        raise ValueError('Installed Windows Sandbox CLI required')
    sequence = 0
    connections = []

    def invoke(arguments):
        nonlocal sequence
        sequence += 1
        record = {'arguments': arguments, 'status': 'STARTED'}
        target = artifacts / f'official-cli-{sequence:03}.json'
        try:
            if arguments[0] == 'connect':
                # The remote-session command can remain attached until the guest stops.
                # Keep the owned handle and a file log; do not block on its GUI lifetime.
                with open(inputs.native(artifacts / f'connection-{sequence:03}.log'), 'xb') as log:
                    child = subprocess.Popen([executable, *arguments], stdout=log, stderr=subprocess.STDOUT,
                                             creationflags=subprocess.CREATE_NO_WINDOW)
                connections.append(child)
                record.update(status='OWNED_CONNECTION_PROCESS_STARTED', pid=child.pid)
                return {'pid': child.pid}
            result = subprocess.run([executable, *arguments], capture_output=True,
                                    text=True, encoding='utf-8', errors='strict', timeout=180,
                                    creationflags=subprocess.CREATE_NO_WINDOW, check=False)
            record.update(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
            if result.returncode:
                raise ValueError('Official sandbox command failed; inspect exact CLI receipt')
            body = json.loads(result.stdout) if result.stdout.strip() else None
            record['status'] = 'RETURNED'
            return body
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            record.update(status='FAILED_OR_UNKNOWN', error_type=type(error).__name__)
            if isinstance(error, subprocess.TimeoutExpired):
                for key, value in [('partial_stdout', error.stdout), ('partial_stderr', error.stderr)]:
                    record[key] = value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value
            raise
        finally:
            write_json(target, record)

    def reap_connections():
        for child in connections:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                dev.stop_owned_process(child)
    invoke.reap_connections = reap_connections
    return invoke


def probe_binding(stage: Path, pin: str, nonce: str, roots: dict | None = None) -> dict:
    if inputs.identity(stage / 'input/inputs.json')['sha256'] != pin:
        raise ValueError('Manifest changed before probe binding')
    manifest = inputs.read_manifest(stage / 'input/inputs.json')
    for row in manifest['files']:
        inputs.member(row['path'])
    package = next(row['path'] for row in manifest['files'] if inputs.member(row['path'])[0] == 'package')
    probes = [package, inputs.ENTRY, str(inputs.GUEST_FOLDERS['AAOSTools'] / 'pwsh.exe')]
    for guest in probes:
        folder, relative = inputs.member(guest)
        # A read-only file attribute would not prove mapping-level isolation.
        source = Path(roots[folder]) if roots else stage / folder
        if getattr(os.stat(inputs.native(source / relative)), 'st_file_attributes', 0) & 1:
            raise ValueError('Probe representative is already a read-only host file')
    output = inputs.GUEST_FOLDERS['AAOSOutput']
    return {'nonce': nonce, 'manifest_sha256': pin, 'manifest': inputs.MANIFEST, 'probes': probes,
            'output_marker': str(output / 'shared-probe-marker.txt'), 'receipt': str(output / 'shared-probe.json')}


def command_for(binding: dict, mode: str = 'mapping') -> tuple[str, dict]:
    name = 'shared_native_sandbox_guest.ps1' if mode == 'native-mapping' else 'shared_sandbox_guest.ps1'
    template = inputs.regular(Path(__file__).with_name(name))
    source = template.read_text(encoding='utf-8')
    if source.count('__BINDING_BASE64__') != 1:
        raise ValueError('Unexpected guest probe template')
    encoded_binding = base64.b64encode(json.dumps(binding).encode()).decode()
    guest = source.replace('__BINDING_BASE64__', encoded_binding)
    return (str(inputs.GUEST_FOLDERS['AAOSTools'] / 'pwsh.exe')
            + ' -NoLogo -NoProfile -NonInteractive -EncodedCommand '
            + base64.b64encode(guest.encode('utf-16-le')).decode(), inputs.identity(template))


def config_for(stage: Path, output: Path, pin: str, mode: str = 'mapping', roots: dict | None = None) -> bytes:
    maker = native_inputs.proposal if mode == 'native-mapping' else inputs.proposal
    config = ET.fromstring(maker(stage, output, pin, roots))
    # The historical lifecycle entry must not run during a mapping-only probe.
    if mode in {'mapping', 'native-mapping'}:
        config.remove(config.find('LogonCommand'))
    elif mode not in {'lifecycle', 'conflict'}:
        raise ValueError('Unknown shared sandbox mode')
    return ET.tostring(config, encoding='utf-8', xml_declaration=True) + b'\n'


def lifecycle_identity(stage: Path, roots: dict | None = None,
                       scope: str = 'MIXED_CORE_SAME_VERSION_LIFECYCLE_ONLY') -> dict:
    manifest = inputs.read_manifest(stage / 'input/inputs.json')
    if manifest['scope'] != scope:
        raise ValueError('Only the reviewed mixed-core same-version lifecycle scope is supported')
    package = Path(roots['package']) if roots else stage / 'package'
    packaging = inputs.read_manifest(package / 'packaging-receipt.json')
    identity = inputs.read_manifest(package / 'mixed-core-identity.json')
    identity_pin = inputs.identity(package / 'mixed-core-identity.json')
    installers = [row for row in manifest['files'] if inputs.member(row['path'])[0] == 'package'
                  and row['path'].casefold().endswith('-setup.exe')]
    if (packaging.get('schema') != 'aaos.mixed-core-packaging/v1'
            or packaging.get('status') != 'LOCAL_MIXED_CORE_PACKAGING_PASS'
            or packaging.get('identity') != identity_pin
            or identity.get('status') != 'PINNED_MIXED_INPUTS_VERIFIED' or len(installers) != 1):
        raise ValueError('Incomplete or inconsistent mixed-core packaging identity')
    mixed = identity['payload']['mixed_components']
    return {'installer_sha256': installers[0]['sha256'], 'mixed_core_identity_sha256': identity_pin['sha256'],
            'mixed_core_receipt_sha256': inputs.identity(package / 'packaging-receipt.json')['sha256'],
            'host_sha256': mixed['host_sha256'], 'core_sha256': mixed['core_sha256'],
            'runtime_manifest_sha256': mixed['backend_runtime_manifest_sha256']}


def conflict_identity(stage: Path, roots: dict) -> dict:
    result = lifecycle_identity(stage, roots, conflict_inputs.SCOPE)
    manifest = inputs.read_manifest(stage / 'input/inputs.json')
    harness = manifest.get('harness_source', {})
    if (harness.get('kind') != 'HARNESS_SUBSET_NOT_PRODUCT_SOURCE'
            or not isinstance(harness.get('files'), list)
            or [row.get('path') for row in harness['files']] != list(conflict_inputs.HARNESS)):
        raise ValueError('Unreviewed conflict harness subset')
    repo = Path(roots['input']) / 'repo'
    for row in harness['files']:
        if inputs.identity(repo / row['path']) != {key: row[key] for key in ('bytes', 'sha256')}:
            raise ValueError('Conflict harness file changed')
    commit = conflict_inputs.git(repo, 'rev-parse', 'HEAD').decode().strip()
    tree = conflict_inputs.git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip()
    if commit != harness.get('snapshot_commit') or tree != harness.get('snapshot_tree'):
        raise ValueError('Conflict harness snapshot identity differs')
    if conflict_inputs.git(repo, 'status', '--porcelain').strip():
        raise ValueError('Conflict harness snapshot is dirty')
    return {**result, 'harness_commit': commit, 'harness_tree': tree,
            'harness_origin_commit': harness['original_commit']}


def prepare(paths: dict, stage: Path, pin: str, mode: str = 'mapping') -> dict:
    proposal = (native_inputs.prepare(paths, stage, pin, mapping_probe=True)
                if mode == 'native-mapping' else inputs.prepare(paths, stage, pin))
    if proposal['status'] != 'SHARED_INPUT_PROPOSAL_ONLY':
        raise ValueError('Inputs did not pass complete proposal verification')
    stage = Path(proposal['source_stage'])
    nonce = uuid.uuid4().hex
    owned = str(uuid.uuid4())
    binding = (native_inputs.probe_binding(stage, pin, nonce, proposal['source_roots'], owned)
               if mode == 'native-mapping' else probe_binding(stage, pin, nonce, proposal['source_roots']))
    command, template_identity = command_for(binding, mode)
    expected_lifecycle = lifecycle_identity(stage, proposal['source_roots']) if mode == 'lifecycle' else None
    expected_conflict = conflict_identity(stage, proposal['source_roots']) if mode == 'conflict' else None
    data = config_for(stage, Path(proposal['output']), pin, mode, proposal['source_roots'])
    destination = paths['artifacts'] / 'shared-probe.wsb'
    with open(inputs.native(destination), 'xb') as stream:
        stream.write(data)
    plan = {'schema': 'aaos.shared-sandbox-plan/v1', 'status': 'MAPPING_PROBE_PREPARED_ONLY',
            'run_root': str(paths['run']), 'stage': str(stage), 'source_manifest_sha256': pin,
            'source_roots': proposal['source_roots'],
            'members': proposal['members'], 'shared_logical_bytes': proposal['shared_logical_bytes'],
            'payload_bytes_copied': 0, 'sandbox_id': owned, 'nonce': nonce, 'mode': mode,
            'config': str(destination), 'config_identity': inputs.identity(destination),
            'output': proposal['output'], 'binding': binding, 'guest_template': template_identity,
            'run_metadata': inputs.identity(paths['run'] / 'run-metadata.json'),
            'command': command, 'expected_lifecycle': expected_lifecycle,
            'expected_conflict': expected_conflict, 'product_lifecycle': 'NOT_EXECUTED'}
    if mode == 'native-mapping':
        plan['native_retry_proposal'] = proposal['native_replay']
        plan['native_business'] = 'NOT_EXECUTED_REQUIRES_SEPARATE_QUALIFICATION'
    write_json(paths['artifacts'] / 'shared-sandbox-plan.json', plan)
    return plan


def verify_guest(plan: dict) -> dict:
    output = Path(plan['output'])
    result = read_object(output / 'shared-probe.json')
    binding = plan['binding']
    if (result.get('schema') != 'aaos.shared-sandbox-guest-probe/v1'
            or result.get('nonce') != plan['nonce'] or result.get('manifest_sha256') != plan['source_manifest_sha256']
            or result.get('status') != 'PASS_READONLY_HANDLES_OUTPUT_WRITE_AND_INPUT_IDENTITIES'
            or result.get('context') != 'SYSTEM_MAPPING_PROBE_ONLY'
            or type(result.get('members_verified')) is not int or result['members_verified'] != plan['members']
            or not isinstance(result.get('readonly'), list) or len(result['readonly']) != 3
            or any(not isinstance(row, dict) for row in result['readonly'])
            or [row.get('path') for row in result['readonly']] != binding['probes']
            or any(row.get('write_open_access_denied') is not True for row in result['readonly'])):
        raise ValueError('Guest proof missing, failed, stale or incorrectly bound')
    marker = inputs.regular(output / 'shared-probe-marker.txt')
    if marker.read_bytes() != ('aaos-shared-probe:' + plan['nonce']).encode():
        raise ValueError('Writable output marker differs')
    return result


def verify_lifecycle(plan: dict) -> dict:
    output = Path(plan['output'])
    terminal = read_object(output / 'guest-terminal.json')
    if (terminal.get('status') != 'VERIFIER_RETURNED_REQUIRES_LIFECYCLE_RECEIPT_REVIEW'
            or terminal.get('verifier_invoked') is not True or terminal.get('error') is not None):
        raise ValueError('Lifecycle guest did not finish successfully')
    receipts = []
    for directory in output.iterdir():
        if len(directory.name) == 32 and all(c in '0123456789abcdef' for c in directory.name):
            inputs.checked(directory)
            candidate = directory / 'lifecycle-receipt.json'
            if candidate.exists():
                receipts.append(candidate)
    if len(receipts) != 1:
        raise ValueError('Exactly one fresh lifecycle receipt required')
    body = read_object(receipts[0])
    if (body.get('schema') != 'archeaxis/installed-lifecycle-receipt/v1'
            or body.get('qualification_scope') != 'LOCAL_MIXED_CORE_INSTALLED_LIFECYCLE'
            or body.get('same_installer_scope') != 'SAME_INSTALLER_SAME_VERSION_REINSTALL_DATA_PRESERVATION'
            or type(body.get('pyc_growth')) is not int or body['pyc_growth'] != 0
            or any(body.get(key) is not True for key in ['complete_lifecycle_verified', 'graceful_shutdown',
                'forced_tree_cleanup', 'clean_uninstall', 'uninstall_retains_data', 'reinstall_readback'])
            or any(body.get(key) != value for key, value in plan['expected_lifecycle'].items())):
        raise ValueError('Lifecycle predicates or same-candidate identity do not match')
    return {'identity': inputs.identity(receipts[0]), 'receipt': body}


def verify_conflict(plan: dict) -> dict:
    output = Path(plan['output'])
    terminal = read_object(output / 'guest-terminal.json')
    execution = read_object(output / 'conflict-run-execution.json')
    body = read_object(output / 'conflict-journey-receipt.json')
    expected = plan['expected_conflict']
    empty_patch = hashlib.sha256(b'').hexdigest()
    guest_repo = str(inputs.GUEST_FOLDERS['AAOSOutput'] / 'repo')
    key = hashlib.sha256(guest_repo.casefold().encode()).hexdigest()[:10]
    guest_run = str(inputs.GUEST_FOLDERS['AAOSOutput'] / f'repo/.project-local/runs/{key}/wdconf')
    host_run = output / f'repo/.project-local/runs/{key}/wdconf'
    if (terminal.get('status') != 'CONFLICT_JOURNEY_RECEIPT_COLLECTED'
            or terminal.get('verifier_invoked') is not True or terminal.get('error') is not None
            or type(terminal.get('harness_exit')) is not int or terminal['harness_exit'] != 0
            or execution.get('status') != 'LOCAL_PASS' or execution.get('source_consistent') is not True
            or execution.get('child_exit_code') != 0 or execution.get('exit_code') != 0
            or execution.get('source_commit') != expected['harness_commit']
            or execution.get('source_tree') != expected['harness_tree']
            or execution.get('source_commit_after') != expected['harness_commit']
            or execution.get('source_patch_sha256') != empty_patch
            or execution.get('source_patch_sha256_after') != empty_patch
            or execution.get('run_root') != guest_run):
        raise ValueError('Conflict terminal/execution/source binding did not pass')
    # The harness owns a second canonical run inside the outer wdconf wrapper.
    # Bind its exact generated ID and metadata before resolving a host path.
    name = body.get('run_root')
    if not isinstance(name, str):
        raise ValueError('Conflict journey run root missing')
    probe_run = PureWindowsPath(name)
    if (str(probe_run) != name or probe_run.parent != PureWindowsPath(guest_run).parent
            or not re.fullmatch(r'webdriver-[0-9a-f]{12}', probe_run.name)):
        raise ValueError('Conflict journey run escaped the canonical guest namespace')
    host_probe = host_run.parent / probe_run.name
    metadata = read_object(host_probe / 'run-metadata.json')
    if (metadata.get('schema') != 'aaos.run-retention/v1'
            or metadata.get('owner') != 'ArcheAxis-Knowledge-OS'
            or metadata.get('worktree_root') != guest_repo or metadata.get('run_id') != probe_run.name
            or metadata.get('source_commit') != expected['harness_commit']
            or metadata.get('source_patch_sha256') != empty_patch):
        raise ValueError('Conflict journey run ownership/source metadata differs')
    # Check the actual canonical run, not a copied first-match receipt alone.
    if (inputs.identity(output / 'conflict-run-execution.json') != inputs.identity(host_run / 'artifacts/execution.json')
            or inputs.identity(output / 'conflict-journey-receipt.json') != inputs.identity(host_probe / 'tmp/journey/receipt.json')):
        raise ValueError('Conflict exported receipts differ from the actual canonical run')
    conflict = nested(body, 'installed_draft_conflict_loop')
    ui = nested(conflict, 'ui_result')
    source = {'commit': expected['harness_commit'], 'patch_sha256': empty_patch}
    if (body.get('ok') is not True or body.get('source_consistent') is not True
            or nested(body, 'host').get('sha256') != expected['host_sha256']
            or nested(body, 'installer').get('sha256') != expected['installer_sha256']
            or nested(conflict, 'launcher', 'core').get('sha256') != expected['core_sha256']
            or conflict.get('status') != 'PASS' or ui.get('status') != 'PASS'
            or ui.get('installed_ui') != 'TRUSTED_WEBDRIVER_CONTROLS'
            or ui.get('restart_readback') is not True or ui.get('source') != source or ui.get('final_source') != source
            or nested(conflict, 'fixture').get('source') != source
            or nested(conflict, 'initializer_exit').get('stopped') is not True
            or any(body.get(k) is not True for k in ('owned_identity_collection_verified', 'owned_ports_released', 'owned_process_cleanup'))
            or body.get('remaining_same_creation_owned_hosts') != [] or body.get('remaining_owned_port_listeners') != []):
        raise ValueError('Conflict predicates, cleanup or same-candidate identity do not match')
    return {'identity': inputs.identity(output / 'conflict-journey-receipt.json'),
            'execution_identity': inputs.identity(output / 'conflict-run-execution.json'),
            'status': 'PASS_TRUSTED_INSTALLED_CONFLICT_AND_RESTART_ONLY', 'source': source}


def execute(paths: dict, plan: dict, cli=None, *, pause=time.sleep) -> dict:
    artifacts = paths['artifacts']
    result_path = artifacts / 'shared-sandbox-execution.json'
    intent = artifacts / 'shared-sandbox-start-intent.json'
    if any(os.path.lexists(inputs.native(path)) for path in (result_path, intent)):
        raise ValueError('A sandbox run may not be replayed')
    if plan != inputs.read_manifest(artifacts / 'shared-sandbox-plan.json'):
        raise ValueError('Prepared plan changed')
    stage = Path(plan['stage'])
    stage = inputs.contained(stage, paths['dev'] / 'runs')
    # Recheck the entire declaration/private boundary before any declared payload.
    inspect = native_inputs.inspect_stage if plan['mode'] == 'native-mapping' else inputs.inspect_stage
    checked = inspect(stage, paths['dev'], plan['source_manifest_sha256'])
    output = inputs.contained(Path(plan['output']), artifacts)
    config = inputs.regular(Path(plan['config']))
    if (plan['run_root'] != str(paths['run']) or output != artifacts / 'sandbox-output'
            or config != artifacts / 'shared-probe.wsb'
            or inputs.identity(paths['run'] / 'run-metadata.json') != plan['run_metadata']
            or str(uuid.UUID(plan['sandbox_id'])) != plan['sandbox_id']
            or uuid.UUID(plan['nonce']).hex != plan['nonce']):
        raise ValueError('Prepared run/output/ID boundary changed')
    for value in checked['source_roots'].values():
        source = Path(value)
        if source == paths['run'] or source.is_relative_to(paths['run']) or paths['run'].is_relative_to(source):
            raise ValueError('Shared source overlaps the writable caller run')
    binding = (native_inputs.probe_binding(stage, plan['source_manifest_sha256'], plan['nonce'],
                                          checked['source_roots'], plan['sandbox_id'])
               if plan['mode'] == 'native-mapping' else
               probe_binding(stage, plan['source_manifest_sha256'], plan['nonce'], checked['source_roots']))
    command, template_identity = command_for(binding, plan['mode'])
    expected_lifecycle = lifecycle_identity(stage, checked['source_roots']) if plan['mode'] == 'lifecycle' else None
    expected_conflict = conflict_identity(stage, checked['source_roots']) if plan['mode'] == 'conflict' else None
    if (plan['binding'] != binding or plan['command'] != command or plan['guest_template'] != template_identity
            or plan['expected_lifecycle'] != expected_lifecycle
            or plan['expected_conflict'] != expected_conflict
            or plan['source_roots'] != checked['source_roots']
            or config.read_bytes() != config_for(stage, output, plan['source_manifest_sha256'], plan['mode'], checked['source_roots'])):
        raise ValueError('Prepared mapping/command/template differs from the reviewed policy')
    if (checked['members'] != plan['members'] or checked['shared_logical_bytes'] != plan['shared_logical_bytes']
            or inputs.identity(Path(plan['config'])) != plan['config_identity']
            or list(Path(plan['output']).iterdir())):
        raise ValueError('Launch inputs/configuration/output changed')
    cli = cli or native_cli(artifacts)
    if inventory(cli):
        raise ValueError('Existing sandbox environments preserved; no launch')
    owned = plan['sandbox_id']
    write_json(intent, {'schema': 'aaos.shared-sandbox-start-intent/v1', 'sandbox_id': owned,
                        'plan_identity': inputs.identity(artifacts / 'shared-sandbox-plan.json'),
                        'config_identity': plan['config_identity']})
    result = {'schema': 'aaos.shared-sandbox-execution/v1', 'status': 'FAIL_OR_INCOMPLETE',
              'sandbox_id': owned, 'payload_bytes_copied': 0, 'product_lifecycle': 'NOT_EXECUTED',
              'guest_write_isolation': 'NOT_VERIFIED', 'stop': 'NOT_REQUESTED', 'error': None}
    qualified = False
    try:
        cli(['start', '--id', owned, '--config', Path(plan['config']).read_text(encoding='utf-8'), '--raw'])
        if owned not in inventory(cli):
            raise ValueError('Requested sandbox ID was not observed')
        cli(['exec', '--id', owned, '--command', plan['command'], '--run-as', 'System', '--raw'])
        result['guest'] = native_inputs.verify_guest(plan) if plan['mode'] == 'native-mapping' else verify_guest(plan)
        result['guest_write_isolation'] = 'PASS_DECLARED_THREE_MAPPING_WRITE_HANDLES'
        if plan['mode'] in {'lifecycle', 'conflict'}:
            result['product_lifecycle' if plan['mode'] == 'lifecycle' else 'product_conflict'] = 'STARTED_PENDING_RECEIPT'
            cli(['connect', '--id', owned, '--raw'])
            for _ in range(480):
                if (output / 'guest-terminal.json').exists():
                    try:
                        inputs.read_manifest(output / 'guest-terminal.json')
                    except (OSError, json.JSONDecodeError):
                        pass  # Observation may race the guest's final file close.
                    else:
                        break
                if owned not in inventory(cli):
                    raise ValueError('Owned environment ended before guest terminal')
                pause(0.5)
            else:
                raise ValueError('Lifecycle guest terminal observation timed out')
            if plan['mode'] == 'lifecycle':
                result['lifecycle'] = verify_lifecycle(plan)
                result['product_lifecycle'] = 'PASS_SAME_CANDIDATE_SAME_VERSION_INSTALLED_LIFECYCLE'
            else:
                result['conflict'] = verify_conflict(plan)
                result['product_conflict'] = 'PASS_SAME_CANDIDATE_INSTALLED_CONFLICT_AND_RESTART'
        qualified = True
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        # The unique ID was bound in a durable intent before the one start attempt.
        # An unknown/timeout result never causes a second start or selection by PID.
        try:
            if owned in inventory(cli):
                write_json(artifacts / 'shared-sandbox-stop-intent.json', {'sandbox_id': owned,
                    'start_intent': inputs.identity(intent), 'action': 'OFFICIAL_STOP_EXACT_ID_ONLY'})
                cli(['stop', '--id', owned, '--raw'])
                for _ in range(40):
                    if owned not in inventory(cli):
                        result['stop'] = 'OWNED_ID_ABSENT_AFTER_OFFICIAL_STOP'
                        break
                    pause(0.5)
                else:
                    raise ValueError('Owned sandbox still present after stop')
            else:
                result['stop'] = 'OWNED_ID_ALREADY_ABSENT'
            if hasattr(cli, 'reap_connections'):
                cli.reap_connections()
            after = inspect(stage, paths['dev'], plan['source_manifest_sha256'])
            result['host_inputs_after'] = after
            if qualified and not result['error'] and result['guest_write_isolation'].startswith('PASS_'):
                result['status'] = {'lifecycle': 'PASS_REAL_OFFLINE_SHARED_SAME_VERSION_LIFECYCLE',
                                    'conflict': 'PASS_REAL_OFFLINE_SHARED_INSTALLED_CONFLICT',
                                    'mapping': 'PASS_REAL_OFFLINE_SHARED_MAPPING_PROBE_ONLY',
                                    'native-mapping': 'PASS_REAL_OFFLINE_NATIVE_COMPLETE_INPUT_MAPPING_ONLY'}[plan['mode']]
        except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as error:
            result['cleanup_or_reverification_error'] = {'type': type(error).__name__, 'message': str(error)}
        write_json(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--execute-probe', action='store_true')
    actions.add_argument('--execute-lifecycle', action='store_true')
    actions.add_argument('--execute-conflict', action='store_true')
    actions.add_argument('--prepare-native-probe', action='store_true')
    actions.add_argument('--execute-native-probe', action='store_true')
    args = parser.parse_args()
    try:
        run = os.environ.get('ARCHEAXIS_RUN_ROOT', '')
        paths = dev.layout(Path(__file__).resolve().parents[2], Path(run).name)
        if not run or Path(run) != paths['run']:
            raise ValueError('Run through scripts/runtime/dev.py')
        mode = ('native-mapping' if args.prepare_native_probe or args.execute_native_probe else
                'conflict' if args.execute_conflict else 'lifecycle' if args.execute_lifecycle else 'mapping')
        plan = prepare(paths, args.stage, args.manifest_sha256, mode)
        result = execute(paths, plan) if args.execute_probe or args.execute_lifecycle or args.execute_conflict or args.execute_native_probe else plan
        print(json.dumps({key: value for key, value in result.items() if key != 'command'}, ensure_ascii=False))
        return 0 if result['status'].startswith(('PASS_', 'MAPPING_PROBE_PREPARED_')) else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({'status': 'FAIL_CLOSED', 'error_type': type(error).__name__, 'error': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
