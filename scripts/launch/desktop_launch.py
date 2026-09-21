"""Prepare a persistent TEST desktop development launch; --launch explicitly opens it.

Uses existing builds and the calling project interpreter, never installs or builds.
This is a development entry, not a portable installer or a user-library migration.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_launch(*, desktop: Path | None = None, core: Path | None = None,
                   fresh_workspace: bool = False) -> dict:
    # This desktop launcher is a TEST entry; bind every invocation to the
    # indexed resource roots before allocating any project-local run artifacts.
    # Explicit build paths do not widen the resource boundary.
    boundary_report = resource_boundaries.check_resource_boundaries(REPO, purpose='test')
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
    # Prefer an explicitly selected project interpreter (for example the
    # project-local Green candidate runtime that carries py-fsrs). Fall back to
    # the caller interpreter, then resolve before applying the no-reparse-path
    # policy. The selected executable is still validated and remains bound to
    # this project-local launch receipt.
    configured_python = os.environ.get('ARCHEAXIS_PYTHON')
    python_source = Path(configured_python) if configured_python else Path(sys.executable)
    python = dev.safe_path(python_source.resolve())
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
    source_head = dev.git(REPO, 'rev-parse', 'HEAD')
    receipt = {
        'schema': 'archeaxis.desktop-launch-prep/v1',
        'status': 'PREPARED_NOT_LAUNCHED',
        'launch_state': 'PREPARED_NOT_LAUNCHED',
        'runtime_claim': 'none',
        'workspace_mode': 'ISOLATED_TEST' if fresh_workspace else 'PERSISTENT_TEST', 'command': [str(desktop)], 'cwd': str(REPO),
        'path_scope': 'project-local',
        'source_head': source_head,
        'launcher_script_sha256': _sha256(Path(__file__).resolve()),
        'desktop_sha256': _sha256(desktop),
        'core_sha256': _sha256(core),
        'resource_boundary_purpose': boundary_report['purpose'],
        'resource_boundary_target': boundary_report['target']['id'],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'environment': {'ARCHEAXIS_PYTHON': str(python),
                        'ARCHAXIS_CORE_BIN': str(core),
                        'ARCHAXIS_VNEXT_DB': str(database),
                        'ARCHAXIS_WORKER_PROFILE': str(profile)},
        'receipt_path': str(directory / 'desktop-launch.json'),
    }
    receipt['worker_profile_sha256'] = _sha256(profile)
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
