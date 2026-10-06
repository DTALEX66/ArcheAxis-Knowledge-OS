from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "ArcheAxis.Desktop"
XNAME = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"


def test_home_quick_capture_is_an_editable_unsaved_draft_with_working_modes():
    root = ET.parse(APP / "MainWindow.axaml").getroot()
    named = {node.get(XNAME): node for node in root.iter() if node.get(XNAME)}

    draft = named["HomeQuickCaptureDraft"]
    assert draft.get("IsReadOnly") != "True"
    assert draft.get("TextChanged") == "OnHomeQuickCaptureDraftChanged"
    assert named["HomeQuickCaptureDraftStatus"].get("Text") == "草稿仅保留在当前窗口；尚未保存到 Core。"
    assert named["HomeQuickCaptureTextModeButton"].get("Click") == "OnHomeQuickCaptureTextModeClick"
    assert named["HomeQuickCaptureLinkModeButton"].get("Click") == "OnHomeQuickCaptureLinkModeClick"

    source = (APP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
    assert "private void OnHomeQuickCaptureDraftChanged" in source
    assert "private void OnHomeQuickCaptureTextModeClick" in source
    assert "private void OnHomeQuickCaptureLinkModeClick" in source
    assert "HomeQuickCaptureDraftStatus.Text = \"草稿仅保留在当前窗口；尚未保存到 Core。\";" in source
    assert "OnHomeQuickCaptureDraftChanged" in source
