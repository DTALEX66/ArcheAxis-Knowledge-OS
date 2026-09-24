"""AAOS motion tokens are connected to accessible desktop state feedback."""

from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
THEME_XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "Themes" / "AaosTheme.axaml"


def _theme_root() -> ET.Element:
    return ET.parse(THEME_XAML).getroot()


def _style(root: ET.Element, selector: str) -> ET.Element:
    return next(
        element
        for element in root.iter()
        if element.tag.endswith("Style") and element.get("Selector") == selector
    )


def _setter(style: ET.Element, property_name: str) -> ET.Element:
    return next(
        element
        for element in style
        if element.tag.endswith("Setter") and element.get("Property") == property_name
    )


def test_loading_status_consumes_emphasis_motion_and_reduced_motion_stays_visible() -> None:
    root = _theme_root()
    resources = {
        element.get("{http://schemas.microsoft.com/winfx/2006/xaml}Key"): element.text
        for element in root.iter()
        if element.get("{http://schemas.microsoft.com/winfx/2006/xaml}Key")
    }

    assert resources["AaosMotionFastMs"] == "120"
    assert resources["AaosMotionStandardMs"] == "180"
    assert resources["AaosMotionEmphasisMs"] == "280"
    assert resources["AaosMotionRevealMs"] == "420"

    loading = _style(root, "TextBlock.status-loading")
    assert _setter(loading, "Foreground").get("Value") == "{DynamicResource AaosInfoBrush}"
    loading_opacity = float(_setter(loading, "Opacity").get("Value", "0"))
    assert 0.0 < loading_opacity < 1.0
    loading_transition = next(
        element
        for element in _setter(loading, "Transitions").iter()
        if element.tag.endswith("DoubleTransition") and element.get("Property") == "Opacity"
    )
    assert loading_transition.get("Duration") == "0:0:0.28"

    reduced = _style(root, "Grid.reduced-motion TextBlock.status-loading")
    assert _setter(reduced, "Opacity").get("Value") == "1"
    reduced_transitions = _setter(reduced, "Transitions")
    assert not any(element.tag.endswith("DoubleTransition") for element in reduced_transitions.iter())
