"""Qualify installed DeepTutor notebook custody with synthetic data, offline.

This exercises the upstream service shared by its UI/CLI, not a GUI acceptance.
The supplied interpreter is reused read-only. All writes use dev.py artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('notebook_dev', ROOT / 'scripts/runtime/dev.py')
assert _spec and _spec.loader
dev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dev)

PROBE = r'''
import hashlib, importlib.util, json, os, sys
from pathlib import Path
from importlib.metadata import version

home = Path(sys.argv[1]).resolve()
phase = sys.argv[2]
adapter_path = Path(sys.argv[3])
os.environ['DEEPTUTOR_HOME'] = str(home)
os.chdir(home)

def check_write(value):
    if isinstance(value, (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(value)).absolute()
        if not path.is_relative_to(home):
            raise PermissionError('probe attempted a write outside its synthetic home')

def audit(event, args):
    if event in ('socket.connect', 'socket.bind', 'subprocess.Popen', 'os.system'):
        raise PermissionError('network and child processes are disabled in notebook qualification')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).absolute()
        if path.drive.upper() == 'E:' or any(
            p.casefold() in {'.codex', '.zcode', '.hermes', '.claude', '.ssh', '.env', '.openhuman'}
            for p in path.parts
        ):
            raise PermissionError('private state access is forbidden in notebook qualification')
        mode, flags = args[1:3]
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        ):
            check_write(path)
    if event in ('os.mkdir', 'os.remove', 'os.rmdir'):
        check_write(args[0])
    if event == 'os.rename':
        check_write(args[0]); check_write(args[1])

sys.addaudithook(audit)
from deeptutor.services.notebook import NotebookManager
spec = importlib.util.spec_from_file_location('custody_adapter', adapter_path)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

assert version('deeptutor') == '1.5.17'
manager = NotebookManager()
assert manager.base_dir.resolve().is_relative_to(home)
manifest = home / 'expected.json'
if phase == 'seed':
    notebook = manager.create_notebook('合成学习笔记', description='ArcheAxis synthetic custody probe', color='#000000')
    saved = manager.add_record([notebook['id']], 'chat', '来源与回答',
        user_query='合成问题：水的化学式是什么？', output='合成回答：H₂O。',
        metadata={'source_ref': 'synthetic-source-001', 'anchor': 'paragraph:1'})
    assert saved['added_to_notebooks'] == [notebook['id']]
    record = manager.get_notebook(notebook['id'])
    exported = manager.export_markdown(notebook['id'])
    assert 'H₂O' in exported
    # The upstream reading export is intentionally not the lossless archive.
    assert '水的化学式' not in exported
    (home / 'notebook.custody.json').write_bytes(adapter.pack_notebook(record, exported))
    manifest.write_text(json.dumps({'notebook': record, 'markdown': exported}, ensure_ascii=False), encoding='utf-8')
else:
    expected = json.loads(manifest.read_text(encoding='utf-8'))
    notebook_id = expected['notebook']['id']
    assert manager.get_notebook(notebook_id) == expected['notebook'], 'restart changed notebook content'
    assert manager.export_markdown(notebook_id) == expected['markdown'], 'restart changed export'
    restored, markdown = adapter.unpack_notebook((home / 'notebook.custody.json').read_bytes())
    assert restored == expected['notebook'] and markdown == expected['markdown']
    assert restored['records'][0]['user_query'] == '合成问题：水的化学式是什么？'
    assert restored['records'][0]['metadata']['anchor'] == 'paragraph:1'
    # Damage only this synthetic derived index. The original notebook must
    # survive rebuilding and remain byte-identical after listing.
    original = manager.base_dir / (notebook_id + '.json')
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    manager.index_file.write_text('{broken synthetic index', encoding='utf-8')
    assert any(n['id'] == notebook_id for n in manager.list_notebooks())
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before
    assert manager.get_notebook(notebook_id) == expected['notebook']
    assert manager.export_markdown(notebook_id) == expected['markdown']
    (home / 'export.md').write_text(expected['markdown'], encoding='utf-8')
source = Path(sys.modules[NotebookManager.__module__].__file__)
print(json.dumps({'phase': phase, 'version': version('deeptutor'), 'status': 'PASS',
    'upstream_notebook_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}))
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    args = parser.parse_args(argv)
    interpreter = dev.safe_path(args.python)
    if not interpreter.is_file():
        raise ValueError('installed DeepTutor interpreter is missing')
    output = dev.artifact_directory(ROOT, 'deeptutor-notebook')
    home = output / 'synthetic-home'
    home.mkdir()
    script = output / 'probe.py'
    script.write_text(PROBE, encoding='utf-8')
    # Do not forward provider variables, agent configuration, or proxy settings.
    allowed = ('SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'TMPDIR')
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env['DEEPTUTOR_HOME'] = str(home)
    results = []
    for phase in ('seed', 'restart-and-rebuild'):
        process = subprocess.Popen([str(interpreter), '-I', '-B', '-X', 'utf8', str(script), str(home), phase,
            str(ROOT / 'app/adapters/deeptutor/custody.py')],
            env=env, cwd=home, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), start_new_session=os.name != 'nt')
        try:
            stdout, stderr = process.communicate(timeout=45)
        except BaseException:
            dev.stop_owned_process(process)
            raise
        (output / f'{phase}.log').write_bytes(stdout + stderr)
        results.append({'phase': phase, 'exit_code': process.returncode})
        if process.returncode:
            print(f'BLOCKED: {phase}; diagnostics: {output / (phase + ".log")}')
            return process.returncode
    hashes = {str(path.relative_to(home)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(home.rglob('*')) if path.is_file()}
    source_files = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        'scripts/ci/check_deeptutor_notebook.py', 'app/adapters/deeptutor/custody.py')}
    receipt = {'status': 'UPSTREAM_SERVICE_CUSTODY_PASS', 'results': results,
               'interpreter': str(interpreter), 'source_sha': dev.git(ROOT, 'rev-parse', 'HEAD'),
               'source_files': source_files, 'files': hashes,
               'limitations': 'Synthetic upstream service only; GUI, Core authority bridge and model calls not tested.'}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'receipt': str(output / 'receipt.json')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
