"""Prepare a clean, bounded conflict harness; never launch or install anything.

Reuse the retained installer/PowerShell. Copy only the declared public portable
Git/drivers/guest entry and a small Git-blob-bound harness, not the old repository
or its history/private state. The new Git identity is a HARNESS SUBSET snapshot,
never the product build identity. Failed preparations remain preserved.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

if __package__:
    from . import dev, sandbox_inputs as inputs
else:
    import dev
    import sandbox_inputs as inputs


HARNESS = (
    '.gitignore', 'scripts/runtime/dev.py',
    'scripts/probes/aaos01_tauri_webdriver_loop.py',
    'scripts/probes/aaos01_office_runtime_loop.py',
    'scripts/probes/native_tcp_listeners.py',
    'scripts/probes/aaos01_grouped_owner_loop.py',
    'scripts/probes/aaos01_installed_draft_conflict_loop.py',
    'scripts/probes/aaos_native_menu_exit.py',
)
SCOPE = 'MIXED_CORE_INSTALLED_CONFLICT_CLEAN_HARNESS_SUBSET'


def write(path: Path, data: bytes) -> None:
    inputs.checked(path.parent).mkdir(parents=True, exist_ok=True)
    with open(inputs.native(path), 'xb') as stream:
        stream.write(data)


def save(path: Path, body: dict) -> None:
    write(path, (json.dumps(body, ensure_ascii=False, indent=2) + '\n').encode())


def selected(document: dict) -> list[dict]:
    if (not isinstance(document, dict) or document.get('scope') != 'MIXED_CORE_INSTALLED_CONFLICT_JOURNEY'
            or document.get('approval') != 'ROOT_REVIEWED_FOR_THIS_FRESH_RUN'
            or not isinstance(document.get('files'), list) or 'source_roots' in document):
        raise ValueError('Only the reviewed original conflict source format is supported')
    result, seen = [], set()
    git_prefix = str(inputs.GUEST_FOLDERS['AAOSInput'] / 'git') + '\\'
    driver_prefix = str(inputs.GUEST_FOLDERS['AAOSInput'] / 'drivers') + '\\'
    prefixes = (str(inputs.GUEST_FOLDERS['AAOSInstall']) + '\\',
                str(inputs.GUEST_FOLDERS['AAOSTools']) + '\\', git_prefix, driver_prefix)
    for row in document['files']:
        if not isinstance(row, dict) or not isinstance(row.get('path'), str):
            raise ValueError('Malformed original declaration')
        name = row['path']
        # Selection is lexical. No old repo file, including .git/private state,
        # is enumerated, opened, hashed or copied by this preparation.
        if not (name.startswith(prefixes) or name == inputs.ENTRY):
            continue
        inputs.member(name)
        if (name.casefold() in seen or type(row.get('bytes')) is not int or row['bytes'] < 0
                or not isinstance(row.get('sha256'), str) or not inputs.SHA.fullmatch(row['sha256'])):
            raise ValueError('Ambiguous selected source identity')
        seen.add(name.casefold())
        result.append(row)
    if (inputs.ENTRY.casefold() not in seen
            or not any(x['path'].startswith(git_prefix) for x in result)
            or not any(x['path'].startswith(driver_prefix) for x in result)):
        raise ValueError('Declared conflict tools or guest entry missing')
    return result


def git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    # A new snapshot has no remotes/hooks/credentials and uses no global config.
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME='AAOS Local Harness', GIT_COMMITTER_NAME='AAOS Local Harness',
               GIT_AUTHOR_EMAIL='harness@localhost', GIT_COMMITTER_EMAIL='harness@localhost',
               GIT_AUTHOR_DATE='2000-01-01T00:00:00Z', GIT_COMMITTER_DATE='2000-01-01T00:00:00Z')
    result = subprocess.run(['git', '-c', 'core.longpaths=true', '-C', str(root), *args], input=data, capture_output=True,
                            env=env, check=False, timeout=120)
    if result.returncode:
        raise ValueError('Bounded local Git operation failed: ' + args[0] + ': '
                         + result.stderr.decode('utf-8', errors='replace')[:2000])
    return result.stdout


def snapshot(root: Path, destination: Path, source_commit: str, empty_template: Path) -> dict:
    if git(root, 'rev-parse', 'HEAD').decode().strip() != source_commit:
        raise ValueError('Source HEAD differs from requested harness identity')
    git(root, 'diff', '--quiet', 'HEAD', '--', *HARNESS)
    blobs = []
    # Validate all selected Git declarations before extracting any blob.
    for name in HARNESS:
        inputs.member(str(inputs.GUEST_FOLDERS['AAOSInput'] / ('repo/' + name)))
        tree = git(root, 'ls-tree', source_commit, '--', name).decode().strip()
        head, path = tree.split('\t') if '\t' in tree else ('', '')
        values = head.split()
        if path != name or len(values) != 3 or values[:2] != ['100644', 'blob']:
            raise ValueError('Harness source is not an exact independent Git blob')
        blobs.append({'path': name, 'git_blob': values[2]})
    destination.mkdir(parents=True)
    empty_template.mkdir()
    git(destination, 'init', '--initial-branch=probe-snapshot', '--template=' + str(empty_template))
    for row in blobs:
        path = destination / row['path']
        write(path, git(root, 'cat-file', 'blob', row['git_blob']))
        row.update(inputs.identity(path))
    git(destination, 'add', '--', *HARNESS)
    tree = git(destination, 'write-tree').decode().strip()
    commit = git(destination, '-c', 'commit.gpgsign=false', 'commit-tree', tree,
                 data=b'Finite conflict harness subset; not a product source snapshot\n').decode().strip()
    git(destination, 'update-ref', 'refs/heads/probe-snapshot', commit)
    git(destination, 'diff', '--quiet', 'HEAD', '--')
    return {'kind': 'HARNESS_SUBSET_NOT_PRODUCT_SOURCE', 'original_commit': source_commit,
            'original_tree': git(root, 'rev-parse', source_commit + '^{tree}').decode().strip(),
            'snapshot_commit': commit, 'snapshot_tree': tree, 'files': blobs}


def prepare(paths: dict, original: Path, pin: str, source_commit: str) -> dict:
    run = inputs.caller_run(paths)
    if len(source_commit) != 40 or any(c not in '0123456789abcdef' for c in source_commit):
        raise ValueError('A full lowercase harness source commit is required')
    original = inputs.contained(original, paths['dev'] / 'runs')
    if original == run or original.is_relative_to(run) or run.is_relative_to(original):
        raise ValueError('Original inputs overlap the writable preparation run')
    manifest = original / 'input/inputs.json'
    if not inputs.SHA.fullmatch(pin) or inputs.identity(manifest)['sha256'] != pin:
        raise ValueError('Original manifest pin differs')
    rows = selected(inputs.read_manifest(manifest))
    stage = paths['artifacts'] / 'clean-conflict-source'
    if os.path.lexists(inputs.native(stage)):
        raise ValueError('Fresh preparation required; old evidence preserved')
    expected = {}
    for row in rows:
        folder, relative = inputs.member(row['path'])
        expected.setdefault(folder, set()).add(relative)
    # Only the four public source groups are enumerated. The old repo is never entered.
    for folder, prefix, guest in [('package', '', 'AAOSInstall'), ('tools', '', 'AAOSTools'),
                                  ('input', 'git', 'AAOSInput'), ('input', 'drivers', 'AAOSInput')]:
        actual = inputs.inventory(original / folder / prefix, guest)
        actual = {prefix + '/' + name if prefix else name for name in actual}
        declared = {name for name in expected.get(folder, set()) if not prefix or name.startswith(prefix + '/')}
        if actual != declared:
            raise ValueError('Selected public source group differs from declared inventory')
    stage.mkdir()
    copied = 0
    for row in rows:
        folder, relative = inputs.member(row['path'])
        source = original / folder / relative
        if inputs.identity(source) != {key: row[key] for key in ('bytes', 'sha256')}:
            raise ValueError('Selected original member changed')
        if folder == 'input':
            target = stage / folder / relative
            inputs.checked(target.parent).mkdir(parents=True, exist_ok=True)
            with open(inputs.native(source), 'rb') as src, open(inputs.native(target), 'xb') as dst:
                shutil.copyfileobj(src, dst)
            if inputs.identity(target) != {key: row[key] for key in ('bytes', 'sha256')}:
                raise ValueError('Copied public tool identity differs')
            copied += row['bytes']
    harness = snapshot(paths['root'], stage / 'input/repo', source_commit, paths['tmp'] / 'empty-git-template')
    roots = {'input': stage / 'input', 'package': original / 'package', 'tools': original / 'tools'}
    members = []
    for guest, folder in inputs.ROOTS.items():
        for name in sorted(inputs.inventory(roots[folder], guest)):
            members.append({'path': str(inputs.GUEST_FOLDERS[guest] / name), **inputs.identity(roots[folder] / name)})
    body = {'approval': 'ROOT_REVIEWED_FOR_THIS_FRESH_RUN', 'scope': SCOPE,
            'source_roots': {name: str(path) for name, path in roots.items()}, 'harness_source': harness,
            'original_manifest_sha256': pin, 'files': members}
    save(stage / 'input/inputs.json', body)
    new_pin = inputs.identity(stage / 'input/inputs.json')['sha256']
    verified = inputs.inspect_stage(stage, paths['dev'], new_pin)
    if inputs.identity(manifest)['sha256'] != pin or git(paths['root'], 'rev-parse', 'HEAD').decode().strip() != source_commit:
        raise ValueError('Original manifest or harness HEAD changed during preparation')
    result = {'schema': 'aaos.clean-conflict-inputs/v1', 'status': 'PREPARED_HOST_ONLY_NOT_CONFLICT_QUALIFIED',
              'stage': str(stage), 'manifest_sha256': new_pin, 'verified': verified, 'harness_source': harness,
              'copied_original_tool_bytes': copied, 'package_and_powershell_bytes_copied': 0,
              'old_repository_read': False, 'launch': 'NOT_EXECUTED'}
    save(paths['artifacts'] / 'clean-conflict-inputs.json', result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-stage', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    try:
        run = os.environ.get('ARCHEAXIS_RUN_ROOT', '')
        paths = dev.layout(Path(__file__).resolve().parents[2], Path(run).name)
        if not run or Path(run) != paths['run']:
            raise ValueError('Run through scripts/runtime/dev.py')
        result = prepare(paths, args.original_stage, args.manifest_sha256, args.source_commit)
        print(json.dumps({key: result[key] for key in ('status', 'stage', 'manifest_sha256', 'launch')}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'FAIL_CLOSED_PREPARATION_PRESERVED', 'error_type': type(error).__name__, 'error': str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
