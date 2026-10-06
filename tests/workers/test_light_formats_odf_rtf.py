"""F13: ODT/ODS/ODP and RTF now have a reader in the product path, and refuse when they lie.

Before this slice an ODF package was refused outright (no media type was named for it) even
though its body is package XML, and RTF was only readable on the legacy surface. The readers
here use the standard library plus the already-declared striprtf engine, so nothing new enters
the lockfile, and every rejection is an error rather than an empty success.
"""

import importlib.util
import io
import os
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIGHT = ROOT / "services/python-workers/document/worker_light_formats.py"

NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
      'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"')
ODT = "application/vnd.oasis.opendocument.text"
ODS = "application/vnd.oasis.opendocument.spreadsheet"
ODP = "application/vnd.oasis.opendocument.presentation"


def _load():
    spec = importlib.util.spec_from_file_location("worker_light_formats", LIGHT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _package(media: str, content: str, mimetype: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", (media if mimetype is None else mimetype).encode("ascii"))
        archive.writestr("content.xml", content.encode("utf-8"))
    return buffer.getvalue()


class LightFormatOdfRtfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.light = _load()

    def test_odt_headings_and_paragraphs_become_locations_with_levels(self):
        content = (
            f'<office:document-content {NS}><office:body><office:text>'
            '<text:h text:outline-level="2">星环闭环</text:h>'
            '<text:p>第一段正文</text:p></office:text></office:body></office:document-content>'
        )
        text, facts, losses = self.light.parse(_package(ODT, content), ODT)
        self.assertEqual(facts["format"], "odt")
        self.assertEqual(facts["title"], None)
        kinds = [item["kind"] for item in facts["locations"]]
        self.assertEqual(kinds, ["odf_heading", "odf_paragraph"])
        self.assertEqual(facts["locations"][0]["level"], "2")
        self.assertEqual(facts["locations"][0]["path"], "heading-2")
        self.assertIn("星环闭环", text)
        self.assertIn("第一段正文", text)
        self.assertTrue(any("content.xml" in loss for loss in losses))

    def test_ods_cells_carry_sheet_row_column_and_the_files_own_value(self):
        content = (
            f'<office:document-content {NS}><office:body><office:spreadsheet>'
            '<table:table table:name="预算">'
            '<table:table-row>'
            '<table:table-cell office:value-type="float" office:value="12.5"/>'
            '<table:table-cell office:value-type="string" table:number-columns-repeated="2">'
            '<text:p>说明</text:p></table:table-cell></table:table-row>'
            '<table:table-row table:number-rows-repeated="4000"><table:table-cell/>'
            '</table:table-row></table:table>'
            '</office:spreadsheet></office:body></office:document-content>'
        )
        text, facts, losses = self.light.parse(_package(ODS, content), ODS)
        cells = [item for item in facts["locations"] if item["kind"] == "odf_table_cell"]
        self.assertEqual(len(cells), 2)
        self.assertEqual((cells[0]["sheet"], cells[0]["row"], cells[0]["column"]), ("预算", 1, 1))
        self.assertEqual(cells[0]["value_type"], "float")
        self.assertEqual(cells[0]["value"], "12.5", "the stored value is reported, not the label")
        self.assertEqual((cells[1]["column"], cells[1]["span"]), (2, 2))
        self.assertIn("预算!R1C1: 12.5", text)
        self.assertTrue(any("capped at 512" in loss for loss in losses),
                        "a declared 4000-row repeat must be reported at the cap, not inflated")

    def test_odp_pages_are_addressable_and_text_sits_under_its_page(self):
        content = (
            f'<office:document-content {NS}><office:body><office:presentation>'
            '<draw:page draw:name="封面"><draw:frame><text:p>标题文字</text:p></draw:frame>'
            '</draw:page></office:presentation></office:body></office:document-content>'
        )
        text, facts, _ = self.light.parse(_package(ODP, content), ODP)
        kinds = [item["kind"] for item in facts["locations"]]
        self.assertEqual(kinds, ["odf_page", "odf_paragraph"])
        self.assertEqual(facts["locations"][1]["path"], "封面/paragraph")
        self.assertIn("Page: 封面", text)

    def test_a_zip_that_does_not_declare_the_media_type_is_refused(self):
        content = f'<office:document-content {NS}><office:body/></office:document-content>'
        with self.assertRaises(ValueError) as caught:
            self.light.parse(_package(ODT, content, mimetype="application/zip"), ODT)
        self.assertIn("mimetype", str(caught.exception))
        with self.assertRaises(ValueError):
            self.light.parse(_package(ODT, content, mimetype=""), ODT)

    def test_an_odt_without_any_readable_text_is_not_reported_as_success(self):
        content = f'<office:document-content {NS}><office:body><office:text/></office:body></office:document-content>'
        with self.assertRaises(ValueError):
            self.light.parse(_package(ODT, content), ODT)

    def test_a_traversal_member_rejects_the_whole_package(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("mimetype", ODT.encode("ascii"))
            archive.writestr("../content.xml", b"<x/>")
        with self.assertRaises(ValueError):
            self.light.parse(buffer.getvalue(), ODT)

    def test_rtf_projection_drops_control_words_and_anchors_paragraphs(self):
        source = ("{\\rtf1\\ansi\\deff0 {\\fonttbl{\\f0 Times;}}\n"
                  "\\f0\\fs24 星环第一段\\par\\par 第二段正文\\par}")
        text, facts, losses = self.light.parse(source.encode("utf-8"), "application/rtf")
        self.assertEqual(facts["format"], "rtf")
        self.assertNotIn("\\f0", text)
        self.assertNotIn("fonttbl", text)
        self.assertIn("星环第一段", text)
        self.assertIn("第二段正文", text)
        self.assertEqual([item["kind"] for item in facts["locations"]], ["rtf_paragraph", "rtf_paragraph"])
        self.assertTrue(any("stripped" in loss for loss in losses))

    def test_an_unnamed_media_type_is_still_not_claimed(self):
        self.assertIsNone(self.light.parse(b"whatever", "application/vnd.oasis.opendocument.graphics"))


if __name__ == "__main__":
    unittest.main()
