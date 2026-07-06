"""Multi-format document ingestion adapter.

Unified entry point for converting PDF, Word, PPT, Excel, HTML, images, and
web pages into clean Markdown. Wraps the best open-source converters:

  Format          | Engine                | pip package
  ────────────────┼───────────────────────┼─────────────────
  PDF (simple)    | markitdown            | markitdown
  PDF (complex)   | marker-pdf / docling  | marker-pdf, docling
  PDF (Chinese)   | PaddleOCR / MinerU    | paddleocr, mineru
  DOCX/PPTX/XLSX  | markitdown            | markitdown
  HTML / Webpage  | trafilatura           | trafilatura
  Web (JS-heavy)  | crawl4ai              | crawl4ai
  Images (OCR)    | PaddleOCR             | paddleocr

All engines are optional — fallback chain tries each in order.
"""
from __future__ import annotations

from pathlib import Path

# ── Format detection ──

def detect_format(file_path: str | Path) -> str:
    """Return a short format key: pdf, docx, pptx, xlsx, html, md, txt, image, unknown."""
    ext = Path(file_path).suffix.lower()
    mapping = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "docx",
        ".pptx": "pptx",
        ".ppt": "pptx",
        ".xlsx": "xlsx",
        ".xls": "xlsx",
        ".html": "html",
        ".htm": "html",
        ".md": "md",
        ".markdown": "md",
        ".txt": "txt",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".gif": "image",
        ".bmp": "image",
        ".webp": "image",
        ".csv": "csv",
    }
    return mapping.get(ext, "unknown")


# ── Engine: markitdown (multi-format, simplest) ──

def _via_markitdown(file_path: str | Path) -> str:
    from markitdown import MarkItDown
    md = MarkItDown()
    result = md.convert(str(file_path))
    return result.text_content


# ── Engine: marker-pdf (high quality PDF) ──

def _via_marker(file_path: str | Path) -> str:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(str(file_path))
    return rendered.markdown


# ── Engine: docling (advanced PDF with tables) ──

def _via_docling(file_path: str | Path) -> str:
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    return result.document.export_to_markdown()


# ── Engine: trafilatura (web/HTML) ──

def _via_trafilatura(source: str, is_url: bool = False) -> str:
    import trafilatura
    if is_url:
        downloaded = trafilatura.fetch_url(source)
        if downloaded is None:
            raise RuntimeError(f"trafilatura failed to fetch: {source}")
        text = trafilatura.extract(downloaded, output_format="markdown")
    else:
        text = trafilatura.extract(source, output_format="markdown")
    if not text:
        raise RuntimeError("trafilatura extraction returned empty")
    return text


# ── Engine: plain text / markdown passthrough ──

def _via_read(file_path: str | Path) -> str:
    return Path(file_path).read_text(encoding="utf-8", errors="replace")


# ── Fallback chain ──

# Ordered by quality/preference per format
_ENGINES = {
    "pdf": [
        ("docling", _via_docling),
        ("marker-pdf", _via_marker),
        ("markitdown", _via_markitdown),
    ],
    "docx": [
        ("markitdown", _via_markitdown),
    ],
    "pptx": [
        ("markitdown", _via_markitdown),
    ],
    "xlsx": [
        ("markitdown", _via_markitdown),
    ],
    "html": [
        ("trafilatura", lambda p: _via_trafilatura(Path(p).read_text(encoding="utf-8", errors="replace"))),
        ("markitdown", _via_markitdown),
    ],
    "image": [
        ("markitdown", _via_markitdown),
    ],
    "md": [
        ("passthrough", _via_read),
    ],
    "txt": [
        ("passthrough", _via_read),
    ],
    "csv": [
        ("markitdown", _via_markitdown),
    ],
}


def convert_file(file_path: str | Path, fmt: str | None = None) -> tuple[str, str]:
    """Convert a file to Markdown text.

    Args:
        file_path: Path to the input file.
        fmt: Optional format override ("pdf", "docx", etc.). Auto-detected if None.

    Returns:
        (markdown_content, engine_used) tuple.

    Raises:
        RuntimeError: If all engines fail for this format.
    """
    fmt = fmt or detect_format(file_path)
    engines = _ENGINES.get(fmt)

    if not engines or engines is None:
        # Unknown format — try markitdown as universal fallback
        engines = [("markitdown", _via_markitdown)]

    if engines is None:
        engines = []

    errors = []
    for engine_name, engine_fn in engines:
        try:
            return engine_fn(str(file_path)), engine_name
        except ImportError as e:
            errors.append(f"{engine_name}: not installed ({e})")
        except Exception as e:
            errors.append(f"{engine_name}: {e}")

    raise RuntimeError(
        f"No engine could convert {fmt} file '{file_path}': {'; '.join(errors)}"
    )


def convert_url(url: str) -> tuple[str, str]:
    """Fetch and convert a web page URL to Markdown.

    Returns:
        (markdown_content, engine_used)
    """
    # Try crawl4ai first (best quality for JS-heavy pages)
    try:
        import asyncio

        from crawl4ai import AsyncWebCrawler

        async def _crawl():
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                return result.markdown

        return asyncio.run(_crawl()), "crawl4ai"
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback to trafilatura
    return _via_trafilatura(url, is_url=True), "trafilatura"


# ── Batch conversion ──

def convert_directory(
    directory: str | Path,
    pattern: str = "*.*",
    limit: int = 50,
) -> list[dict]:
    """Convert all files in a directory to Markdown.

    Returns list of {path, format, content, engine}.
    Skips files where all engines fail (logs warning).
    """
    from pathlib import Path

    from loguru import logger

    results = []
    dir_path = Path(directory).resolve()
    files = sorted(dir_path.glob(pattern))[:limit]

    for fp in files:
        if fp.is_dir():
            continue
        fmt = detect_format(fp)
        if fmt == "unknown":
            logger.debug(f"Skip unknown format: {fp.name}")
            continue
        try:
            content, engine = convert_file(fp, fmt)
            results.append({
                "path": str(fp),
                "relative_path": str(fp.relative_to(dir_path)),
                "format": fmt,
                "content": content,
                "engine": engine,
            })
        except RuntimeError as e:
            logger.warning(f"Convert failed: {fp.name} — {e}")

    return results
