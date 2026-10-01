"""The formal shell preserves both user-authorized palettes and theme bindings."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "apps" / "ArcheAxis.Desktop" / "Themes" / "AaosTheme.axaml"
PALETTE = ROOT / "apps" / "ArcheAxis.Desktop" / "ThemePalette.cs"


def _palette_colors(name: str) -> dict[str, str]:
    code = PALETTE.read_text(encoding="utf-8")
    match = re.search(rf'{name}Colors = new Dictionary<string, string>\s*\{{(.*?)\n    \}};', code, re.S)
    assert match is not None, name
    return dict(re.findall(r'\["([^"]+)"\] = "(#[A-Fa-f0-9]+)"', match.group(1)))


def _brushes() -> dict[str, str]:
    root = ET.parse(THEME).getroot()
    return {
        item.get("{http://schemas.microsoft.com/winfx/2006/xaml}Key"): item.get("Color")
        for item in root.iter()
        if item.tag.endswith("SolidColorBrush")
    }


def test_monochrome_palette_uses_black_white_surfaces_and_neutral_primary_actions() -> None:
    brushes = _palette_colors("Monochrome")

    assert brushes["AaosBackgroundBrush"] == "#080A0C"
    assert brushes["AaosSidebarBrush"] == "#101316"
    assert brushes["AaosSurfaceBrush"] == "#171A1D"
    assert brushes["AaosSurface2Brush"] == "#202428"
    assert brushes["AaosBorderBrush"] == "#3B4146"
    assert brushes["AaosPrimaryBrush"] == "#E1E4E6"
    assert brushes["AaosPrimaryTextBrush"] == "#101214"


def test_monochrome_remains_neutral_and_aurora_default_is_explicitly_selectable() -> None:
    forbidden = {"#1FC8C5", "#164B50", "#133B42", "#123C4A", "#8FC3A1"}
    assert {value.upper() for value in _palette_colors("Monochrome").values()}.isdisjoint(forbidden)
    aurora = _palette_colors("Aurora")
    assert aurora["AaosBackgroundBrush"] == "#061118"
    assert aurora["AaosPrimaryBrush"] == "#1FC8C5"
    assert aurora["AaosIvoryBrush"] == "#F3EFE6"
    assert _brushes()["AaosBackgroundBrush"] == aurora["AaosBackgroundBrush"]
    palette_code = PALETTE.read_text(encoding="utf-8")
    assert "palette == Monochrome ? MonochromeColors : AuroraColors" in palette_code
    assert "resources[key] = new SolidColorBrush(Color.Parse(value));" in palette_code
    shell = (PALETTE.parent / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    assert "ThemePalette.Apply(ThemePalette.Aurora);" in shell
    assert "SettingsThemePaletteBox.SelectionChanged += OnThemePaletteChanged;" in shell
