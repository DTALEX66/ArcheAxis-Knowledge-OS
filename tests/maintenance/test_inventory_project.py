"""Metadata inventory boundaries; run through the project dev launcher."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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

    def test_capacity_comparison_reports_growth_and_explicit_budget_without_deletion(self):
        (self.project / "target").mkdir()
        sample = self.project / "target" / "sample.bin"
        sample.write_bytes(b"abc")
        baseline = self.scan()
        sample.write_bytes(b"abcdef")
        current = self.scan()
        diagnosis = self.inventory.capacity_diagnostics(current, baseline, {"target": 5})
        self.assertEqual(diagnosis["comparison_status"], "COMPARABLE_OBSERVED_SCOPE")
        row = next(r for r in diagnosis["groups"] if r["path"] == "target")
        self.assertEqual(row["delta_bytes"], 3)
        self.assertEqual(row["budget_status"], "EXCEEDED")
        self.assertIn("cargo", row["producer"])
        self.assertEqual(sample.read_bytes(), b"abcdef")

    def test_volume_free_change_is_measured_without_claiming_reclaimed_space(self):
        observations = [SimpleNamespace(total=1000, used=600, free=400),
                        SimpleNamespace(total=1000, used=620, free=380)]
        with patch.object(shutil, 'disk_usage', side_effect=observations) as usage:
            report = self.scan()
        self.assertEqual(usage.call_count, 2)
        self.assertTrue(all(call.args == (self.project,) for call in usage.call_args_list))
        volume = report['volume_space']
        self.assertEqual(volume['before']['free_bytes'], 400)
        self.assertEqual(volume['after']['free_bytes'], 380)
        self.assertEqual(volume['observed_free_delta_bytes'], -20)
        self.assertIsNone(volume['attributed_reclaimed_bytes'])

    def test_volume_failure_retains_logical_inventory_and_explicit_unknown(self):
        (self.project / 'sample').write_bytes(b'abc')
        with patch.object(shutil, 'disk_usage', side_effect=OSError('volume unavailable')):
            report = self.scan()
        self.assertEqual(report['totals']['bytes'], 3)
        self.assertEqual(report['volume_space']['before']['status'], 'unavailable')
        self.assertIsNone(report['volume_space']['observed_free_delta_bytes'])

    def test_invalid_root_does_not_query_volume(self):
        with patch.object(shutil, 'disk_usage', side_effect=AssertionError('must not query')):
            report = self.scan('E:/not-authorized')
        self.assertEqual(report['status'], 'error')

    def test_capacity_never_calls_an_opaque_or_missing_group_under_budget(self):
        (self.project / ".hermes").mkdir()
        current = self.scan()
        diagnosis = self.inventory.capacity_diagnostics(current, budgets={".hermes": 100, "missing": 100})
        states = {r["path"]: r["budget_status"] for r in diagnosis["groups"]}
        self.assertEqual(states[".hermes"], "UNKNOWN")
        self.assertEqual(states["missing"], "UNKNOWN")

    def test_capacity_rejects_different_scope_and_marks_changed_completeness(self):
        current = self.scan()
        baseline = json.loads(json.dumps(current))
        baseline["root"] = str(self.project / "another")
        with self.assertRaisesRegex(ValueError, "scope"):
            self.inventory.capacity_diagnostics(current, baseline)
        baseline["root"] = current["root"]
        baseline["totals"]["errors"] = 1
        diagnosis = self.inventory.capacity_diagnostics(current, baseline)
        self.assertEqual(diagnosis["comparison_status"], "INCOMPLETE_OR_CHANGED_OBSERVATIONS")

    def test_capacity_cli_budget_is_an_alarm_not_a_cleanup_command(self):
        (self.project / "target").mkdir()
        sample = self.project / "target" / "sample.bin"
        sample.write_bytes(b"abc")
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.project),
                                 "--budget", "target=2"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["capacity"]["exceeded_groups"], ["target"])
        self.assertEqual(sample.read_bytes(), b"abc")

    def test_capacity_baseline_refuses_private_and_external_paths_before_reading(self):
        for path in [self.project / ".project-local/.zcode/snapshot.json",
                     self.project / ".project-local/agents/snapshot.json",
                     self.project / "outside.json"]:
            with (
                patch.object(Path, "read_text", side_effect=AssertionError("must not read")),
                self.assertRaises(ValueError),
            ):
                self.inventory.load_baseline(path, self.project)

    def test_capacity_cli_unknown_budget_cannot_pass(self):
        (self.project / '.zcode').mkdir()
        for group in ('.zcode', 'missing'):
            with self.subTest(group=group):
                result = subprocess.run(
                    [sys.executable, '-B', str(SCRIPT), str(self.project),
                     '--budget', f'{group}=100'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 3, result.stderr)
                capacity = json.loads(result.stdout)['capacity']
                self.assertEqual(capacity['unknown_budget_groups'], [group])

    def test_capacity_cli_exceeded_takes_precedence_over_unknown(self):
        (self.project / 'target').mkdir()
        (self.project / 'target/sample.bin').write_bytes(b'abc')
        result = subprocess.run(
            [sys.executable, '-B', str(SCRIPT), str(self.project),
             '--budget', 'target=2', '--budget', 'missing=100'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        capacity = json.loads(result.stdout)['capacity']
        self.assertEqual(capacity['unknown_budget_groups'], ['missing'])
        self.assertEqual(capacity['exceeded_groups'], ['target'])

    def test_private_directories_and_mixed_hermes_are_opaque_unknown_size(self):
        for name in (".codex", ".dsh", ".openhuman", ".hermes", ".zcode"):
            (self.project / name).mkdir()
            (self.project / name / "private.dat").write_bytes(b"do not read")
        (self.project / "src").mkdir()
        (self.project / "src" / ".claude").mkdir()
        (self.project / "src" / ".claude" / "private.dat").write_bytes(b"do not read")
        real_scandir = os.scandir

        def reject_private_scan(path):
            self.assertNotIn(Path(path).name, {".git", ".codex", ".dsh", ".openhuman", ".hermes", ".claude", ".zcode"})
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

    @unittest.skipUnless(os.name == "nt", "Windows long-path metadata regression")
    def test_long_project_paths_are_counted_without_following_links(self):
        long_dir = self.project / ("a" * 80) / ("b" * 80) / ("c" * 80)
        native = Path("\\\\?\\" + str(long_dir))
        native.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, Path("\\\\?\\" + str(self.project / ("a" * 80))))
        (native / "sample.txt").write_bytes(b"long-path-sample")
        report = self.scan()
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["totals"]["bytes"], len(b"long-path-sample"))

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
