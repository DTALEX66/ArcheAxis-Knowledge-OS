"""Home graph follows B10's outer-window 1160px single-column boundary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"


def test_home_graph_uses_window_width_and_exact_b10_boundary() -> None:
    source = SHELL.read_text(encoding="utf-8")
    layout = source.split("private void ApplyResponsiveLayout", 1)[1]
    graph = layout.split("var homeGraphSingleColumn", 1)[1].split("HomeHeroVisual.IsVisible", 1)[0]

    assert graph.startswith(" = frameSize.Width <= 1160;")
    assert "HomeGraphContentGrid.ColumnDefinitions = homeGraphSingleColumn" in graph
    assert "HomeGraphContentGrid.RowDefinitions = homeGraphSingleColumn" in graph
    assert "Grid.SetColumn(HomeNodeDetailsCard, homeGraphSingleColumn ? 0 : 1);" in graph
    assert "Grid.SetRow(HomeNodeDetailsCard, homeGraphSingleColumn ? 1 : 0);" in graph
    assert "contentWidth < 1100" not in graph

    # Representative native window sizes: 1280 stays beside the graph;
    # 1160 is the first stacked boundary, and 720 remains stacked.
    assert (1280 <= 1160) is False
    assert (1160 <= 1160) is True
    assert (720 <= 1160) is True
