"""AXW-023E: structured HTML/Web adapter (main-content-first + metadata).

Extracts readable main content from an HTML file/URL string using
trafilatura (already in the dependency tree) with metadata preserved
(title, URL, fetch time, robots boundary). Fails closed when trafilatura
is unavailable or extraction returns nothing — never a fake success.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.adapter_contract import AdapterResult

_META_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_META_ROBOTS = re.compile(r'<meta[^>]+name=["\']robots["\'][^>]*content=["\']([^"\']+)', re.I)


def _sha256(file_path: str | Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _meta_robots(raw: str) -> str | None:
    m = _META_ROBOTS.search(raw)
    return m.group(1).strip() if m else None


def _extract_article(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    """Return (block_or_None, error)."""
    import trafilatura

    try:
        extracted = trafilatura.extract(raw, include_comments=False, include_tables=True)
    except Exception as exc:  # pragma: no cover
        return None, f"trafilatura extraction failed: {exc}"
    if not extracted or not extracted.strip():
        return None, "trafilatura returned no main content"
    return (
        {
            "kind": "article",
            "text": extracted,
            "anchor": {"source": "main-content", "char_count": len(extracted)},
        },
        None,
    )


def convert_html(raw: str, *, url: str | None = None) -> AdapterResult:
    """Convert HTML text into a structured article block.

    ``raw`` is the HTML source; ``url`` optionally records provenance.
    Robots meta is preserved as metadata (never followed here — the
    adapter only reads what the caller already fetched).
    """
    if not raw or not raw.strip():
        return AdapterResult(success=False, content="", engine="html-adapter", error="empty HTML input")

    try:
        import trafilatura  # noqa: F401
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="html-adapter",
            error="HTML conversion requires trafilatura; add to dependencies.",
        )

    block, error = _extract_article(raw)
    if block is None:
        return AdapterResult(success=False, content="", engine="html-adapter", error=error or "no content")

    title_m = _META_TITLE.search(raw)
    robots = _meta_robots(raw)
    metadata: dict[str, Any] = {
        "char_count": len(block["text"]),
        "block_count": 1,
        "blocks": [block],
        "title": title_m.group(1).strip() if title_m else None,
        "robots": robots,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "loss_notes": [],
    }
    if url:
        metadata["url"] = url
    return AdapterResult(success=True, content=block["text"], engine="html-adapter", metadata=metadata)


def convert_html_file(file_path: str | Path) -> AdapterResult:
    """Convert an .html file on disk (reads bytes; tolerant of encoding)."""
    path = Path(file_path)
    if not path.is_file():
        return AdapterResult(success=False, content="", engine="html-adapter", error="file not found")
    raw = path.read_text(encoding="utf-8", errors="replace")
    result = convert_html(raw)
    if result.success:
        result.metadata["source_file"] = str(path)
        result.metadata["source_sha256"] = _sha256(path)
    return result


def convert_html_to_run(
    html_source: str | Path,
    db: str | Path,
    source_name: str | None = None,
    version: int = 1,
    *,
    url: str | None = None,
) -> dict[str, Any]:
    """Convert HTML (string or file) and persist a ConversionRun."""
    if isinstance(html_source, (str, Path)) and Path(html_source).is_file():
        result = convert_html_file(html_source)
        source_name = source_name or Path(html_source).name
    else:
        result = convert_html(html_source, url=url)
        source_name = source_name or (url or "html-source")
    if not result.success:
        raise RuntimeError(result.error or "HTML conversion failed")

    from app.ingestion.conversion_run import create_conversion_run, store_conversion_run

    if result.metadata.get("source_sha256"):
        raw_sha = result.metadata["source_sha256"]
    else:
        raw_sha = _sha256_from_text(result.content)
    blocks: list[dict[str, Any]] = result.metadata.get("blocks") or []
    loss = result.metadata.get("loss_notes") or []
    run = create_conversion_run(
        raw_sha256=raw_sha,
        source_name=source_name,
        blocks=blocks,
        engine=result.engine,
        version=version,
    )
    store_conversion_run(db, run)
    return {"run_id": run.run_id, "document_id": run.document.document_id, "block_count": len(blocks), "loss_notes": loss}


def _sha256_from_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
