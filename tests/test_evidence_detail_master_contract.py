import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "Views" / "EvidenceCenterView.axaml"
CODE_PATH = ROOT / "apps" / "ArcheAxis.Desktop" / "Views" / "EvidenceCenterView.axaml.cs"


def test_evidence_detail_matches_b05_columns_and_seven_large_source_nodes():
    root = ET.parse(XAML_PATH).getroot()
    named = {element.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name"): element for element in root.iter()}

    detail_grid = named["EvidenceDetailPageGrid"]
    assert detail_grid.get("ColumnDefinitions") == "1.1*,1*"

    illustration = named["EvidenceSourceChainIllustration"]
    nodes = [element for element in illustration.iter() if element.tag.endswith("Ellipse")]
    assert len(nodes) == 7
    assert all(node.get("Width") == "32" and node.get("Height") == "32" for node in nodes)


def test_evidence_detail_stacks_at_narrow_width_and_keeps_core_unknowns():
    code = CODE_PATH.read_text(encoding="utf-8")
    assert "var detailColumns = width < 1024 ? 1 : 2;" in code
    assert 'new ColumnDefinitions("1.1*,1*")' in code
    assert 'EvidenceVerifiedMetricText.Text = "—"' in code
    assert 'EvidenceReviewMetricText.Text = "—"' in code
    xaml = XAML_PATH.read_text(encoding="utf-8")
    assert 'Text="已验证 · Core 未暴露"' in xaml
    assert 'Text="待复核 · Core 未暴露"' in xaml
    assert "DataTemplate" in code and "using Avalonia.Controls.Templates;" in code


def test_evidence_empty_state_uses_l6_aurora_ring_and_preserves_truthful_actions():
    root = ET.parse(XAML_PATH).getroot()
    named = {element.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name"): element for element in root.iter()}
    empty_state = named["EvidenceEmptyState"]
    assert not any(element.tag.endswith("Image") for element in empty_state.iter())
    artwork = named["EvidenceEmptyStateImage"]
    rings = [element for element in artwork.iter() if element.tag.endswith("Border")]
    assert len(rings) == 1
    assert rings[0].get("BorderBrush") == "{DynamicResource AaosPrimaryBrush}"
    assert rings[0].get("Width") == rings[0].get("Height") == "64"
    assert any(element.tag.endswith("AaosIcon") and element.get("IconName") == "Evidence" for element in rings[0].iter())
    assert 'Text="尚未读取 Evidence anchor"' in XAML_PATH.read_text(encoding="utf-8")
    assert 'AutomationProperties.Name="去捕获来源"' in XAML_PATH.read_text(encoding="utf-8")
    assert 'AutomationProperties.Name="查看任务回执"' in XAML_PATH.read_text(encoding="utf-8")
    code = CODE_PATH.read_text(encoding="utf-8")
    assert "EvidenceEmptyStateImage.Width = 64;" in code
    assert "EvidenceEmptyStateImage.Height = 64;" in code


def test_evidence_empty_states_recreate_the_b10_ring_without_non_suite_clipart():
    xaml_text = XAML_PATH.read_text(encoding="utf-8")
    root = ET.fromstring(xaml_text)
    named = {element.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name"): element for element in root.iter()}
    evidence_art = named["EvidenceEmptyStateImage"]
    assert not any(element.tag.endswith("Image") for element in named["EvidenceEmptyState"].iter())
    assert evidence_art.tag.endswith("Border")
    assert evidence_art.get("Width") == evidence_art.get("Height") == "64"
    assert evidence_art.get("CornerRadius") == "32"
    assert any(element.tag.endswith("AaosIcon") and element.get("IconName") == "Evidence" for element in evidence_art.iter())

    home_path = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"
    home_text = home_path.read_text(encoding="utf-8")
    home = ET.parse(home_path).getroot()
    home_named = {element.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name"): element for element in home.iter()}
    assert not any(element.tag.endswith("Image") for element in home_named["HomeRecentEvidenceEmptyState"].iter())
    assert 'Source="avares://ArcheAxis.Desktop/Assets/aaos-evidence-anchor-empty-state.png"' not in home_text
