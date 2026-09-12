"""Exercise generation/check commands and the generated Python parser."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/contracts/generate_vocabulary.py"
SOURCES = ("assessment-vocabulary.schema.json", "job-status.schema.json")
OUTPUTS = (
    "crates/archeaxis-contracts/src/generated/vocabulary.rs",
    "apps/ArcheAxis.Desktop/Contracts/Generated/Vocabulary.g.cs",
    "services/python-workers/contracts/generated/vocabulary.py",
)


class VocabularyGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "--quiet", str(self.root)], check=True, capture_output=True)
        source_dir = self.root / "packages/contracts/v1"
        source_dir.mkdir(parents=True)
        for name in SOURCES:
            (source_dir / name).write_bytes((ROOT / "packages/contracts/v1" / name).read_bytes())

    def run_generator(self, *args):
        self.assertTrue(SCRIPT.is_file(), "single-source vocabulary generator missing")
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(self.root), *args],
                              capture_output=True, text=True, encoding="utf-8", check=False)

    def test_missing_outputs_fail_check_without_writes(self):
        result = self.run_generator("--check")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(set(json.loads(result.stdout)["drift"]), set(OUTPUTS))
        self.assertFalse((self.root / "crates").exists())

    def test_generate_then_actual_constant_corruption_fails_exact_check(self):
        self.assertEqual(self.run_generator().returncode, 0)
        self.assertEqual(self.run_generator("--check").returncode, 0)
        for relative in OUTPUTS:
            path = self.root / relative
            original = path.read_bytes()
            path.write_bytes(original.replace(b'"queued"', b'"invented"', 1))
            result = self.run_generator("--check")
            self.assertEqual(result.returncode, 1, relative)
            self.assertIn(relative, json.loads(result.stdout)["drift"])
            path.write_bytes(original)

    def test_print_json_is_read_only_and_matches_generated_bytes(self):
        result = self.run_generator("--print-json")
        self.assertEqual(result.returncode, 0, result.stderr)
        printed = json.loads(result.stdout)
        self.assertEqual(set(printed), set(OUTPUTS))
        self.assertFalse((self.root / "crates").exists())
        self.assertEqual(self.run_generator().returncode, 0)
        for relative, content in printed.items():
            self.assertEqual((self.root / relative).read_bytes(), content.encode("utf-8"))

    def test_generated_python_parses_all_schema_enums_and_rejects_unknowns(self):
        self.assertEqual(self.run_generator().returncode, 0)
        path = self.root / OUTPUTS[2]
        spec = importlib.util.spec_from_file_location("generated_vocabulary", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = {}
        for name in SOURCES:
            schema = json.loads((self.root / "packages/contracts/v1" / name).read_text(encoding="utf-8"))
            expected.update({key: tuple(value["enum"]) for key, value in schema["$defs"].items()})
        self.assertEqual(dict(module.VOCABULARY), expected)
        for category, values in expected.items():
            for value in values:
                self.assertEqual(module.parse_value(category, value), value)
            self.assertFalse(module.is_valid(category, "invented_value"))
            with self.assertRaises(ValueError):
                module.parse_value(category, "invented_value")
        for category, value in [("invented_category", "queued"), ("job_status", "QUEUED"),
                                ("job_status", None), ([], "queued")]:
            self.assertFalse(module.is_valid(category, value))
            with self.assertRaises(ValueError):
                module.parse_value(category, value)

    def test_source_enum_change_invalidates_all_outputs(self):
        self.assertEqual(self.run_generator().returncode, 0)
        path = self.root / "packages/contracts/v1/job-status.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["$defs"]["job_status"]["enum"].append("fixture_new_status")
        path.write_text(json.dumps(schema), encoding="utf-8")
        result = self.run_generator("--check")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(set(json.loads(result.stdout)["drift"]), set(OUTPUTS))

    def test_shared_wire_cases_use_real_checked_in_python_binding(self):
        spec = importlib.util.spec_from_file_location("checked_vocabulary", ROOT / OUTPUTS[2])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cases = json.loads((ROOT / "tests/contract/fixtures/vocabulary-cases.json").read_text(encoding="utf-8"))
        self.assertTrue(cases)
        for case in cases:
            with self.subTest(case=case):
                if case["valid"]:
                    self.assertEqual(module.parse_value(case["category"], case["value"]), case["value"])
                else:
                    with self.assertRaises(ValueError):
                        module.parse_value(case["category"], case["value"])

    def test_protected_drive_is_rejected_before_any_metadata_read(self):
        self.assertTrue(SCRIPT.is_file(), "single-source vocabulary generator missing")
        spec = importlib.util.spec_from_file_location("generate_vocabulary", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(Path, "lstat", side_effect=AssertionError("protected drive accessed")):
            with self.assertRaises(ValueError):
                module.safe_path(Path("E:/unauthorized"))

    def test_linked_output_parent_is_rejected_without_writing_through_it(self):
        target = self.root / "unowned"
        target.mkdir()
        link = self.root / "crates"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                                    capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_generator()
        self.assertEqual(result.returncode, 2)
        self.assertIn("reparse", json.loads(result.stdout)["error"])
        self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
