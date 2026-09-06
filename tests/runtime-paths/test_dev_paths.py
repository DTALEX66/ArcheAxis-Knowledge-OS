"""Real normal/linked/concurrent/failing run and adversarial path regression."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == '__main__':
    unittest.main()
