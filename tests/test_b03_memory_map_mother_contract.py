import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosMemoryGraphView.axaml.cs"
XAML = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosMemoryGraphView.axaml"


def test_b03_memory_graph_is_explicitly_a_schematic_not_core_data() -> None:
    code = CODE.read_text(encoding="utf-8")
    xaml = XAML.read_text(encoding="utf-8")
    assert "NodeSelected" in code
    assert "静态示意" in xaml
    assert "不代表 Core 条目或关系" in xaml


def test_b03_page_combines_memory_graph_search_and_review_in_one_canvas() -> None:
    root = ET.parse(ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml").getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    named = {node.get(xname): node for node in root.iter() if node.get(xname)}
    page = named["MemoryMapSurface"]
    graph = named["MemoryMapMotherGraph"]
    search = named["MemoryMapSearchCard"]
    review = named["MemoryMapReviewCard"]
    for child in (graph, search, review):
        assert child in list(page.iter())
    assert graph.tag.endswith("AaosMemoryGraphView")
    assert search.get("Grid.Row") == "0"
    assert review.get("Grid.Row") == "1"


def test_b03_search_and_review_use_existing_core_routes_without_fake_values() -> None:
    root = ET.parse(ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml").getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    named = {node.get(xname): node for node in root.iter() if node.get(xname)}
    code = (ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    assert named["MemoryMapSearchBox"].tag.endswith("TextBox")
    assert named["MemoryMapSearchButton"].get("Click") == "OnMemoryMapSearchClick"
    assert named["MemoryMapStartReviewButton"].get("Click") == "OnReviewClick"
    assert 'SearchPageQueryBox.Text = MemoryMapSearchBox.Text;' in code
    assert 'SetSection("search", "搜索")' in code
    assert "await OnSearchPageClickAsync();" in code
    assert 'SetSection("review", "复习 / FSRS")' in code
    assert "MemoryMapMotherGraph.SetReducedMotion(_reducedMotion)" in code
    assert "MemoryMapMotherGraph.SetMotionActive(section == \"memory-map\")" in code
