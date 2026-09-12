"""Real normal/linked/concurrent/failing run and adversarial path regression."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

LAUNCHER = Path(__file__).resolve().parents[2] / 'scripts/runtime/dev.py'
SPEC = importlib.util.spec_from_file_location('dev_paths', LAUNCHER)
dev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev)


class DevelopmentPaths(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='runtime-paths-')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / '项目 with spaces'
        self.repo.mkdir()
        self.run_git('init', '-q')
        self.run_git('config', 'user.email', 'fixture@example.invalid')
        self.run_git('config', 'user.name', 'Path fixture')
        (self.repo / '.gitignore').write_text('.project-local/\n', encoding='utf-8')
        self.run_git('add', '.gitignore')
        self.run_git('commit', '-qm', 'fixture')
        self.env = dict(os.environ)
        self.env.pop('ARCHEAXIS_DEV_ROOT', None)
        self.env.pop('ARCHEAXIS_RUN_ROOT', None)
        self.env_patch = patch.dict(os.environ, self.env, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def run_git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args],
                                       text=True, encoding='utf-8', stderr=subprocess.STDOUT)

    def command(self, root=None, exit_code=0):
        return [sys.executable, '-B', str(LAUNCHER), '--root', str(root or self.repo), '--',
                sys.executable, '-B', '-c',
                'import os,pathlib,sys; '
                'pathlib.Path(os.environ["TMP"],"proof.txt").write_text("ok"); '
                f'sys.exit({exit_code})']

    def test_normal_run_writes_only_ignored_root_and_records_failure(self):
        before = {p.relative_to(self.repo) for p in self.repo.rglob('*') if '.git' not in p.parts}
        result = subprocess.run(self.command(exit_code=7), env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 7, result.stderr)
        receipts = list(self.repo.glob('.project-local/runs/*/*/artifacts/execution.json'))
        self.assertEqual(len(receipts), 1)
        receipt = json.loads(receipts[0].read_text(encoding='utf-8'))
        self.assertEqual(receipt['exit_code'], 7)
        self.assertEqual(len(receipt['source_commit']), 40)
        after = {p.relative_to(self.repo) for p in self.repo.rglob('*') if '.git' not in p.parts}
        self.assertTrue(all(p.parts[0] == '.project-local' for p in after - before))
        self.assertFalse((self.repo / '.hermes').exists())

    def test_concurrent_runs_do_not_share_tmp(self):
        children = [subprocess.Popen(self.command(), env=self.env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE) for _ in range(2)]
        for child in children:
            _, stderr = child.communicate(timeout=30)
            self.assertEqual(child.returncode, 0, stderr)
        proofs = list(self.repo.glob('.project-local/runs/*/*/tmp/proof.txt'))
        self.assertEqual(len(proofs), 2)
        self.assertNotEqual(proofs[0].parent, proofs[1].parent)

    def test_launcher_pins_actual_python_for_cross_language_workers(self):
        command = self.command()
        command[-1] = ('import os,sys,pathlib; '
                       'assert pathlib.Path(os.environ.get("ARCHEAXIS_PYTHON", "missing")) == pathlib.Path(sys.executable)')
        result = subprocess.run(command, env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cargo_mutable_cache_is_routed_to_project_root(self):
        values = dev.environment(dev.layout(self.repo, 'cargo-cache'))
        self.assertEqual(values.get('CARGO_HOME'), str(self.repo / '.project-local/cache/cargo'))

    def test_main_cargo_target_matches_bare_cargo_without_worktree_collision(self):
        import tomllib

        config = tomllib.loads((LAUNCHER.parents[2] / '.cargo/config.toml').read_text())
        main = dev.environment(dev.layout(self.repo, 'main-cargo'))
        self.assertEqual(Path(main['CARGO_TARGET_DIR']),
                         self.repo / config['build']['target-dir'])
        linked = self.repo / '.project-local/worktrees/cargo-linked'
        self.run_git('worktree', 'add', '--detach', str(linked))
        other = dev.environment(dev.layout(linked, 'linked-cargo'))
        self.assertNotEqual(main['CARGO_TARGET_DIR'], other['CARGO_TARGET_DIR'])
        self.assertTrue(Path(other['CARGO_TARGET_DIR']).is_relative_to(
            self.repo / '.project-local/build'))
        self.assertFalse((linked / '.project-local').exists())

    def test_nuget_child_overrides_foreign_caches_and_reuses_only_cache(self):
        names = ('NUGET_PACKAGES', 'NUGET_HTTP_CACHE_PATH',
                 'NUGET_PLUGINS_CACHE_PATH', 'NUGET_SCRATCH')
        child_env = dict(self.env)
        child_env.update({name: str(self.repo / 'foreign-cache') for name in names})
        command = self.command()
        command[-1] = (
            'import json,os,pathlib; '
            f'names={names!r}; '
            'root=pathlib.Path(os.environ["ARCHEAXIS_DEV_ROOT"]); '
            'run=pathlib.Path(os.environ["ARCHEAXIS_RUN_ROOT"]); '
            'values={name:os.environ[name] for name in names}; '
            'assert all(pathlib.Path(value).is_relative_to(root) for value in values.values()); '
            'assert pathlib.Path(values["NUGET_SCRATCH"]).is_relative_to(run/"tmp"); '
            '(run/"artifacts"/"nuget-paths.json").write_text(json.dumps(values))'
        )
        for _ in range(2):
            result = subprocess.run(command, env=child_env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        receipts = list(self.repo.glob('.project-local/runs/*/*/artifacts/nuget-paths.json'))
        self.assertEqual(len(receipts), 2)
        first, second = [json.loads(path.read_text()) for path in receipts]
        for name in names[:-1]:
            self.assertEqual(first[name], second[name])
        self.assertNotEqual(first['NUGET_SCRATCH'], second['NUGET_SCRATCH'])
        self.assertFalse((self.repo / 'foreign-cache').exists())

    def test_linked_worktree_uses_owner_root_with_separate_identity(self):
        linked = self.repo / '.project-local/worktrees/linked'
        self.run_git('worktree', 'add', '--detach', str(linked))
        a, b = dev.layout(self.repo), dev.layout(linked)
        self.assertEqual(a['dev'], b['dev'])
        self.assertNotEqual(a['run'].parent, b['run'].parent)
        result = subprocess.run(self.command(root=linked), env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((linked / '.project-local').exists())

    def test_unignored_root_rejected_before_write(self):
        (self.repo / '.gitignore').write_text('', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Git-ignored'):
            dev.layout(self.repo)
        self.assertFalse((self.repo / '.project-local').exists())

    def test_override_escape_and_run_traversal_rejected(self):
        with patch.dict(os.environ, {'ARCHEAXIS_DEV_ROOT': str(self.repo.parent)}), self.assertRaises(ValueError):
            dev.layout(self.repo)
        with self.assertRaisesRegex(ValueError, 'run ID'):
            dev.layout(self.repo, '../escape')

    def test_run_id_cannot_be_reused(self):
        paths = dev.layout(self.repo, 'same-run')
        dev.prepare(paths)
        with self.assertRaises(FileExistsError):
            dev.prepare(paths)

    def test_symlink_or_junction_cannot_redirect_root(self):
        target = self.repo / 'redirected'
        target.mkdir()
        link = self.repo / '.project-local'
        if os.name == 'nt':
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                                    capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.addCleanup(lambda: link.rmdir() if link.exists() else None)
        else:
            link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'linked development path'):
            dev.layout(self.repo)
        self.assertEqual(list(target.iterdir()), [])

    def test_subdirectory_caller_rejected(self):
        child = self.repo / 'child'
        child.mkdir()
        with self.assertRaisesRegex(ValueError, 'exact Git worktree'):
            dev.layout(child)

    def test_artifact_directory_allocates_distinct_children_in_owned_run(self):
        first = dev.artifact_directory(self.repo, 'probe')
        second = dev.artifact_directory(self.repo, 'probe')
        run = Path(os.environ['ARCHEAXIS_RUN_ROOT'])
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, run / 'artifacts' / 'probe')
        self.assertEqual(second.parent, first.parent)
        self.assertTrue(first.is_dir() and second.is_dir())

    def test_artifact_directory_rejects_traversal_before_allocating_run(self):
        for name in ('../escape', '/absolute', 'two/parts', '.zcode', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                dev.artifact_directory(self.repo, name)
        self.assertFalse((self.repo / '.project-local').exists())

    def test_artifact_directory_rejects_foreign_run(self):
        foreign = self.repo / 'foreign-run'
        foreign.mkdir()
        with patch.dict(os.environ, {'ARCHEAXIS_RUN_ROOT': str(foreign)}), self.assertRaises(ValueError):
            dev.artifact_directory(self.repo, 'probe')
        self.assertEqual(list(foreign.iterdir()), [])

    def test_state_path_is_stable_without_creating_files(self):
        first = dev.state_path(self.repo, 'batch', 'source.jsonl')
        second = dev.state_path(self.repo, 'batch', 'source.jsonl')
        self.assertEqual(first, second)
        self.assertTrue(first.is_relative_to(self.repo / '.project-local' / 'state'))
        self.assertFalse((self.repo / '.project-local').exists())
        for name in ('../escape', '/absolute', 'two/parts', '..'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                dev.state_path(self.repo, 'batch', name)

    def test_interrupted_output_stops_owned_child_and_records_cancelled(self):
        child = Mock()
        child.stdout.__iter__ = Mock(side_effect=KeyboardInterrupt)
        with patch.object(sys, 'argv', self.command()[3:]), \
             patch.object(dev.subprocess, 'Popen', return_value=child), \
             patch.object(dev, 'stop_owned_process') as stop, \
             patch.object(dev, 'git', return_value='a' * 40), \
             patch.object(dev, 'layout', return_value={
                 'root': self.repo, 'run': self.repo / 'run',
                 'artifacts': self.repo / 'artifacts'}), \
             patch.object(dev, 'prepare', return_value={}):
            (self.repo / 'artifacts').mkdir()
            self.assertEqual(dev.main(), 130)
        stop.assert_called_once_with(child)
        receipt = json.loads((self.repo / 'artifacts/execution.json').read_text())
        self.assertEqual(receipt['exit_code'], 130)
        self.assertTrue(receipt['cancelled'])

    @unittest.skipUnless(os.name == 'nt', 'Windows process-tree verification')
    def test_windows_cleanup_reaps_grandchild_and_preserves_unrelated_process(self):
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        sleeper = [sys.executable, '-B', '-c', 'import time; time.sleep(120)']
        outsider = subprocess.Popen(sleeper, creationflags=subprocess.CREATE_NO_WINDOW)
        parent = subprocess.Popen(
            [sys.executable, '-B', '-c',
             'import subprocess,sys,time; '
             'p=subprocess.Popen([sys.executable,"-B","-c","import time; time.sleep(120)"]); '
             'print(p.pid,flush=True); time.sleep(120)'],
            stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        handle = None
        try:
            grandchild_pid = int(parent.stdout.readline())
            handle = kernel.OpenProcess(0x100000, False, grandchild_pid)
            self.assertTrue(handle)
            self.assertEqual(kernel.WaitForSingleObject(handle, 0), 258)
            dev.stop_owned_process(parent)
            self.assertIsNotNone(parent.poll())
            self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
            self.assertIsNone(outsider.poll())
        finally:
            dev.stop_owned_process(parent)
            dev.stop_owned_process(outsider)
            parent.stdout.close()
            if handle:
                kernel.CloseHandle(handle)

    def test_cleanup_failure_is_not_recorded_as_successful_cancellation(self):
        child = Mock()
        child.stdout.__iter__ = Mock(side_effect=KeyboardInterrupt)
        with patch.object(sys, 'argv', self.command()[3:]), \
             patch.object(dev.subprocess, 'Popen', return_value=child), \
             patch.object(dev, 'stop_owned_process', side_effect=RuntimeError('denied')), \
             patch.object(dev, 'git', return_value='a' * 40), \
             patch.object(dev, 'layout', return_value={
                 'root': self.repo, 'run': self.repo / 'run',
                 'artifacts': self.repo / 'artifacts'}), \
             patch.object(dev, 'prepare', return_value={}):
            (self.repo / 'artifacts').mkdir()
            with self.assertRaisesRegex(RuntimeError, 'cleanup failed'):
                dev.main()
        receipt = json.loads((self.repo / 'artifacts/execution.json').read_text())
        self.assertEqual(receipt['exit_code'], 1)
        self.assertEqual(receipt['owned_process_cleanup'], 'failed')


if __name__ == '__main__':
    unittest.main()
