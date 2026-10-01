import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosMemoryGraphView.axaml"
CODE_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosMemoryGraphView.axaml.cs"


def test_memory_graph_hover_and_filter_highlight_only_the_schematic_neighbors() -> None:
    xaml = ET.parse(XAML_PATH).getroot()
    code = CODE_PATH.read_text(encoding="utf-8")
    canvas = next(node for node in xaml.iter() if node.tag.endswith("Canvas"))
    edges_block = re.search(r"MasterEdges\s*=\s*\[(.*?)\];", code, re.S)
    assert edges_block is not None
    edges = re.findall(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", edges_block.group(1))

    assert len(edges) >= 36
    assert all(source != target for source, target in edges)
    assert "静态示意" in canvas.attrib.get("AutomationProperties.HelpText", "")
    assert "不代表 Core 条目或关系" in canvas.attrib.get("AutomationProperties.HelpText", "")
    assert "public void SetRelationFilter(string? nodeName)" in code
    assert "_hoveredNode = node" in code and "_focusedNode = node" in code
    assert "UpdateRelationHighlight();" in code
    assert "edge.Stroke = isRelated && activeIndex >= 0" in code
    assert "node.Opacity = activeIndex < 0" in code
    assert "ThemePalette.PaletteChanged += OnPaletteChanged;" in code


def test_memory_graph_reduced_motion_disables_highlight_transitions_and_graph_motion() -> None:
    code = CODE_PATH.read_text(encoding="utf-8")
    assert "node.Transitions = reducedMotion ? new Transitions() : null;" in code
    assert "if (_reducedMotion || !_motionActive || !IsVisible)" in code
    assert "_pulseTimer.Stop();" in code
    assert "_motionElapsedSeconds = 0;" in code
