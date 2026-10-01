"""The final mark follows the user's 2026-10-01 star-and-orbit brand boards."""

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/ArcheAxis.Desktop"


def test_brand_mark_is_a_theme_aware_vector_orbit():
    xaml = (APP / "AaosBrandMark.axaml").read_text(encoding="utf-8")
    root = ET.fromstring(xaml)
    assert root.attrib["Width"] == root.attrib["Height"] == "48"
    assert xaml.count("<Ellipse") >= 3
    assert "AaosGoldBrush" in xaml and "AaosPrimaryBrush" in xaml
    assert "AaosIvoryBrush" in xaml
    assert 'Text="AA"' not in xaml
    assert "Bitmap" not in xaml


def test_packaged_vector_source_and_shell_use_star_mark():
    svg = (APP / "Assets/aaos-brand-mark.svg").read_text(encoding="utf-8")
    ET.fromstring(svg)
    assert 'viewBox="0 0 48 48"' in svg
    assert "<circle" in svg and "<ellipse" in svg
    assert 'fill="#F8F6EB"' in svg
    assert ">AA</text>" not in svg
    main = ET.parse(APP / "MainWindow.axaml").getroot()
    marks = [node for node in main.iter() if node.tag.endswith("}AaosBrandMark")]
    assert len(marks) >= 2
