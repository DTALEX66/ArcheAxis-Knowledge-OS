from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosReviewScheduleChart.axaml"
CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosReviewScheduleChart.axaml.cs"


def test_review_schedule_chart_has_no_synthetic_schedule_bars() -> None:
    root = ET.parse(VIEW).getroot()
    bars = [node for node in root.iter() if "review-schedule-bar" in node.get("Classes", "").split()]
    text_blocks = [node.get("Text", "") for node in root.iter() if node.tag.endswith("TextBlock")]

    assert root.get("{http://schemas.microsoft.com/winfx/2006/xaml}Class") == "ArcheAxis.Desktop.AaosReviewScheduleChart"
    assert bars == []
    assert "暂无排程数据" in text_blocks
    assert "Core 未提供未来复习数量；收到真实排程后在此显示。" in text_blocks
    plot = next(node for node in root.iter() if node.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name") == "PlotGrid")
    vertical_guides = [node for node in plot if node.tag.endswith("Border") and node.get("Grid.RowSpan") == "4" and node.get("BorderThickness") == "0,0,1,0"]
    horizontal_guides = [node for node in plot if node.tag.endswith("Border") and node.get("Grid.ColumnSpan") == "7" and node.get("BorderThickness") == "0,0,0,1"]
    assert len(vertical_guides) == 7
    assert len(horizontal_guides) == 4
    assert not any(node.tag.endswith(("Polyline", "Path", "TextBox")) for node in root.iter())
    assert not re.search(r"\b(?:19|20)\d{2}[-/.年]", " ".join(text_blocks))


def test_review_schedule_chart_uses_theme_resources_and_scales_inside_clip() -> None:
    root = ET.parse(VIEW).getroot()
    xml = VIEW.read_text(encoding="utf-8")
    names = {node.tag.rsplit("}", 1)[-1] for node in root.iter()}

    assert "Grid" in names
    assert "PlotGrid" in {node.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name") for node in root.iter()}
    assert "ClipToBounds=\"True\"" in xml or "ClipToBounds=\"true\"" in xml
    assert "{DynamicResource AaosPrimaryBrush}" in xml
    assert "{DynamicResource AaosBorderBrush}" in xml


def test_review_schedule_chart_automation_name_states_no_review_history_data() -> None:
    root = ET.parse(VIEW).getroot()
    name = root.get("AutomationProperties.Name", "")
    code = CODE.read_text(encoding="utf-8")

    assert "尚未收到 Core 排程数据" in name
    assert "AaosReviewScheduleChart" in code
