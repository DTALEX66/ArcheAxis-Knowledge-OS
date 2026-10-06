import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml.cs"
XNAME = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"


def _named():
    root = ET.parse(XAML).getroot()
    return {node.get(XNAME): node for node in root.iter() if node.get(XNAME)}


def test_evidence_mother_keeps_filter_then_provenance_table_with_real_source_rows():
    named = _named()
    assert named["EvidenceCategoryTabs"].get("Orientation") == "Horizontal"
    assert named["EvidenceLibraryListSurface"].get("MinHeight") in (None, "160")
    assert named["EvidenceAnchorsList"].get("MaxHeight") == "560"
    row = next(
        node for node in ET.parse(XAML).getroot().iter()
        if node.get("{http://schemas.microsoft.com/winfx/2006/xaml}Key") == "EvidenceLibraryRowTemplate"
    )
    assert row.find(".//*[@ColumnDefinitions='2*,1*,1*,1*,.8*,1.2*']") is not None
    assert "{Binding SourceId}" in ET.tostring(row, encoding="unicode")


def test_empty_projection_is_inline_and_does_not_claim_sample_sources():
    named = _named()
    empty = named["EvidenceEmptyState"]
    assert empty.get("VerticalAlignment") == "Top"
    assert empty.get("Padding") in ("8,6", "10,6")
    code = CODE.read_text(encoding="utf-8")
    assert "width < 760 ? 24 : 40" in code
    assert "未生成示例记录" in code


def test_narrow_evidence_metrics_reflow_without_crushing_card_labels():
    code = CODE.read_text(encoding="utf-8")
    assert "var metricColumns = width < 420 ? 1 : width < 900 ? 2 : 4;" in code
    assert "EvidenceMetricsGrid.ColumnDefinitions = new ColumnDefinitions(string.Join(\",\", Enumerable.Repeat(\"*\", metricColumns)))" in code
    assert "Grid.SetColumn(metricCard, index % metricColumns);" in code
    assert "Grid.SetRow(metricCard, index / metricColumns);" in code
    assert "EvidenceCategoryTabs" in code
    assert "EvidenceLibraryCompactRowTemplate" in code


def test_evidence_library_uses_b05_provenance_table_with_truthful_unavailable_fields():
    named = _named()
    assert named["EvidenceLibraryTableHeaderGrid"].get("ColumnDefinitions") == "2*,1*,1*,1*,.8*,1.2*"
    header_text = {
        node.get("Text")
        for node in ET.parse(XAML).getroot().iter()
        if node.tag.endswith("TextBlock")
    }
    assert {"证据", "来源", "可信度", "主题", "引用", "状态"} <= header_text
    code = CODE.read_text(encoding="utf-8")
    # The unavailable columns must stay explicitly unavailable — never 0, never a fabricated
    # figure. The wording no longer names the Core, which is the de-jargon direction for a
    # default page; what it must keep is that the field is reported as not supplied at all.
    assert 'ConfidenceDisplay => "未提供"' in code
    assert 'TopicDisplay => "未提供"' in code
    assert 'CitationCountDisplay => "未提供"' in code
    assert "EvidenceLibraryTableHeader.IsVisible = width >= 1120;" in code
