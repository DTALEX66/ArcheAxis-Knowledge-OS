"""AXW-012B: PDF extraction must work against a real PDF in the product path.

The old `test_pdf_uses_markitdown` wrote plain text into a `.pdf` filename,
which is a text-disguised-as-PDF contract test, not conversion evidence. This
test drives a genuine minimal PDF binary (a valid one-page PDF with a text
stream) through the product's convert path under the ci-adapters group that
carries markitdown[pdf].
"""

from __future__ import annotations

# A minimal but real single-page PDF containing the words "Evidence Driven
# Learning" as a text stream. This is valid PDF binary, not a renamed text file.
REAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 60>>stream\n"
    b"BT /F1 24 Tf 72 720 Td (Evidence Driven Learning) Tj ET\n"
    b"endstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n"
    b"0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000245 00000 n \n"
    b"0000000347 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n"
    b"410\n"
    b"%%EOF\n"
)


def test_pdf_is_real_binary_not_disguised_text() -> None:
    # Guard against accidentally reverting to a text-disguised-PDF fixture.
    assert REAL_PDF.startswith(b"%PDF-")
    assert b"Evidence Driven Learning" in REAL_PDF


def test_product_convert_path_extracts_real_pdf(tmp_path) -> None:
    from app.ingestion.multi_format import convert_file

    f = tmp_path / "real.pdf"
    f.write_bytes(REAL_PDF)

    content, engine = convert_file(str(f))
    assert engine == "markitdown"
    assert "Evidence Driven Learning" in content


def test_pdf_requires_pdf_backend_present() -> None:
    """Under ci-adapters (markitdown[pdf]) the PDF backend must be importable;
    without it, installed-wheel PDF conversion is unverified."""
    import importlib

    for mod in ("pdfminer", "pdfplumber"):
        assert importlib.util.find_spec(mod) is not None, f"missing {mod}"
