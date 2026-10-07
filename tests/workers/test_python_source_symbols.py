"""F01: a Python source file now reports the symbols it declares, through the text route.

The symbols come from the interpreter's own parser over the file's bytes, the anchors stay
line-based, and a file that does not parse says so instead of producing a plausible list.
"""

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIGHT = ROOT / "services/python-workers/document/worker_light_formats.py"
TEXT = ROOT / "services/python-workers/document/worker_text.py"
MEDIA = "text/x-python"

SOURCE = '''"""Docstring."""
import os
from pathlib import Path


class AnchorStore:
    def put(self, key, value):
        return value

    async def fetch(self, key):
        return None


def top_level(a, b):
    return a + b
'''

BROKEN = "def unclosed(:\n    pass\n"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class PythonSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.light = _load("worker_light_formats_f01", LIGHT)
        cls.text = _load("worker_text_f01", TEXT)

    def test_symbols_names_kinds_and_lines_come_from_the_files_own_tree(self):
        text, facts, losses = self.light.parse(SOURCE.encode("utf-8"), MEDIA)
        self.assertEqual(facts["format"], "python")
        self.assertTrue(facts["parsed"])
        self.assertEqual(text, SOURCE)
        by_name = {item["name"]: item for item in facts["locations"]}
        self.assertEqual(by_name["AnchorStore"]["symbol_kind"], "class")
        self.assertEqual(by_name["put"]["symbol_kind"], "function")
        self.assertEqual(by_name["fetch"]["symbol_kind"], "async_function")
        self.assertEqual(by_name["top_level"]["symbol_kind"], "function")
        self.assertEqual(by_name["os"]["symbol_kind"], "import")
        self.assertTrue(all(item["line"] > 0 for item in facts["locations"]))
        self.assertEqual(
            SOURCE.splitlines()[by_name["AnchorStore"]["line"] - 1].strip(),
            "class AnchorStore:",
            "a symbol's line must point at its own declaration",
        )
        self.assertTrue(any("line based" in loss for loss in losses))

    def test_an_unparseable_file_reports_that_instead_of_inventing_symbols(self):
        text, facts, losses = self.light.parse(BROKEN.encode("utf-8"), MEDIA)
        self.assertFalse(facts["parsed"])
        self.assertEqual(facts["symbols"], [])
        self.assertIn("SyntaxError", facts["parse_error"])
        self.assertEqual(text, BROKEN, "the source text is still projected")
        self.assertTrue(any("no symbols are claimed" in loss for loss in losses))

    def test_the_symbols_survive_the_route_that_a_job_actually_uses(self):
        import tempfile
        with tempfile.TemporaryDirectory() as box:
            path = Path(box) / "module.py"
            path.write_text(SOURCE, encoding="utf-8")
            out = self.text.extract(str(path), MEDIA)
        params = out["loss_receipt"]["params"]
        self.assertEqual(params["media_type"], MEDIA)
        self.assertEqual(params["format"]["format"], "python")
        names = {item["name"] for item in params["format"]["locations"]}
        self.assertLessEqual({"AnchorStore", "put", "fetch", "top_level", "os"}, names)
        self.assertTrue(out["structure"], "line anchors must still be there")
        self.assertTrue(all(item["path"][-1].startswith("line-") for item in out["structure"]),
                        "anchors stay line-based; symbols are reported facts, not a second scheme")

    def test_a_python_file_no_longer_travels_as_undifferentiated_plain_text(self):
        # Both tables must name the type, and the matrix checker is what proves they agree: the
        # parity rule fails if one side names it and the other does not.
        attempts = (ROOT / "crates/archeaxis-application/src/attempts.rs").read_text(encoding="utf-8")
        transport = (ROOT / "services/python-workers/transport/text_ndjson.py").read_text(encoding="utf-8")
        self.assertIn('"py" => "text/x-python"', attempts)
        # The name table is a first-match match expression: a `.py` in the earlier text/plain arm
        # makes the specific arm unreachable, and the file then travels as plain text while every
        # table still appears to name it.
        plain_arm = attempts.split('"txt" |', 1)[1].split("=>", 1)[0]
        self.assertNotIn('"py"', plain_arm, "the text/plain arm must not shadow the Python name")
        self.assertEqual(transport.count('"text/x-python"'), 1)
        completed = subprocess.run(
            [sys.executable, "-B", "scripts/check_format_matrix.py", "--matrix",
             "docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0, (completed.stdout + completed.stderr)[-200:])


if __name__ == "__main__":
    unittest.main()
