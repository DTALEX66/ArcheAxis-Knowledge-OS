import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "ArcheAxis.Desktop"
XNAME = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"


def test_home_heading_bar_remains_visible_before_b10_dashboard():
    root = ET.parse(APP / "MainWindow.axaml").getroot()
    named = {node.get(XNAME): node for node in root.iter() if node.get(XNAME)}
    scroll = named["WorkspaceScrollViewer"]
    content = next(node for node in scroll if named["WorkspaceHeadingBar"] in list(node))

    assert list(content).index(named["WorkspaceHeadingBar"]) < list(content).index(named["HomeSurface"])
    assert named["WorkspaceHeadingText"].get("Text") == "首页"
    assert named["HomePageDescription"].get("IsVisible") != "False"
    assert named["HomePageActions"].get("IsVisible") != "False"
    assert "HomeWelcomeHero" not in named
    assert named["HomeStatsSurface"] in list(named["HomeSurface"])

    source = (APP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    start = source.index("private void SetSection(string section, string heading)")
    end = source.index("private ", start + len("private void SetSection(string section, string heading)"))
    method = source[start:end]

    assert "WorkspaceHeadingText.Text = displayHeading;" in method
    assert "HomePageDescription.IsVisible = section == \"home\";" in method
    assert "WorkspaceHeadingBar.IsVisible = true;" in method
    assert "WorkspaceHeadingBar.IsVisible = section != \"home\";" not in method
    assert "HomePageActions.IsVisible = section == \"home\";" in method
