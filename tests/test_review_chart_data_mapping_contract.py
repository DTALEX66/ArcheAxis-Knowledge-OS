from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosReviewScheduleChart.axaml"
CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosReviewScheduleChart.axaml.cs"


def test_review_chart_maps_only_received_projection_values() -> None:
    code = CODE.read_text(encoding="utf-8")

    assert "IReadOnlyList<ReviewScheduleDay>" in code
    assert "record ReviewScheduleDay(DateOnly Day, int DueCount)" in code
    assert "points.Max(point => point.DueCount)" in code
    assert "point.DueCount / (double)maximum" in code
    assert "new ReviewScheduleDay" not in code
    assert "Enumerable.Range" not in code


def test_review_chart_keeps_theme_aware_empty_state_legend_and_date_axis() -> None:
    root = ET.parse(VIEW).getroot()
    xml = VIEW.read_text(encoding="utf-8")
    code = CODE.read_text(encoding="utf-8")
    names = {
        node.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name")
        for node in root.iter()
    }

    assert "EmptyState" in names
    assert "ScheduleBarsCanvas" in names
    assert "TimelineAxis" in names
    assert "图例" in xml or "排程卡片" in xml
    assert 'ThemePalette.ResolveBrush("AaosPrimaryBrush")' in code
    assert "{DynamicResource AaosBorderBrush}" in xml
    assert "暂无排程数据" in xml
    assert "Text=\"今天\"" in xml
    assert "today.AddDays(dayOffset)" in code
    assert 'date.ToString("ddd", CultureInfo.CurrentCulture)' in code
