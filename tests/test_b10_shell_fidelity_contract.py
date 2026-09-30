import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml"
BACKDROP = ROOT / "apps/ArcheAxis.Desktop/AaosBackdrop.cs"


def test_shell_uses_theme_aware_ambient_grid_and_b03_navigation_glyphs():
    xaml = WINDOW.read_text(encoding="utf-8")
    source = BACKDROP.read_text(encoding="utf-8")

    assert '<local:AaosBackdrop' in xaml
    assert 'Grid.RowSpan="4"' in xaml
    assert 'Grid.ColumnSpan="4"' in xaml
    assert 'x:Name="RailWorkspaceButton"' in xaml
    assert 'IconName="Home"' in xaml
    assert 'IconName="NavigationDot"' not in xaml
    assert "GridSpacing = 32" in source
    assert 'ResolveBrush("AaosGridBrush")' in source
    assert "DrawEllipse" in source
    assert "PushOpacityMask" in source


def test_collapsed_activity_dock_matches_the_motherboard_product_footer():
    xaml = WINDOW.read_text(encoding="utf-8")

    assert 'x:Name="ActivityDockBrandFooter"' in xaml
    assert 'Text="ArcheAxis · PRODUCT UI · LOCAL KNOWLEDGE WORKSPACE"' in xaml
    assert 'x:Name="ActivityDockMainContent"' in xaml


def test_settings_theme_picker_lives_inside_the_appearance_card():
    root = ET.fromstring(WINDOW.read_text(encoding="utf-8"))
    ns = {"x": "http://schemas.microsoft.com/winfx/2006/xaml"}
    controls = next(node for node in root.iter() if node.get(f"{{{ns['x']}}}Name") == "SettingsControlsGrid")
    appearance = next(node for node in controls.iter() if node.get(f"{{{ns['x']}}}Name") == "SettingsAppearanceCard")
    assert any(node.get(f"{{{ns['x']}}}Name") == "SettingsThemePaletteBox" for node in appearance.iter())
    assert "Core 未暴露；当前仅为界面占位。" not in "".join(controls.itertext())


def test_settings_unknown_values_are_not_rendered_as_false_toggles():
    root = ET.parse(WINDOW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    controls = next(node for node in root.iter() if node.get(xname) == "SettingsControlsGrid")
    switches = [node for node in controls.iter() if node.tag.endswith("ToggleSwitch")]
    text = ET.tostring(controls, encoding="unicode")

    assert len(switches) == 7
    assert all(node.get("IsChecked") == "{x:Null}" and node.get("IsEnabled") == "False" for node in switches)
    assert all(node.get("IsThreeState") == "True" for node in switches)
    assert all(node.get("OffContent") == node.get("OnContent") == "" for node in switches)
    assert text.count("CORE 未接入") == 7
    availability = [node for node in controls.iter() if "settings-availability" in node.get("Classes", "").split()]
    assert len(availability) == 7


def test_home_starts_with_b10_stats_evidence_and_graph_without_hero():
    root = ET.parse(WINDOW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    by_name = {node.get(xname): node for node in root.iter() if node.get(xname)}
    home = by_name["HomeSurface"]
    visible = [node.get(xname) for node in home if node.get("IsVisible") != "False"]
    assert visible[:3] == ["HomeStatsSurface", "HomeEvidenceContentGrid", "HomeGraphContentGrid"]
    assert by_name["HomePrimaryContentGrid"].get("IsVisible") == "False"
    assert "HomeWelcomeHero" not in by_name
    assert "HomeHeroPlanetImage" not in by_name
    assert by_name["HomeStatsSurface"].get("ColumnDefinitions") == "*,*,*,*"
    assert by_name["HomeEvidenceContentGrid"].get("ColumnDefinitions") == "1.2*,1*"
    assert by_name["HomeTodayProgressCard"].get("Grid.Column") == "1"
    assert by_name["HomeTodayProgressGrid"].get("IsVisible") == "True"
    assert [by_name[name].get("Grid.Column", "0") for name in ("HomeQuickCaptureCard", "HomeTodayFocusCard")] == ["0", "1"]


def test_topbar_matches_b10_fixed_height():
    xaml = (ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml").read_text(encoding="utf-8")
    b10 = (ROOT / "tests" / "fixtures" / "aaos-ui-mother" / "index.html").read_text(encoding="utf-8")
    assert 'x:Name="TopbarShell"' in xaml and 'MinHeight="78"' in xaml
    assert re.search(r"\.topbar\s*\{[^}]*height\s*:\s*78px", b10, re.S)
