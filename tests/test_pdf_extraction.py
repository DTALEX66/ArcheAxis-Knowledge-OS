"""AXW-012B: PDF extraction must work against a real PDF in the product path.

The old `test_pdf_uses_markitdown` wrote plain text into a `.pdf` filename,
which is a text-disguised-as-PDF contract test, not conversion evidence. This
test drives a genuine minimal PDF binary (a valid one-page PDF with a text
stream) through the product's convert path under the ci-adapters group that
carries markitdown[pdf].
"""

from __future__ import annotations

from tests.golden_pdf_fixture import GOLDEN_PDF as REAL_PDF


def test_pdf_is_real_binary_not_disguised_text() -> None:
    # Guard against accidentally reverting to a text-disguised-PDF fixture.
    assert REAL_PDF.startswith(b"%PDF-")
    assert b"Golden Journey Evidence" in REAL_PDF


def test_product_convert_path_extracts_real_pdf(tmp_path) -> None:
    from app.ingestion.multi_format import convert_file

    f = tmp_path / "real.pdf"
    f.write_bytes(REAL_PDF)

    content, engine = convert_file(str(f))
    assert engine == "markitdown"
    assert "Golden Journey Evidence" in content


def test_pdf_requires_pdf_backend_present() -> None:
    """Under ci-adapters (markitdown[pdf]) the PDF backend must be importable;
    without it, installed-wheel PDF conversion is unverified."""
    import importlib

    for mod in ("pdfminer", "pdfplumber"):
        assert importlib.util.find_spec(mod) is not None, f"missing {mod}"
