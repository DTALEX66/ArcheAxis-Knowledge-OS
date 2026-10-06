"""Guard the Desktop review write -> receipt -> Core readback transition."""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"
CORE = ROOT / "crates/archeaxis-api/src/lib.rs"


def _submit_source() -> str:
    source = SHELL.read_text(encoding="utf-8")
    return source.split("private async void OnSubmitReviewClick", 1)[1].split(
        "public sealed class LearningQueueRow", 1
    )[0]


def test_success_requires_matching_persisted_review_identity_and_answer() -> None:
    submit = _submit_source()
    core = CORE.read_text(encoding="utf-8")

    assert '"/api/v1/learning/reviews"' in submit
    assert '"event_id"' in submit
    assert '/api/v1/learning/items/{Uri.EscapeDataString(submittedItemKey)}/state' in submit
    for field in ('"item_key"', '"latest_review"', '"assessment_id"', '"answer"'):
        assert field in submit
        assert field in core
    for comparison in (
        "stateItem.GetString() == submittedItemKey",
        "latestEventId == receiptEventId",
        "latestAssessment.GetString() == submittedAssessmentId",
        "latestAnswer.GetString() == answer",
    ):
        assert comparison in submit
    assert submit.index("if (!readbackVerified)") < submit.index(
        'ShowToast("复习结果已由 Core 记录")'
    )


def test_unverified_or_interrupted_readback_retains_retry_identity() -> None:
    submit = _submit_source()
    guard = submit.split("if (!readbackVerified)", 1)[1].split(
        'ShowToast("复习结果已由 Core 记录")', 1
    )[0]
    exception_path = submit.split("catch (Exception)", 1)[1]

    assert "SubmitReviewButton.IsEnabled = true;" in guard
    assert "SubmitReviewButton2.IsEnabled = true;" in guard
    assert "return;" in guard
    assert "_activeReviewEventId = null" not in guard
    assert "_activeExposureId = null" not in guard
    assert "SubmitReviewButton.IsEnabled = true;" in exception_path
    assert "SubmitReviewButton2.IsEnabled = true;" in exception_path
    assert "_activeReviewEventId = null" not in exception_path
    assert "_activeExposureId = null" not in exception_path
    assert submit.index("_activeReviewEventId ??=") < submit.index("var payload =")
    assert submit.index("_activeExposureId ??=") < submit.index("var payload =")


def test_restored_answer_is_bound_to_the_current_assessment() -> None:
    learning = SHELL.read_text(encoding="utf-8").split(
        "private async void OnLearningClick", 1
    )[1].split("private async void OnSubmitReviewClick", 1)[0]

    assert "LearningAnswerReadback.AnswerForAssessment(" in learning
    assert "outcomeDocument.RootElement, _activeAssessmentId" in learning
    assert "先前 Assessment 的回答仅保留为历史记录" in learning
    assert learning.index("LearningAnswerReadback.AnswerForAssessment(") < learning.index(
        "LearningAnswerBox.Text = savedAnswerText"
    )


def test_answer_binding_executes_the_desktop_csharp_helper() -> None:
    powershell = shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell 7 is required to compile and execute the Desktop C# helper")
    result = subprocess.run(
        [powershell, "-NoProfile", "-File", str(ROOT / "tests/desktop/LearningAnswerReadback.Tests.ps1")],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("PASS:") == 10
