import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "Views" / "EvidenceCenterView.axaml"
CODE_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "Views" / "EvidenceCenterView.axaml.cs"


def _named_elements():
    root = ET.parse(XAML_PATH).getroot()
    return {element.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name"): element for element in root.iter()}


def test_evidence_actions_have_semantic_icons_and_accessible_names():
    named = _named_elements()
    for button_name, icon_name in (
        ("EvidenceRefreshButton", "Refresh"),
        ("EvidenceBackButton", "ChevronLeft"),
        ("EvidenceDetailOpenSourceButton", "Source"),
    ):
        button = named[button_name]
        assert button.get("{https://github.com/avaloniaui}") is None
        assert button.get("AutomationProperties.Name") or any(key.endswith("}Name") for key in button.attrib)
        assert any(element.tag.endswith("AaosIcon") and element.get("IconName") == icon_name for element in button.iter())


def test_source_chain_visual_does_not_render_unverified_related_nodes_as_real_data():
    illustration = _named_elements()["EvidenceSourceChainIllustration"]
    assert sum(element.tag.endswith("Ellipse") for element in illustration.iter()) == 7
    assert "不表示真实关联数量" in XAML_PATH.read_text(encoding="utf-8")
    assert "引用尚未读取" in XAML_PATH.read_text(encoding="utf-8")


def test_evidence_detail_surface_fades_in_and_back_navigation_restores_list_focus():
    named = _named_elements()
    detail = named["EvidenceDetailSurface"]
    transitions = [element for element in detail.iter() if element.tag.endswith("DoubleTransition")]
    assert any(element.get("Property") == "Opacity" for element in transitions)
    code = CODE_PATH.read_text(encoding="utf-8")
    assert "Dispatcher.UIThread.Post" in code
    assert "EvidenceAnchorsList.Focus()" in code
    assert "EvidenceDetailSurface.Opacity = 0;" in code
