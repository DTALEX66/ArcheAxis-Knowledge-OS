import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "ArcheAxis.Desktop"


def test_home_uses_b10_graph_instead_of_planet_orbit_artwork():
    xaml = (APP / "MainWindow.axaml").read_text(encoding="utf-8")
    code = (APP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    graph = (APP / "AaosMemoryGraphView.axaml.cs").read_text(encoding="utf-8")
    root = ET.fromstring(xaml)
    assert "HomeHeroPlanetImage" not in xaml
    assert "AaosHomeHeroOrbit" not in xaml
    assert any(node.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name") == "HomeHeroVisual" and node.tag.endswith("}AaosMemoryGraphView") for node in root.iter())
    assert "HomeHeroVisual.UseB10HomeLayout();" in code
    assert "B10HomeNodes" in graph and "B10HomeEdges" in graph
    assert "aaos-home-hero-" not in xaml + code


def test_home_artwork_keeps_the_core_data_boundary():
    xaml = (APP / "MainWindow.axaml").read_text(encoding="utf-8")
    graph_xaml = (APP / "AaosMemoryGraphView.axaml").read_text(encoding="utf-8")
    assert "Core 尚未提供节点与关系投影" in xaml
    assert "不代表 Core 条目或关系" in graph_xaml
