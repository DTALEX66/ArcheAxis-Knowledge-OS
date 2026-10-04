"""The formal shell preserves user-authorized palettes and theme bindings."""
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


def test_every_palette_resolves_the_glass_and_content_brushes():
    tables = [_palette_colors(name) for name in ("Ivory", "Monochrome", "Aurora")]
    assert all(set(table) == set(tables[0]) for table in tables)
    for table in tables:
        assert {"AaosGlassBrush", "AaosGlassRimBrush", "AaosHeroTextBrush", "AaosHeroMutedBrush",
                "AaosPrimaryTextBrush", "AaosErrorBrush", "AaosMutedBrush"} <= table.keys()


def test_primary_action_label_contrast_survives_every_palette_and_hover():
    def luminance(hex_color):
        channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4 for channel in channels]
        return sum(channel * weight for channel, weight in zip(linear, (.2126, .7152, .0722)))
    for name in ("Ivory", "Monochrome", "Aurora"):
        palette = _palette_colors(name)
        values = sorted([luminance(palette["AaosPrimaryBrush"]), luminance(palette["AaosPrimaryTextBrush"])])
        assert (values[1] + .05) / (values[0] + .05) >= 4.5, name
    theme = ET.parse(THEME).getroot()
    hover = next(node for node in theme if node.get("Selector") == "Button.primary-action:pointerover")
    assert any(node.get("Property") == "Foreground" and node.get("Value") == "{DynamicResource AaosPrimaryTextBrush}" for node in hover)


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
    assert aurora["AaosBackgroundBrush"] == "#081020"
    assert aurora["AaosPrimaryBrush"] == "#2EC4B6"
    assert aurora["AaosIvoryBrush"] == "#F8F6EB"
    assert _brushes()["AaosBackgroundBrush"] == aurora["AaosBackgroundBrush"]
    palette_code = PALETTE.read_text(encoding="utf-8")
    assert "Ivory => IvoryColors" in palette_code
    assert "Monochrome => MonochromeColors" in palette_code
    assert "resources[key] = new SolidColorBrush(Color.Parse(value));" in palette_code
    shell = (PALETTE.parent / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    assert "ThemePalette.Apply(ThemePalette.Aurora);" in shell
    assert "SettingsThemePaletteBox.SelectionChanged += OnThemePaletteChanged;" in shell


def test_aurora_effects_and_navigation_gradients_follow_current_brand_tokens() -> None:
    aurora = _palette_colors("Aurora")
    theme = THEME.read_text(encoding="utf-8")
    palette_code = PALETTE.read_text(encoding="utf-8")
    assert aurora["AaosGoldBrush"] == "#F4D08B"
    assert aurora["AaosSurface2Brush"] == "#1A2233"
    assert aurora["AaosAmbientStart"] == aurora["AaosPrimaryBrush"]
    assert aurora["AaosBrandMarkEnd"] == aurora["AaosPrimaryBrush"]
    assert aurora["AaosAmbientSecondaryBrush"] == "#55F4D08B"
    assert 'Aurora => "#66F4D08B"' in palette_code
    assert 'Ivory => "#449A6F21"' in palette_code
    for old_color in ("#1FC8C5", "#8DC398", "#14343D", "#102630", "#061118"):
        assert old_color not in theme
