import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "apps/ArcheAxis.Desktop/AaosIcon.axaml.cs"
XAML = ROOT / "apps/ArcheAxis.Desktop/AaosIcon.axaml"


def geometries():
    source = CODE.read_text(encoding="utf-8")
    return dict(re.findall(r'^\s*\["([^"]+)"\]\s*=\s*"([^"]+)"', source, re.M))


def test_growth_icon_uses_four_independent_rising_bars_without_a_baseline():
    growth = geometries()["Growth"]
    assert "M2,21 L22,21" not in growth
    assert all(token in growth for token in ("M3,19 L3,14", "M8,19 L8,11", "M13,19 L13,8", "M18,19 L18,4"))


def test_connection_icon_has_three_linked_nodes_and_no_central_hub():
    connection = geometries()["Connection"]
    assert "M12,14" not in connection
    assert all(token in connection for token in ("M12,2 A2,2", "M6,16 A2,2", "M18,16 A2,2"))
    assert connection.count(" A2,2") == 6  # two arcs draw each closed node
    assert "M12,4 L4,18 L20,18 Z" not in connection


def test_thinking_icon_matches_lamp_and_circular_head_motif():
    thinking = geometries()["Thinking"]
    assert "M12,2 A9,9 0 1,1 12,20" in thinking
    assert "M12,6 L12,11" in thinking
    assert "M10,9 L12,11 L14,9" in thinking


def test_navigation_dot_is_a_small_filled_state_marker_without_icon_circle_outline_control():
    code = CODE.read_text(encoding="utf-8")
    xaml = XAML.read_text(encoding="utf-8")
    assert '["NavigationDot"] = "M9,12 A3,3 0 1,1 15,12 A3,3 0 1,1 9,12 Z"' in code
    assert 'IconPath.Fill = isNavigationDot ? Foreground : Brushes.Transparent;' in code
    assert 'x:Name="NavigationDotShape"' not in xaml
