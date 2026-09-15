"""Prepare a persistent TEST desktop development launch; --launch explicitly opens it.

Uses existing builds and the calling project interpreter, never installs or builds.
This is a development entry, not a portable installer or a user-library migration.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('desktop_dev', REPO / 'scripts/runtime/dev.py')
assert _spec and _spec.loader
dev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dev)
_resource_spec = importlib.util.spec_from_file_location(
    'resource_boundaries', REPO / 'scripts/maintenance/check_resource_boundaries.py')
assert _resource_spec and _resource_spec.loader
resource_boundaries = importlib.util.module_from_spec(_resource_spec)
_resource_spec.loader.exec_module(resource_boundaries)


def prepare_launch(*, desktop: Path | None = None, core: Path | None = None,
                   fresh_workspace: bool = False) -> dict:
    # The default desktop launcher is a TEST entry; bind it to the indexed
    # ceshi corpus before allocating any project-local run artifacts.
    if desktop is None and core is None:
        resource_boundaries.check_resource_boundaries(REPO, purpose='test')
    paths = dev.layout(REPO)
    desktop = dev.safe_path(desktop or paths['build'] / 'dotnet/ArcheAxis.Desktop/bin/Debug/net10.0/ArcheAxis.Desktop.exe')
    core = dev.safe_path(core or paths['cargo_build'] / 'debug/archeaxis-api.exe')
    for path in (desktop, core):
        if not path.is_relative_to(paths['dev']):
            raise ValueError('development executable must be inside project .project-local')
        if path.relative_to(paths['dev']).parts[0] not in {'build', 'runs', 'dist'}:
            raise ValueError('development executable must be a build, run or dist artifact')
        if not path.is_file():
            raise ValueError('required development executable is missing')
    # Resolve the interpreter link before applying the no-reparse-path policy.
    # CI images may expose Python through a symlink; the resolved executable is
    # still validated and remains bound to the current interpreter.
    python = dev.safe_path(Path(sys.executable).resolve())
    script = dev.safe_path(REPO / 'services/python-workers/transport/text_ndjson.py')
    if not python.is_file() or not script.is_file():
        raise ValueError('worker interpreter or script is missing')
    directory = dev.artifact_directory(REPO, 'desktop-launch')
    database = (directory / 'workspace.sqlite' if fresh_workspace else
                dev.state_path(REPO, 'desktop-test', 'workspace.sqlite'))
    profile = directory / 'worker-profile.json'
    profile.write_text(json.dumps({
        'schema': 'archeaxis.worker-profile/v1', 'python': str(python),
        'script': str(script), 'staging': str(directory / 'worker-staging'),
    }, indent=2) + '\n', encoding='utf-8')
    receipt = {
        'status': 'PREPARED_NOT_LAUNCHED',
        'workspace_mode': 'ISOLATED_TEST' if fresh_workspace else 'PERSISTENT_TEST', 'command': [str(desktop)], 'cwd': str(REPO),
        'environment': {'ARCHAXIS_CORE_BIN': str(core),
                        'ARCHAXIS_VNEXT_DB': str(database),
                        'ARCHAXIS_WORKER_PROFILE': str(profile)},
        'receipt_path': str(directory / 'desktop-launch.json'),
    }
    Path(receipt['receipt_path']).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desktop', type=Path)
    parser.add_argument('--core', type=Path)
    parser.add_argument('--fresh-workspace', action='store_true',
                        help='use a new isolated TEST database instead of resuming the worktree TEST workspace')
    parser.add_argument('--launch', action='store_true', help='open the prepared desktop and wait for it to close')
    args = parser.parse_args(argv)
    try:
        receipt = prepare_launch(desktop=args.desktop, core=args.core, fresh_workspace=args.fresh_workspace)
    except (OSError, ValueError) as exc:
        print(f'desktop preparation failed: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
    if not args.launch:
        return 0
    child = subprocess.Popen(receipt['command'], cwd=receipt['cwd'],
                             env={**os.environ, **receipt['environment']},
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                             start_new_session=os.name != 'nt')
    try:
        return child.wait()
    except BaseException:
        dev.stop_owned_process(child)
        raise


if __name__ == '__main__':
    raise SystemExit(main())
