"""The formal Avalonia shell follows the current monochrome visual authority."""
from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "apps" / "ArcheAxis.Desktop" / "Themes" / "AaosTheme.axaml"


def _brushes() -> dict[str, str]:
    root = ET.parse(THEME).getroot()
    return {
        item.get("{http://schemas.microsoft.com/winfx/2006/xaml}Key"): item.get("Color")
        for item in root.iter()
        if item.tag.endswith("SolidColorBrush")
    }


def test_formal_shell_uses_black_white_surfaces_and_neutral_primary_actions() -> None:
    brushes = _brushes()

    assert brushes["AaosBackgroundBrush"] == "#080A0C"
    assert brushes["AaosSidebarBrush"] == "#101316"
    assert brushes["AaosSurfaceBrush"] == "#171A1D"
    assert brushes["AaosSurface2Brush"] == "#202428"
    assert brushes["AaosBorderBrush"] == "#3B4146"
    assert brushes["AaosPrimaryBrush"] == "#E1E4E6"
    assert brushes["AaosPrimaryTextBrush"] == "#101214"


def test_default_shell_surfaces_do_not_reintroduce_saturated_green_or_cyan() -> None:
    root = ET.parse(THEME).getroot()
    forbidden = {"#1FC8C5", "#164B50", "#133B42", "#123C4A", "#8FC3A1"}
    colors = {
        value.upper()
        for element in root.iter()
        for attribute, value in element.attrib.items()
        if attribute in {"Color", "Background", "Foreground", "BorderBrush"}
        and value.startswith("#")
    }

    assert colors.isdisjoint(forbidden)
