"""Home graph responds to the actual content width after shell panels."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"


def test_home_graph_uses_available_content_width() -> None:
    source = SHELL.read_text(encoding="utf-8")
    layout = source.split("private void ApplyResponsiveLayout", 1)[1]
    graph = layout.split("var homeGraphSingleColumn", 1)[1].split("HomeHeroVisual.IsVisible", 1)[0]

    assert graph.startswith(" = contentWidth <= 1160;")
    assert "HomeGraphContentGrid.ColumnDefinitions = homeGraphSingleColumn" in graph
    assert "HomeGraphContentGrid.RowDefinitions = homeGraphSingleColumn" in graph
    assert "Grid.SetColumn(HomeNodeDetailsCard, homeGraphSingleColumn ? 0 : 1);" in graph
    assert "Grid.SetRow(HomeNodeDetailsCard, homeGraphSingleColumn ? 1 : 0);" in graph
    assert "contentWidth < 1100" not in graph

    # The shell subtracts the rail, context sidebar and inspector before this decision.
    assert "frameSize.Width <= 1160" not in graph
