import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"


def test_primary_navigation_matches_current_mother_icon_rail_and_topbar():
    root = ET.parse(XAML).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    frame = next(node for node in root.iter() if node.get(xname) == "MainFrameGrid")
    rail = next(node for node in root.iter() if node.get(xname) == "PrimaryRail")
    topbar = next(node for node in root.iter() if node.get(xname) == "TopbarShell")
    code = CODE.read_text(encoding="utf-8")

    assert frame.get("ColumnDefinitions", "").startswith("84,0,*,0")
    assert rail.get("Width") == "84"
    assert rail.get("Grid.Row") == "0"
    assert rail.get("Grid.RowSpan") == "4"
    brand = next(node for node in rail.iter() if node.get(xname) == "PrimaryRailBrand")
    assert brand.get("Grid.Row") == "0"
    assert any(node.get("Text") == "ArcheAxis" for node in brand.iter())
    assert topbar.get("Grid.Row") == "0"
    assert topbar.get("Grid.Column") == "2"
    assert topbar.get("Grid.ColumnSpan") == "2"
    assert "Grid.SetColumn(TopbarShell, mobile ? 0 : 2);" in code
    assert "Grid.SetColumnSpan(TopbarShell, mobile ? 4 : 2);" in code
    assert 'private const double MasterSidebarWidth = 84d;' in code
    assert 'PrimaryRail.IsVisible = !mobile;' in code
    assert 'MobileRail.IsVisible = mobile;' in code


def test_daily_routes_use_distinct_vector_icons_responsive_labels_and_accessible_names():
    root = ET.parse(XAML).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    rail = next(node for node in root.iter() if node.get(xname) == "PrimaryRail")
    names = ["RailWorkspaceButton", "RailCaptureButton", "RailEvidenceButton", "RailOriginalsButton",
             "RailLearningButton", "RailMachineButton", "RailWorkspaceTreeButton", "RailMemoryMapButton",
             "RailSearchButton", "RailReviewButton"]
    buttons = {node.get(xname): node for node in rail.iter() if node.get(xname)}

    for name in names:
        button = buttons[name]
        assert "master-nav-button" in button.get("Classes", "")
        assert any(node.tag.endswith("}AaosIcon") and node.get("IconName") for node in button.iter())
        assert any(node.get("Text") and node.get(xname)
                   for node in button.iter() if node.tag.endswith("}TextBlock"))
        assert button.get("AutomationProperties.Name")
        assert button.get("ToolTip.Tip")

    code = CODE.read_text(encoding="utf-8")
    assert "var expandedRail = !mobile && frameSize.Width >= narrowActionsBreakpoint;" in code
    assert "var sidebarWidth = expandedRail ? 224d : MasterSidebarWidth;" in code
    assert "RailHomeLabel.IsVisible = expandedRail;" in code
