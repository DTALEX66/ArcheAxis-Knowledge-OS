from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_VIEW = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"


def test_search_b05_first_fold_is_query_then_full_width_results_table() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    names = {element.get(xname): element for element in root.iter() if element.get(xname)}
    search = names["SearchSurface"]
    parents = {child: parent for parent in root.iter() for child in parent}

    def direct_child(element: ET.Element) -> ET.Element:
        while parents[element] is not search:
            element = parents[element]
        return element

    assert list(search).index(direct_child(names["SearchPageQueryGrid"])) < list(search).index(direct_child(names["SearchPageResultsList"]))
    assert "SearchPageSelectedDetailBorder" not in names
    filters = names["SearchPageFilters"]
    assert direct_child(filters) is direct_child(names["SearchPageQueryGrid"])
    assert names["SearchPageFiltersStatus"].get("Text")
    assert not any(element.tag.endswith("Expander") and filters in list(element.iter()) for element in search.iter())
    header = names["SearchResultsHeaderGrid"]
    assert header.get("ColumnDefinitions") == "*,*,*,*,*"
    assert [item.get("Text") for item in header if item.tag.endswith("TextBlock")] == ["结果", "类型", "主题", "来源", "更新时间"]
    result_row = names["SearchPageResultsList"].find(".//{*}DataTemplate")
    assert result_row is not None
    row_grid = result_row.find(".//{*}Grid")
    assert row_grid is not None
    assert row_grid.get("ColumnDefinitions") == header.get("ColumnDefinitions")
    row_text = {element.get("Text") for element in result_row.iter()}
    assert "{Binding Head}" in row_text
    assert "{Binding KindLabel}" in row_text
    assert "{Binding TopicLabel}" in row_text
    assert "{Binding SourceLabel}" in row_text
    assert "{Binding UpdatedLabel}" in row_text


def test_search_filters_and_selected_data_remain_available_without_duplicate_detail_card() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    names = {element.get(xname): element for element in root.iter() if element.get(xname)}
    for name in ("SearchPageTypeFilter", "SearchPageActiveOnly"):
        assert name in names
    for name in ("SearchPageSourceFilter", "SearchPageTopicFilter", "SearchPageTimeFilter"):
        assert name in names and names[name].get("IsEnabled") == "False"
    assert names["SearchPageTypeFilter"].get("SelectedIndex") == "0"
    assert names["SearchPageActiveOnly"].get("Content") == "仅当前有效"
    code = (ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    assert 'public string TopicLabel => "Core 未暴露";' in code
    assert 'public string UpdatedLabel => "Core 未暴露";' in code
    assert 'ReadDisplayValue(item, "source_id")' in code
    assert "ProjectSelectedLibraryResult(selected);" in code
