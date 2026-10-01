from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"


def test_capture_uses_compact_input_tabs_and_core_receipt_list() -> None:
    root = ET.parse(VIEW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    names = {node.get(xname): node for node in root.iter() if node.get(xname)}
    capture = names["CaptureSurface"]
    assert names["CaptureTypeGrid"].get("ColumnDefinitions") == "Auto,Auto,Auto,Auto,Auto,Auto"
    code = (ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    assert 'var captureCompact = contentWidth < 760;' in code
    assert 'new ColumnDefinitions("1*")' in code
    assert names["CaptureDraftBox"].get("AcceptsReturn") == "True"
    assert names["CaptureSaveButton"].get("IsEnabled") == "False"
    assert names["CaptureRecentList"] in list(capture.iter())
    for name in ("CaptureDocumentButton", "CaptureImageButton", "CaptureAudioButton"):
        assert name in names
    assert "web/link/note" in names["CaptureUnavailableModesText"].get("Text", "").lower()


def test_search_filter_row_does_not_render_unavailable_unlabeled_dropdowns() -> None:
    root = ET.parse(VIEW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    names = {node.get(xname): node for node in root.iter() if node.get(xname)}
    search = names["SearchSurface"]
    assert names["SearchPageFiltersStatus"].get("Text")
    for name in ("SearchPageSourceFilter", "SearchPageTopicFilter", "SearchPageTimeFilter"):
        assert names[name].get("IsVisible") == "False"
    assert names["SearchPageQueryBox"].get("MinHeight") == "48"
    assert names["SearchPageResultsList"] in list(search.iter())
    assert names["SearchResultsHeaderGrid"].get("ColumnDefinitions") == "*,*,*,*,*"
