"""R15/F14: a legacy binary workbook is read, converted sheet by sheet, and loss-reported.

Three separate things the requirement names: the original bytes (custody, already universal),
a converted counterpart (one CSV per sheet, declared the way a container declares members), and
a loss report that says what the conversion cannot carry. A cached formula result is reported as
the value the file carries, never as a recalculated one.
"""

from __future__ import annotations

import builtins
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
OFFICE = REPO / "services" / "python-workers" / "document" / "worker_office.py"
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "golden-xls-anchor.xls"
GOLDEN_SHA256 = "3225b8bb590f799dc0a16a92118a1f80aec8cde53e0b4c71bc200f451aa72353"
XLS_MEDIA = "application/vnd.ms-excel"
DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load("xls_worker_office", OFFICE)
transport = _load("xls_transport", TRANSPORT)


class XlsReaderTests(unittest.TestCase):
    def test_the_golden_workbook_is_read_as_its_own_types_not_as_plain_text(self):
        out = worker.extract(str(GOLDEN))
        params = out["loss_receipt"]["params"]
        self.assertEqual(out["format"], "xls")
        self.assertEqual(params["engine"], "xlrd")
        self.assertEqual(params["sheets"], 2)
        types = params["cell_types"]
        for kind in ("text", "number", "date", "boolean", "empty"):
            self.assertIn(kind, types, types)
        self.assertIn("星环 知识平台", out["text"], "CJK survives the real BIFF8 path")
        self.assertIn("2026-10-07 09:30:00", out["text"],
                      "a date is converted with the workbook's own datemode")
        self.assertEqual(params["datemode"], 0)
        # the merged pair holds one value: it must not be counted twice
        self.assertEqual(out["text"].count("spanning label"), 1)

    def test_each_sheet_comes_out_as_a_declared_csv_member(self):
        with tempfile.TemporaryDirectory() as box:
            members = Path(box) / "members"
            out = worker.extract(str(GOLDEN), member_dir=str(members))
            declared = out["loss_receipt"]["params"]["structure"]["extractable_members"]
            self.assertEqual([item["name"] for item in declared],
                             ["Evidence.csv", "Numbers.csv"])
            for item in declared:
                self.assertNotIn("/", item["file"])
                written = (members / item["file"]).read_bytes()
                self.assertEqual(len(written), item["bytes"])
                self.assertEqual(hashlib.sha256(written).hexdigest(), item["sha256"])
            first = (members / declared[0]["file"]).read_text(encoding="utf-8")
            self.assertIn("Sheet evidence anchor", first)
            self.assertIn("星环 知识平台", first)

    def test_no_transfer_area_still_projects_and_declares_nothing(self):
        out = worker.extract(str(GOLDEN))
        self.assertEqual(out["loss_receipt"]["params"]["structure"]["extractable_members"], [])
        self.assertTrue(out["text"])

    def test_the_conversion_states_what_it_cannot_carry(self):
        losses = worker.extract(str(GOLDEN))["loss_receipt"]["losses"]
        joined = "; ".join(losses)
        for clause in ("formulas are not recalculated", "number formats", "merged-cell spans",
                       "charts", "macros", "original bytes stay the source of record"):
            self.assertIn(clause, joined)

    def test_a_cached_formula_is_reported_as_a_value_not_a_recomputed_one(self):
        # the engine exposes no formula text for this file, and the receipt must say so rather
        # than let a cached number read like a computed result
        losses = worker.extract(str(GOLDEN))["loss_receipt"]["losses"]
        self.assertTrue(any("no formula text" in line for line in losses), losses)

    def test_corrupt_bytes_fail_with_a_reason_instead_of_an_empty_success(self):
        with tempfile.TemporaryDirectory() as box:
            path = Path(box) / "broken.xls"
            path.write_bytes(b"%PDF-1.4 this is not a workbook")
            with self.assertRaises(ValueError) as caught:
                worker.extract(str(path))
        self.assertIn("xls could not be opened", str(caught.exception))

    def test_a_missing_engine_fails_the_job_rather_than_projecting_nothing(self):
        real_import = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == "xlrd":
                raise ImportError("no xlrd")
            return real_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as box:
            path = Path(box) / "any.xls"
            path.write_bytes(GOLDEN.read_bytes())
            with mock.patch.object(builtins, "__import__", side_effect=blocked):
                with self.assertRaises(RuntimeError) as caught:
                    worker.extract(str(path))
        self.assertIn("xlrd not installed", str(caught.exception))

    def test_the_golden_fixture_bytes_are_the_pinned_ones(self):
        self.assertEqual(hashlib.sha256(GOLDEN.read_bytes()).hexdigest(), GOLDEN_SHA256,
                         "a fixture cited by receipts is not edited to suit a test")
        manifest = json.loads((GOLDEN.parent / "manifest.json").read_text(encoding="utf-8"))
        entry = manifest["fixtures"]["golden-xls-anchor.xls"]
        self.assertEqual(entry["sha256"], GOLDEN_SHA256)
        self.assertEqual(entry["rights_basis"], "project-authored synthetic test fixture")


class XlsRouteTests(unittest.TestCase):
    def request(self, digest: str, media_type: str) -> dict:
        return {
            "schema": "archeaxis.worker-request/v1", "type": "job_request", "request_id": "r",
            "job_id": "j", "attempt": 1, "protocol_minor": 0, "capability": "office.structure",
            "capability_version": "1", "deadline_ms": 60_000,
            "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": media_type}],
            "parameters": {},
        }

    def run_route(self, media_type: str, label: str):
        # a real package for each media type: the route refuses a mislabelled file for the wrong
        # reason, which would not prove anything about the transfer area
        payload = (GOLDEN.read_bytes() if media_type == XLS_MEDIA
                   else GOLDEN.parent.joinpath("golden-docx-anchor.docx").read_bytes())
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as box:
            staging = Path(box) / "staging"
            (staging / "input").mkdir(parents=True)
            (staging / "input" / digest).write_bytes(payload)
            root = staging / f"attempt-{label}"
            outputs, _measurements, _losses = transport.execute(
                self.request(digest, media_type), staging, artifact_root=root)
            loss = next(o for o in outputs if o["kind"] == "loss_report")
            receipt = json.loads((staging / "output" / loss["uri"].rsplit("/", 1)[-1]).read_bytes())
            # read the transfer area before the temporary directory goes away, and hand back
            # its bytes rather than paths that no longer exist by the time the caller looks
            members = root / "members"
            written = ({p.name: p.read_bytes() for p in sorted(members.iterdir())}
                       if members.is_dir() else None)
            return receipt, written

    def test_the_workbook_route_receives_a_transfer_area_and_a_docx_does_not(self):
        receipt, written = self.run_route(XLS_MEDIA, "xls")
        declared = receipt["params"]["structure"]["extractable_members"]
        self.assertEqual(len(declared), 2, declared)
        self.assertIsNotNone(written, "the workbook route must have received a transfer area")
        for item in declared:
            self.assertIn(item["file"], written)
            self.assertEqual(len(written[item["file"]]), item["bytes"])
            self.assertEqual(hashlib.sha256(written[item["file"]]).hexdigest(), item["sha256"],
                             "the declared digest is of the bytes actually on disk")
        docx, docx_written = self.run_route(DOCX_MEDIA, "docx")
        # a word processor file declares no members at all; the Core reads this the same way,
        # by finding nothing under params.structure.extractable_members
        self.assertEqual(docx["params"].get("structure", {}).get("extractable_members", []), [])
        self.assertIsNone(docx_written, "a word processor file gets no members directory")

    def test_the_matrix_tables_name_the_legacy_type_in_both_directions(self):
        # the same parity rule that caught the earlier false ODF support reads this table pair
        completed = subprocess.run(
            [sys.executable, "-B", "scripts/check_format_matrix.py", "--matrix",
             "docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json"],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0, (completed.stdout + completed.stderr)[-300:])


class XlsMemberDepthTests(unittest.TestCase):
    """A converted sheet lands in the same attempt-keyed transfer area as a container's members.

    That directory reaches 247 characters in an ordinary worktree, and this fixture's own sheet
    titles put the written file past the length Windows enforces on a plain path - where the
    create fails as ERROR_FILE_NOT_FOUND. The premise is measured on the machine running this, so
    a host that lifts the limit is reported rather than silently passed.
    """

    def test_a_sheet_is_still_declared_at_the_depth_the_host_transfer_area_has(self):
        if sys.platform != "win32":
            self.skipTest("the plain-path limit is a Windows fact")
        box = Path(tempfile.mkdtemp())
        try:
            node = box
            if len(str(node)) < 239:
                node = node / ("c" * (239 - len(str(node)) - 1))
            if len(str(node)) > 243:
                self.skipTest("the temporary base is already too deep to express the host shape")
            node.mkdir(parents=True, exist_ok=True)
            members = node / "members"
            members.mkdir()
            target = members / "sheet-01-Evidence.csv"
            self.assertLessEqual(len(str(members)), 251)
            self.assertGreaterEqual(len(str(target)), 261)
            try:
                target.write_bytes(b"x")
                reachable = True
            except OSError:
                reachable = False
            if reachable:
                self.skipTest("this machine creates files past the limit, so the shape is absent")

            out = worker.extract(str(GOLDEN), member_dir=str(members))
            declared = out["loss_receipt"]["params"]["structure"]["extractable_members"]
            self.assertEqual([item["name"] for item in declared],
                             ["Evidence.csv", "Numbers.csv"], declared)
            for item in declared:
                written = transport.filesystem_path(members / item["file"]).read_bytes()
                self.assertEqual(len(written), item["bytes"])
                self.assertEqual(hashlib.sha256(written).hexdigest(), item["sha256"])
        finally:
            shutil.rmtree(transport.filesystem_path(box), ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
