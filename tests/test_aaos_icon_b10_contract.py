import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON_CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosIcon.axaml.cs"
ICON_XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosIcon.axaml"
MAIN_XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"
THEME_CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "ThemePalette.cs"
B10_HTML = ROOT / "tests" / "fixtures" / "aaos-ui-mother" / "index.html"
ICON_BOARD = ROOT / "tests" / "fixtures" / "aaos-ui-mother" / "icon-system.png"


def test_portable_mother_assets_preserve_owner_supplied_bytes():
    assert hashlib.sha256(B10_HTML.read_bytes()).hexdigest() == (
        "1da1fe0d1feb55db98fba5e28cdbaf2e261e7ec4f562d3410cc9b7e74b3149f1"
    )
    assert hashlib.sha256(ICON_BOARD.read_bytes()).hexdigest() == (
        "ae10bdbfd751cfef6c624c934431c3dfdb05bdfdf8ab0c78fd6cf1fe5ef40c5b"
    )


def test_primary_navigation_uses_latest_mother_vector_icons():
    code = ICON_CODE.read_text(encoding="utf-8")
    names = set(re.findall(r'^\s*\["([^"]+)"\]\s*=', code, re.M))
    assert {"Home", "Import", "Original", "Knowledge", "Evidence", "Search", "Memory", "Growth", "HumanAi", "Connection", "Thinking", "Calendar", "Settings"} <= names
    main = MAIN_XAML.read_text(encoding="utf-8")
    root = ET.fromstring(main)
    namespace = {"x": "http://schemas.microsoft.com/winfx/2006/xaml"}
    expected = {
        "RailWorkspaceButton": "Home",
        "RailCaptureButton": "Import",
        "RailEvidenceButton": "Evidence",
        "RailOriginalsButton": "Original",
        "RailLearningButton": "HumanAi",
        "RailMachineButton": "Connection",
        "RailWorkspaceTreeButton": "Workspace",
        "RailMemoryMapButton": "Memory",
        "RailSearchButton": "Search",
        "RailReviewButton": "Review",
        "RailSystemButton": "Settings",
    }
    for button_name, icon_name in expected.items():
        button = next(node for node in root.iter() if node.get(f"{{{namespace['x']}}}Name") == button_name)
        assert any(node.get("IconName") == icon_name for node in button.iter())
        assert not any("b10-nav-dot" in node.get("Classes", "").split() for node in button.iter())
    assert 'IconName="Home"' in main


def test_icon_stroke_and_foreground_follow_every_theme_palette():
    code = ICON_CODE.read_text(encoding="utf-8")
    xaml = ICON_XAML.read_text(encoding="utf-8")
    palettes = THEME_CODE.read_text(encoding="utf-8")
    assert "IconStrokeThickness => 1.7" in code
    assert 'Stroke="{Binding Foreground, RelativeSource={RelativeSource AncestorType=UserControl}}"' in xaml
    assert 'StrokeThickness="{Binding IconStrokeThickness' in xaml
    # The intent is that every palette defines the ivory brush the icons bind to, not that there is
    # a particular number of palettes. The cosmic theme layer added a third (深空主题/DeepSpace), and
    # a hand-counted "== 2" described the palette count rather than the rule. Assert the rule: one
    # definition per palette table, whatever number of tables exists.
    palette_tables = re.findall(
        r"static readonly IReadOnlyDictionary<string, string>\s+\w+Colors\s*=", palettes)
    assert len(palette_tables) >= 2, (
        f"expected at least a light and a dark palette, found {len(palette_tables)}")
    assert palettes.count('["AaosIvoryBrush"]') == len(palette_tables), (
        "every palette table must define the ivory brush the icons bind to: "
        f"{palettes.count('[\"AaosIvoryBrush\"]')} definitions for {len(palette_tables)} tables")
    assert "#F8F6EB" in palettes and "#F1F2F3" in palettes
    assert ICON_BOARD.is_file()


def test_product_action_icons_are_registered_and_used_by_visible_controls():
    code = ICON_CODE.read_text(encoding="utf-8")
    xaml = MAIN_XAML.read_text(encoding="utf-8")
    names = set(re.findall(r'^\s*\["([^"]+)"\]\s*=', code, re.M))
    expected = {"Close", "Plus", "Refresh", "Import", "Export", "Filter", "Calendar", "Link", "Copy", "Check", "Clock", "Source", "Save", "Edit", "Notifications"}
    assert expected <= names
    assert 'IconName="Notifications"' in xaml
    assert 'IconName="Workspace"' in xaml
    assert 'IconName="Capture"' in xaml
    assert 'IconName="Save"' in xaml
    assert 'IconName="Link"' in xaml
