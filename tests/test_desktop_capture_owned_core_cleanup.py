"""Capture exits must release the Core child owned by the Desktop window."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"


def test_capture_disposes_owned_core_before_forced_process_exit() -> None:
    code = SHELL.read_text(encoding="utf-8")
    capture = code.split("private async void OnLoaded", 1)[1].split(
        "// Only start and authenticate our own Core", 1
    )[0]

    assert 'AAOS_UI_CAPTURE_WAIT_CORE' in capture
    assert "WorkerProfile.Load(AppContext.BaseDirectory" in capture
    assert "_supervisor = new CoreSupervisor(captureDbPath, textWorker: captureWorker);" in capture
    assert capture.index("try\n            {") < capture.index("_supervisor = new CoreSupervisor")
    assert capture.index("CaptureWindowPng(capturePath);") < capture.index("finally")
    assert capture.index("finally") < capture.index("_supervisor?.Dispose();")
    assert capture.index("_supervisor?.Dispose();") < capture.index("Environment.Exit(0);")
    assert "_supervisor = null;" in capture


def test_capture_error_also_releases_owned_core() -> None:
    code = SHELL.read_text(encoding="utf-8")
    capture = code.split("private async void OnLoaded", 1)[1].split(
        "// Only start and authenticate our own Core", 1
    )[0]
    guarded = capture.split("try\n            {", 1)[1].split("finally", 1)[0]

    assert "await _supervisor.StartAsync()" in guarded
    assert "await RefreshWorkspaceSummaryAsync()" in guarded
    assert guarded.index("await _supervisor.StartAsync()") < guarded.index("SetCaptureRoute(captureRoute);")
    assert "await RefreshEvidenceAsync();" in guarded
    assert "CaptureWindowPng(capturePath);" in guarded
    assert "_supervisor?.Dispose();" not in guarded
