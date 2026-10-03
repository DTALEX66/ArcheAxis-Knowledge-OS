import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "ArcheAxis.Desktop"


def test_home_memory_graph_matches_b10_six_node_layout():
    source = (APP / "AaosMemoryGraphView.axaml.cs").read_text(encoding="utf-8")
    nodes_block = re.search(r"B10HomeNodes\s*=\s*\[(.*?)\];", source, re.S)
    edges_block = re.search(r"B10HomeEdges\s*=\s*\[(.*?)\];", source, re.S)
    assert nodes_block and edges_block
    nodes = re.findall(r'new GraphNodeDefinition\("([^\"]+)",\s*([\d.]+),\s*([\d.]+)\)', nodes_block.group(1))
    edges = [tuple(map(int, pair)) for pair in re.findall(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", edges_block.group(1))]
    # The six master nodes are named in the product's own language; the layout they pin is
    # unchanged, so this only tracks the wording.
    assert {name for name, _, _ in nodes} == {"证据", "原文", "学习", "记忆", "工作区", "复习"}
    assert len(nodes) == 6
    assert edges == [(-1, 0), (-1, 1), (-1, 2), (-1, 3), (-1, 4), (-1, 5)]
    assert "UseB10HomeLayout()" in source
    assert "CanvasHeight / 100d" in source


def test_main_window_selects_b10_home_graph_but_keeps_b03_memory_map():
    code = (APP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    xaml = ET.parse(APP / "MainWindow.axaml").getroot()
    name = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    controls = {node.get(name): node for node in xaml.iter() if node.get(name)}
    assert "HomeHeroVisual.UseB10HomeLayout();" in code
    assert controls["HomeHeroVisual"].tag.endswith("AaosMemoryGraphView")
    assert controls["MemoryMapMotherGraph"].tag.endswith("AaosMemoryGraphView")
    assert "HomeHeroPlanetImage" not in (APP / "MainWindow.axaml").read_text(encoding="utf-8")
