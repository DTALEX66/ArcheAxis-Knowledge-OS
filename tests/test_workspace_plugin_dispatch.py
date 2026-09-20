"""P1 regression tests for the workspace intake plugin dispatch seam."""

from __future__ import annotations

from pathlib import Path

from app.capability.builtin import activate_all_builtins
from app.capability.conversion import ConversionDispatcher, reset_active_converters
from app.capability.store import CapabilityStore
from app.ingestion.multi_format import ConversionTrace
from app.workspace import service


def _real_dispatcher(tmp_path: Path) -> ConversionDispatcher:
    store = CapabilityStore(tmp_path / "capabilities")
    activate_all_builtins(store)
    return ConversionDispatcher(store)


def test_intake_prefers_an_active_builtin_converter(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "article.html"
    source.write_text(
        "<html><head><title>Plugin route</title></head>"
        "<body><article><h1>Plugin route</h1>"
        "<p>The active builtin converter owns this extraction.</p>"
        "</article></body></html>",
        encoding="utf-8",
    )
    dispatcher = _real_dispatcher(tmp_path)
    monkeypatch.setattr(service, "_get_conversion_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(
        service,
        "convert_file_with_trace",
        lambda _source: (_ for _ in ()).throw(AssertionError("fallback chain was used")),
    )

    try:
        content, engine, trace = service._convert_file_for_intake(source)
    finally:
        reset_active_converters()

    assert "active builtin converter" in content
    assert engine == "html-adapter"
    assert trace.attempted_engines == ("plugin:ax.builtin.converter.html",)
    assert trace.fallback_used is False


def test_inactive_builtin_converter_preserves_existing_fallback_trace(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "article.html"
    source.write_text("<html><body>fallback input</body></html>", encoding="utf-8")
    dispatcher = ConversionDispatcher(CapabilityStore(tmp_path / "capabilities"))
    expected = ConversionTrace(
        attempted_engines=("trafilatura", "safe-http+raw"),
        fallback_used=True,
        fallback_reason="primary unavailable",
    )
    monkeypatch.setattr(service, "_get_conversion_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(
        service,
        "convert_file_with_trace",
        lambda _source: ("fallback content", "safe-http+raw", expected),
    )

    content, engine, trace = service._convert_file_for_intake(source)

    assert (content, engine, trace) == ("fallback content", "safe-http+raw", expected)


def test_plugin_failure_falls_back_without_leaking_source_path(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "article.html"
    source.write_text("<html><body>broken plugin input</body></html>", encoding="utf-8")
    dispatcher = _real_dispatcher(tmp_path)
    monkeypatch.setattr(service, "_get_conversion_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(
        service,
        "convert_file_with_trace",
        lambda _source: (
            "fallback content",
            "safe-http+raw",
            ConversionTrace(
                attempted_engines=("safe-http+raw",),
                fallback_used=False,
            ),
        ),
    )

    # A plugin error must be converted into a path-free fallback trace.  The
    # malformed/empty adapter result is supplied by the real HTML plugin.
    source.write_text("", encoding="utf-8")
    try:
        content, engine, trace = service._convert_file_for_intake(source)
    finally:
        reset_active_converters()

    assert content == "fallback content"
    assert engine == "safe-http+raw"
    assert trace.fallback_used is True
    assert trace.attempted_engines == (
        "plugin:ax.builtin.converter.html",
        "safe-http+raw",
    )
    assert trace.fallback_reason == "plugin ax.builtin.converter.html failed; built-in chain used"
    assert str(source) not in (trace.fallback_reason or "")
