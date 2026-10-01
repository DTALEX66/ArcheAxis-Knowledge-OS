"""Guard the Desktop review write -> receipt -> Core readback transition."""

from pathlib import Path


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
