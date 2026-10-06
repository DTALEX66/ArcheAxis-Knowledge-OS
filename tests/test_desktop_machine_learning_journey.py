"""Desktop G4 wiring contracts; human judgement stays a separate click."""
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps/ArcheAxis.Desktop"


def test_each_human_action_has_its_own_handler_and_authenticated_core_route():
    xaml = (DESKTOP / "MainWindow.axaml").read_text(encoding="utf-8")
    code = (DESKTOP / "MainWindow.MachineLearning.cs").read_text(encoding="utf-8")
    for handler, route in (
        ("OnMachineAnswerClick", '"/api/v1/machine/answers"'),
        ("OnMachineCorrectionClick", '"/api/v1/machine/corrections"'),
        ("OnMachineAcceptCorrectionClick", '/review-decisions"'),
        ("OnMachineRetestClick", '"/api/v1/machine/retests"'),
        ("OnMachineJourneyReadbackClick", '/api/v1/machine/tasks/'),
    ):
        assert f'Click="{handler}"' in xaml
        assert route in code
    assert "_supervisor.SendAsync(" in code
    assert "HttpClient" not in code
    assert "SendMachineAsync" not in code
    assert "MachineLearningJourney" in code
    assert 'action = "accepted"' in code
    assert "MarkCorrectionAccepted" in code
    assert "未判定重测正确" in code


def test_journey_diagnostics_are_collapsed_and_busy_controls_are_bounded():
    tree = ET.parse(DESKTOP / "MainWindow.axaml")
    names = {element.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name"): element
             for element in tree.iter()}
    for name in ("MachineJourneyDiagnostics", "LearningSupportDetails", "ReviewPageDiagnostics"):
        assert names[name].tag.endswith("Expander")
        assert names[name].get("IsExpanded") == "False"
    assert names["MachineJourneyProgress"].get("IsIndeterminate") == "True"
    code = (DESKTOP / "MainWindow.MachineLearning.cs").read_text(encoding="utf-8")
    assert "_machineJourneyInProgress" in code
    assert "finally" in code
    assert "UpdateMachineJourneyControls();" in code


def test_only_model_requests_receive_the_model_deadline():
    code = (DESKTOP / "CoreSupervisor.cs").read_text(encoding="utf-8")
    assert "ModelHttp" in code
    assert 'path is "/api/v1/machine/answers" or "/api/v1/machine/retests"' in code
    assert "TimeSpan.FromSeconds(125)" in code
    assert "TimeSpan.FromSeconds(5)" in code


def test_raw_identity_and_receipt_fields_live_in_closed_diagnostics():
    tree = ET.parse(DESKTOP / "MainWindow.axaml")
    parents = {child: parent for parent in tree.iter() for child in parent}
    names = {element.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name"): element for element in tree.iter()}
    for name in ("CaptureReceiptText", "KnowledgeIdBox", "KnowledgeObjectMetaText", "KnowledgeResultsText",
                 "ReviewPageReceiptText", "MachineKnowledgeIdBox", "MachineJourneyIdentityText",
                 "MachineJourneyDiagnosticsText", "RecoveryResultsText", "MemoryMapResultsText",
                 "JobLookupResultsText", "InspectorObjectText", "KnowledgeQualificationText"):
        ancestor = names[name]
        collapsed = False
        while ancestor in parents:
            ancestor = parents[ancestor]
            if ancestor.tag.endswith("Expander") and ancestor.get("IsExpanded") == "False":
                collapsed = True
                break
        assert collapsed, name


def test_journey_state_compiles_and_executes_against_response_fixtures():
    powershell = shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell 7 is required for Desktop C# behavioural tests")
    result = subprocess.run(
        [powershell, "-NoProfile", "-File", str(ROOT / "tests/desktop/MachineLearningJourney.Tests.ps1")],
        cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "JOURNEY PASS" in result.stdout


def test_retest_can_be_corrected_again_and_reduced_motion_has_static_waiting_state():
    code = (DESKTOP / "MainWindow.MachineLearning.cs").read_text(encoding="utf-8")
    assert "_machineJourney.CanRecordCorrection" in code
    assert "MachineJourneyProgress.IsIndeterminate = !_reducedMotion;" in code
    assert "MachineJourneyProgress.IsVisible = _machineJourneyInProgress && !_reducedMotion;" in code
    assert "MachineJourneyWaitingText.IsVisible = _machineJourneyInProgress && _reducedMotion;" in code
