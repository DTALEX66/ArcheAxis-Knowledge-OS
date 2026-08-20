"""AXW-023A: structured DOCX adapter with conversion-run persistence.

Converts a .docx into a structured ConversionRun of DerivedBlocks (paragraphs
and tables) using the already-approved markitdown engine, then persists it to
the local SQLite store via ``create_conversion_run`` + ``store_conversion_run``.

This gives DOCX content structural anchors (paragraph / table) so later
Claim/Evidence work can pin to a specific block. If markitdown is unavailable
the conversion fails closed with a clear error (never a fake success).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from shared.adapter_contract import AdapterResult


def _sha256(file_path: str | Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_blocks(markdown: str) -> list[dict[str, Any]]:
    """Split markdown into paragraph/table/heading blocks.

    Each block carries a stable ``kind`` and a ``source_md`` anchor so the
    DerivedBlock can be pinned by location. Tables are represented as a single
    'table' block whose text is the flattened rows.
    """
    blocks: list[dict[str, Any]] = []
    for raw in re.split(r"\n\s*\n", markdown):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("|"):
            rows = [r.strip("|") for r in line.splitlines() if r.strip()]
            blocks.append(
                {
                    "kind": "table",
                    "text": "\n".join(rows),
                    "anchor": {"source_md": line[:200]},
                }
            )
        elif line.startswith("#"):
            blocks.append(
                {"kind": "heading", "text": line.lstrip("#").strip(), "anchor": {"source_md": line[:200]}}
            )
        else:
            blocks.append(
                {"kind": "paragraph", "text": line, "anchor": {"source_md": line[:200]}}
            )
    return blocks


def convert_docx(file_path: str | Path) -> AdapterResult:
    """Convert a .docx to structured blocks.

    Uses markitdown for the actual extraction; fails closed if it is
    unavailable. Returns the markdown text in ``content`` so callers that only
    need flat text still work, with per-block structure available via
    ``metadata["blocks"]``.
    """
    path = Path(file_path)
    if not path.is_file():
        return AdapterResult(
            success=False,
            content="",
            engine="docx-adapter",
            error="DOCX file not found",
        )

    try:
        from markitdown import MarkItDown
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="docx-adapter",
            error="DOCX conversion requires markitdown; install markitdown[pdf].",
        )

    try:
        md = MarkItDown()
        text = md.convert(str(path)).text_content or ""
    except Exception as exc:  # pragma: no cover - host-tooling dependent
        return AdapterResult(
            success=False,
            content="",
            engine="docx-adapter",
            error=f"markitdown DOCX conversion failed: {exc}",
        )

    if not text.strip():
        return AdapterResult(
            success=False,
            content="",
            engine="docx-adapter",
            error="DOCX conversion returned no content; treat as degraded.",
        )

    blocks = _to_blocks(text)
    return AdapterResult(
        success=True,
        content=text,
        engine="docx-adapter",
        metadata={"char_count": len(text), "block_count": len(blocks), "blocks": blocks},
    )


def convert_docx_to_run(
    file_path: str | Path,
    db: str | Path,
    source_name: str | None = None,
    version: int = 1,
) -> dict[str, Any]:
    """Convert a .docx and persist a ConversionRun; returns run metadata.

    Raises RuntimeError if conversion fails (no fake success).
    """
    result = convert_docx(file_path)
    if not result.success:
        raise RuntimeError(result.error or "DOCX conversion failed")

    from app.ingestion.conversion_run import create_conversion_run, store_conversion_run

    raw_sha = _sha256(file_path)
    blocks: list[dict[str, Any]] = result.metadata.get("blocks") or []
    run = create_conversion_run(
        raw_sha256=raw_sha,
        source_name=source_name or Path(file_path).name,
        blocks=blocks,
        engine=result.engine,
        version=version,
    )
    store_conversion_run(db, run)
    return {"run_id": run.run_id, "document_id": run.document.document_id, "block_count": len(blocks)}
