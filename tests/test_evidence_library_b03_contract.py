import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/Views/EvidenceCenterView.axaml.cs"
XNAME = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"


def _named():
    root = ET.parse(XAML).getroot()
    return {node.get(XNAME): node for node in root.iter() if node.get(XNAME)}


def _resource(key):
    root = ET.parse(XAML).getroot()
    xkey = "{http://schemas.microsoft.com/winfx/2006/xaml}Key"
    return next(node for node in root.iter() if node.get(xkey) == key)


def test_b03_library_has_category_tabs_without_invented_filter_contract():
    named = _named()
    tabs = named["EvidenceCategoryTabs"]
    labels = [node.get("Content") for node in tabs if node.tag.endswith("Button")]
    assert labels == ["全部", "文章", "书籍", "视频", "网页"]
    assert named["EvidenceAllCategoryButton"].get("IsEnabled") != "False"
    for name in ("Article", "Book", "Video", "Web"):
        button = named[f"Evidence{name}CategoryButton"]
        assert button.get("IsEnabled") == "False"
        assert "Core" in button.get("ToolTip.Tip", "")


def test_b05_evidence_rows_use_six_column_provenance_table_layout():
    named = _named()
    row = _resource("EvidenceLibraryRowTemplate")
    text = XAML.read_text(encoding="utf-8")
    assert named["EvidenceAnchorsList"] in list(named["EvidenceLibraryListSurface"].iter())
    assert named["EvidenceLibraryTableHeaderGrid"].get("ColumnDefinitions") == "2*,1*,1*,1*,.8*,1.2*"
    for field in ("AnchorId", "SourceId", "ConfidenceDisplay", "TopicDisplay", "CitationCountDisplay", "VerificationStatusDisplay"):
        assert f"{{Binding {field}}}" in ET.tostring(row, encoding="unicode")
    assert {"证据", "来源", "可信度", "主题", "引用", "状态"} <= {
        node.get("Text") for node in named["EvidenceLibraryTableHeaderGrid"] if node.tag.endswith("TextBlock")
    }
    assert "EvidenceFullRowTemplate" not in text


def test_b05_metadata_and_four_kpis_remain_without_sample_values():
    named = _named()
    row = ET.tostring(_resource("EvidenceLibraryRowTemplate"), encoding="unicode")
    for field in ("SourceRevisionDisplay", "RawSha256Display", "LocatorDisplay", "CreatedAtDisplay"):
        assert f"{{Binding {field}}}" in row
    assert len(named["EvidenceMetricsGrid"]) == 4
    code = CODE.read_text(encoding="utf-8")
    # The row heading is the cited quote when the Core supplied one and a neutral label
    # otherwise; the raw anchor id lives on the row's detail line instead of being the title.
    assert 'public string TitleDisplay => string.IsNullOrWhiteSpace(Quote)' in code
    for field in ("ConfidenceDisplay", "TopicDisplay", "CitationCountDisplay"):
        assert f'{field} => "未提供"' in code
    assert 'PublicationYearDisplay => "年份未提供"' in code
    assert 'VerificationStatusDisplay => "验证状态未提供"' in code


def test_narrow_layout_keeps_same_rows_and_category_tabs():
    code = CODE.read_text(encoding="utf-8")
    assert "EvidenceLibraryRowTemplate" in code
    assert "EvidenceLibraryCompactRowTemplate" in code
    assert "EvidenceCategoryTabs" in code
    assert "EvidenceDetailPageGrid.ColumnDefinitions" in code
