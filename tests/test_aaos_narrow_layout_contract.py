import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"
XNAME = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"


def _named():
    root = ET.parse(XAML).getroot()
    return {node.get(XNAME): node for node in root.iter() if node.get(XNAME)}


def test_mobile_topbar_keeps_search_and_two_actions_without_text_pressure():
    named = _named()
    code = CODE.read_text(encoding="utf-8")
    for name in ("TopbarCommandText", "TopbarNotificationsLabel", "TopbarWorkspaceLabel"):
        assert named[name].tag.endswith("TextBlock")
        assert f"{name}.IsVisible = !mobile;" in code
    assert named["TopbarBrand"].get("IsVisible") == "{ReflectionBinding IsVisible, ElementName=MobileRail}"
    assert "TopbarCommandButton.MaxWidth = mobile ?" in code
    assert "TopbarShell.Padding = mobile ?" in code
    # B10 @media(max-width:840px) includes the boundary itself.
    assert "var mobile = frameSize.Width <= mobileBreakpoint;" in code


def test_mobile_page_heading_reflows_inspector_and_editor_actions():
    named = _named()
    code = CODE.read_text(encoding="utf-8")
    assert named["WorkspaceHeadingBar"].tag.endswith("Grid")
    assert "WorkspaceHeadingBar.RowDefinitions = mobile" in code
    assert "Grid.SetRow(OriginalEditorPageActions, mobile ? 1 : 0);" in code
    assert "Grid.SetColumn(InspectorDrawerButton, mobile ? 1 : 2);" in code
    assert 'mobile ? "检查器"' in code


def test_narrow_metric_and_recovery_cards_fill_available_width():
    named = _named()
    code = CODE.read_text(encoding="utf-8")
    for name in ("LearningMetricsGrid", "ReviewMetricsGrid", "MachineMetricGrid", "RecoverySummaryGrid"):
        assert named[name].get("HorizontalAlignment") == "Stretch"
        assert f"{name}.ItemWidth =" in code
    assert "Math.Min(250, learningMetricContentWidth" not in code
    assert "RecoverySummaryGrid.ItemWidth =" in code


def test_home_narrow_first_fold_keeps_all_real_kpis_in_two_compact_columns():
    named = _named()
    code = CODE.read_text(encoding="utf-8")
    responsive = code[code.index("const double homeStatsTwoColumnBreakpoint") : code.index("HomeQuickCaptureActions.Orientation")]
    dashboard_start = code.index("var homeDashboardSingleColumn = contentWidth")
    home_dashboard = code[dashboard_start : code.index("HomeEvidenceContentGrid.IsVisible", dashboard_start)]

    assert len([name for name in ("HomeStatsSourceCard", "HomeStatsKnowledgeCard", "HomeStatsLearningCard", "HomeStatsJobsCard") if name in named]) == 4
    assert "const double homeStatsSingleColumnBreakpoint = 840;" in responsive
    assert "var homeHeroStacked = contentWidth <= homeStatsSingleColumnBreakpoint;" not in responsive
    assert "new ColumnDefinitions(\"*,*\")" in responsive
    assert "HomeStatsSurface.RowDefinitions = frameSize.Width <= homeStatsSingleColumnBreakpoint" in responsive
    assert "var homeDashboardSingleColumn = contentWidth < 840;" in home_dashboard
    assert "Grid.SetColumn(HomeStatsSurface.Children[index], frameSize.Width <= homeStatsSingleColumnBreakpoint ? 0 : index % (frameSize.Width <= homeStatsTwoColumnBreakpoint ? 2 : 4));" in responsive
    assert "Grid.SetRow(HomeStatsSurface.Children[index], frameSize.Width <= homeStatsSingleColumnBreakpoint ? index : frameSize.Width <= homeStatsTwoColumnBreakpoint ? index / 2 : 0);" in responsive
    assert "HomeEvidenceContentGrid.ColumnDefinitions = homeEvidenceStacked" in responsive
    assert "HomeTodayProgressGrid.ColumnDefinitions = homeProgressSingleColumn" in responsive
    assert all(any(node.get("Text") == "—" for node in named[name].iter()) for name in ("HomeStatsSourceCard", "HomeStatsKnowledgeCard", "HomeStatsLearningCard", "HomeStatsJobsCard"))


def test_narrow_search_filters_expand_across_the_card():
    named = _named()
    code = CODE.read_text(encoding="utf-8")
    # Core has not projected these filters yet; keep an explanatory status row
    # instead of rendering unlabeled disabled selectors that consume the fold.
    assert named["SearchPageFilters"].get("HorizontalAlignment") == "Stretch"
    assert named["SearchPageFiltersStatus"].get("Text") == "来源 · 主题 · 时间筛选：Core 暂未投影"
    assert "SearchPageFilterExpander" not in named
    assert re.search(r"SearchPageFilters\.Width\s*=\s*narrowActions\s*\?", code)


def test_editor_core_status_occupies_its_own_row_below_document_canvas():
    named = _named()
    document_card = named["OriginalDocumentCard"]
    layout = next(iter(document_card))
    canvas = named["OriginalDocumentCanvas"]
    footer = next(
        child for child in layout
        if any("正文与版本由 Core Original 提供" in node.get("Text", "") for node in child.iter())
    )
    assert layout.get("RowDefinitions") == "Auto,*,Auto"
    assert canvas.get("Grid.Row") == "1"
    assert footer.get("Grid.Row") == "2"
