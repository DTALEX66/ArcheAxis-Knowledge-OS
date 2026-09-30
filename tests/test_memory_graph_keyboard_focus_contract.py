import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "Themes" / "AaosTheme.axaml"
GRAPH_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosMemoryGraphView.axaml.cs"


def test_keyboard_focused_memory_graph_node_gets_themed_stroke_and_glow() -> None:
    root = ET.parse(THEME_PATH).getroot()
    styles = [node for node in root.iter() if node.tag.endswith("Style")]
    focus_style = next(
        (node for node in styles if node.get("Selector") == "Button.aaos-graph-node.focus-visible Ellipse"),
        None,
    )

    assert focus_style is not None, "keyboard-focused graph nodes need their own ellipse treatment"
    setters = [node for node in focus_style.iter() if node.tag.endswith("Setter")]
    assert any(node.get("Property") == "Stroke" and node.get("Value") == "{DynamicResource AaosPrimaryBrush}" for node in setters)
    assert any(node.get("Property") == "StrokeThickness" and node.get("Value") == "3" for node in setters)
    assert any(node.tag.endswith("DropShadowEffect") for node in focus_style.iter())
    assert 'node.Classes.Set("focus-visible", true);' in GRAPH_PATH.read_text(encoding="utf-8")


def test_graph_focus_reuses_existing_reduced_motion_transition_suppression() -> None:
    root = ET.parse(THEME_PATH).getroot()
    styles = [node for node in root.iter() if node.tag.endswith("Style")]
    reduced = next(
        (node for node in styles if node.get("Selector") == "Grid.reduced-motion Button.aaos-graph-node"),
        None,
    )
    assert reduced is not None
    transitions = [node for node in reduced.iter() if node.tag.endswith("Transitions")]
    assert transitions and len(list(transitions[0])) == 0
