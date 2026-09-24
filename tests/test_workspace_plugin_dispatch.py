"""P1 regression tests for the workspace intake plugin dispatch seam."""

from __future__ import annotations

from pathlib import Path

from app.capability.builtin import activate_all_builtins
from app.capability.conversion import ConversionDispatcher, FileConverter, reset_active_converters
from app.capability.store import CapabilityStore
from app.ingestion.multi_format import ConversionTrace
from app.workspace import service
from shared.adapter_contract import AdapterResult


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
    dispatcher.get_converter = lambda _plugin_id: FileConverter(
        plugin_id="ax.builtin.converter.html",
        name="test HTML converter",
        convert=lambda _source, _options=None: AdapterResult(
            success=True,
            content="The active builtin converter owns this extraction.",
            engine="html-adapter",
        ),
    )
    monkeypatch.setattr(service, "_get_conversion_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(
        service,
        "convert_file_with_trace",
        lambda _source: (_ for _ in ()).throw(AssertionError("fallback chain was used")),
    )

    try:
        content, engine, trace, provenance = service._convert_file_for_intake(
            source, include_plugin_provenance=True
        )
        legacy_content, legacy_engine, legacy_trace = service._convert_file_for_intake(
            source
        )
    finally:
        reset_active_converters()

    assert "active builtin converter" in content
    assert engine == "html-adapter"
    assert trace.attempted_engines == ("plugin:ax.builtin.converter.html",)
    assert trace.fallback_used is False
    assert provenance == {
        "id": "ax.builtin.converter.html",
        "version": "1.0.0",
        "content_hash": dispatcher.installed_provenance(
            "ax.builtin.converter.html"
        )["content_hash"],
    }
    assert legacy_content and legacy_engine == "html-adapter"
    assert legacy_trace.fallback_used is False


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

    content, engine, trace, provenance = service._convert_file_for_intake(
        source, include_plugin_provenance=True
    )
    assert (content, engine, trace, provenance) == (
        "fallback content",
        "safe-http+raw",
        expected,
        None,
    )


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
