"""Build auditable ConversionRuns for workspace file intake."""
from __future__ import annotations

import re
from pathlib import Path

from app.ingestion.conversion_run import ConversionRun, create_conversion_run


def _flat_text_blocks(content: str) -> list[dict[str, object]]:
    """Create stable paragraph anchors when a format has no native structure."""
    blocks: list[dict[str, object]] = []
    for ordinal, match in enumerate(re.finditer(r"\S.*?(?:\n\s*\n|\Z)", content, re.S), start=1):
        text = match.group(0).strip()
        if text:
            blocks.append(
                {
                    "kind": "paragraph",
                    "text": text,
                    "anchor": {
                        "ordinal": ordinal,
                        "char_start": match.start(),
                        "char_end": match.end(),
                    },
                }
            )
    return blocks


def _pdf_blocks(path: Path) -> tuple[list[dict[str, object]], list[str]]:
    """Extract page/text/table structure without requiring OCR tooling."""
    import pdfplumber

    blocks: list[dict[str, object]] = []
    loss_notes: list[str] = []
    with pdfplumber.open(path) as document:
        for page_index, page in enumerate(document.pages):
            page_number = page_index + 1
            text = (page.extract_text() or "").strip()
            page_anchor = {
                "page_index": page_index,
                "page_number": page_number,
                "bbox": [0, 0, page.width, page.height],
            }
            if text:
                blocks.append({"kind": "page", "text": text, "anchor": page_anchor})
            else:
                loss_notes.append(f"page {page_number}: no embedded text extracted")
            if page.images:
                loss_notes.append(
                    f"page {page_number}: image semantics retained as a loss boundary"
                )
            for table_index, table in enumerate(page.find_tables(), start=1):
                rows = table.extract()
                table_text = "\n".join(
                    " | ".join((cell or "").strip() for cell in row) for row in rows
                ).strip()
                if table_text:
                    blocks.append(
                        {
                            "kind": "table",
                            "text": table_text,
                            "anchor": {
                                **page_anchor,
                                "table_index": table_index,
                                "bbox": list(table.bbox),
                            },
                        }
                    )
    if not blocks:
        raise RuntimeError("PDF structural extraction produced no blocks")
    return blocks, loss_notes


def build_workspace_conversion_run(
    *,
    source_path: str | Path,
    raw_sha256: str,
    source_name: str,
    source_format: str,
    converted_content: str,
    extractor_identity: str,
) -> ConversionRun:
    """Create an immutable run from one already-preserved workspace upload.

    PDFs use page/text/table structure from the local PDF backend without
    requiring OCR. Other formats retain the selected converter output and
    receive paragraph/character anchors.
    """
    path = Path(source_path)
    if source_format == "pdf":
        blocks, loss_notes = _pdf_blocks(path)
        engine = "pdfplumber-structured"
    else:
        blocks = _flat_text_blocks(converted_content)
        loss_notes = []
        engine = extractor_identity
    if not blocks:
        raise RuntimeError("conversion produced no structured blocks")
    return create_conversion_run(
        raw_sha256=raw_sha256,
        source_name=source_name,
        blocks=blocks,
        engine=engine,
        loss_notes=loss_notes,
    )
