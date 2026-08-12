"""Multi-format document ingestion adapter.

Unified entry point for converting PDF, Word, PPT, Excel, HTML, images, and
web pages into clean text/Markdown. Uses the shared adapter contract and
fallback fixtures for graceful unavailable-engine handling.

  Format          | Engines (in priority order)
  ────────────────┼──────────────────────────────────────────
  PDF             | markitdown → docling  (marker-pdf REVIEW-BLOCK, excluded)
  DOCX / PPT/XLS  | markitdown
  HTML            | trafilatura → safe-http+raw
  Image           | pytesseract+tesseract (real OCR; unavailable if no Tesseract)
  Media (video/au)| convert_ffmpeg (metadata-only; no ASR — never claimed as content)
  JSON Canvas     | native JSON Canvas text-node projection
  TXT / MD        | passthrough (always available)

All engines are optional. The adapter contract (shared/adapter_contract)
classifies each as installed / unavailable; the call chain tries each
declared engine and returns the first success with non-empty content or a
clear error. A conversion never claims success from metadata alone
(MFX-010 honest-capability guard).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from shared.adapter_contract import (
    AdapterResult,
)
from shared.approved_paths import ApprovedRoots, ApprovedRootsError
from shared.safe_http import SafeHTTPPolicy, fetch

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APPROVED_ROOTS = ApprovedRoots(source_roots=[_PROJECT_ROOT], output_roots=[_PROJECT_ROOT])

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
        ".canvas": "canvas",
        ".txt": "txt",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".gif": "image",
        ".bmp": "image",
        ".webp": "image",
        ".mp4": "media_video",
        ".mov": "media_video",
        ".mkv": "media_video",
        ".avi": "media_video",
        ".webm": "media_video",
        ".mp3": "media_audio",
        ".wav": "media_audio",
        ".m4a": "media_audio",
        ".flac": "media_audio",
        ".csv": "csv",
    }
    return mapping.get(ext, "unknown")


# ── Content-based format detection (H2: Magika ONNX) ──

# Magika label → multi_format key mapping
_CONTENT_FORMAT_MAP: dict[str, str] = {
    "pdf": "pdf", "docx": "docx", "xlsx": "xlsx", "pptx": "pptx",
    "doc": "docx", "xls": "xlsx", "ppt": "pptx",
    "odt": "docx", "ods": "xlsx", "odp": "pptx",
    "html": "html", "xml": "html", "sgml": "html",
    "txt": "txt", "markdown": "md", "csv": "csv", "tsv": "csv",
    # JSON-like labels: fall back to extension detection so formats like
    # .canvas (JSON Canvas) keep their specific handler instead of
    # collapsing into generic text.
    "yaml": "txt", "toml": "txt",
    "png": "image", "jpeg": "image", "gif": "image", "webp": "image",
    "bmp": "image", "tiff": "image", "ico": "image", "svg": "image",
    "mp3": "media_audio", "wav": "media_audio", "flac": "media_audio",
    "m4a": "media_audio", "ogg": "media_audio",
    "mp4": "media_video", "mkv": "media_video", "webm": "media_video",
    "flv": "media_video",
    "zip": "unknown", "tar": "unknown", "gzip": "unknown",
    "epub": "docx", "rtf": "docx",
    "python": "txt", "javascript": "txt", "shell": "txt",
}


def detect_format_from_content(file_path: str | Path) -> str:
    """Use Magika content detection for robust format identification.

    Falls back to extension-based detection if Magika model is unavailable
    or if the detected label doesn't map to a known engine.

    Text formats (txt/md/csv/tsv) trust the extension FIRST: Magika
    frequently mislabels GBK/GB2312-encoded Chinese text files as csv or
    html, which would route them to the wrong engine (e.g. markitdown)
    and silently mangle the encoding. A .txt file is always read with
    the passthrough engine's encoding cascade; content detection stays
    authoritative only for formats whose extension is ambiguous or whose
    content is genuinely binary.
    """
    path = Path(file_path)
    if not path.is_file():
        return detect_format(file_path)

    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".markdown", ".csv", ".tsv"}:
        return detect_format(file_path)

    try:
        from shared.file_detection import detect, is_available

        if not is_available():
            return detect_format(file_path)

        content = path.read_bytes()[:8192]  # first 8KB sufficient for Magika
        result = detect(content, path_hint=path.name)
        label = str(result.get("label", "unknown"))
        return _CONTENT_FORMAT_MAP.get(label, detect_format(file_path))
    except (OSError, ImportError):
        return detect_format(file_path)


# ── Engine wrappers ──


def _via_markitdown(file_path: str) -> AdapterResult:
    from markitdown import MarkItDown

    md = MarkItDown()
    result = md.convert(str(file_path))
    text = result.text_content
    return AdapterResult(
        success=True,
        content=text,
        engine="markitdown",
        metadata={"char_count": len(text)},
    )


def _via_image_ocr(file_path: str) -> AdapterResult:
    """OCR an image with Tesseract + pytesseract (real content conversion).

    This is the honest image engine: it returns success only when real text
    was extracted. If Tesseract/pytesseract is unavailable it returns a clear
    unavailable failure (never a metadata-only fake success). An image whose
    OCR yields no text is reported as a warning rather than content success.
    """
    import shared.adapter_fixtures as _af

    if not (_af._tesseract_available() and _af._pytesseract_importable()):
        return AdapterResult(
            success=False,
            content="",
            engine="ocr-unavailable",
            error=(
                "Image OCR requires Tesseract-OCR (system) and pytesseract (Python). "
                "Install both to OCR images; no metadata is claimed as content."
            ),
        )
    try:
        import pytesseract
        from PIL import Image

        text = pytesseract.image_to_string(Image.open(str(file_path)))
    except Exception as exc:  # pragma: no cover - depends on host tooling
        return AdapterResult(
            success=False,
            content="",
            engine="pytesseract",
            error=f"pytesseract OCR failed: {exc}",
        )
    if not text.strip():
        return AdapterResult(
            success=False,
            content="",
            engine="pytesseract",
            error="Image OCR returned no text; treat as degraded (no content).",
        )
    return AdapterResult(
        success=True,
        content=text,
        engine="pytesseract+tesseract",
        metadata={"char_count": len(text)},
    )


def _via_marker(file_path: str) -> AdapterResult:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(file_path)
    text = rendered.markdown
    return AdapterResult(
        success=True,
        content=text,
        engine="marker-pdf",
        metadata={"char_count": len(text)},
    )


def _via_docling(file_path: str) -> AdapterResult:
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(file_path)
    text = result.document.export_to_markdown()
    return AdapterResult(
        success=True,
        content=text,
        engine="docling",
        metadata={"char_count": len(text)},
    )


def _via_pdf_ocr(file_path: str) -> AdapterResult:
    """OCR a scanned PDF page-by-page with Tesseract + pytesseract.

    Honest scanned-PDF engine: renders each page with PyMuPDF (fitz) and
    OCRs it with Tesseract. Returns success only when real text was
    extracted; a PDF whose pages all OCR to nothing (or missing tooling)
    fails closed with a clear reason — never a metadata-only success.
    Page markers keep the output anchored to source pages for later
    evidence/cross-check work.
    """
    import shared.adapter_fixtures as _af

    if not (_af._tesseract_available() and _af._pytesseract_importable()):
        return AdapterResult(
            success=False,
            content="",
            engine="ocr-unavailable",
            error=(
                "Scanned-PDF OCR requires Tesseract-OCR (system), pytesseract "
                "(Python) and PyMuPDF (fitz). Install all three to OCR scanned "
                "PDFs; no metadata is claimed as content."
            ),
        )
    try:
        import io

        import fitz
        import pytesseract
        from PIL import Image
    except Exception as exc:  # pragma: no cover - depends on host tooling
        return AdapterResult(
            success=False,
            content="",
            engine="pdf-ocr-unavailable",
            error=f"Scanned-PDF OCR dependencies unavailable: {exc}",
        )
    try:
        doc = fitz.open(file_path)
        parts: list[str] = []
        for page_no, page in enumerate(doc, 1):
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            parts.append(f"<!-- page {page_no} -->\n{text.strip()}")
        doc.close()
    except Exception as exc:  # pragma: no cover - depends on host tooling
        return AdapterResult(
            success=False,
            content="",
            engine="pytesseract",
            error=f"Scanned-PDF OCR failed: {exc}",
        )
    content = "\n\n".join(parts)
    if not content.strip():
        return AdapterResult(
            success=False,
            content="",
            engine="pytesseract",
            error="Scanned-PDF OCR returned no text; treat as degraded (no content).",
        )
    return AdapterResult(
        success=True,
        content=content,
        engine="pytesseract+tesseract(pdf)",
        metadata={"char_count": len(content)},
    )


def _via_trafilatura(html: str) -> AdapterResult:
    import trafilatura

    text = trafilatura.extract(html, output_format="markdown")
    if not text:
        return AdapterResult(
            success=False, content="", engine="trafilatura", error="trafilatura returned empty"
        )
    return AdapterResult(
        success=True,
        content=text,
        engine="trafilatura",
        metadata={"char_count": len(text)},
    )


def _via_read(file_path: str) -> AdapterResult:
    raw = Path(file_path).read_bytes()
    text = _decode_text_bytes(raw, file_path)
    return AdapterResult(
        success=True,
        content=text,
        engine="passthrough",
        metadata={"char_count": len(text)},
    )


def _decode_text_bytes(raw: bytes, source: str = "<bytes>") -> str:
    """Decode a text file with UTF-8 first, then common legacy encodings.

    Chinese-Windows text files are frequently GBK/GB2312; a naive UTF-8
    read with errors=replace silently mangles them. Decode strictly and
    fall back through GB18030 (superset of GBK/GB2312) before finally
    degrading to UTF-8-with-replacement so every caller gets real text
    when a legacy encoding is in play.
    """
    for encoding in ("utf-8", "gb18030", "utf-16", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _via_canvas(file_path: str) -> AdapterResult:
    """Project JSON Canvas nodes without executing files or following links.

    Uses shared/json_canvas.py validator (ADS-003) for spec-compliant validation.
    Unknown fields are preserved on roundtrip.
    """
    from shared.json_canvas import CanvasError, validate_json_canvas

    raw = Path(file_path).read_text(encoding="utf-8")
    payload = json.loads(raw)

    try:
        validate_json_canvas(payload)
    except CanvasError as e:
        raise ValueError(f"Invalid JSON Canvas: {e}") from e

    sections: list[str] = []
    for node in payload["nodes"]:
        node_type = node.get("type")
        if node_type == "text":
            text = node.get("text")
            if isinstance(text, str) and text.strip():
                sections.append(text.strip())
        elif node_type in {"file", "link", "group"}:
            label = node.get("file") or node.get("url") or node.get("label")
            if isinstance(label, str) and label.strip():
                sections.append(f"- {node_type}: {label.strip()}")

    text = "\n\n".join(sections)
    return AdapterResult(
        success=True,
        content=text,
        engine="json-canvas",
        metadata={"char_count": len(text), "node_count": len(payload["nodes"])},
    )


# ── Adapter-framework wrappers (using shared/adapter_fixtures) ──
# These integrate the adapter contract (O-series) into the product pipeline.


def _via_adapter_fixtures(fmt: str, adapters: list[str]) -> list[tuple[str, Any]]:
    """Build engine chain entries for the given format from adapter fixtures.

    Each adapter name maps to a function in ``shared.adapter_fixtures``.
    Returns (engine_name, wrapper_fn) tuples ready for ``_ENGINES``.
    """
    # Lazy-import to avoid pulling heavy trees at module level
    import shared.adapter_fixtures as _af

    supported = {
        "convert_newspaper4k",
        "convert_readabilipy",
        "convert_scrapling",
        "convert_pillow",
        "convert_ffmpeg",
        "convert_youtube_transcript",
        "convert_docling",
        "convert_markitdown",
        "convert_trafilatura",
    }
    from shared.adapter_contract import AdapterInput

    entries: list[tuple[str, Any]] = []
    for name in adapters:
        if name not in supported:
            continue

        def _make_wrapper(_name=name):
            def wrapper(file_path: str) -> AdapterResult:
                inp = AdapterInput(source=file_path)
                return getattr(_af, _name)(inp)
            return wrapper

        entries.append((name.replace("convert_", ""), _make_wrapper()))
    return entries


# ── Engine chain map ──

_ENGINES: dict[str, list[tuple[str, Any]]] = {
    "pdf": [
        ("markitdown", _via_markitdown),
        # marker-pdf (_via_marker) EXCLUDED: supply-chain ledger B003
        # (Marker) is REVIEW-BLOCK — code Apache-2.0 but weights are a
        # modified OpenRAIL-M requiring separate review. Must not be a
        # default engine. Re-add only after weight licensing resolves.
        ("pytesseract+tesseract(pdf)", _via_pdf_ocr),
        ("docling", _via_docling),
    ],
    "docx": [("markitdown", _via_markitdown)],
    "pptx": [("markitdown", _via_markitdown)],
    "xlsx": [("markitdown", _via_markitdown)],
    "csv": [("markitdown", _via_markitdown)],
    "html": [
        ("trafilatura", lambda p: _via_trafilatura(Path(p).read_text(encoding="utf-8", errors="replace"))),
        ("safe-http+raw", _via_read),
    ],
    "image": [
        ("pytesseract+tesseract", _via_image_ocr),
        ("markitdown", _via_markitdown),
    ],
    "media_video": _via_adapter_fixtures("media_video", ["convert_ffmpeg"]),
    "media_audio": _via_adapter_fixtures("media_audio", ["convert_ffmpeg"]),
    "article": _via_adapter_fixtures("article", ["convert_newspaper4k", "convert_readabilipy"]),
    "md": [("passthrough", _via_read)],
    "txt": [("passthrough", _via_read)],
    "canvas": [("json-canvas", _via_canvas)],
}


def convert_file(
    file_path: str | Path,
    fmt: str | None = None,
    *,
    quality: bool = False,
) -> tuple[str, str] | tuple[str, str, dict[str, object]]:
    """Convert a file to text/Markdown using the best available engine.

    Args:
        file_path: Path to the input file.
        fmt: Optional format override (auto-detected if None).
        quality: If True, also return quality assessment dict as third element.

    Returns:
        (text_content, engine_used) tuple, or (text_content, engine_used, quality)
        if quality=True.

    Raises:
        RuntimeError: If all engines fail for this format.
    """
    fmt = fmt or detect_format_from_content(file_path)
    engines = _ENGINES.get(fmt)

    def _return(text: str, engine: str) -> tuple[str, str] | tuple[str, str, dict[str, object]]:
        if quality:
            from shared.text_quality import assess_conversion

            q = assess_conversion(source_path=str(file_path), output_text=text)
            return text, engine, q
        return text, engine

    if not engines:
        # Unknown format — try markitdown as universal fallback
        engines = [("markitdown", _via_markitdown)]

    errors = []
    for engine_name, engine_fn in engines:
        try:
            result: AdapterResult = engine_fn(str(file_path))
            # Content post-condition: a conversion only "succeeds" when it
            # produced non-empty text. Empty/whitespace-only output (e.g. a
            # metadata-only or placeholder result) must not be claimed as
            # content success (MFX-010 honest-capability guard).
            if result.success and result.content.strip():
                return _return(result.content, result.engine)
            reason = result.error or "returned empty content"
            errors.append(f"{engine_name}: {reason}")
        except ImportError as e:
            errors.append(f"{engine_name}: not installed ({e})")
        except Exception as e:
            errors.append(f"{engine_name}: {e}")

    raise RuntimeError(
        f"No engine could convert {fmt} file '{file_path}': {'; '.join(errors)}"
    )


def convert_url(url: str) -> tuple[str, str]:
    """Fetch and convert a web page URL to text/Markdown.

    Uses the adapter contract to determine the best available web engine.
    Falls back to raw HTML (no markdown conversion) when no web extraction
    engine is installed.

    Tries installed adapters in priority order:
      1. newspaper4k (news articles, auto-detect if supported)
      2. readabilipy (Mozilla Readability — general article extraction)
      3. trafilatura (if installed)
      4. safe-http+raw (always available)

    Returns:
        (text_content, engine_used)

    Raises:
        RuntimeError: If HTTP fetch fails.
    """
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").rstrip(".").casefold()
    if hostname in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}:
        from shared.adapter_contract import AdapterInput
        from shared.adapter_fixtures import convert_youtube_transcript

        transcript = convert_youtube_transcript(AdapterInput(source=url))
        if transcript.success:
            return transcript.content, transcript.engine

    response = fetch(
        url,
        policy=SafeHTTPPolicy(
            max_bytes=5_000_000,
            allowed_content_types=("text/html", "application/xhtml+xml"),
        ),
    )
    html = response.body.decode("utf-8", errors="replace")

    # Try installed web adapters through the adapter contract
    from shared.adapter_contract import AdapterInput
    from shared.adapter_fixtures import (
        convert_newspaper4k,
        convert_readabilipy,
    )

    inp = AdapterInput(source=url)
    adapter_results: list[tuple[str, AdapterResult]] = []

    # 1) newspaper4k — news article extraction
    try:
        result = convert_newspaper4k(inp)
        adapter_results.append(("newspaper4k", result))
    except Exception:
        pass

    # 2) readabilipy — general readability extraction
    try:
        result = convert_readabilipy(inp)
        adapter_results.append(("readabilipy", result))
    except Exception:
        pass

    # 3) trafilatura — HTML extraction
    try:
        import trafilatura  # noqa: F401
        text = trafilatura.extract(html, output_format="markdown")
        if text:
            return text, "safe-http+trafilatura"
    except ImportError:
        pass

    # 4) Return first successful adapter result
    for engine_name, result in adapter_results:
        if result.success:
            return result.content, f"safe-http+{engine_name}"

    # Fallback: return raw HTML (always available)
    return html, "safe-http+raw"


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
            results.append(
                {
                    "path": str(fp),
                    "relative_path": str(fp.relative_to(dir_path)),
                    "format": fmt,
                    "content": content,
                    "engine": engine,
                }
            )
        except RuntimeError as e:
            logger.warning(f"Convert failed: {fp.name} — {e}")

    return results


def convert_directory_resumable(
    directory: str | Path,
    manifest_path: str | Path,
    pattern: str = "**/*",
    max_files: int = 200,
    output_dir: str | Path | None = None,
) -> dict:
    """Convert files to durable Markdown artifacts with fingerprint-verified resume."""
    import os
    import tempfile

    from shared.processing_manifest import (
        ProcessingManifest,
        file_sha256,
        source_artifact_key,
    )

    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError(f"directory not found: {root}")
    manifest_file = Path(manifest_path).resolve()
    artifacts = Path(output_dir).resolve() if output_dir else manifest_file.parent / "artifacts"
    output_root = Path(output_dir).resolve() if output_dir else manifest_file.parent
    if not output_root.is_dir():
        output_root = output_root.parent
    manifest_root = manifest_file.parent if manifest_file.parent.is_dir() else manifest_file.parent.parent
    if not output_root.is_dir() or not manifest_root.is_dir():
        raise ValueError(f"output root parent not found: {output_root}")
    approved = ApprovedRoots(source_roots=[root], output_roots=[output_root, manifest_root])
    manifest_file = approved.resolve_output(manifest_file)
    artifacts = approved.resolve_output(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    manifest = ProcessingManifest(manifest_file)
    results: list[dict] = []
    resumed = processed = 0

    for file_path in sorted(root.glob(pattern)):
        if processed >= max_files:
            break
        if not file_path.is_file():
            continue
        try:
            resolved_file = approved.resolve_source(file_path)
        except ApprovedRootsError:
            continue
        if resolved_file == manifest_file or artifacts in resolved_file.parents:
            continue
        relative = resolved_file.relative_to(root).as_posix()
        if manifest.can_resume(relative, resolved_file, approved_roots=approved):
            latest = manifest.latest()[relative]
            resumed += 1
            results.append(
                {"path": relative, "status": "resumed", "output": latest["output"]}
            )
            continue

        processed += 1
        fmt = detect_format(resolved_file)
        source_hash = file_sha256(resolved_file)
        if fmt == "unknown":
            manifest.record(
                relative,
                status="needs_review",
                handler="unsupported-format",
                error=f"unsupported extension: {resolved_file.suffix.lower()}",
                metadata={"source_sha256": source_hash},
            )
            results.append({"path": relative, "status": "needs_review", "format": fmt})
            continue

        temporary: Path | None = None
        try:
            content, engine = convert_file(resolved_file, fmt)
            if file_sha256(resolved_file) != source_hash:
                raise RuntimeError("source changed during conversion")
            output = artifacts / f"{source_artifact_key(resolved_file, root)}.md"
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="\n",
                dir=artifacts,
                delete=False,
                suffix=".tmp",
            ) as stream:
                stream.write(content)
                temporary = Path(stream.name)
            os.replace(temporary, output)
            output_hash = file_sha256(output)
        except Exception as exc:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            manifest.record(
                relative,
                status="failed",
                handler="fallback-chain",
                error=f"{type(exc).__name__}: {exc}",
                metadata={"format": fmt, "source_sha256": source_hash},
            )
            results.append({"path": relative, "status": "failed", "format": fmt})
            continue

        manifest.record(
            relative,
            status="converted",
            handler=engine,
            output=str(output),
            metadata={
                "format": fmt,
                "character_count": len(content),
                "source_sha256": source_hash,
                "output_sha256": output_hash,
                "handler_version": 1,
            },
        )
        results.append(
            {
                "path": relative,
                "status": "converted",
                "format": fmt,
                "engine": engine,
                "output": str(output),
            }
        )

    return {
        "root": str(root),
        "manifest": str(manifest_file),
        "output_dir": str(artifacts),
        "processed": processed,
        "resumed": resumed,
        "summary": manifest.summary(),
        "results": results,
    }
