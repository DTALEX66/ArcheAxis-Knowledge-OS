"""Qualify shared read-only mappings and retained same-version lifecycle inputs.

Installation occurs only in the explicit lifecycle guest; never in the host.
No product inference, payload copy, ACL or global configuration change.
Each execution allocates a fresh ID/output and stops only that ID through the OS CLI.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

if __package__:
    from . import dev, sandbox_inputs as inputs
else:
    import dev
    import sandbox_inputs as inputs


def write_json(path: Path, value: dict) -> None:
    inputs.contained(path, path.parents[1])
    with open(inputs.native(path), 'x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


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


def probe_binding(stage: Path, pin: str, nonce: str) -> dict:
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
        if getattr(os.stat(inputs.native(stage / folder / relative)), 'st_file_attributes', 0) & 1:
            raise ValueError('Probe representative is already a read-only host file')
    output = inputs.GUEST_FOLDERS['AAOSOutput']
    return {'nonce': nonce, 'manifest_sha256': pin, 'manifest': inputs.MANIFEST, 'probes': probes,
            'output_marker': str(output / 'shared-probe-marker.txt'), 'receipt': str(output / 'shared-probe.json')}


def command_for(binding: dict) -> tuple[str, dict]:
    template = inputs.regular(Path(__file__).with_name('shared_sandbox_guest.ps1'))
    source = template.read_text(encoding='utf-8')
    if source.count('__BINDING_BASE64__') != 1:
        raise ValueError('Unexpected guest probe template')
    encoded_binding = base64.b64encode(json.dumps(binding).encode()).decode()
    guest = source.replace('__BINDING_BASE64__', encoded_binding)
    return (str(inputs.GUEST_FOLDERS['AAOSTools'] / 'pwsh.exe')
            + ' -NoLogo -NoProfile -NonInteractive -EncodedCommand '
            + base64.b64encode(guest.encode('utf-16-le')).decode(), inputs.identity(template))


def config_for(stage: Path, output: Path, pin: str, mode: str = 'mapping') -> bytes:
    config = ET.fromstring(inputs.proposal(stage, output, pin))
    # The historical lifecycle entry must not run during a mapping-only probe.
    if mode == 'mapping':
        config.remove(config.find('LogonCommand'))
    elif mode != 'lifecycle':
        raise ValueError('Unknown shared sandbox mode')
    return ET.tostring(config, encoding='utf-8', xml_declaration=True) + b'\n'


def lifecycle_identity(stage: Path) -> dict:
    manifest = inputs.read_manifest(stage / 'input/inputs.json')
    if manifest['scope'] != 'MIXED_CORE_SAME_VERSION_LIFECYCLE_ONLY':
        raise ValueError('Only the reviewed mixed-core same-version lifecycle scope is supported')
    packaging = inputs.read_manifest(stage / 'package/packaging-receipt.json')
    identity = inputs.read_manifest(stage / 'package/mixed-core-identity.json')
    identity_pin = inputs.identity(stage / 'package/mixed-core-identity.json')
    installers = [row for row in manifest['files'] if inputs.member(row['path'])[0] == 'package'
                  and row['path'].casefold().endswith('-setup.exe')]
    if (packaging.get('schema') != 'aaos.mixed-core-packaging/v1'
            or packaging.get('status') != 'LOCAL_MIXED_CORE_PACKAGING_PASS'
            or packaging.get('identity') != identity_pin
            or identity.get('status') != 'PINNED_MIXED_INPUTS_VERIFIED' or len(installers) != 1):
        raise ValueError('Incomplete or inconsistent mixed-core packaging identity')
    mixed = identity['payload']['mixed_components']
    return {'installer_sha256': installers[0]['sha256'], 'mixed_core_identity_sha256': identity_pin['sha256'],
            'mixed_core_receipt_sha256': inputs.identity(stage / 'package/packaging-receipt.json')['sha256'],
            'host_sha256': mixed['host_sha256'], 'core_sha256': mixed['core_sha256'],
            'runtime_manifest_sha256': mixed['backend_runtime_manifest_sha256']}


def prepare(paths: dict, stage: Path, pin: str, mode: str = 'mapping') -> dict:
    proposal = inputs.prepare(paths, stage, pin)
    if proposal['status'] != 'SHARED_INPUT_PROPOSAL_ONLY':
        raise ValueError('Inputs did not pass complete proposal verification')
    stage = Path(proposal['source_stage'])
    nonce = uuid.uuid4().hex
    binding = probe_binding(stage, pin, nonce)
    command, template_identity = command_for(binding)
    expected_lifecycle = lifecycle_identity(stage) if mode == 'lifecycle' else None
    data = config_for(stage, Path(proposal['output']), pin, mode)
    destination = paths['artifacts'] / 'shared-probe.wsb'
    with open(inputs.native(destination), 'xb') as stream:
        stream.write(data)
    plan = {'schema': 'aaos.shared-sandbox-plan/v1', 'status': 'MAPPING_PROBE_PREPARED_ONLY',
            'run_root': str(paths['run']), 'stage': str(stage), 'source_manifest_sha256': pin,
            'members': proposal['members'], 'shared_logical_bytes': proposal['shared_logical_bytes'],
            'payload_bytes_copied': 0, 'sandbox_id': str(uuid.uuid4()), 'nonce': nonce, 'mode': mode,
            'config': str(destination), 'config_identity': inputs.identity(destination),
            'output': proposal['output'], 'binding': binding, 'guest_template': template_identity,
            'run_metadata': inputs.identity(paths['run'] / 'run-metadata.json'),
            'command': command, 'expected_lifecycle': expected_lifecycle, 'product_lifecycle': 'NOT_EXECUTED'}
    write_json(paths['artifacts'] / 'shared-sandbox-plan.json', plan)
    return plan


def verify_guest(plan: dict) -> dict:
    output = Path(plan['output'])
    result = inputs.read_manifest(output / 'shared-probe.json')
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
    terminal = inputs.read_manifest(output / 'guest-terminal.json')
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
    body = inputs.read_manifest(receipts[0])
    if (body.get('schema') != 'archeaxis/installed-lifecycle-receipt/v1'
            or body.get('qualification_scope') != 'LOCAL_MIXED_CORE_INSTALLED_LIFECYCLE'
            or body.get('same_installer_scope') != 'SAME_INSTALLER_SAME_VERSION_REINSTALL_DATA_PRESERVATION'
            or type(body.get('pyc_growth')) is not int or body['pyc_growth'] != 0
            or any(body.get(key) is not True for key in ['complete_lifecycle_verified', 'graceful_shutdown',
                'forced_tree_cleanup', 'clean_uninstall', 'uninstall_retains_data', 'reinstall_readback'])
            or any(body.get(key) != value for key, value in plan['expected_lifecycle'].items())):
        raise ValueError('Lifecycle predicates or same-candidate identity do not match')
    return {'identity': inputs.identity(receipts[0]), 'receipt': body}


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
    checked = inputs.inspect_stage(stage, paths['dev'], plan['source_manifest_sha256'])
    output = inputs.contained(Path(plan['output']), artifacts)
    config = inputs.regular(Path(plan['config']))
    if (plan['run_root'] != str(paths['run']) or output != artifacts / 'sandbox-output'
            or config != artifacts / 'shared-probe.wsb'
            or inputs.identity(paths['run'] / 'run-metadata.json') != plan['run_metadata']
            or str(uuid.UUID(plan['sandbox_id'])) != plan['sandbox_id']
            or uuid.UUID(plan['nonce']).hex != plan['nonce']):
        raise ValueError('Prepared run/output/ID boundary changed')
    binding = probe_binding(stage, plan['source_manifest_sha256'], plan['nonce'])
    command, template_identity = command_for(binding)
    expected_lifecycle = lifecycle_identity(stage) if plan['mode'] == 'lifecycle' else None
    if (plan['binding'] != binding or plan['command'] != command or plan['guest_template'] != template_identity
            or plan['expected_lifecycle'] != expected_lifecycle
            or config.read_bytes() != config_for(stage, output, plan['source_manifest_sha256'], plan['mode'])):
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
    try:
        cli(['start', '--id', owned, '--config', Path(plan['config']).read_text(encoding='utf-8'), '--raw'])
        if owned not in inventory(cli):
            raise ValueError('Requested sandbox ID was not observed')
        cli(['exec', '--id', owned, '--command', plan['command'], '--run-as', 'System', '--raw'])
        result['guest'] = verify_guest(plan)
        result['guest_write_isolation'] = 'PASS_DECLARED_THREE_MAPPING_WRITE_HANDLES'
        if plan['mode'] == 'lifecycle':
            result['product_lifecycle'] = 'STARTED_PENDING_RECEIPT'
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
            result['lifecycle'] = verify_lifecycle(plan)
            result['product_lifecycle'] = 'PASS_SAME_CANDIDATE_SAME_VERSION_INSTALLED_LIFECYCLE'
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
            after = inputs.inspect_stage(stage, paths['dev'], plan['source_manifest_sha256'])
            result['host_inputs_after'] = after
            if not result['error'] and result['guest_write_isolation'].startswith('PASS_'):
                result['status'] = ('PASS_REAL_OFFLINE_SHARED_SAME_VERSION_LIFECYCLE'
                                    if plan['mode'] == 'lifecycle' else 'PASS_REAL_OFFLINE_SHARED_MAPPING_PROBE_ONLY')
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
    args = parser.parse_args()
    try:
        run = os.environ.get('ARCHEAXIS_RUN_ROOT', '')
        paths = dev.layout(Path(__file__).resolve().parents[2], Path(run).name)
        if not run or Path(run) != paths['run']:
            raise ValueError('Run through scripts/runtime/dev.py')
        plan = prepare(paths, args.stage, args.manifest_sha256, 'lifecycle' if args.execute_lifecycle else 'mapping')
        result = execute(paths, plan) if args.execute_probe or args.execute_lifecycle else plan
        print(json.dumps({key: value for key, value in result.items() if key != 'command'}, ensure_ascii=False))
        return 0 if result['status'].startswith(('PASS_', 'MAPPING_PROBE_PREPARED_')) else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({'status': 'FAIL_CLOSED', 'error_type': type(error).__name__, 'error': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
