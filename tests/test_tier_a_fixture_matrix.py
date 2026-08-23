"""Tier A fixed-format fixtures must survive ConversionRun persistence.

These are code-level structural oracles, not a claim that the same formats
have qualified in a bundled Windows installation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from app.ingestion.conversion_run import resolve_conversion_run, store_conversion_run
from app.ingestion.docx_adapter import convert_docx_to_run
from app.ingestion.html_adapter import convert_html_to_run
from app.ingestion.multi_format import convert_file
from app.ingestion.pptx_adapter import convert_pptx_to_run
from app.ingestion.structured_conversion import build_workspace_conversion_run
from app.ingestion.xlsx_adapter import convert_xlsx_to_run
from tests.golden_pdf_fixture import GOLDEN_PDF

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPOSITORY_ROOT / "tests" / "fixtures"
DOCX_FIXTURE = (
    REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "imported-designs"
    / "reference-deliveries"
    / "archeaxis-2026"
    / "ArcheAxis OS Overview.docx"
)


def _readback(db: Path, receipt: dict[str, object]):
    run_id = receipt["run_id"]
    assert isinstance(run_id, str)
    restored = resolve_conversion_run(db, run_id)
    assert restored is not None
    return restored


def test_tier_a_fixed_office_fixtures_keep_native_structure_after_readback(tmp_path: Path) -> None:
    """DOCX/PPTX/XLSX preserve their format-native anchors after persistence."""
    database = tmp_path / "tier-a-office.sqlite"

    docx = _readback(database, convert_docx_to_run(DOCX_FIXTURE, database))
    pptx = _readback(database, convert_pptx_to_run(FIXTURES / "sample.pptx", database))
    xlsx = _readback(database, convert_xlsx_to_run(FIXTURES / "sample.xlsx", database))

    assert docx.source_name == DOCX_FIXTURE.name
    assert any(block.kind == "heading" and block.anchor["source_md"] for block in docx.document.blocks)
    assert [block.anchor["slide_number"] for block in pptx.document.blocks] == [1, 2]
    assert [block.anchor["sheet"] for block in xlsx.document.blocks] == ["Data", "Notes"]
    assert "C1:=SUM(B2:B3)" in xlsx.document.blocks[0].text


def test_tier_a_fixed_html_and_pdf_fixtures_keep_evidence_anchors_after_readback(tmp_path: Path) -> None:
    """HTML article and real PDF retain their semantic and page anchors."""
    database = tmp_path / "tier-a-web-pdf.sqlite"
    html = _readback(database, convert_html_to_run(FIXTURES / "tier_a_article.html", database))

    pdf_path = tmp_path / "tier-a-golden.pdf"
    pdf_path.write_bytes(GOLDEN_PDF)
    converted_pdf, engine = convert_file(str(pdf_path))
    pdf = build_workspace_conversion_run(
        source_path=pdf_path,
        raw_sha256=hashlib.sha256(GOLDEN_PDF).hexdigest(),
        source_name=pdf_path.name,
        source_format="pdf",
        converted_content=converted_pdf,
        extractor_identity=engine,
    )
    store_conversion_run(database, pdf)
    restored_pdf = resolve_conversion_run(database, pdf.run_id)

    assert "stable main-content marker" in html.document.blocks[0].text
    assert html.document.blocks[0].anchor["source"] == "main-content"
    assert restored_pdf is not None
    assert any(block.kind == "page" and block.anchor["page_number"] == 1 for block in restored_pdf.document.blocks)
    assert "Golden Journey Evidence" in restored_pdf.document.blocks[0].text
