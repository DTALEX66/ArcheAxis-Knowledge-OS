import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "Themes" / "AaosTheme.axaml"


def test_global_button_brushes_follow_b10_nav_color_transition_timing() -> None:
    root = ET.parse(THEME_PATH).getroot()
    button_style = next(
        (node for node in root.iter() if node.tag.endswith("Style") and node.get("Selector") == "Button"),
        None,
    )
    assert button_style is not None
    transitions = next((node for node in button_style.iter() if node.tag.endswith("Transitions")), None)
    assert transitions is not None

    brush_transitions = [node for node in transitions if node.tag.endswith("BrushTransition")]
    assert {node.get("Property") for node in brush_transitions} == {"Background", "BorderBrush", "Foreground"}
    assert all(node.get("Duration") == "0:0:0.22" for node in brush_transitions)
    assert all(
        node.find("{https://github.com/avaloniaui}BrushTransition.Easing/{https://github.com/avaloniaui}SplineEasing") is not None
        for node in brush_transitions
    )


def test_reduced_motion_clears_global_button_brush_transitions() -> None:
    root = ET.parse(THEME_PATH).getroot()
    reduced_style = next(
        (node for node in root.iter() if node.tag.endswith("Style") and node.get("Selector") == "Grid.reduced-motion Button"),
        None,
    )
    assert reduced_style is not None
    transitions = next((node for node in reduced_style.iter() if node.tag.endswith("Transitions")), None)
    assert transitions is not None and len(transitions) == 0
