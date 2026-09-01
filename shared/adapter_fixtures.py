"""Fallback fixture adapters — placeholder handlers for unavailable engines.

Every fallback returns an AdapterResult with success=False and a clear
human-readable error. No engine is faked; no video/audio is claimed as
"supported" unless actually installed and exercised.

This module also registers every known adapter's capability into the global
adapter registry (see shared/adapter_contract), classifying each as
installed, importable, fallback, or unavailable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from shared.adapter_contract import (
    AdapterCapability,
    AdapterInput,
    AdapterKind,
    AdapterResult,
    AdapterStatus,
    register_adapter,
)
from shared.approved_paths import ApprovedRoots
from shared.safe_http import SafeHTTPPolicy, fetch

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APPROVED_ROOTS = ApprovedRoots(source_roots=[_PROJECT_ROOT], output_roots=[_PROJECT_ROOT])

# ── Helper: detect installed tools ──


def _is_usable_ffmpeg_tool(candidate: str | Path, tool_name: str) -> bool:
    """Verify a binary instead of trusting a possibly stale Windows shim."""
    try:
        completed = subprocess.run(
            [str(candidate), "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and tool_name in completed.stdout.casefold()


def _resolve_ffmpeg_tool(tool_name: str) -> str | None:
    """Resolve ffmpeg/ffprobe via PATH then the configured shared-tool root."""
    candidates = [shutil.which(tool_name) or ""]
    external_root = os.environ.get("OS_EXTERNAL_CONFIG", "").strip()
    if external_root:
        root = Path(external_root)
        candidates.extend(
            str(root / relative)
            for relative in (
                Path("10-toolchains") / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / f"{tool_name}.exe",
                Path("toolchains") / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / f"{tool_name}.exe",
            )
        )
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        normalized = os.path.normcase(os.path.abspath(candidate))
        if normalized in seen:
            continue
        seen.add(normalized)
        if Path(candidate).is_file() and _is_usable_ffmpeg_tool(candidate, tool_name):
            return candidate
    return None


def _ffmpeg_available() -> bool:
    return _resolve_ffmpeg_tool("ffmpeg") is not None


def _tesseract_available() -> bool:
    import shutil

    if shutil.which("tesseract"):
        return True
    windows_default = Path("/c/Program Files/Tesseract-OCR/tesseract.exe")
    return windows_default.is_file()


def _pytesseract_importable() -> bool:
    try:
        import pytesseract  # noqa: F401

        return True
    except ImportError:
        return False


def _youtube_transcript_importable() -> bool:
    try:
        import youtube_transcript_api  # noqa: F401

        return True
    except ImportError:
        return False


def _markitdown_importable() -> bool:
    try:
        import markitdown  # noqa: F401

        return True
    except ImportError:
        return False


def _trafilatura_importable() -> bool:
    try:
        import trafilatura  # noqa: F401

        return True
    except ImportError:
        return False


def _newspaper4k_importable() -> bool:
    try:
        import newspaper  # noqa: F401

        return True
    except ImportError:
        return False


def _docling_importable() -> bool:
    try:
        import docling  # noqa: F401

        return True
    except ImportError:
        return False


def _scrapling_importable() -> bool:
    try:
        import scrapling  # noqa: F401

        return True
    except ImportError:
        return False


def _readabilipy_importable() -> bool:
    try:
        import readabilipy  # noqa: F401

        return True
    except ImportError:
        return False


# ── Fallback handlers ──


def fallback_any(_input: AdapterInput) -> AdapterResult:
    """Generic fallback — engine not available."""
    fmt = _input.format or "unknown"
    return AdapterResult(
        success=False,
        content="",
        engine="fallback",
        error=f"No adapter available for format '{fmt}'. "
        f"Install the required engine (see adapter registry).",
    )


def fallback_read(input_: AdapterInput) -> AdapterResult:
    """Passthrough: read plain text / markdown files directly."""
    path = Path(input_.source)
    if not path.is_file():
        return AdapterResult(
            success=False,
            content="",
            engine="fallback-read",
            error=f"File not found: {input_.source}",
        )
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="fallback-read",
            error=f"Failed to read {input_.source}: {exc}",
        )
    return AdapterResult(
        success=True,
        content=text,
        engine="passthrough",
        metadata={"char_count": len(text)},
    )


def fallback_webpage(input_: AdapterInput) -> AdapterResult:
    """Fallback for web page fetch when trafilatura is unavailable.

    Returns the raw HTML body (minimally sanitised) as content, since
    no HTML-to-markdown converter is installed.
    """

    policy = SafeHTTPPolicy(
        max_bytes=5_000_000,
        allowed_content_types=("text/html", "application/xhtml+xml"),
    )
    try:
        response = fetch(input_.source, policy=policy)
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="fallback-raw-html",
            error=f"HTTP fetch failed for {input_.source}: {exc}",
        )
    html = response.body.decode("utf-8", errors="replace")
    return AdapterResult(
        success=True,
        content=html,
        engine="safe-http",
        metadata={"content_type": response.content_type, "byte_count": len(response.body)},
    )


def convert_newspaper4k(input_: AdapterInput) -> AdapterResult:
    """Convert a news article URL to extracted plain text via newspaper4k.

    Uses newspaper.article() as a single-shot shortcut — no build() needed.
    Returns markdown-formatted title + body text.
    """
    try:
        import newspaper
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="newspaper4k",
            error="newspaper4k is not installed. Run: pip install newspaper4k",
        )

    try:
        article = newspaper.article(input_.source, language=input_.options.get("language"))
        title = article.title or ""
        body = article.text or ""
        if not title and not body:
            return AdapterResult(
                success=False,
                content="",
                engine="newspaper4k",
                error=f"newspaper4k extracted no content from {input_.source}",
            )
        markdown = f"# {title}\n\n{body}" if title else body
        return AdapterResult(
            success=True,
            content=markdown.strip(),
            engine="newspaper4k",
            metadata={
                "char_count": len(markdown.strip()),
                "title": title,
                "authors": article.authors,
                "publish_date": str(article.publish_date) if article.publish_date else None,
            },
        )
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="newspaper4k",
            error=f"newspaper4k conversion failed: {exc}",
        )


def convert_docling(input_: AdapterInput) -> AdapterResult:
    """Convert a document file (PDF, DOCX, PPTX, XLSX) to markdown via Docling.

    Uses docling.document_converter.DocumentConverter. Supports local files
    and URLs. Returns extracted markdown with page count metadata.
    """
    try:
        import docling  # noqa: F401
        from docling.document_converter import DocumentConverter
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="docling",
            error="docling is not installed. Run: pip install docling",
        )

    try:
        converter = DocumentConverter()
        result = converter.convert(input_.source)
        doc = result.document
        markdown = doc.export_to_markdown()
        if not markdown.strip():
            return AdapterResult(
                success=False,
                content="",
                engine="docling",
                error=f"docling extracted no content from {input_.source}",
            )
        return AdapterResult(
            success=True,
            content=markdown.strip(),
            engine="docling",
            metadata={
                "char_count": len(markdown.strip()),
                "page_count": len(list(doc.pages)) if hasattr(doc, "pages") else 0,
            },
        )
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="docling",
            error=f"docling conversion failed: {exc}",
        )


def convert_markitdown(input_: AdapterInput) -> AdapterResult:
    """Convert any supported file format to markdown via MarkItDown.

    Supports PDF, DOCX, PPTX, XLSX, CSV, images, and more via the
    unified markitdown library (https://github.com/microsoft/markitdown).
    Uses MarkItDown.convert() for file paths or raw content.
    """
    try:
        from markitdown import MarkItDown
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="markitdown",
            error="markitdown is not installed. Run: pip install markitdown",
        )

    try:
        md = MarkItDown()
        result = md.convert(str(input_.source))
        text = result.text_content
        if not text.strip():
            return AdapterResult(
                success=False,
                content="",
                engine="markitdown",
                error=f"markitdown extracted no content from {input_.source}",
            )
        return AdapterResult(
            success=True,
            content=text.strip(),
            engine="markitdown",
            metadata={
                "char_count": len(text.strip()),
                "format": input_.format or "auto",
            },
        )
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="markitdown",
            error=f"markitdown conversion failed: {exc}",
        )


def fallback_image_ocr(input_: AdapterInput) -> AdapterResult:
    """Fallback for image OCR — tesseract or pytesseract is unavailable."""
    return AdapterResult(
        success=False,
        content="",
        engine="fallback",
        error="Image OCR requires Tesseract-OCR (system) and pytesseract (Python). "
        "Install both, or provide an already-extracted text file.",
    )


def convert_trafilatura(input_: AdapterInput) -> AdapterResult:
    """Extract clean text from an HTML page or file via trafilatura.

    Supports:
      - URL sources (auto-fetched via trafilatura.fetch_url)
      - Local HTML file paths (read and extracted)

    Returns extracted text (default format) or markdown on success.
    """
    try:
        import trafilatura
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="trafilatura",
            error="trafilatura is not installed. Run: pip install trafilatura",
        )

    source = input_.source
    if not source:
        return AdapterResult(
            success=False,
            content="",
            engine="trafilatura",
            error="Empty source — provide a URL or file path",
        )

    try:
        # URL source — fetch + extract
        if source.startswith(("http://", "https://")):
            downloaded = trafilatura.fetch_url(source)
            if not downloaded:
                return AdapterResult(
                    success=False,
                    content="",
                    engine="trafilatura",
                    error=f"trafilatura fetch_url returned no content for {source}",
                )
            text = trafilatura.extract(
                downloaded,
                output_format=input_.options.get("output_format", "markdown"),
                include_comments=input_.options.get("include_comments", False),
                include_tables=input_.options.get("include_tables", True),
            )
        else:
            # Local file — read HTML and extract
            from pathlib import Path

            path = Path(source)
            if not path.is_file():
                return AdapterResult(
                    success=False,
                    content="",
                    engine="trafilatura",
                    error=f"File not found: {source}",
                )
            html = path.read_text(encoding="utf-8", errors="replace")
            text = trafilatura.extract(
                html,
                output_format=input_.options.get("output_format", "markdown"),
                include_comments=input_.options.get("include_comments", False),
                include_tables=input_.options.get("include_tables", True),
            )

        if not text:
            return AdapterResult(
                success=False,
                content="",
                engine="trafilatura",
                error="trafilatura.extract returned no content",
            )
        return AdapterResult(
            success=True,
            content=text.strip(),
            engine="trafilatura",
            metadata={
                "char_count": len(text.strip()),
                "source": source,
                "format": input_.options.get("output_format", "markdown"),
            },
        )
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="trafilatura",
            error=f"trafilatura conversion failed: {exc}",
        )


def convert_scrapling(input_: AdapterInput) -> AdapterResult:
    """Extract clean text from a web page via Scrapling.

    Uses Scrapling's Fetcher to fetch a URL and parse the HTML into
    clean text content. Supports CSS selector-based extraction for
    targeted content via the ``selector`` option.

    Returns extracted plain text on success.
    """
    try:
        from scrapling.fetchers import Fetcher
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="scrapling",
            error="scrapling is not installed. Run: pip install scrapling",
        )

    source = input_.source
    if not source:
        return AdapterResult(
            success=False,
            content="",
            engine="scrapling",
            error="Empty source — provide a URL or file path",
        )

    try:
        page = Fetcher.get(source)
        if page is None:
            return AdapterResult(
                success=False,
                content="",
                engine="scrapling",
                error=f"Scrapling Fetcher returned no result for {source}",
            )

        # Extract text — use CSS selector if provided, else full text
        selector = input_.options.get("selector")
        if selector:
            elements = page.css(selector)
            text = "\n".join(el.text for el in elements if el.text)
        else:
            text = page.text

        if not text or not text.strip():
            return AdapterResult(
                success=False,
                content="",
                engine="scrapling",
                error=f"Scrapling extracted no text content from {source}",
            )

        return AdapterResult(
            success=True,
            content=text.strip(),
            engine="scrapling",
            metadata={
                "char_count": len(text.strip()),
                "source": source,
                "selector": selector or "full_text",
            },
        )
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="scrapling",
            error=f"Scrapling conversion failed: {exc}",
        )


def convert_readabilipy(input_: AdapterInput) -> AdapterResult:
    """Extract clean main content from an HTML page via readabilipy.

    Uses Mozilla Readability (via readabilipy) to extract article title,
    byline, and clean text content from HTML. Supports URL sources
    (auto-fetch via safe_http) and local HTML file paths.

    Returns extracted plain text on success.
    """
    try:
        from readabilipy import simple_json_from_html_string
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="readabilipy",
            error="readabilipy is not installed. Run: pip install readabilipy",
        )

    source = input_.source
    if not source:
        return AdapterResult(
            success=False,
            content="",
            engine="readabilipy",
            error="Empty source — provide a URL or file path",
        )

    try:
        # Fetch or read HTML
        if source.startswith(("http://", "https://")):
            from shared.safe_http import SafeHTTPPolicy, fetch

            policy = SafeHTTPPolicy(
                max_bytes=5_000_000,
                allowed_content_types=("text/html", "application/xhtml+xml"),
            )
            response = fetch(source, policy=policy)
            html = response.body.decode("utf-8", errors="replace")
        else:
            from pathlib import Path

            path = Path(source)
            if not path.is_file():
                return AdapterResult(
                    success=False,
                    content="",
                    engine="readabilipy",
                    error=f"File not found: {source}",
                )
            html = path.read_text(encoding="utf-8", errors="replace")

        # Extract via Readability
        data = simple_json_from_html_string(html, use_readability=False)
        if not data:
            return AdapterResult(
                success=False,
                content="",
                engine="readabilipy",
                error="readabilipy returned no extracted content",
            )

        title = data.get("title", "") or ""
        byline = data.get("byline", "") or ""
        content_text = data.get("plain_content", data.get("content", "")) or ""

        # Build markdown output
        parts = []
        if title:
            parts.append(f"# {title}")
        if byline:
            parts.append(f"*By {byline}*")
        if content_text:
            parts.append(content_text.strip())

        output = "\n\n".join(p.strip() for p in parts if p.strip())
        if not output:
            return AdapterResult(
                success=False,
                content="",
                engine="readabilipy",
                error="readabilipy extracted no content from the page",
            )

        return AdapterResult(
            success=True,
            content=output,
            engine="readabilipy",
            metadata={
                "char_count": len(output),
                "title": title,
                "byline": byline,
                "source": source,
            },
        )
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="readabilipy",
            error=f"readabilipy conversion failed: {exc}",
        )


def convert_youtube_transcript(input_: AdapterInput) -> AdapterResult:
    """Fetch a YouTube video transcript via youtube-transcript-api.

    Accepts a YouTube video ID (e.g. ``dQw4w9WgXcQ``) or a full YouTube URL
    (``https://www.youtube.com/watch?v=...``, ``https://youtu.be/...``,
    ``https://m.youtube.com/watch?v=...``).

    Returns the transcript as markdown-formatted text with ``[MM:SS]``
    timestamps per snippet.  Supports language override via the
    ``language`` option (ISO 639‑1 code, default ``en``).
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="youtube-transcript-api",
            error="youtube-transcript-api is not installed. "
            "Run: pip install youtube-transcript-api",
        )

    source = input_.source.strip()
    if not source:
        return AdapterResult(
            success=False,
            content="",
            engine="youtube-transcript-api",
            error="Empty source — provide a YouTube video ID or URL",
        )

    # Extract video ID from various URL formats
    video_id = source
    if "youtube.com/watch" in source or "youtu.be/" in source or "m.youtube.com" in source:
        import re
        patterns = [
            r"(?:v=|/)([a-zA-Z0-9_-]{11})(?:&|$|/|\?)",
            r"youtu\.be/([a-zA-Z0-9_-]{11})",
        ]
        for pat in patterns:
            m = re.search(pat, source)
            if m:
                video_id = m.group(1)
                break

    language = input_.options.get("language", "en")
    preserve_formatting = input_.options.get("preserve_formatting", False)

    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(
            video_id=video_id,
            languages=(language,),
            preserve_formatting=preserve_formatting,
        )
    except Exception as exc:
        exc_name = type(exc).__name__
        return AdapterResult(
            success=False,
            content="",
            engine="youtube-transcript-api",
            error=f"Failed to fetch transcript: {exc_name}: {exc}",
        )

    # Build formatted transcript with timestamps
    snippets = list(transcript)
    if not snippets:
        return AdapterResult(
            success=False,
            content="",
            engine="youtube-transcript-api",
            error="No transcript snippets returned; the video may lack captions.",
        )

    lines = []
    for s in snippets:
        minutes = int(s.start // 60)
        seconds = int(s.start % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {s.text}")

    content = "\n".join(lines)
    return AdapterResult(
        success=True,
        content=content,
        engine="youtube-transcript-api",
        metadata={
            "char_count": len(content),
            "snippet_count": len(snippets),
            "video_id": video_id,
            "language": transcript.language_code if hasattr(transcript, "language_code") else language,
            "is_generated": getattr(transcript, "is_generated", False),
        },
    )


def convert_ffmpeg(input_: AdapterInput) -> AdapterResult:
    """Extract metadata from a media file via ffmpeg/ffprobe.

    Uses ffprobe to read container metadata, stream info (codec,
    resolution, sample rate), and duration. Returns a JSON-like
    metadata summary as content text.

    Supports video formats (mp4, mov, mkv, avi, webm) and audio
    formats (mp3, wav, m4a, flac).
    """
    if not _ffmpeg_available():
        return AdapterResult(
            success=False,
            content="",
            engine="ffmpeg",
            error="ffmpeg executable not found in PATH. See https://ffmpeg.org/download.html",
        )

    source = input_.source
    if not source:
        return AdapterResult(
            success=False,
            content="",
            engine="ffmpeg",
            error="Empty source — provide a file path to a media file",
        )

    path = Path(source)
    if not path.is_file():
        return AdapterResult(
            success=False,
            content="",
            engine="ffmpeg",
            error=f"File not found: {source}",
        )

    try:
        import json
        import subprocess

        # Use ffprobe to extract stream and format metadata
        ffprobe = _resolve_ffmpeg_tool("ffprobe")
        if not ffprobe:
            return AdapterResult(
                success=False,
                content="",
                engine="ffmpeg",
                error="ffprobe executable not found or not runnable; no metadata is claimed as content.",
            )
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return AdapterResult(
                success=False,
                content="",
                engine="ffmpeg",
                error=f"ffprobe returned exit code {result.returncode}: {result.stderr[:200]}",
            )

        probe = json.loads(result.stdout)

        # Build a readable metadata summary
        fmt = probe.get("format", {})
        streams = probe.get("streams", [])

        lines = [f"File: {path.name}", f"Size: {fmt.get('size', '?')} bytes"]
        duration = fmt.get("duration", "?")
        lines.append(f"Duration: {duration}s")
        lines.append(f"Format: {fmt.get('format_name', '?')}")
        bitrate = fmt.get("bit_rate")
        if bitrate:
            lines.append(f"Overall bitrate: {bitrate} bps")

        # Summarise each stream
        for i, stream in enumerate(streams):
            codec_type = stream.get("codec_type", "unknown")
            codec = stream.get("codec_name", "?")
            if codec_type == "video":
                res = f"{stream.get('width', '?')}x{stream.get('height', '?')}"
                fps = stream.get("r_frame_rate", "?")
                lines.append(f"  Video stream {i}: {codec} {res} @ {fps} fps")
            elif codec_type == "audio":
                sr = stream.get("sample_rate", "?")
                ch = stream.get("channels", "?")
                lines.append(f"  Audio stream {i}: {codec} {sr} Hz, {ch} ch")
            else:
                lines.append(f"  Stream {i}: {codec_type} ({codec})")

        content = "\n".join(lines)

        metadata = {
            "byte_size": int(fmt.get("size", 0)),
            "duration_seconds": float(duration) if duration != "?" else 0.0,
            "format_name": fmt.get("format_name", ""),
            "stream_count": len(streams),
            "has_video": any(s.get("codec_type") == "video" for s in streams),
            "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        }

        return AdapterResult(
            success=True,
            content=content,
            engine="ffmpeg",
            metadata=metadata,
        )

    except subprocess.TimeoutExpired:
        return AdapterResult(
            success=False,
            content="",
            engine="ffmpeg",
            error=f"ffprobe timed out processing {source}",
        )
    except json.JSONDecodeError as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="ffmpeg",
            error=f"Failed to parse ffprobe output: {exc}",
        )
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="ffmpeg",
            error=f"ffmpeg/ffprobe failed: {exc}",
        )


def _pillow_available() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def convert_pillow(input_: AdapterInput) -> AdapterResult:
    """Extract image metadata via Pillow.

    Reads image format, dimensions, mode, file size, and EXIF-like metadata
    from image files (PNG, JPEG, GIF, BMP, WebP, TIFF, SVG via cairosvg
    if installed). Returns a structured metadata summary as content text.

    The format parameter ``image`` matches the AdapterKind.IMAGE enumeration
    for most raster formats; individual format keys (png, jpg, gif, …) are
    also registered for priority-based lookup.
    """
    if not _pillow_available():
        return AdapterResult(
            success=False,
            content="",
            engine="pillow",
            error="Pillow is not installed. Run: pip install Pillow",
        )

    source = input_.source
    if not source:
        return AdapterResult(
            success=False,
            content="",
            engine="pillow",
            error="Empty source — provide a file path to an image",
        )

    path = Path(source)
    if not path.is_file():
        return AdapterResult(
            success=False,
            content="",
            engine="pillow",
            error=f"File not found: {source}",
        )

    try:
        from PIL import Image

        img = Image.open(path)
        fmt = img.format or "unknown"
        mode = img.mode
        width, height = img.size
        file_size = path.stat().st_size

        # Try to read EXIF-like info
        info = img.info or {}
        exif_data = {}
        for key in ("dpi", "orientation", "description", "artist", "software",
                     "copyright", "gamma", "transparency"):
            if key in info:
                exif_data[key] = str(info[key])

        lines = [
            f"File: {path.name}",
            f"Size: {file_size:,} bytes",
            f"Format: {fmt}",
            f"Mode: {mode}",
            f"Dimensions: {width} x {height} pixels",
        ]
        if exif_data:
            lines.append("Metadata:")
            for k, v in exif_data.items():
                lines.append(f"  {k}: {v}")

        content = "\n".join(lines)

        metadata = {
            "byte_size": file_size,
            "width": width,
            "height": height,
            "format": fmt,
            "mode": mode,
        }
        metadata.update(exif_data)

        return AdapterResult(
            success=True,
            content=content,
            engine="pillow",
            metadata=metadata,
        )
    except Exception as exc:
        return AdapterResult(
            success=False,
            content="",
            engine="pillow",
            error=f"Pillow failed to process {source}: {exc}",
        )


# ── Registry population — auto-classify every known adapter ──


def _register_all() -> None:
    """Populate the global adapter registry with real-time classifications."""
    # ── Document adapters ──
    md_available = _markitdown_importable()
    for fmt in ("pdf", "docx", "pptx", "xlsx", "csv"):
        register_adapter(
            AdapterCapability(
                kind=AdapterKind.DOCUMENT,
                format=fmt,
                engine="markitdown",
                status=AdapterStatus.INSTALLED if md_available else AdapterStatus.UNAVAILABLE,
                priority=10,
                notes="pip install markitdown" if not md_available else "",
            )
        )

    # docling — document understanding (PDF, DOCX, PPTX, XLSX)
    dl_available = _docling_importable()
    status = AdapterStatus.INSTALLED if dl_available else AdapterStatus.UNAVAILABLE
    for fmt in ("pdf", "docx", "pptx", "xlsx"):
        register_adapter(
            AdapterCapability(
                kind=AdapterKind.DOCUMENT,
                format=fmt,
                engine="docling",
                status=status,
                priority=30,
                notes="pip install docling" if not dl_available else "",
            )
        )

    # Plain text passthrough (always available)
    for fmt in ("md", "txt"):
        register_adapter(
            AdapterCapability(
                kind=AdapterKind.PLAINTEXT,
                format=fmt,
                engine="passthrough",
                status=AdapterStatus.INSTALLED,
                priority=1,
            )
        )

    # ── Webpage adapters ──
    tf_available = _trafilatura_importable()
    register_adapter(
        AdapterCapability(
            kind=AdapterKind.WEBPAGE,
            format="html",
            engine="trafilatura",
            status=AdapterStatus.INSTALLED if tf_available else AdapterStatus.UNAVAILABLE,
            priority=10,
            requires_network=True,
            notes="pip install trafilatura" if not tf_available else "",
        )
    )
    np4k_available = _newspaper4k_importable()
    register_adapter(
        AdapterCapability(
            kind=AdapterKind.WEBPAGE,
            format="html",
            engine="newspaper4k",
            status=AdapterStatus.INSTALLED if np4k_available else AdapterStatus.UNAVAILABLE,
            priority=20,
            requires_network=True,
            notes="pip install newspaper4k" if not np4k_available else "",
        )
    )
    register_adapter(
        AdapterCapability(
            kind=AdapterKind.WEBPAGE,
            format="html",
            engine="safe-http+raw",
            status=AdapterStatus.INSTALLED,
            priority=50,
            requires_network=True,
            notes="Returns raw HTML only (no markdown conversion)",
        )
    )
    sp_available = _scrapling_importable()
    register_adapter(
        AdapterCapability(
            kind=AdapterKind.WEBPAGE,
            format="html",
            engine="scrapling",
            status=AdapterStatus.INSTALLED if sp_available else AdapterStatus.UNAVAILABLE,
            priority=25,
            requires_network=True,
            notes="pip install scrapling" if not sp_available else "",
        )
    )
    rp_available = _readabilipy_importable()
    register_adapter(
        AdapterCapability(
            kind=AdapterKind.WEBPAGE,
            format="html",
            engine="readabilipy",
            status=AdapterStatus.INSTALLED if rp_available else AdapterStatus.UNAVAILABLE,
            priority=30,
            requires_network=True,
            notes="pip install readabilipy" if not rp_available else "",
        )
    )

    # ── Media video ──
    ffmpeg_ok = _ffmpeg_available()
    register_adapter(
        AdapterCapability(
            kind=AdapterKind.MEDIA_VIDEO,
            format="mp4",
            engine="ffmpeg",
            status=AdapterStatus.INSTALLED if ffmpeg_ok else AdapterStatus.UNAVAILABLE,
            priority=10,
            requires_external_binary=True,
            notes="ffmpeg must be in PATH" if not ffmpeg_ok else "",
        )
    )
    # Same ffmpeg adapter covers all video formats
    for vfmt in ("mov", "mkv", "avi", "webm"):
        register_adapter(
            AdapterCapability(
                kind=AdapterKind.MEDIA_VIDEO,
                format=vfmt,
                engine="ffmpeg",
                status=AdapterStatus.INSTALLED if ffmpeg_ok else AdapterStatus.UNAVAILABLE,
                priority=10,
                requires_external_binary=True,
            )
        )

    # ── Media audio ──
    for afmt in ("mp3", "wav", "m4a", "flac"):
        register_adapter(
            AdapterCapability(
                kind=AdapterKind.MEDIA_AUDIO,
                format=afmt,
                engine="ffmpeg",
                status=AdapterStatus.INSTALLED if ffmpeg_ok else AdapterStatus.UNAVAILABLE,
                priority=10,
                requires_external_binary=True,
            )
        )

    # ── OCR ──
    ocr_ok = _tesseract_available() and _pytesseract_importable()
    register_adapter(
        AdapterCapability(
            kind=AdapterKind.OCR,
            format="image",
            engine="pytesseract+tesseract",
            status=AdapterStatus.INSTALLED if ocr_ok else AdapterStatus.UNAVAILABLE,
            priority=10,
            requires_external_binary=True,
            notes="pip install pytesseract Pillow; install Tesseract-OCR system package"
            if not ocr_ok
            else "",
        )
    )

    # ── YouTube ──
    yt_ok = _youtube_transcript_importable()
    register_adapter(
        AdapterCapability(
            kind=AdapterKind.YOUTUBE,
            format="youtube",
            engine="youtube-transcript-api",
            status=AdapterStatus.INSTALLED if yt_ok else AdapterStatus.UNAVAILABLE,
            priority=10,
            requires_network=True,
            notes="pip install youtube-transcript-api" if not yt_ok else "",
        )
    )

    # ── Image / Pillow ──
    pillow_ok = _pillow_available()
    image_status = AdapterStatus.INSTALLED if pillow_ok else AdapterStatus.UNAVAILABLE
    # Register both the generic "image" format key and individual raster formats
    for fmt in ("image", "png", "jpg", "jpeg", "gif", "bmp", "webp", "tiff"):
        register_adapter(
            AdapterCapability(
                kind=AdapterKind.IMAGE,
                format=fmt,
                engine="pillow",
                status=image_status,
                priority=10,
            )
        )


def ensure_registered() -> None:
    """Idempotent adapter registry initialisation.

    Re-registers on every call so a partially cleared registry (for example,
    after an isolated test registers a temporary capability) is restored to
    the complete known-adapter set.
    """
    _register_all()


ensure_registered()
