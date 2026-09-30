"""The settings availability badge colors its label on the text control."""

import xml.etree.ElementTree as ET
from pathlib import Path

THEME = Path(__file__).resolve().parents[1] / "apps/ArcheAxis.Desktop/Themes/AaosTheme.axaml"


def test_settings_availability_foreground_targets_textblock() -> None:
    styles = {
        style.get("Selector"): {
            setter.get("Property"): setter.get("Value")
            for setter in style
            if setter.tag.endswith("Setter")
        }
        for style in ET.parse(THEME).getroot()
        if style.tag.endswith("Style")
    }

    assert "Foreground" not in styles["Border.settings-availability"]
    assert styles["Border.settings-availability TextBlock"]["Foreground"] == (
        "{DynamicResource AaosMutedBrush}"
    )
