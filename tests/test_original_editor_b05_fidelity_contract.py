from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"
NS = {"x": "http://schemas.microsoft.com/winfx/2006/xaml"}
NAME = f"{{{NS['x']}}}Name"


def _nodes() -> dict[str, ET.Element]:
    root = ET.parse(XAML).getroot()
    return {node.get(NAME): node for node in root.iter() if node.get(NAME)}


def test_original_editor_keeps_mother_composition_with_document_and_reference_rail() -> None:
    nodes = _nodes()
    surface = nodes["OriginalEditorSurface"]
    grid = nodes["OriginalEditorGrid"]
    assert grid.get("ColumnDefinitions") == "2.1*,1*"
    assert nodes["OriginalDocumentCard"] in list(grid.iter())
    assert nodes["OriginalReferenceRail"] in list(grid.iter())
    assert list(grid).index(nodes["OriginalDocumentCard"]) < list(grid).index(nodes["OriginalReferenceRail"])
    assert not any("写作、引用证据、版本、AI 辅助和发布" in n.get("Text", "") for n in surface.iter())


def test_original_editor_toolbar_is_iconic_but_truthfully_disabled() -> None:
    nodes = _nodes()
    toolbar = nodes["OriginalEditorFormatToolbar"]
    buttons = [node for node in toolbar.iter() if node.tag.endswith("Button")]
    assert len(buttons) >= 4
    assert all(node.get("IsEnabled") == "False" for node in buttons)
    names = " ".join(node.get("AutomationProperties.Name", "") for node in buttons)
    assert "标题格式" in names and "粗体" in names and "斜体" in names


def test_original_editor_title_and_body_form_one_read_only_document_canvas() -> None:
    nodes = _nodes()
    canvas = nodes["OriginalDocumentCanvas"]
    assert nodes["OriginalTitleBox"] in list(canvas.iter())
    assert nodes["OriginalEditorBodyBox"] in list(canvas.iter())
    assert nodes["OriginalTitleBox"].get("IsReadOnly") == "True"
    assert nodes["OriginalEditorBodyBox"].get("IsReadOnly") == "True"
    assert nodes["OriginalEditorBodyBox"].get("AcceptsReturn") == "True"


def test_original_editor_reference_and_version_panels_only_render_core_bound_data() -> None:
    nodes = _nodes()
    surface = nodes["OriginalEditorSurface"]
    assert nodes["OriginalEvidenceReferencesList"] in list(surface.iter())
    assert nodes["OriginalVersionHistoryList"] in list(surface.iter())
    text = " ".join(node.get("Text", "") for node in surface.iter() if node.tag.endswith("TextBlock"))
    assert "引用仅呈现 Core 绑定的 Evidence" in text
    assert "载入 Original 后显示真实版本" in text
    assert "示例引用" not in text and "版本 1" not in text
