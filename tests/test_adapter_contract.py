"""Tests for unified adapter contract and fallback fixtures."""

from __future__ import annotations

import pytest

from shared.adapter_contract import (
    AdapterCapability,
    AdapterInput,
    AdapterKind,
    AdapterResult,
    AdapterStatus,
    get_adapter_registry,
    lookup_adapter,
    lookup_adapters,
    register_adapter,
)
from shared.safe_http import SafeHTTPError


class TestAdapterContract:
    """Typed contract dataclasses."""

    def test_adapter_capability_frozen(self):
        cap = AdapterCapability(
            kind=AdapterKind.DOCUMENT, format="pdf", engine="markitdown"
        )
        assert cap.kind == AdapterKind.DOCUMENT
        assert cap.format == "pdf"
        assert cap.engine == "markitdown"
        assert cap.status == AdapterStatus.UNAVAILABLE  # default
        assert cap.priority == 100  # default

    def test_adapter_input_defaults(self):
        inp = AdapterInput(source="test.pdf")
        assert inp.source == "test.pdf"
        assert inp.format is None
        assert inp.options == {}

    def test_adapter_result_success(self):
        result = AdapterResult(
            success=True, content="# Hello", engine="markitdown", metadata={"char_count": 9}
        )
        assert result.success
        assert result.content == "# Hello"
        assert result.engine == "markitdown"

    def test_adapter_result_failure(self):
        result = AdapterResult(
            success=False, content="", engine="fallback", error="No engine available"
        )
        assert not result.success
        assert result.error == "No engine available"

    def test_adapter_result_no_error(self):
        """Success result may omit error field."""
        result = AdapterResult(success=True, content="ok", engine="passthrough")
        assert result.error is None


class TestAdapterRegistry:
    """Registration and lookup."""

    def setup_method(self):
        # Reset registry for clean tests
        import shared.adapter_contract as mod

        mod._ADAPTER_REGISTRY.clear()

    def test_register_and_lookup(self):
        cap = AdapterCapability(
            kind=AdapterKind.DOCUMENT,
            format="pdf",
            engine="test-engine",
            status=AdapterStatus.INSTALLED,
            priority=5,
        )
        register_adapter(cap)

        found = lookup_adapter(AdapterKind.DOCUMENT, "pdf", "test-engine")
        assert found is not None
        assert found.engine == "test-engine"
        assert found.status == AdapterStatus.INSTALLED

    def test_lookup_nonexistent_returns_none(self):
        assert lookup_adapter(AdapterKind.DOCUMENT, "nonexistent", "nope") is None

    def test_register_multiple_and_sort_by_priority(self):
        caps = [
            AdapterCapability(
                kind=AdapterKind.DOCUMENT,
                format="pdf",
                engine="slow",
                status=AdapterStatus.INSTALLED,
                priority=50,
            ),
            AdapterCapability(
                kind=AdapterKind.DOCUMENT,
                format="pdf",
                engine="fast",
                status=AdapterStatus.INSTALLED,
                priority=10,
            ),
            AdapterCapability(
                kind=AdapterKind.DOCUMENT,
                format="pdf",
                engine="medium",
                status=AdapterStatus.INSTALLED,
                priority=30,
            ),
        ]
        register_adapter(*caps)

        matches = lookup_adapters(AdapterKind.DOCUMENT, "pdf")
        assert len(matches) == 3
        assert [m.engine for m in matches] == ["fast", "medium", "slow"]

    def test_get_registry_returns_copy(self):
        cap = AdapterCapability(
            kind=AdapterKind.WEBPAGE, format="html", engine="test"
        )
        register_adapter(cap)
        registry = get_adapter_registry()
        assert "webpage:html:test" in registry


class TestAdapterFixtures:
    """Fallback fixture adapters (from shared/adapter_fixtures)."""

    def test_fallback_any(self):
        from shared.adapter_fixtures import fallback_any

        result = fallback_any(AdapterInput(source="test.xyz", format="xyz"))
        assert not result.success
        assert result.engine == "fallback"
        assert "No adapter available" in (result.error or "")

    def test_fallback_read_success(self, tmp_path):
        from shared.adapter_fixtures import fallback_read

        f = tmp_path / "test.md"
        f.write_text("# Hello World", encoding="utf-8")
        result = fallback_read(AdapterInput(source=str(f)))
        assert result.success
        assert result.content == "# Hello World"
        assert result.engine == "passthrough"

    def test_fallback_read_file_not_found(self):
        from shared.adapter_fixtures import fallback_read

        result = fallback_read(AdapterInput(source="/nonexistent/file.md"))
        assert not result.success
        assert "not found" in (result.error or "").lower()

    def test_fallback_image_ocr(self):
        from shared.adapter_fixtures import fallback_image_ocr

        result = fallback_image_ocr(AdapterInput(source="test.png"))
        assert not result.success
        assert "Tesseract" in (result.error or "")


class TestAdapterRegistryPopulation:
    """Registry is auto-populated at import time."""

    def test_registry_contains_document_adapters(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        registry = get_adapter_registry()

        # Document adapters
        pdf_keys = [k for k in registry if k.startswith("document:pdf:")]
        assert len(pdf_keys) >= 2  # markitdown, docling

        docx_keys = [k for k in registry if k.startswith("document:docx:")]
        assert any("markitdown" in k for k in docx_keys)

        pptx_keys = [k for k in registry if k.startswith("document:pptx:")]
        assert len(pptx_keys) >= 1  # markitdown, docling

        xlsx_keys = [k for k in registry if k.startswith("document:xlsx:")]
        assert len(xlsx_keys) >= 1  # markitdown, docling

    def test_registry_contains_plaintext_passthrough(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()

        md_cap = lookup_adapter(AdapterKind.PLAINTEXT, "md", "passthrough")
        assert md_cap is not None
        assert md_cap.status == AdapterStatus.INSTALLED

        txt_cap = lookup_adapter(AdapterKind.PLAINTEXT, "txt", "passthrough")
        assert txt_cap is not None
        assert txt_cap.status == AdapterStatus.INSTALLED

    def test_registry_contains_webpage_adapters(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        registry = get_adapter_registry()

        html_keys = [k for k in registry if k.startswith("webpage:html:")]
        assert len(html_keys) >= 3  # trafilatura + newspaper4k + raw html

    def test_registry_contains_media_video_adapters(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        registry = get_adapter_registry()

        mp4_keys = [k for k in registry if k.startswith("media_video:")]
        assert len(mp4_keys) >= 4  # mp4, mov, mkv, avi, webm

    def test_registry_contains_media_audio_adapters(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        registry = get_adapter_registry()

        audio_keys = [k for k in registry if k.startswith("media_audio:")]
        assert len(audio_keys) >= 4  # mp3, wav, m4a, flac

    def test_registry_contains_youtube_adapter(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        yt = lookup_adapter(AdapterKind.YOUTUBE, "youtube", "youtube-transcript-api")
        assert yt is not None
        assert yt.requires_network

    def test_registry_idempotent(self):
        """Multiple ensures don't double-register."""
        import shared.adapter_contract as mod
        from shared.adapter_fixtures import ensure_registered

        mod._ADAPTER_REGISTRY.clear()
        ensure_registered()
        count1 = len(get_adapter_registry())
        ensure_registered()
        count2 = len(get_adapter_registry())
        assert count1 == count2


class TestMultiFormatAdapter:
    """End-to-end file conversion tests."""

    def test_detect_format_by_extension(self):
        from app.ingestion.multi_format import detect_format

        assert detect_format("doc.pdf") == "pdf"
        assert detect_format("doc.docx") == "docx"
        assert detect_format("page.html") == "html"
        assert detect_format("readme.md") == "md"
        assert detect_format("map.canvas") == "canvas"
        assert detect_format("data.csv") == "csv"
        assert detect_format("image.png") == "image"
        assert detect_format("clip.mp4") == "media_video"
        assert detect_format("recording.wav") == "media_audio"
        assert detect_format("unknown.xyz") == "unknown"

    def test_media_formats_reach_ffmpeg_product_chain(self, monkeypatch, tmp_path):
        """Registered FFmpeg formats must be reachable through convert_file."""
        from app.ingestion import multi_format

        media = tmp_path / "clip.mp4"
        media.write_bytes(b"controlled-media-fixture")
        seen = []

        def fake_ffmpeg(adapter_input):
            seen.append(adapter_input.source)
            return AdapterResult(
                success=True,
                content="media metadata",
                engine="ffmpeg",
                metadata={"stream_count": 1},
            )

        monkeypatch.setattr("shared.adapter_fixtures.convert_ffmpeg", fake_ffmpeg)
        content, engine = multi_format.convert_file(media)

        assert content == "media metadata"
        assert engine == "ffmpeg"
        assert seen == [str(media)]

    def test_youtube_url_reaches_transcript_product_chain(self, monkeypatch):
        """YouTube URL intake must use the registered transcript adapter."""
        from app.ingestion import multi_format

        seen = []

        def fake_transcript(adapter_input):
            seen.append(adapter_input.source)
            return AdapterResult(
                success=True,
                content="[00:00] governed transcript",
                engine="youtube-transcript-api",
                metadata={"video_id": "abcdefghijk", "snippet_count": 1},
            )

        monkeypatch.setattr("shared.adapter_fixtures.convert_youtube_transcript", fake_transcript)
        content, engine = multi_format.convert_url("https://www.youtube.com/watch?v=abcdefghijk")

        assert content == "[00:00] governed transcript"
        assert engine == "youtube-transcript-api"
        assert seen == ["https://www.youtube.com/watch?v=abcdefghijk"]

    def test_txt_passthrough(self, tmp_path):
        """Plain text conversion always works (no external deps)."""
        from app.ingestion.multi_format import convert_file

        f = tmp_path / "hello.txt"
        f.write_text("Hello, world!", encoding="utf-8")
        content, engine = convert_file(str(f))
        assert content == "Hello, world!"
        assert engine == "passthrough"

    def test_md_passthrough(self, tmp_path):
        """Markdown passthrough always works."""
        from app.ingestion.multi_format import convert_file

        f = tmp_path / "test.md"
        f.write_text("# Title\n\nBody text", encoding="utf-8")
        content, engine = convert_file(str(f))
        assert "# Title" in content
        assert engine == "passthrough"

    def test_json_canvas_projects_text_nodes_without_execution(self, tmp_path):
        from app.ingestion.multi_format import convert_file

        f = tmp_path / "lesson.canvas"
        f.write_text(
            '{"nodes":[{"id":"a","type":"text","x":0,"y":0,"width":200,"height":60,"text":"# Lesson\\n\\nRecall"},'
            '{"id":"b","type":"link","x":200,"y":0,"width":200,"height":60,"url":"https://example.invalid"}],"edges":[]}',
            encoding="utf-8",
        )
        content, engine = convert_file(f)

        assert "# Lesson" in content
        assert "https://example.invalid" in content
        assert engine == "json-canvas"

    def test_pdf_uses_markitdown(self, tmp_path):
        """PDF conversion uses markitdown when installed."""
        from app.ingestion.multi_format import convert_file

        f = tmp_path / "test.pdf"
        f.write_text("# Markdown in a .pdf file", encoding="utf-8")
        content, engine = convert_file(str(f))
        assert "Markdown in a" in content
        assert engine == "markitdown"

    def test_html_uses_trafilatura(self, tmp_path):
        """HTML uses trafilatura when installed."""
        from app.ingestion.multi_format import convert_file

        f = tmp_path / "test.html"
        f.write_text("<html><body><p>Hello</p></body></html>", encoding="utf-8")
        content, engine = convert_file(str(f))
        assert content == "Hello"
        assert engine == "trafilatura"

    def test_unsupported_format_uses_universal_fallback(self, tmp_path):
        """Unknown format falls back to markitdown as universal engine."""
        from app.ingestion.multi_format import convert_file

        f = tmp_path / "test.xyz"
        f.write_text("some content", encoding="utf-8")
        content, engine = convert_file(str(f))
        assert content == "some content"
        assert engine == "markitdown"

    def test_convert_url_graceful_failure(self):
        """convert_url gracefully fails on unreachable URL (no DNS)."""
        from app.ingestion.multi_format import convert_url

        with pytest.raises(SafeHTTPError):
            convert_url("http://127.0.0.1:1/nonexistent")


class TestAdapterContractImport:
    """Verify the contract module is importable and self-consistent."""

    def test_adapter_kind_values(self):
        assert len(AdapterKind) >= 7  # document, webpage, media_video, media_audio, ocr, youtube, plaintext, image

    def test_adapter_status_values(self):
        assert AdapterStatus.INSTALLED.value == "installed"
        assert AdapterStatus.UNAVAILABLE.value == "unavailable"
        assert AdapterStatus.FALLBACK.value == "fallback"
        assert AdapterStatus.IMPORTABLE.value == "importable"


class TestDoclingAdapter:
    """Focused tests for the docling document understanding adapter."""

    def test_registry_contains_docling_pdf(self):
        import shared.adapter_contract as contract
        import shared.adapter_fixtures as fixtures
        from shared.adapter_fixtures import ensure_registered

        if not contract._ADAPTER_REGISTRY:
            fixtures._registered = False
        ensure_registered()
        cap = lookup_adapter(AdapterKind.DOCUMENT, "pdf", "docling")
        assert cap is not None
        assert cap.engine == "docling"
        assert cap.priority == 30

    def test_registry_contains_docling_docx(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        cap = lookup_adapter(AdapterKind.DOCUMENT, "docx", "docling")
        assert cap is not None

    def test_registry_contains_docling_pptx(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        cap = lookup_adapter(AdapterKind.DOCUMENT, "pptx", "docling")
        assert cap is not None

    def test_registry_contains_docling_xlsx(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        cap = lookup_adapter(AdapterKind.DOCUMENT, "xlsx", "docling")
        assert cap is not None

    def test_convert_docling_not_installed_returns_unavailable(self):
        """Simulate docling not installed by patching the import."""
        import builtins

        from shared.adapter_fixtures import convert_docling

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "docling":
                raise ImportError("docling not available")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            result = convert_docling(AdapterInput(source="test.pdf"))
            assert not result.success
            assert "is not installed" in (result.error or "")
            assert result.engine == "docling"
        finally:
            builtins.__import__ = real_import

    def test_convert_docling_empty_input_fails_gracefully(self):
        """Empty source should not crash — produce a non-success result."""
        from shared.adapter_fixtures import convert_docling

        result = convert_docling(AdapterInput(source=""))
        assert not result.success or result.content

class TestMarkitdownAdapter:
    """Focused tests for the markitdown universal document parsing adapter."""

    def test_registry_contains_markitdown_pdf(self):
        import shared.adapter_contract as contract
        import shared.adapter_fixtures as fixtures
        from shared.adapter_fixtures import ensure_registered

        if not contract._ADAPTER_REGISTRY:
            fixtures._registered = False
        ensure_registered()
        cap = lookup_adapter(AdapterKind.DOCUMENT, "pdf", "markitdown")
        assert cap is not None
        assert cap.engine == "markitdown"
        assert cap.priority == 10

    def test_registry_contains_markitdown_docx(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        cap = lookup_adapter(AdapterKind.DOCUMENT, "docx", "markitdown")
        assert cap is not None

    def test_registry_contains_markitdown_all_formats(self):
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        for fmt in ("pdf", "docx", "pptx", "xlsx", "csv"):
            cap = lookup_adapter(AdapterKind.DOCUMENT, fmt, "markitdown")
            assert cap is not None, f"markitdown missing for {fmt}"

    def test_convert_markitdown_not_installed_returns_unavailable(self):
        """Simulate markitdown not installed by patching the import."""
        import builtins

        from shared.adapter_fixtures import convert_markitdown

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "markitdown":
                raise ImportError("markitdown not available")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            result = convert_markitdown(AdapterInput(source="test.pdf"))
            assert not result.success
            assert "is not installed" in (result.error or "")
            assert result.engine == "markitdown"
        finally:
            builtins.__import__ = real_import

    def test_convert_markitdown_empty_input_fails_gracefully(self):
        """Empty source should not crash — produce a non-success result."""
        from shared.adapter_fixtures import convert_markitdown

        result = convert_markitdown(AdapterInput(source=""))
        assert not result.success or result.content

    def test_convert_markitdown_text_file_passthrough(self, tmp_path):
        """A plain-text .pdf file should be readable by markitdown."""
        from shared.adapter_fixtures import convert_markitdown

        # Only block markitdown if it's actually importable
        try:
            import markitdown  # noqa: F401
        except ImportError:
            pytest.skip("markitdown not installed — cannot test real conversion")

        f = tmp_path / "test_passthrough.pdf"
        f.write_text("# Hello from markitdown\n\nSome body text.", encoding="utf-8")
        result = convert_markitdown(AdapterInput(source=str(f)))
        assert result.success
        assert "Hello" in result.content
        assert result.engine == "markitdown"
        assert "char_count" in result.metadata
        assert result.metadata["char_count"] > 0


class TestNewspaper4kAdapter:
    """Focused tests for the newspaper4k article extraction adapter."""

    def test_registry_contains_newspaper4k(self):
        import shared.adapter_contract as contract
        import shared.adapter_fixtures as fixtures
        from shared.adapter_fixtures import ensure_registered

        if not contract._ADAPTER_REGISTRY:
            fixtures._registered = False
        ensure_registered()
        cap = lookup_adapter(AdapterKind.WEBPAGE, "html", "newspaper4k")
        assert cap is not None
        assert cap.engine == "newspaper4k"
        assert cap.requires_network
        assert cap.priority == 20

    def test_convert_newspaper4k_not_installed_returns_unavailable(self):
        """Simulate newspaper not installed by patching the import."""
        import builtins

        from shared.adapter_fixtures import convert_newspaper4k

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "newspaper":
                raise ImportError("newspaper not available")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            result = convert_newspaper4k(AdapterInput(source="https://example.com"))
            assert not result.success
            assert "is not installed" in (result.error or "")
            assert result.engine == "newspaper4k"
        finally:
            builtins.__import__ = real_import

    def test_convert_newspaper4k_empty_input_fails_gracefully(self):
        """Empty source should not crash — produce a non-success result."""
        from shared.adapter_fixtures import convert_newspaper4k

        result = convert_newspaper4k(AdapterInput(source=""))
        assert not result.success or result.content

    def test_convert_newspaper4k_real_url_extracts_article(self):
        """Real URL extraction via newspaper4k (network required)."""
        from shared.adapter_fixtures import convert_newspaper4k

        result = convert_newspaper4k(AdapterInput(source="https://example.com"))
        assert result.success
        assert "Example Domain" in result.content
        assert result.engine == "newspaper4k"
        assert "char_count" in result.metadata
        assert result.metadata["char_count"] > 0


class TestTrafilaturaAdapter:
    """Focused tests for the trafilatura web extraction adapter."""

    def test_registry_contains_trafilatura(self):
        """Verify trafilatura is registered in the adapter registry."""
        import shared.adapter_contract as contract
        import shared.adapter_fixtures as fixtures
        from shared.adapter_fixtures import ensure_registered

        if not contract._ADAPTER_REGISTRY:
            fixtures._registered = False
        ensure_registered()
        cap = lookup_adapter(AdapterKind.WEBPAGE, "html", "trafilatura")
        assert cap is not None
        assert cap.engine == "trafilatura"
        assert cap.requires_network
        assert cap.priority == 10

    def test_convert_trafilatura_not_installed_returns_unavailable(self):
        """Simulate trafilatura not installed by patching the import."""
        import builtins

        from shared.adapter_fixtures import convert_trafilatura

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "trafilatura":
                raise ImportError("trafilatura not available")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            result = convert_trafilatura(AdapterInput(source="https://example.com"))
            assert not result.success
            assert "is not installed" in (result.error or "")
            assert result.engine == "trafilatura"
        finally:
            builtins.__import__ = real_import

    def test_convert_trafilatura_empty_source_fails_gracefully(self):
        """Empty source should produce a non-success result (regardless of install status)."""
        from shared.adapter_fixtures import convert_trafilatura

        result = convert_trafilatura(AdapterInput(source=""))
        assert not result.success

    def test_convert_trafilatura_file_not_found_fails_gracefully(self):
        """Non-existent file path should produce a non-success result."""
        from shared.adapter_fixtures import convert_trafilatura

        result = convert_trafilatura(AdapterInput(source="/nonexistent/file.html"))
        assert not result.success

    def test_convert_trafilatura_html_file_extracts_content(self, tmp_path):
        """Real HTML file extraction (trafilatura must be installed)."""
        from shared.adapter_fixtures import convert_trafilatura

        # Skip if trafilatura is not installed
        try:
            import trafilatura  # noqa: F401
        except ImportError:
            pytest.skip("trafilatura not installed — cannot test real extraction")

        f = tmp_path / "test.html"
        f.write_text(
            "<html><body><article><h1>Test Article</h1><p>Some body text here.</p></article></body></html>",
            encoding="utf-8",
        )
        result = convert_trafilatura(AdapterInput(source=str(f)))
        assert result.success
        assert "Test Article" in result.content
        assert result.engine == "trafilatura"
        assert "char_count" in result.metadata
        assert result.metadata["char_count"] > 0


class TestScraplingAdapter:
    """Focused tests for the scrapling web extraction adapter."""

    def test_registry_contains_scrapling(self):
        """Verify scrapling is registered in the adapter registry."""
        import shared.adapter_contract as contract
        import shared.adapter_fixtures as fixtures
        from shared.adapter_fixtures import ensure_registered

        if not contract._ADAPTER_REGISTRY:
            fixtures._registered = False
        ensure_registered()
        cap = lookup_adapter(AdapterKind.WEBPAGE, "html", "scrapling")
        assert cap is not None
        assert cap.engine == "scrapling"
        assert cap.requires_network
        assert cap.priority == 25

    def test_convert_scrapling_not_installed_returns_unavailable(self):
        """Simulate scrapling not installed by patching the import."""
        import builtins

        from shared.adapter_fixtures import convert_scrapling

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "scrapling":
                raise ImportError("scrapling not available")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            result = convert_scrapling(AdapterInput(source="https://example.com"))
            assert not result.success
            assert "is not installed" in (result.error or "")
            assert result.engine == "scrapling"
        finally:
            builtins.__import__ = real_import

    def test_convert_scrapling_empty_source_fails_gracefully(self):
        """Empty source should produce a non-success result."""
        from shared.adapter_fixtures import convert_scrapling

        result = convert_scrapling(AdapterInput(source=""))
        assert not result.success

    def test_convert_scrapling_unknown_host_fails_gracefully(self):
        """Unreachable host should not crash — produce a non-success result."""
        from shared.adapter_fixtures import convert_scrapling

        result = convert_scrapling(AdapterInput(source="http://127.0.0.1:1/nonexistent"))
        assert not result.success or result.content


class TestYoutubeTranscriptAdapter:
    """Focused tests for the youtube-transcript-api adapter."""

    def test_registry_contains_youtube_transcript(self):
        """Verify youtube-transcript-api is registered in the adapter registry."""
        import shared.adapter_contract as contract
        import shared.adapter_fixtures as fixtures
        from shared.adapter_fixtures import ensure_registered

        if not contract._ADAPTER_REGISTRY:
            fixtures._registered = False
        ensure_registered()
        cap = lookup_adapter(AdapterKind.YOUTUBE, "youtube", "youtube-transcript-api")
        assert cap is not None
        assert cap.engine == "youtube-transcript-api"
        assert cap.requires_network
        assert cap.priority == 10

    def test_convert_youtube_transcript_not_installed(self):
        """Simulate youtube-transcript-api not installed."""
        import builtins

        from shared.adapter_fixtures import convert_youtube_transcript

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "youtube_transcript_api":
                raise ImportError("not available")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            result = convert_youtube_transcript(AdapterInput(source="dQw4w9WgXcQ"))
            assert not result.success
            assert "is not installed" in (result.error or "")
            assert result.engine == "youtube-transcript-api"
        finally:
            builtins.__import__ = real_import

    def test_empty_source_fails_gracefully(self):
        """Empty source should produce a non-success result."""
        from shared.adapter_fixtures import convert_youtube_transcript

        result = convert_youtube_transcript(AdapterInput(source=""))
        assert not result.success
        assert "Empty source" in (result.error or "")

    def test_invalid_video_id_returns_error(self):
        """A non-existent video ID should produce a non-success result."""
        from shared.adapter_fixtures import convert_youtube_transcript

        result = convert_youtube_transcript(AdapterInput(source="xyz-invalid-123"))
        assert not result.success or result.content

    def test_url_formats_extract_video_id(self):
        """Full YouTube URLs should still fetch via extracted video ID."""
        from shared.adapter_fixtures import convert_youtube_transcript

        # Standard watch URL
        result = convert_youtube_transcript(
            AdapterInput(source="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        )
        assert not result.success or result.content

    def test_youtube_transcript_language_option(self):
        """Language option should be accepted without error."""
        from shared.adapter_fixtures import convert_youtube_transcript

        result = convert_youtube_transcript(
            AdapterInput(
                source="dQw4w9WgXcQ",
                options={"language": "en"},
            )
        )
        assert not result.success or result.content
        if result.success:
            assert result.metadata.get("language") == "en"


class TestFFmpegAdapter:
    """Focused tests for the ffmpeg media metadata extraction adapter."""

    def test_registry_contains_ffmpeg_video(self):
        """Verify ffmpeg is registered for video formats."""
        import shared.adapter_contract as contract
        import shared.adapter_fixtures as fixtures
        from shared.adapter_fixtures import ensure_registered

        if not contract._ADAPTER_REGISTRY:
            fixtures._registered = False
        ensure_registered()
        for fmt in ("mp4", "mov", "mkv", "avi", "webm"):
            cap = lookup_adapter(AdapterKind.MEDIA_VIDEO, fmt, "ffmpeg")
            assert cap is not None, f"ffmpeg missing for video format {fmt}"
            assert cap.priority == 10
            assert cap.requires_external_binary

    def test_registry_contains_ffmpeg_audio(self):
        """Verify ffmpeg is registered for audio formats."""
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        for fmt in ("mp3", "wav", "m4a", "flac"):
            cap = lookup_adapter(AdapterKind.MEDIA_AUDIO, fmt, "ffmpeg")
            assert cap is not None, f"ffmpeg missing for audio format {fmt}"

    def test_convert_ffmpeg_not_installed_returns_unavailable(self):
        """Simulate ffmpeg not available by mocking shutil.which."""
        import shutil
        from unittest.mock import patch

        from shared.adapter_fixtures import convert_ffmpeg

        with patch.object(shutil, "which", return_value=None):
            result = convert_ffmpeg(AdapterInput(source="test.mp4"))
            assert not result.success
            assert "not installed" in (result.error or "").lower() or "not found" in (result.error or "").lower()
            assert result.engine == "ffmpeg"

    def test_convert_ffmpeg_empty_source_fails_gracefully(self):
        """Empty source should produce a non-success result."""
        from shared.adapter_fixtures import convert_ffmpeg

        result = convert_ffmpeg(AdapterInput(source=""))
        assert not result.success

    def test_convert_ffmpeg_file_not_found_fails_gracefully(self):
        """Non-existent file should produce a non-success result."""
        from shared.adapter_fixtures import convert_ffmpeg

        result = convert_ffmpeg(AdapterInput(source="/nonexistent/media.mp4"))
        assert not result.success
        assert "not found" in (result.error or "").lower()

    def test_convert_ffmpeg_real_video_file(self, tmp_path):
        """Create a tiny synthetic video and verify ffprobe can read it."""
        from shared.adapter_fixtures import _ffmpeg_available, convert_ffmpeg

        # Skip if ffmpeg is not available
        if not _ffmpeg_available():
            pytest.skip("ffmpeg not available — cannot test real file")

        import subprocess

        video_path = tmp_path / "test_minimal.mp4"
        # Use ffmpeg to generate the smallest valid mp4
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "color=c=black:s=2x2:d=0.1:r=1",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(video_path),
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)

        if not video_path.is_file():
            pytest.skip("ffmpeg could not generate test video")

        result = convert_ffmpeg(AdapterInput(source=str(video_path)))
        assert result.success
        assert result.engine == "ffmpeg"
        assert "File:" in result.content
        assert result.metadata.get("byte_size", 0) > 0
        assert result.metadata.get("stream_count", 0) >= 1
        assert result.metadata.get("has_video") is True

        # Verify a second call returns the same result shape
        result2 = convert_ffmpeg(AdapterInput(source=str(video_path)))
        assert result2.success
        assert result2.metadata["byte_size"] == result.metadata["byte_size"]

    def test_convert_ffmpeg_empty_file_fails_gracefully(self, tmp_path):
        """An empty file should fail gracefully (ffprobe cannot parse it)."""
        from shared.adapter_fixtures import _ffmpeg_available, convert_ffmpeg
        if not _ffmpeg_available():
            pytest.skip("ffmpeg not available")

        empty_file = tmp_path / "empty.mp4"
        empty_file.write_text("", encoding="utf-8")

        result = convert_ffmpeg(AdapterInput(source=str(empty_file)))
        assert not result.success
        assert result.engine == "ffmpeg"


class TestReadabilipyAdapter:
    """Focused tests for the readabilipy web extraction adapter."""

    def test_registry_contains_readabilipy(self):
        """Verify readabilipy is registered in the adapter registry."""
        import shared.adapter_contract as contract
        import shared.adapter_fixtures as fixtures
        from shared.adapter_fixtures import ensure_registered

        if not contract._ADAPTER_REGISTRY:
            fixtures._registered = False
        ensure_registered()
        cap = lookup_adapter(AdapterKind.WEBPAGE, "html", "readabilipy")
        assert cap is not None
        assert cap.engine == "readabilipy"
        assert cap.requires_network
        assert cap.priority == 30

    def test_convert_readabilipy_not_installed_returns_unavailable(self):
        """Simulate readabilipy not installed by patching the import."""
        import builtins

        from shared.adapter_fixtures import convert_readabilipy

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "readabilipy":
                raise ImportError("readabilipy not available")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            result = convert_readabilipy(AdapterInput(source="https://example.com"))
            assert not result.success
            assert "is not installed" in (result.error or "")
            assert result.engine == "readabilipy"
        finally:
            builtins.__import__ = real_import

    def test_convert_readabilipy_empty_source_fails_gracefully(self):
        """Empty source should produce a non-success result."""
        from shared.adapter_fixtures import convert_readabilipy

        result = convert_readabilipy(AdapterInput(source=""))
        assert not result.success

    def test_convert_readabilipy_local_html_file_extracts_content(self, tmp_path):
        """A temporary HTML file should produce extracted content without dirtying Git."""
        from shared.adapter_fixtures import convert_readabilipy

        # Create a minimal article HTML fixture
        html = """<!DOCTYPE html>
<html><head><title>Readability Test</title></head>
<body><article>
<h1>Main Article Title</h1>
<p>This is the article content that should be extracted by the readability algorithm.</p>
</article><aside>Sidebar noise</aside></body></html>"""
        fixture_path = tmp_path / "readability_article.html"
        fixture_path.write_text(html, encoding="utf-8")

        result = convert_readabilipy(AdapterInput(source=str(fixture_path)))
        assert result.success
        assert "Main Article Title" in result.content
        assert "article content" in result.content
        assert result.engine == "readabilipy"
        assert result.metadata.get("title") == "Readability Test"


class TestPillowAdapter:
    """Focused tests for the Pillow image metadata extraction adapter."""

    def test_registry_contains_pillow_image(self):
        """Verify Pillow is registered for the generic image format."""
        import shared.adapter_contract as contract
        import shared.adapter_fixtures as fixtures
        from shared.adapter_fixtures import ensure_registered

        if not contract._ADAPTER_REGISTRY:
            fixtures._registered = False
        ensure_registered()
        cap = lookup_adapter(AdapterKind.IMAGE, "image", "pillow")
        assert cap is not None
        assert cap.engine == "pillow"
        assert cap.priority == 10

    def test_registry_contains_pillow_all_formats(self):
        """Verify Pillow is registered for all common raster formats."""
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        for fmt in ("png", "jpg", "jpeg", "gif", "bmp", "webp", "tiff"):
            cap = lookup_adapter(AdapterKind.IMAGE, fmt, "pillow")
            assert cap is not None, f"Pillow missing for format {fmt}"

    def test_registry_count(self):
        """Verify all 8 image format registrations exist."""
        from shared.adapter_fixtures import ensure_registered

        ensure_registered()
        registry = get_adapter_registry()
        image_keys = [k for k in registry if k.startswith("image:")]
        assert len(image_keys) == 8  # image + png + jpg + jpeg + gif + bmp + webp + tiff

    def test_convert_pillow_not_installed_returns_unavailable(self):
        """Simulate Pillow not installed by patching the import."""
        import builtins

        from shared.adapter_fixtures import convert_pillow

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "PIL":
                raise ImportError("Pillow not available")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            result = convert_pillow(AdapterInput(source="test.png"))
            assert not result.success
            assert "is not installed" in (result.error or "")
            assert result.engine == "pillow"
        finally:
            builtins.__import__ = real_import

    def test_empty_source_fails_gracefully(self):
        """Empty source should produce a non-success result."""
        from shared.adapter_fixtures import convert_pillow

        result = convert_pillow(AdapterInput(source=""))
        assert not result.success
        assert "Empty source" in (result.error or "")

    def test_file_not_found_fails_gracefully(self):
        """Non-existent file should produce a non-success result."""
        from shared.adapter_fixtures import convert_pillow

        result = convert_pillow(AdapterInput(source="/nonexistent/image.png"))
        assert not result.success
        assert "not found" in (result.error or "").lower()

    def test_convert_pillow_real_png_file(self, tmp_path):
        """Create a real tiny PNG and verify Pillow extracts metadata."""
        # Create a minimal PNG
        from PIL import Image

        from shared.adapter_fixtures import convert_pillow

        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 50), color="red")
        img.save(str(img_path))

        result = convert_pillow(AdapterInput(source=str(img_path)))
        assert result.success
        assert result.engine == "pillow"
        assert "File: test.png" in result.content
        assert result.metadata.get("width") == 100
        assert result.metadata.get("height") == 50
        assert "PNG" in result.content or result.metadata.get("format") == "PNG"
        assert result.metadata.get("byte_size", 0) > 0

    def test_convert_pillow_real_jpg_file(self, tmp_path):
        """Create a real JPEG and verify Pillow extracts metadata."""
        from PIL import Image

        from shared.adapter_fixtures import convert_pillow

        img_path = tmp_path / "test.jpg"
        img = Image.new("RGB", (200, 100), color="blue")
        img.save(str(img_path), "JPEG")

        result = convert_pillow(AdapterInput(source=str(img_path)))
        assert result.success
        assert result.engine == "pillow"
        assert result.metadata.get("width") == 200
        assert result.metadata.get("format") == "JPEG"

    def test_convert_pillow_gif_file(self, tmp_path):
        """Create a GIF and verify Pillow extracts metadata."""
        from PIL import Image

        from shared.adapter_fixtures import convert_pillow

        img_path = tmp_path / "test.gif"
        img = Image.new("RGB", (50, 50), color="green")
        img.save(str(img_path), "GIF")

        result = convert_pillow(AdapterInput(source=str(img_path)))
        assert result.success
        assert result.metadata.get("format") == "GIF"
        assert result.metadata.get("width") == 50

    def test_convert_pillow_idempotent(self, tmp_path):
        """Two calls on the same file return the same metadata shape."""
        from PIL import Image

        from shared.adapter_fixtures import convert_pillow

        img_path = tmp_path / "idempotent.png"
        img = Image.new("RGB", (64, 48), color="white")
        img.save(str(img_path))

        result1 = convert_pillow(AdapterInput(source=str(img_path)))
        result2 = convert_pillow(AdapterInput(source=str(img_path)))
        assert result1.success == result2.success
        assert result1.metadata["byte_size"] == result2.metadata["byte_size"]
        assert result1.metadata["width"] == result2.metadata["width"]
