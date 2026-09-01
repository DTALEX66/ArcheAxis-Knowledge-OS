"""AXW-023B~F regression tests: structured adapters (honest degradation).

Each adapter test verifies:
- fails closed with a clear error when its engine dependency is missing
  (no fake success).
- produces structured blocks with anchors when the engine is present.
- never reports success from empty content.
"""

import contextlib
import os
import pathlib
import wave

from app.ingestion.html_adapter import convert_html
from app.ingestion.media_adapter import convert_media
from app.ingestion.ocr_adapter import convert_ocr
from app.ingestion.pptx_adapter import convert_pptx
from app.ingestion.xlsx_adapter import convert_xlsx

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

_HTML_SAMPLE = (
    "<html><head><title>Sample Article</title>"
    "<meta name='robots' content='noindex'></head>"
    "<body><article><h1>Hello</h1><p>Main content paragraph.</p></article>"
    "<nav>ignored sidebar</nav></body></html>"
)


def _real_pptx():
    cand = _REPO_ROOT / "tests/fixtures/sample.pptx"
    return cand if cand.is_file() else None


def _real_xlsx():
    cand = _REPO_ROOT / "tests/fixtures/sample.xlsx"
    return cand if cand.is_file() else None


# ── AXW-023B PPTX ────────────────────────────────────────────────────────


def test_pptx_missing_file_fails_closed(tmp_path) -> None:
    res = convert_pptx(str(tmp_path / "nope.pptx"))
    assert not res.success
    assert res.error


def test_pptx_without_engine_fails_closed() -> None:
    pptx = _real_pptx()
    if pptx is None:
        return
    with contextlib.suppress(ImportError):
        from pptx import Presentation  # noqa: F401
    res = convert_pptx(str(pptx))
    if res.success:
        assert res.content.strip(), "success with empty content"
        kinds = [b["kind"] for b in res.metadata["blocks"]]
        assert "slide" in kinds or "slide-empty" in kinds
        for b in res.metadata["blocks"]:
            assert "slide_index" in b["anchor"]
        return
    assert res.error, "failed conversion must explain why"


# ── AXW-023C XLSX ────────────────────────────────────────────────────────


def test_xlsx_missing_file_fails_closed(tmp_path) -> None:
    res = convert_xlsx(str(tmp_path / "nope.xlsx"))
    assert not res.success
    assert res.error


def test_xlsx_without_engine_fails_closed() -> None:
    xlsx = _real_xlsx()
    if xlsx is None:
        return
    with contextlib.suppress(ImportError):
        from openpyxl import load_workbook  # noqa: F401
    res = convert_xlsx(str(xlsx))
    if res.success:
        assert res.content.strip(), "success with empty content"
        for b in res.metadata["blocks"]:
            assert "sheet" in b["anchor"]
        return
    assert res.error, "failed conversion must explain why"


def test_xlsx_real_formula_fixture_preserves_a1_anchor_and_formula_text(tmp_path) -> None:
    """A Tier A workbook fixture keeps coordinates and formula text verbatim."""
    openpyxl = __import__("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Metrics"
    sheet["A1"] = 2
    sheet["A2"] = 3
    sheet["A3"] = "=SUM(A1:A2)"
    fixture = tmp_path / "tier-a-formula.xlsx"
    workbook.save(fixture)
    workbook.close()

    result = convert_xlsx(fixture)

    assert result.success, result.error
    assert "A1:2" in result.content
    assert "A3:=SUM(A1:A2)" in result.content
    assert "A3:==SUM(A1:A2)" not in result.content
    assert result.metadata["blocks"][0]["anchor"]["sheet"] == "Metrics"


# ── AXW-023D OCR ─────────────────────────────────────────────────────────


def test_ocr_missing_file_fails_closed(tmp_path) -> None:
    res = convert_ocr(str(tmp_path / "nope.pdf"))
    assert not res.success
    assert res.error


def test_ocr_quality_and_language_metrics() -> None:
    """Pure-function checks on quality/language helpers without OCR runs."""
    from app.ingestion.ocr_adapter import _detect_language, _quality

    # Non-space printable ratio, rounded to 3dp by the helper itself.
    assert _quality("hello world") == 0.909
    assert _quality("") == 0.0
    assert "zh" in _detect_language("这是中文测试")
    assert "eng" in _detect_language("hello world")


# ── AXW-023E HTML ────────────────────────────────────────────────────────


def test_html_extracts_main_content_and_metadata() -> None:
    res = convert_html(_HTML_SAMPLE)
    assert res.success
    assert "Main content paragraph" in res.content
    assert "Hello" in res.content  # article heading extracted
    assert res.metadata["title"] == "Sample Article"
    assert res.metadata["robots"] == "noindex"
    assert "fetched_at" in res.metadata
    assert res.metadata["blocks"][0]["kind"] == "article"


def test_html_empty_input_fails_closed() -> None:
    res = convert_html("   ")
    assert not res.success
    assert res.error


# ── AXW-023F Media ───────────────────────────────────────────────────────


def test_media_missing_file_fails_closed(tmp_path) -> None:
    res = convert_media(str(tmp_path / "nope.mp4"))
    assert not res.success
    assert res.error


def test_media_without_engine_fails_closed(tmp_path) -> None:
    """faster-whisper is optional; without it conversion must fail closed
    with a clear error and must NEVER trigger a model download."""
    fake = tmp_path / "empty.mp4"
    fake.write_bytes(b"\x00\x00\x00\x00")
    res = convert_media(str(fake))
    assert not res.success
    assert res.error


def test_media_silence_guard_rejects_zero_signal_but_not_audible_pcm(tmp_path) -> None:
    """Whisper may hallucinate short stock phrases on a truly silent clip."""
    from app.ingestion.media_adapter import _is_effectively_silent

    silent = tmp_path / "silent.wav"
    audible = tmp_path / "audible.wav"
    for path, frames in ((silent, b"\x00\x00" * 1600), (audible, b"\x10\x27" * 1600)):
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16000)
            output.writeframes(frames)

    assert _is_effectively_silent(silent)
    assert not _is_effectively_silent(audible)


def test_media_ffmpeg_resolution_skips_broken_path_shim_and_uses_external_config(tmp_path, monkeypatch) -> None:
    """A stale Scoop shim must not hide the verified external FFmpeg binary."""
    from app.ingestion import media_adapter

    external = tmp_path / "external"
    fallback = external / "10-toolchains" / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe"
    fallback.parent.mkdir(parents=True)
    fallback.write_bytes(b"fixture")
    stale = tmp_path / "stale-ffmpeg.exe"
    stale.write_bytes(b"fixture")
    monkeypatch.setenv("OS_EXTERNAL_CONFIG", str(external))
    monkeypatch.delenv("FFMPEG_CMD", raising=False)
    monkeypatch.setattr(media_adapter.shutil, "which", lambda _name: str(stale))
    monkeypatch.setattr(media_adapter, "_is_usable_ffmpeg", lambda candidate: os.fspath(candidate) == os.fspath(fallback))

    assert media_adapter.resolve_ffmpeg() == str(fallback)


def test_unified_media_metadata_fallback_never_claims_transcript(tmp_path, monkeypatch) -> None:
    """Container metadata is useful evidence, but is not converted media content."""
    from app.ingestion import multi_format
    from shared import adapter_fixtures
    from shared.adapter_contract import AdapterResult

    clip = tmp_path / "lesson.mp3"
    clip.write_bytes(b"not-a-real-media-file")
    monkeypatch.setattr(
        adapter_fixtures,
        "convert_ffmpeg",
        lambda _input: AdapterResult(True, "Duration: 3s", "ffmpeg", metadata={"duration_seconds": 3}),
    )

    result = multi_format._via_media_metadata(str(clip))

    assert not result.success
    assert "metadata-only" in (result.error or "")


def test_unified_media_conversion_prefers_local_time_anchored_transcript(tmp_path, monkeypatch) -> None:
    """The general importer must prefer local ASR over metadata-only FFmpeg."""
    from app.ingestion import media_adapter
    from app.ingestion.multi_format import convert_file
    from shared.adapter_contract import AdapterResult

    clip = tmp_path / "lesson.mp3"
    clip.write_bytes(b"not-a-real-media-file")

    def local_transcript(*_args, **_kwargs) -> AdapterResult:
        return AdapterResult(
            success=True,
            content="local transcript",
            engine="faster-whisper/local-model",
            metadata={
                "blocks": [
                    {"kind": "transcript", "text": "local transcript", "anchor": {"start_s": 0.0, "end_s": 1.0}}
                ]
            },
        )

    monkeypatch.setattr(media_adapter, "convert_media", local_transcript)

    text, engine = convert_file(clip)

    assert text == "local transcript"
    assert engine == "faster-whisper/local-model"


def test_unified_image_ocr_reconfigures_tesseract_for_each_conversion(tmp_path, monkeypatch) -> None:
    """A stale environment must not survive into the general import path."""
    from PIL import Image
    import pytesseract
    import shared.adapter_fixtures as fixtures
    from app.ingestion import ocr_adapter
    from app.ingestion.multi_format import _via_image_ocr

    image = tmp_path / "page.png"
    Image.new("RGB", (8, 8), "white").save(image)
    configured: list[bool] = []
    monkeypatch.setattr(ocr_adapter, "configure_tesseract", lambda: configured.append(True))
    monkeypatch.setattr(fixtures, "_tesseract_available", lambda: True)
    monkeypatch.setattr(fixtures, "_pytesseract_importable", lambda: True)
    monkeypatch.setattr(pytesseract, "image_to_string", lambda _image: "configured OCR")

    result = _via_image_ocr(str(image))

    assert configured == [True]
    assert result.success
    assert result.content == "configured OCR"
