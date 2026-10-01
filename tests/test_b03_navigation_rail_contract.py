import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"


def test_primary_navigation_matches_b10_labeled_rail_and_topbar():
    root = ET.parse(XAML).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    frame = next(node for node in root.iter() if node.get(xname) == "MainFrameGrid")
    rail = next(node for node in root.iter() if node.get(xname) == "PrimaryRail")
    topbar = next(node for node in root.iter() if node.get(xname) == "TopbarShell")
    code = CODE.read_text(encoding="utf-8")

    assert frame.get("ColumnDefinitions", "").startswith("280,0,*,0")
    assert rail.get("Width") == "280"
    assert rail.get("Grid.Row") == "0"
    assert rail.get("Grid.RowSpan") == "4"
    brand = next(node for node in rail.iter() if node.get(xname) == "PrimaryRailBrand")
    assert brand.get("Grid.Row") == "0"
    assert any(node.get("Text") == "ArcheAxis" for node in brand.iter())
    assert topbar.get("Grid.Row") == "0"
    assert topbar.get("Grid.ColumnSpan") == "4"
    assert 'private const double MasterSidebarWidth = 280d;' in code
    assert 'PrimaryRail.IsVisible = !mobile;' in code
    assert 'MobileRail.IsVisible = mobile;' in code


def test_all_primary_routes_keep_hidden_visual_labels_and_accessible_names():
    root = ET.parse(XAML).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    rail = next(node for node in root.iter() if node.get(xname) == "PrimaryRail")
    names = ["RailWorkspaceButton", "RailCaptureButton", "RailEvidenceButton", "RailOriginalsButton",
             "RailLearningButton", "RailMachineButton", "RailWorkspaceTreeButton", "RailMemoryMapButton",
             "RailSearchButton", "RailReviewButton", "RailSystemButton"]
    buttons = {node.get(xname): node for node in rail.iter() if node.get(xname)}

    for name in names:
        button = buttons[name]
        assert "master-nav-button" in button.get("Classes", "")
        assert "icon-rail-button" not in button.get("Classes", "")
        assert any("b10-nav-dot" in node.get("Classes", "").split() for node in button.iter())
        assert any(node.get("Text") for node in button.iter() if node.tag.endswith("}TextBlock"))
        assert button.get("AutomationProperties.Name")
        assert button.get("ToolTip.Tip")
