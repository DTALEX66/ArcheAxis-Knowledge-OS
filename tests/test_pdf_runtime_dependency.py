"""Input-free dependency hello and version-bound PDF receipts, no model/service."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "services/python-workers/document/worker_pdf.py"


def hello(mode):
    # The hook isolates dependencies only in this child; no package install/removal.
    program = r"""
import builtins, runpy, sys, types
real = builtins.__import__
mode, worker, staging = sys.argv[1:]
def restricted(name, *args, **kwargs):
    if name in ('pymupdf','fitz'):
        if mode.startswith('version:'): return types.SimpleNamespace(__version__=mode[8:], open=lambda **kw: (_ for _ in ()).throw(AssertionError('opened document during hello')))
        if mode == 'missing': raise ModuleNotFoundError(name=name)
        if mode == 'broken': raise ImportError('native library unavailable')
        if mode == 'unversioned': return types.SimpleNamespace(open=lambda **kw: (_ for _ in ()).throw(AssertionError('opened document during hello')))
        if mode == 'wrong-module': return types.SimpleNamespace(__version__='1.0.0')
    return real(name, *args, **kwargs)
builtins.__import__ = restricted
sys.argv = [worker, '--staging-root', staging]
runpy.run_path(worker, run_name='__main__')
"""
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run(
            [sys.executable, "-B", "-c", program, mode, str(WORKER), d],
            input=b"",
            capture_output=True,
            timeout=10,
        )
        frames = [json.loads(line) for line in out.stdout.splitlines()]
        import jsonschema

        schema = json.loads(
            (ROOT / "packages/contracts/v1/worker-protocol.schema.json").read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema["$defs"]["hello"]).validate(frames[0])
        return frames[0]


class PdfDependencyTests(unittest.TestCase):
    def assert_observed(self, mode, status):
        value = hello(mode)
        self.assertEqual(value["type"], "hello")
        self.assertEqual(
            value.get("runtime_dependency"), {"name": "pymupdf", "status": status, "version": None}
        )
        # A route is a declaration, never proof that its required engine works.
        self.assertIn("pdf.extract", value["capabilities"])

    def test_missing_dependency_is_not_healthy_hello(self):
        self.assert_observed("missing", "MISSING")

    def test_native_import_failure_is_distinct(self):
        self.assert_observed("broken", "IMPORT_FAILED")

    def test_missing_version_is_distinct_without_opening_document(self):
        self.assert_observed("unversioned", "VERSION_UNKNOWN")

    def test_unrelated_fitz_package_is_not_pdf_engine(self):
        self.assert_observed("wrong-module", "IMPORT_FAILED")

    def test_real_hello_observes_version_but_executes_no_document(self):
        import pymupdf

        value = hello("real")
        self.assertEqual(
            value["runtime_dependency"],
            {"name": "pymupdf", "status": "AVAILABLE", "version": pymupdf.__version__},
        )

    def test_schema_worker_and_core_share_absolute_version_boundary(self):
        import jsonschema

        schema = json.loads(
            (ROOT / "packages/contracts/v1/worker-protocol.schema.json").read_text(encoding="utf-8")
        )
        validator = jsonschema.Draft202012Validator(schema["$defs"]["hello"])
        for version in ("1.0\n", "1" * 64 + "\n"):
            with self.subTest(version=repr(version)):
                value = hello("version:" + version)
                self.assertEqual(value["runtime_dependency"]["status"], "VERSION_UNKNOWN")
                value["runtime_dependency"] = {
                    "name": "pymupdf",
                    "status": "AVAILABLE",
                    "version": version,
                }
                self.assertTrue(list(validator.iter_errors(value)))

    def test_file_receipt_has_actual_loaded_engine_version(self):
        import pymupdf

        spec = importlib.util.spec_from_file_location("pdf_dependency_test_worker", WORKER)
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "controlled.pdf"
            doc = pymupdf.open()
            doc.new_page().insert_text((72, 100), "Controlled PDF 6371 km")
            doc.save(path)
            doc.close()
            result = worker.extract(str(path))
        self.assertIn("6371 km", result["text"])
        self.assertEqual(result["engine_version"], pymupdf.__version__)
        self.assertEqual(result["loss_receipt"]["engine_version"], pymupdf.__version__)
        self.assertEqual(
            result["loss_receipt"]["params"]["runtime_dependency"],
            {"name": "pymupdf", "status": "AVAILABLE", "version": pymupdf.__version__},
        )


if __name__ == "__main__":
    unittest.main()
