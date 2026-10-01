import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosBrandMark.axaml"
CODE_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosBrandMark.axaml.cs"
SVG_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "Assets" / "aaos-brand-mark.svg"
MAIN_WINDOW_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"


def test_brand_mark_matches_b10_tile_and_uses_live_theme_resources():
    xaml = XAML_PATH.read_text(encoding="utf-8")
    code = CODE_PATH.read_text(encoding="utf-8")
    root = ET.fromstring(xaml)

    assert root.attrib.get("Width") == "48"
    assert root.attrib.get("Height") == "48"
    assert 'CornerRadius="16"' in xaml
    assert 'x:Name="MarkSurface"' in xaml
    assert 'Text="AA"' in xaml
    assert 'FontWeight="Black"' in xaml
    assert 'Foreground="{DynamicResource AaosPrimaryTextBrush}"' in xaml
    assert 'Foreground="#FFFFFF"' not in xaml
    assert 'x:Name="RadialHighlight"' in xaml
    assert 'AaosBrandMarkBrush' in xaml
    assert 'AaosBrandMarkGlowEffect' in xaml
    assert 'AaosPrimaryBrush' in xaml
    assert "Bitmap" not in xaml
    assert "ThemePalette" not in code


def test_brand_mark_does_not_use_unsupported_text_block_properties():
    xaml = XAML_PATH.read_text(encoding="utf-8")
    assert "CharacterSpacing=" not in xaml


def test_brand_mark_scales_with_host_size_without_fixed_inner_canvas():
    root = ET.parse(XAML_PATH).getroot()
    grids = [node for node in root.iter() if node.tag.endswith("}Grid")]
    assert grids
    assert grids[0].get("Width") is None
    assert grids[0].get("Height") is None


def test_main_window_uses_48_dip_b10_brand_tile():
    root = ET.parse(MAIN_WINDOW_PATH).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    brand = next(node for node in root.iter() if node.get(xname) == "TopbarBrand")
    marks = [node for node in brand if node.tag.endswith("}AaosBrandMark")]
    assert len(marks) == 1
    assert marks[0].get("Width") == marks[0].get("Height") == "48"


def test_vector_brand_asset_matches_b10_aa_tile():
    svg = SVG_PATH.read_text(encoding="utf-8")
    ET.fromstring(svg)
    assert 'viewBox="0 0 48 48"' in svg
    assert 'rx="16"' in svg
    assert 'font-size="16" font-weight="900"' in svg
    assert '>AA</text>' in svg
    assert 'stop-color="#37CAC7"' in svg and 'stop-color="#90C291"' in svg
    assert 'stop-color="#E2E5E7"' in svg and 'stop-color="#ADB4B8"' in svg
    assert "orbit" not in svg.lower()
