from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/ArcheAxis.Desktop"
XNAME = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"


def test_home_page_heading_and_actions_are_visible_before_b10_dashboard():
    xaml = ET.parse(APP / "MainWindow.axaml").getroot()
    named = {node.get(XNAME): node for node in xaml.iter() if node.get(XNAME)}
    code = (APP / "MainWindow.axaml.cs").read_text(encoding="utf-8")

    assert "WorkspaceHeadingBar" in named
    assert "HomePageDescription" in named
    assert "HomePageActions" in named
    assert "WorkspaceHeadingBar.IsVisible = true;" in code
    assert "HomePageDescription.IsVisible = section == \"home\";" in code
    assert "HomePageActions.IsVisible = section == \"home\";" in code
    assert "HomeStatsSurface" in named
    assert "HomeWelcomeHero" not in named
