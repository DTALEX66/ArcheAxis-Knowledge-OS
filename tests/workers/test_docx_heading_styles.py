"""R15/F07: a DOCX heading is separated from a body paragraph by what the file itself says.

The level comes from, in that order: the paragraph's own `w:outlineLvl`, the outline level the
document's style definition assigns to the referenced style, and a built-in heading style name.
A paragraph none of those describe stays a paragraph - no level is inferred from text, length or
capitalisation, because that is how a document gets a fabricated outline.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKER = REPO / "services" / "python-workers" / "document" / "worker_office.py"
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "golden-docx-anchor.docx"

DOCUMENT = '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:body>
  {paragraphs}
 </w:body>
</w:document>
'''

STYLES = '''<?xml version="1.0" encoding="UTF-8"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 {styles}
</w:styles>
'''


def paragraph(text: str, properties: str = "") -> str:
    inside = f"<w:pPr>{properties}</w:pPr>" if properties else ""
    return f"<w:p>{inside}<w:r><w:t>{text}</w:t></w:r></w:p>"


def spec(name: str, definition: str) -> str:
    return f'<w:style w:type="paragraph" w:styleId="{name}">{definition}</w:style>'


def write_docx(path: Path, paragraphs: str, styles: str | None = None) -> None:
    entries = {"word/document.xml": DOCUMENT.format(paragraphs=paragraphs)}
    if styles is not None:
        entries["word/styles.xml"] = STYLES.format(styles=styles)
    with zipfile.ZipFile(path, "w") as archive:
        for name, body in entries.items():
            archive.writestr(name, body)


def load():
    module_spec = importlib.util.spec_from_file_location("worker_office_headings", WORKER)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


class DocxHeadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = load()

    def test_the_golden_fixture_keeps_its_one_heading_and_a_plain_body_paragraph(self):
        out = self.worker.extract(str(GOLDEN))
        params = out["loss_receipt"]["params"]
        self.assertEqual(params["heading_count"], 1)
        self.assertEqual(params["paragraph_count"], 2)
        self.assertEqual(params["headings"], [
            {"level": 1, "style": "Heading1", "characters": 24}
        ], params["headings"])
        first, second = out["structure"][:2]
        self.assertEqual(first.get("heading_level"), 1)
        self.assertEqual(second.get("style"), None)
        self.assertNotIn("heading_level", second)

    def test_a_level_defined_by_the_style_not_named_by_it_is_still_a_heading(self):
        # the paragraph only says "MyTitle"; the level lives in the style definition, and a
        # reader that ignores styles.xml would call this a body paragraph
        with tempfile.TemporaryDirectory() as box:
            path = Path(box) / "styled.docx"
            write_docx(
                path,
                paragraph("Section opener", '<w:pStyle w:val="MyTitle"/>')
                + paragraph("Body copy", '<w:pStyle w:val="MyBody"/>'),
                spec("MyTitle", '<w:name w:val="Title Custom"/><w:pPr><w:outlineLvl w:val="2"/></w:pPr>')
                + spec("MyBody", '<w:name w:val="Body Custom"/>'),
            )
            out = self.worker.extract(str(path))
        params = out["loss_receipt"]["params"]
        self.assertEqual(params["style_definitions"], 2)
        self.assertEqual(params["heading_count"], 1)
        self.assertEqual(params["headings"], [{"level": 3, "style": "Title Custom", "characters": 14}])
        self.assertEqual(out["structure"][1]["style"], "Body Custom")
        self.assertNotIn("heading_level", out["structure"][1])

    def test_a_paragraph_level_beats_the_style_and_a_numbered_name_is_read_in_either_language(self):
        with tempfile.TemporaryDirectory() as box:
            path = Path(box) / "levels.docx"
            write_docx(
                path,
                paragraph("Direct", '<w:pStyle w:val="Heading2"/><w:outlineLvl w:val="0"/>')
                + paragraph("中文标题", '<w:pStyle w:val="标题 3"/>')
                + paragraph("No style at all"),
                spec("Heading2", '<w:name w:val="heading 2"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr>'),
            )
            out = self.worker.extract(str(path))
        headings = out["loss_receipt"]["params"]["headings"]
        # the second paragraph names a style the document never defines, so the receipt reports
        # the name the file actually contains rather than inventing a display name for it
        self.assertEqual(headings, [
            {"level": 1, "style": "heading 2", "characters": 6},
            {"level": 3, "style": "标题 3", "characters": 4},
        ], headings)
        self.assertEqual(out["structure"][0]["heading_level"], 1, "the paragraph's own level wins")
        self.assertNotIn("heading_level", out["structure"][2])

    def test_a_document_without_heading_information_gets_no_invented_outline(self):
        with tempfile.TemporaryDirectory() as box:
            path = Path(box) / "flat.docx"
            write_docx(path, paragraph("ALL CAPS LOOKS LIKE A TITLE") + paragraph("Second line"))
            out = self.worker.extract(str(path))
        params = out["loss_receipt"]["params"]
        self.assertEqual(params["heading_count"], 0)
        self.assertEqual(params["headings"], [])
        self.assertEqual(params["style_definitions"], 0)

    def test_navigation_stays_line_based_and_kinds_are_unchanged(self):
        # the heading information is a reported fact; promoting it to an addressing level is a
        # contract change this slice deliberately does not make
        out = self.worker.extract(str(GOLDEN))
        self.assertEqual([item["kind"] for item in out["structure"]], ["paragraph", "paragraph"])
        self.assertEqual([item["path"] for item in out["structure"]],
                         [["paragraph-1"], ["paragraph-2"]])


if __name__ == "__main__":
    unittest.main()
