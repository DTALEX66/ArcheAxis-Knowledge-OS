"""B05 presentation contract for the formal machine-learning page."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_VIEW = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"
MAIN_CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs"
XAML_NAME = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"


def _named(root: ET.Element, name: str) -> ET.Element:
    return next(node for node in root.iter() if node.get(XAML_NAME) == name)


def test_machine_learning_navigation_and_route_title_use_b05_name() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    menu = _named(root, "NavigateMachineMenuItem")
    rail = _named(root, "RailMachineButton")
    mobile = _named(root, "MobileMachineButton")
    code = MAIN_CODE.read_text(encoding="utf-8")

    assert menu.get("Header") == "机器学习"
    assert menu.get("AutomationProperties.Name") == "导航到机器学习"
    assert rail.get("ToolTip.Tip") == "机器学习"
    assert rail.get("AutomationProperties.Name") == "打开机器学习"
    assert mobile.get("AutomationProperties.Name") == "打开机器学习"
    assert 'SetSection("machine-growth", "机器学习")' in code
    assert 'SetNavigationMenuState(NavigateMachineMenuItem, section == "machine-growth", "机器学习")' in code


def test_machine_learning_trend_uses_empty_b05_grid_without_sample_series() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    machine = _named(root, "MachineKnowledgeSurface")
    trend = _named(machine, "MachineTrendChart")
    gridlines = [node for node in trend.iter() if "machine-trend-gridline" in node.get("Classes", "").split()]
    trend_text = " ".join(node.get("Text", "") for node in machine.iter())

    assert trend.get("MinHeight") == "420"
    assert len(gridlines) == 4
    assert [node.get("Grid.Row") for node in gridlines] == ["0", "1", "2", "3"]
    assert "MachineTrendStatusText" in {node.get(XAML_NAME) for node in machine.iter()}
    assert "Core 尚未提供历史指标" in trend_text
    assert _named(machine, "MachineTrendStatusText").get("HorizontalAlignment") == "Center"
    assert not any(node.tag.endswith(("Path", "Polyline", "Polygon")) for node in trend.iter())


def test_machine_learning_dashboard_uses_adaptive_metrics_and_keeps_task_receipt_secondary() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    machine = _named(root, "MachineKnowledgeSurface")
    metrics = _named(machine, "MachineMetricGrid")
    cards = [node for node in metrics if node.tag.endswith("Border")]
    details = _named(machine, "MachineTaskReceiptDetails")
    task_grid = _named(machine, "MachineTaskGrid")
    code = MAIN_CODE.read_text(encoding="utf-8")

    assert len(cards) == 4
    assert details.tag.endswith("Expander")
    assert details.get("IsExpanded") == "False"
    assert task_grid in list(details.iter())
    assert "machineMetricContentWidth" in code
    assert "MachineMetricGrid.ItemWidth" in code
