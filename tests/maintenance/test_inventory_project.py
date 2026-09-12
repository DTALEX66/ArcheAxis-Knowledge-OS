"""Metadata inventory boundaries; run through the project dev launcher."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/maintenance/inventory_project.py"


class InventoryProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        self.project.mkdir()
        subprocess.run(["git", "init", "--quiet", str(self.project)], check=True,
                       capture_output=True)
        spec = importlib.util.spec_from_file_location("inventory_project", SCRIPT)
        self.inventory = importlib.util.module_from_spec(spec)
        if SCRIPT.exists():
            spec.loader.exec_module(self.inventory)

    def scan(self, root=None):
        self.assertTrue(SCRIPT.is_file(), "read-only inventory tool is not implemented")
        return self.inventory.inventory_project(root or self.project)

    def test_real_tree_reports_logical_bytes_and_self_consistent_groups(self):
        (self.project / "root.txt").write_bytes(b"abc")
        (self.project / "src").mkdir()
        (self.project / "src" / "a.txt").write_bytes(b"12345")
        (self.project / "src" / "empty.txt").write_bytes(b"")
        report = self.scan()
        self.assertEqual(report["unit"], "logical_bytes")
        self.assertEqual(report["totals"]["bytes"], 8)
        self.assertEqual(report["totals"]["files"], 3)
        for field in ("bytes", "files", "errors", "skipped_reparse", "excluded"):
            self.assertEqual(report["totals"][field], sum(g[field] for g in report["groups"]))
        for group in report["groups"]:
            self.assertEqual(group["cleanup"]["status"], "pending")
            self.assertFalse(group["cleanup"]["deletion_authorized"])

    def test_private_directories_and_mixed_hermes_are_opaque_unknown_size(self):
        for name in (".codex", ".dsh", ".openhuman", ".hermes"):
            (self.project / name).mkdir()
            (self.project / name / "private.dat").write_bytes(b"do not read")
        (self.project / "src").mkdir()
        (self.project / "src" / ".claude").mkdir()
        (self.project / "src" / ".claude" / "private.dat").write_bytes(b"do not read")
        real_scandir = os.scandir

        def reject_private_scan(path):
            self.assertNotIn(Path(path).name, {".git", ".codex", ".dsh", ".openhuman", ".hermes", ".claude"})
            return real_scandir(path)

        with patch.object(os, "scandir", reject_private_scan):
            report = self.scan()
        self.assertEqual(report["totals"]["bytes"], 0)
        self.assertEqual(report["repository_total_bytes"], None)
        hermes = next(e for e in report["exclusions"] if e["path"] == ".hermes")
        self.assertIsNone(hermes["bytes"])
        self.assertEqual(hermes["status"], "not_measured")

    def test_directory_link_is_not_followed(self):
        target = Path(self.temp.name) / "outside"
        target.mkdir()
        (target / "outside.txt").write_bytes(b"outside")
        link = self.project / "redirect"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                                    capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        report = self.scan()
        self.assertEqual(report["totals"]["files"], 0)
        self.assertEqual(report["totals"]["skipped_reparse"], 1)
        self.assertEqual(report["reparse_points"][0]["path"], "redirect")

    def test_missing_root_and_non_root_are_explicit_errors(self):
        missing = self.scan(self.project / "missing")
        self.assertEqual(missing["status"], "error")
        self.assertEqual(missing["errors"][0]["kind"], "FileNotFoundError")
        child = self.project / "child"
        child.mkdir()
        report = self.scan(child)
        self.assertEqual(report["status"], "error")
        self.assertIn("exact Git project root", report["errors"][0]["message"])

    def test_scandir_permission_failure_preserves_other_measured_groups(self):
        denied = self.project / "denied"
        denied.mkdir()
        (self.project / "good.txt").write_bytes(b"123")
        real_scandir = os.scandir

        def deny_one(path):
            if Path(path) == denied:
                raise PermissionError("simulated directory permission denial")
            return real_scandir(path)

        with patch.object(os, "scandir", deny_one):
            report = self.scan()
        self.assertEqual(report["status"], "partial")
        self.assertEqual((report["totals"]["bytes"], report["totals"]["errors"]), (3, 1))
        self.assertEqual(report["errors"][0]["kind"], "PermissionError")

    def test_protected_drive_is_rejected_before_metadata_access(self):
        self.assertTrue(SCRIPT.is_file(), "read-only inventory tool is not implemented")
        with patch.object(Path, "lstat", side_effect=AssertionError("must not access protected drive")):
            report = self.inventory.inventory_project("E:/not-authorized")
        self.assertEqual(report["status"], "error")

    def test_inventory_never_opens_file_contents_and_accepts_extra_private_names(self):
        (self.project / "file.txt").write_bytes(b"abc")
        private = self.project / "custom-agent-runtime"
        private.mkdir()
        (private / "state.dat").write_bytes(b"private")
        with patch.object(Path, "open", side_effect=AssertionError("file contents must not be read")):
            report = self.inventory.inventory_project(self.project, exclude_names=["custom-agent-runtime"])
        self.assertEqual(report["totals"]["bytes"], 3)
        self.assertIn("custom-agent-runtime", {item["path"] for item in report["exclusions"]})

    def test_project_owned_agent_private_state_and_env_files_are_not_inspected(self):
        private = self.project / ".project-local" / "agents"
        private.mkdir(parents=True)
        (private / "state.dat").write_bytes(b"private state")
        (self.project / ".env.production").write_bytes(b"not a real credential")
        report = self.scan()
        self.assertEqual(report["totals"]["bytes"], 0)
        self.assertIn(".project-local/agents", {item["path"] for item in report["exclusions"]})

    def test_cli_outputs_json_and_reports_missing_root_with_nonzero_exit(self):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.project)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["mode"], "read_only_dry_run")
        missing = subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.project / "missing")],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(json.loads(missing.stdout)["status"], "error")


if __name__ == "__main__":
    unittest.main()
