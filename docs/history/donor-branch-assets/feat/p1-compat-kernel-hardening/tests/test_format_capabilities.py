from __future__ import annotations

from app.ingestion.multi_format import format_capabilities


def test_format_capabilities_do_not_overclaim_images_or_media() -> None:
    report = format_capabilities()

    assert report["md"]["status"] == "ready"
    assert report["txt"]["status"] == "ready"
    assert report["json"]["status"] == "ready"
    assert report["canvas"]["status"] == "degraded"
    assert report["image"]["status"] == "metadata_only"
    assert report["media_audio"]["status"] in {"metadata_only", "missing_dependency"}
    assert report["media_video"]["status"] in {"metadata_only", "missing_dependency"}
    assert "OCR" in str(report["image"]["reason"])
    assert "ASR" in str(report["media_audio"]["reason"])


def test_document_capabilities_expose_missing_dependencies_or_degraded_state() -> None:
    report = format_capabilities()

    for fmt in ("pdf", "docx", "pptx", "xlsx", "csv"):
        assert report[fmt]["status"] in {"degraded", "missing_dependency"}
        assert report[fmt]["engine"] == "markitdown"
        assert isinstance(report[fmt]["missing_modules"], list)
