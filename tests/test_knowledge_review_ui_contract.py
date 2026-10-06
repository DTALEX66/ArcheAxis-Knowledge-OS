from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"


def test_knowledge_page_exposes_human_review_fields_and_actions():
    root = ET.parse(XAML).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    controls = {node.get(xname): node for node in root.iter() if node.get(xname)}
    for name in (
        "KnowledgeQualificationText",
        "KnowledgeReviewActionBox",
        "KnowledgeReviewActorBox",
        "KnowledgeReviewNoteBox",
        "KnowledgeReviewNewBodyBox",
        "SubmitKnowledgeReviewButton",
    ):
        assert name in controls
    actions = [item.get("Tag") for item in controls["KnowledgeReviewActionBox"] if item.tag.endswith("ComboBoxItem")]
    assert actions == ["accepted", "rejected", "deprecated", "modified"]


def test_human_review_uses_current_read_identity_and_rereads_core():
    code = CODE.read_text(encoding="utf-8")
    assert '"/api/v1/knowledge-items/{Uri.EscapeDataString(knowledgeId)}/qualification"' in code
    assert '"/api/v1/knowledge-items/{Uri.EscapeDataString(knowledgeId)}/review-decisions"' in code
    assert "_knowledgeReadId" in code
    assert 'HttpMethod.Post' in code
    assert "KnowledgeIdBox.Text = reviewedKnowledgeId" in code
    assert 'OnReadKnowledgeClick(this, new RoutedEventArgs());' in code
