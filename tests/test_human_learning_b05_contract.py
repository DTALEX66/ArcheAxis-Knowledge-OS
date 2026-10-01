from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_VIEW = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml"


def test_human_learning_master_starts_with_metrics_and_keeps_load_action_in_plan_card() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    nodes = {element.get(xname): element for element in root.iter() if element.get(xname)}
    learning = nodes["LearningSurface"]
    direct_named_children = [element.get(xname) for element in learning]
    assert direct_named_children.index("LearningPageHeader") < direct_named_children.index("LearningMetricsGrid")
    assert direct_named_children.index("LearningMetricsGrid") < direct_named_children.index("LearningPlanGrid")
    assert "LoadLearningButton" not in direct_named_children
    plan = nodes["LearningPlanGrid"]
    assert nodes["LoadLearningButton"] in list(plan.iter())


def test_human_learning_empty_queue_uses_core_status_without_fake_topics() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    nodes = {element.get(xname): element for element in root.iter() if element.get(xname)}
    rows = nodes["LearningPlanPlaceholderRows"]
    assert "尚未读取 Core 学习队列。" in " ".join(element.get("Text", "") for element in rows.iter())
    assert not any("learning-plan-empty-bar" in element.get("Classes", "") for element in rows.iter())
    assert all("未暴露学习主题" not in element.get("Text", "") for element in rows.iter())
    assert any("Core Learning projection" in element.get("Text", "") for element in nodes["LearningPlanGrid"].iter())


def test_human_learning_matches_master_columns_and_hides_support_panels_until_requested() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    nodes = {element.get(xname): element for element in root.iter() if element.get(xname)}
    metrics = nodes["LearningMetricsGrid"]
    assert metrics.get("ItemWidth") == "280"
    assert metrics.get("ItemHeight") == "126"
    plan = nodes["LearningPlanGrid"]
    assert plan.get("ColumnDefinitions") == "1.25*,2*"
    assert nodes["LearningSupportDetails"].tag.endswith("Expander")
    assert nodes["LearningSupportDetails"].get("IsExpanded") == "False"
    for name in ("LearningReviewCard", "LearningProvenancePanel"):
        assert nodes[name].get("IsVisible") != "False"
        assert nodes[name] in list(nodes["LearningSupportDetails"].iter())


def test_human_learning_promotes_real_core_queue_into_the_primary_plan_card() -> None:
    root = ET.parse(MAIN_VIEW).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    nodes = {element.get(xname): element for element in root.iter() if element.get(xname)}
    plan = nodes["LearningPlanGrid"]

    assert nodes["LearningStatusText"] in list(plan.iter())
    assert nodes["LearningQueueList"] in list(plan.iter())
    assert nodes["LearningQueueList"].get("AutomationProperties.Name") == "待复习学习队列"
    assert "Core Learning projection" in " ".join(
        element.get("Text", "") for element in plan.iter() if element.tag.endswith("TextBlock")
    )
