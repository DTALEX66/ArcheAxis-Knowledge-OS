import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosMemoryGraphView.axaml"
CODE = ROOT / "apps" / "ArcheAxis.Desktop" / "AaosMemoryGraphView.axaml.cs"
NS = {"a": "https://github.com/avaloniaui"}


def test_memory_graph_matches_b03_labeled_cross_network_and_truth_boundary():
    xaml = ET.parse(VIEW).getroot()
    source = CODE.read_text(encoding="utf-8")
    canvas = xaml.find(".//a:Canvas", NS)
    xaml_text = " ".join(node.text or "" for node in xaml.iter())

    assert canvas is not None
    assert "静态示意" in xaml.attrib.get("AutomationProperties.Name", "") + xaml_text
    assert "不代表 Core 条目或关系" in canvas.attrib.get("AutomationProperties.HelpText", "")
    assert "MasterNodeCount = 14" in source

    nodes_block = re.search(r"MasterNodes\s*=\s*\[(.*?)\];", source, re.S)
    assert nodes_block is not None
    nodes = re.findall(r'new GraphNodeDefinition\("([^\"]+)",\s*([\d.]+),\s*([\d.]+)\)', nodes_block.group(1))
    labels = {label for label, _, _ in nodes}
    assert len(nodes) == 14
    assert {"AI", "认知", "人类", "学习", "记忆", "思考", "证据", "来源", "时间", "原创", "工作区", "捕获", "复习", "关系"} <= labels
    assert 'Text = definition.Label' in source

    edges_block = re.search(r"MasterEdges\s*=\s*\[(.*?)\];", source, re.S)
    assert edges_block is not None
    edges = [tuple(map(int, pair)) for pair in re.findall(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", edges_block.group(1))]
    assert len(edges) >= 36
    assert all(source == -1 or target == -1 or source != target for source, target in edges)
    assert any(source == -1 or target == -1 for source, target in edges)
    assert any(abs(source - target) > 1 and source >= 0 and target >= 0 for source, target in edges)

    assert "AutomationProperties.SetName" in source
    assert "AutomationProperties.SetHelpText" in source
    assert "不代表 Core 条目或关系" in source
    assert "HitTargetSize = 44" in source
    assert "node.PointerEntered += OnNodePointerEntered" in source
    assert "node.GotFocus += OnNodeGotFocus" in source
    assert "node.Click += OnNodeClick" in source


def test_memory_graph_has_reduced_motion_safe_center_pulse_and_node_feedback():
    source = CODE.read_text(encoding="utf-8")

    assert "if (_reducedMotion || !_motionActive || !IsVisible)" in source
    assert "_pulseTimer.Stop();" in source
    assert "node.Transitions = reducedMotion ? new Transitions() : null;" in source
    assert "UpdateRelationHighlight();" in source
