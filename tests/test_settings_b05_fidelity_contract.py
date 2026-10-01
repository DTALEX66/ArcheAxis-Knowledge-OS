from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_VIEW = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"


def _named_elements():
    root = ET.parse(MAIN_VIEW).getroot()
    xaml_name = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    return {
        element.get(xaml_name): element
        for element in root.iter()
        if element.get(xaml_name)
    }


def test_settings_b05_uses_eight_two_column_cards_with_mother_spacing():
    names = _named_elements()
    grid = names["SettingsControlsGrid"]

    assert grid.get("ColumnDefinitions") == "*,*"
    assert grid.get("ColumnSpacing") == "60"
    assert grid.get("RowSpacing") == "40"
    cards = [child for child in list(grid) if child.tag.endswith("Border")]
    assert len(cards) == 8
    assert all(card.get("MinHeight") == "120" for card in cards)
    assert all(card.get("Padding") in {"24", "28"} for card in cards)


def test_unavailable_settings_keep_unknown_disabled_state_and_explain_it_visually():
    names = _named_elements()
    grid = names["SettingsControlsGrid"]
    unavailable_switches = [
        switch
        for switch in grid.iter()
        if switch.tag.endswith("ToggleSwitch")
    ]

    assert len(unavailable_switches) == 7
    for switch in unavailable_switches:
        assert switch.get("IsEnabled") == "False"
        assert switch.get("IsChecked") == "{x:Null}"
        assert switch.get("IsThreeState") == "True"
        assert switch.get("OffContent") in (None, "")
        parent = next(element for element in grid.iter() if switch in list(element))
        assert any(
            element.tag.endswith("TextBlock")
            and "CORE 未接入" in (element.get("Text") or "")
            for element in parent.iter()
        )
        assert any(
            element.tag.endswith("Border")
            and "settings-availability" in (element.get("Classes") or "")
            for element in parent.iter()
        )


def test_settings_theme_selector_and_narrow_layout_contract_remain_available():
    names = _named_elements()
    grid = names["SettingsControlsGrid"]
    assert names["SettingsThemePaletteBox"] in list(grid.iter())
    code = (ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    assert "SettingsThemePaletteBox.SelectionChanged += OnThemePaletteChanged;" in code
    assert 'SettingsControlsGrid.ColumnDefinitions = contentWidth < 840 ? new ColumnDefinitions("*") : new ColumnDefinitions("*,*");' in code
    assert 'var settingsControlColumns = contentWidth < 840 ? 1 : 2;' in code
