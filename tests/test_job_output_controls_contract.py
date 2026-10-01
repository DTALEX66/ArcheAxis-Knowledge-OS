import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"


def test_jobs_page_exposes_attempt_bound_cancel_and_output_controls():
    root = ET.parse(XAML).getroot()
    xname = "{http://schemas.microsoft.com/winfx/2006/xaml}Name"
    controls = {node.get(xname): node for node in root.iter() if node.get(xname)}
    for name in ("JobCancelButton", "JobOutputKindBox", "JobReadOutputButton", "JobOutputText"):
        assert name in controls
    kinds = [item.get("Tag") for item in controls["JobOutputKindBox"] if item.tag.endswith("ComboBoxItem")]
    assert kinds == ["text", "document_structure", "loss_report"]


def test_job_actions_verify_latest_execution_identity_and_terminal_state():
    code = CODE.read_text(encoding="utf-8")
    assert '"/api/v1/jobs/{Uri.EscapeDataString(selected.JobId)}/executions/{Uri.EscapeDataString(selected.RequestId)}/cancel"' in code
    assert '"/api/v1/jobs/{Uri.EscapeDataString(selected.JobId)}/outputs/{Uri.EscapeDataString(kind)}"' in code
    assert 'ReadDisplayValue(status.RootElement, "request_id")' in code
    assert 'ReadDisplayValue(status.RootElement, "attempt")' in code
    assert "selected.RequestId" in code and "selected.Attempt" in code
    assert 'ReadDisplayValue(metadata, "kind")' in code
