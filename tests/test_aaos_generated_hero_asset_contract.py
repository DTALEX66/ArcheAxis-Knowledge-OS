import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "ArcheAxis.Desktop"


def test_home_uses_cosmic_planet_artwork_and_keeps_the_graph_distinct():
    xaml = (APP / "MainWindow.axaml").read_text(encoding="utf-8")
    code = (APP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    graph = (APP / "AaosMemoryGraphView.axaml.cs").read_text(encoding="utf-8")
    root = ET.fromstring(xaml)
    assert 'x:Name="HomePlanetHero"' in xaml
    assert 'home-planet-hero-20261001.png' in xaml
    assert (APP / "Assets/home-planet-hero-20261001.png").is_file()
    assert (APP / "Assets/home-planet-hero-monochrome-20261001.png").is_file()
    assert 'home-planet-hero-monochrome-20261001.png' in code
    assert any(node.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name") == "HomeHeroVisual" and node.tag.endswith("}AaosMemoryGraphView") for node in root.iter())
    assert "HomeHeroVisual.UseB10HomeLayout();" in code
    assert "B10HomeNodes" in graph and "B10HomeEdges" in graph


def test_home_artwork_keeps_the_core_data_boundary():
    xaml = (APP / "MainWindow.axaml").read_text(encoding="utf-8")
    graph_xaml = (APP / "AaosMemoryGraphView.axaml").read_text(encoding="utf-8")
    assert "Core 尚未提供节点与关系投影" in xaml
    assert "不代表 Core 条目或关系" in graph_xaml
