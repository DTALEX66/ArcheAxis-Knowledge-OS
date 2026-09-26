"""The Avalonia learning loop must match the Core projection and retry contract.

These are source-level contract checks, not runtime evidence. No .NET SDK is
available to this repository's Python suite, so the desktop shell is compiled by
CI's `desktop-vnext` job; what is pinned here is the agreement between the two
sides that a reviewer can re-derive from the tracked sources alone:

* the Core nests provenance under `learner.references`, and the shell must read
  it there, splitting `active` source versions from superseded ones;
* the review ids (`client_event_id`, which is the Core's idempotency key, and
  `exposure_id`) belong to one exposure and must be reused on retry.

The producer half is read from the Rust source rather than restated here, so a
change to the projection shape fails these tests instead of silently drifting
away from the shell.
"""

from __future__ import annotations

import re
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs"
PROGRAM = ROOT / "apps" / "ArcheAxis.Desktop" / "Program.cs"
CORE = ROOT / "crates" / "archeaxis-api" / "src" / "lib.rs"
REVIEW_SCHEMA = ROOT / "packages" / "contracts" / "learning" / "v1" / "review.schema.json"


def _shell_source() -> str:
    return SHELL.read_text(encoding="utf-8")


def test_add_to_learning_selects_the_created_item_and_ignores_stale_navigation() -> None:
    handler = _region(_shell_source(), "private async void OnAddKnowledgeToLearningClick", "private async void OnReadMachineTaskClick")
    assert "var knowledgeId = _learningEligibleKnowledgeId" in handler
    assert "bool IsCurrentRequest()" in handler
    assert "requestVersion == _knowledgeRequestVersion" in handler
    assert '_activeSection == "knowledge"' in handler
    assert handler.index("_selectedLearningItemKey = itemKey;") < handler.index("OnLearningClick(sender, e);")
    assert "if (IsCurrentRequest())" in handler


def test_reader_candidate_submission_disables_its_own_action() -> None:
    handler = _region(_shell_source(), "private async void OnSourceBoundCandidateRequested", "private void OnSourceReaderOpenJobRequested")
    assert "if (SourceReaderView.CandidateSubmissionInProgress)" in handler
    assert "SourceReaderView.SetCandidateSubmissionInProgress(true);" in handler
    assert "SourceReaderView.SetCandidateSubmissionInProgress(false);" in handler
    assert "CreateKnowledgeCandidateButton.IsEnabled" not in handler
    assert "requestVersion == _sourceReaderRequestVersion" in handler
    assert "ReferenceEquals(SourceReaderView.SelectedRow, e.Row)" in handler
    assert "string.Equals(rawSha, e.RawSha256, StringComparison.Ordinal)" in handler
    assert handler.index("if (!IsCurrentSource())") < handler.index("KnowledgeIdBox.Text = knowledgeId;")


def test_programmatic_knowledge_id_read_survives_deferred_text_changed() -> None:
    shell = _shell_source()
    changed = _region(shell, "private void OnKnowledgeIdChanged", "private async void OnReadKnowledgeClick")
    read = _region(shell, "private async void OnReadKnowledgeClick", "private async void OnAddKnowledgeToLearningClick")
    assert changed.index("string.Equals(_observedKnowledgeInput, currentInput") < changed.index("++_knowledgeRequestVersion")
    assert read.index("_observedKnowledgeInput = KnowledgeIdBox.Text") < read.index("++_knowledgeRequestVersion")


def _region(source: str, start_marker: str, end_marker: str | None = None) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start) if end_marker else len(source)
    return source[start:end]


# ------------------------------------------------------------------ producer


def test_core_projection_nests_card_references_under_the_learner_section() -> None:
    """`item_state` is the only producer of the fact the shell renders."""
    core = CORE.read_text(encoding="utf-8")
    producer = _region(core, "async fn item_state", "\nasync fn ")

    assert '"learner"' in producer, "the projection must keep the learner section"
    assert '"references"' in producer, "the learner section must carry references"
    assert producer.index('"learner"') < producer.index('"references"'), (
        "references must be nested inside learner, not emitted at the document root"
    )
    assert '"knowledge_id"' in producer and '"active"' in producer, (
        "each reference must carry its knowledge_id and whether it is still active"
    )


# --------------------------------------------------------------- provenance


def test_desktop_reads_provenance_from_learner_references() -> None:
    shell = _shell_source()

    assert 'RootElement.TryGetProperty("learner"' in shell, (
        "the shell must descend into the learner section before reading references"
    )
    assert 'learner.TryGetProperty("references"' in shell, (
        "references must be read from the learner section"
    )
    assert not re.search(r'RootElement\.TryGetProperty\("references"', shell), (
        "reading references from the document root reported 未记录 for every item"
    )


def test_desktop_separates_current_from_superseded_source_versions() -> None:
    shell = _shell_source()
    provenance = _region(
        shell,
        "private async void OnLearningClick",
        "private async void OnSubmitReviewClick",
    )

    assert "当前来源版本" in provenance, "current source versions must be shown as such"
    assert "已被替代版本" in provenance, "superseded source versions must be shown as such"
    assert 'TryGetProperty("knowledge_id"' in provenance, "the version id must be read"
    assert 'TryGetProperty("active"' in provenance, "the active flag must drive the split"
    assert "JsonValueKind.True" in provenance, (
        "only an explicit active=true may be treated as a current source version"
    )


# -------------------------------------------------------------------- retry


def test_review_ids_are_allocated_once_per_exposure_and_reused_on_retry() -> None:
    shell = _shell_source()
    submit = _region(shell, "private async void OnSubmitReviewClick")
    payload = submit.split("var payload = JsonSerializer.Serialize", 1)[1].split("});", 1)[0]

    assert "Guid.NewGuid" not in payload, (
        "re-allocating an id inside the payload makes every retry a new review"
    )
    assert "client_event_id = submittedEventId" in payload
    assert "exposure_id = submittedExposureId" in payload
    assert "_activeReviewEventId ??=" in submit, "the id pair is allocated once per exposure"
    assert "_activeExposureId ??=" in submit, "the id pair is allocated once per exposure"
    assert "_activeReviewEventId = null;" in submit, "a success must close the exposure"
    assert "_activeExposureId = null;" in submit, "a success must close the exposure"


def test_review_submission_requires_a_real_answer() -> None:
    shell = _shell_source()
    submit = _region(shell, "private async void OnSubmitReviewClick")

    assert 'string.IsNullOrWhiteSpace(answer)' in submit
    assert "请输入回答" in submit


def test_desktop_binds_review_to_core_owned_assessment() -> None:
    shell = _shell_source()
    learning = _region(shell, "private async void OnLearningClick", "private async void OnSubmitReviewClick")
    submit = _region(shell, "private async void OnSubmitReviewClick")

    assert "/assessment" in learning
    assert 'GetProperty("assessment_id")' in learning
    assert 'GetProperty("question")' in learning
    assert 'GetProperty("content")' in learning
    assert "assessment_id = submittedAssessmentId" in submit
    assert "knowledge_version = submittedKnowledgeVersion" in submit


def test_desktop_requires_assessment_bound_to_current_active_knowledge() -> None:
    shell = _shell_source()
    learning = _region(shell, "private async void OnLearningClick", "private async void OnSubmitReviewClick")

    assert "activeKnowledgeId" in learning
    assert "knowledge_id" in learning
    assert "assessmentReady" in learning
    assert "LearningAnswerBox.IsEnabled = assessmentReady" in learning
    assert "SubmitReviewButton.IsEnabled = assessmentReady" in learning
    assert 'assessment.RootElement.TryGetProperty("knowledge_id"' in learning
    assert "HttpStatusCode.NotFound" in learning
    assert "assessmentResponse.IsSuccessStatusCode" in learning


def test_desktop_keeps_mastery_projection_open_when_review_response_arrives() -> None:
    shell = _shell_source()
    submit = _region(shell, "private async void OnSubmitReviewClick")

    assert "JsonDocument.Parse" in submit
    assert 'TryGetProperty("answer"' in submit
    assert 'TryGetProperty("mastery_projection"' in submit
    assert 'TryGetProperty("closed"' in submit
    assert "Mastery projection 未闭合" in submit


def test_desktop_projects_review_schedule_receipt_without_promoting_mastery() -> None:
    shell = _shell_source()
    submit = _region(shell, "private async void OnSubmitReviewClick")
    xaml = (ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml").read_text(encoding="utf-8")

    assert 'x:Name="LearningReviewReceiptText"' in xaml
    for field in ("schedule_authority", "schedule_state", "next_review", "next_review_days"):
        assert f'ReadDisplayValue(reviewRoot, "{field}")' in submit
    assert "Mastery projection：" in submit
    assert "Knowledge Truth" in xaml


def test_desktop_projects_persisted_schedule_and_mastery_state_on_learning_open() -> None:
    shell = _shell_source()
    learning = _region(shell, "private async void OnLearningClick", "private async void OnSubmitReviewClick")

    assert 'ReadDisplayValue(learner, "scheduled_events")' in learning
    assert 'ReadDisplayValue(learner, "unscheduled_events")' in learning
    assert 'TryGetProperty("latest_review"' in learning
    assert 'ReadDisplayValue(latestReview, "schedule_authority")' in learning
    assert 'ReadDisplayValue(latestReview, "schedule_state")' in learning
    assert "FormatProjectionJsonForDisplay(" in learning
    assert 'ReadDisplayValue(projection, "closed")' in learning
    assert 'LearningItemText.Text = $"{assessmentText}' in learning


def test_schedule_json_is_indented_for_narrow_inspector_readability() -> None:
    shell = _shell_source()
    formatter = _region(shell, "private static string FormatProjectionJsonForDisplay", "private async void OnRefreshJobsClick")

    assert "JsonDocument.Parse(value)" in formatter
    assert "JsonSerializerOptions { WriteIndented = true }" in formatter
    assert "catch (JsonException)" in formatter


def test_review_schema_accepts_desktop_payload_fields_without_opening_schedule_state() -> None:
    schema = json.loads(REVIEW_SCHEMA.read_text(encoding="utf-8"))
    properties = schema["properties"]
    for field in (
        "answer",
        "assessment_id",
        "question_version",
        "knowledge_version",
        "exposure_id",
        "assist_strategy",
        "rating_version",
        "correction_id",
    ):
        assert field in properties
    assert schema["additionalProperties"] is False
    conditional = schema["allOf"][0]
    assert conditional["then"]["required"] == ["assessment_id"]
    assert "schedule_state" not in properties


def test_review_schema_validates_desktop_payload_and_rejects_authoritative_fields() -> None:
    schema = json.loads(REVIEW_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    valid_payload = {
        "item_key": "item-1",
        "client_event_id": "event-1",
        "correct": True,
        "rating": 3,
        "answer": "answer",
        "assessment_id": "assessment-1",
        "knowledge_version": "knowledge-v1",
        "exposure_id": "exposure-1",
        "rating_version": "desktop-v1",
    }
    assert not list(validator.iter_errors(valid_payload))
    assert list(validator.iter_errors({**valid_payload, "schedule_state": "review"}))
    assert list(validator.iter_errors({key: value for key, value in valid_payload.items() if key != "assessment_id"}))
    assert list(validator.iter_errors({**valid_payload, "correct": True, "rating": 1}))
    assert list(validator.iter_errors({**valid_payload, "correct": False, "rating": 3}))


def test_desktop_rejects_inconsistent_correctness_and_fsrs_rating_before_post() -> None:
    shell = _shell_source()
    submit = _region(shell, "private async void OnSubmitReviewClick", "public sealed class LibraryResultRow")

    assert "if (_activeReviewRating is null)" in submit
    assert "var rating = _activeReviewRating.Value;" in submit
    assert "_activeReviewRating ?? (correct ? 3 : 1)" not in submit
    assert "if ((correct && rating == 1) || (!correct && rating != 1))" in submit
    assert "SubmitReviewButton.IsEnabled = false;" in submit


@pytest.mark.parametrize(
    ("correct", "rating", "expected_valid"),
    [
        (True, 1, False),
        (True, 2, True),
        (True, 3, True),
        (True, 4, True),
        (False, 1, True),
        (False, 2, False),
        (False, 3, False),
        (False, 4, False),
    ],
)
def test_desktop_review_rating_rule_matches_shared_contract_matrix(
    correct: bool, rating: int, expected_valid: bool
) -> None:
    schema = json.loads(REVIEW_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = {
        "item_key": "item-1",
        "client_event_id": "event-1",
        "correct": correct,
        "rating": rating,
    }
    shell = _shell_source()
    submit = _region(shell, "private async void OnSubmitReviewClick", "public sealed class LibraryResultRow")
    rust = CORE.read_text(encoding="utf-8")

    assert bool(list(validator.iter_errors(payload))) is (not expected_valid)
    assert "if ((correct && rating == 1) || (!correct && rating != 1))" in submit
    assert "(rating == 1) == body.correct" in rust


def test_desktop_ignores_late_review_receipts_for_a_replaced_exposure() -> None:
    shell = _shell_source()
    submit = _region(shell, "private async void OnSubmitReviewClick", "public sealed class LibraryResultRow")

    assert "private long _reviewRequestVersion;" in shell
    assert "var reviewRequestVersion = ++_reviewRequestVersion;" in submit
    assert "IsCurrentReviewSubmission(" in submit
    assert submit.count("if (!IsCurrentReviewSubmission(") >= 2
    assert "catch (Exception)" in submit


def test_desktop_reads_latest_learning_event_on_open_for_restart_readback() -> None:
    shell = _shell_source()
    learning = _region(shell, "private async void OnLearningClick", "private async void OnSubmitReviewClick")

    assert '"/api/v1/learning/events/' in learning
    assert 'TryGetProperty("events"' in learning
    assert 'TryGetProperty("outcome"' in learning
    assert 'TryGetProperty("answer"' in learning
    assert 'TryGetProperty("mastery_projection"' in learning
    assert "已保存回答" in learning
    assert "Mastery projection 未闭合" in learning
    assert "学习记录：未读回" in learning


def test_desktop_restores_persisted_answer_text_on_open() -> None:
    shell = _shell_source()
    learning = _region(shell, "private async void OnLearningClick", "private async void OnSubmitReviewClick")

    assert "savedAnswerText" in learning
    assert "LearningAnswerBox.Text = savedAnswerText" in learning


def test_new_learning_presentation_clears_previous_review_outcome_selection() -> None:
    shell = _shell_source()
    learning = _region(shell, "private async void OnLearningClick", "private async void OnSubmitReviewClick")

    assert "ReviewOutcomeBox.SelectedIndex = 0;" in learning


def test_fsrs_rating_does_not_silently_change_core_correctness() -> None:
    shell = _shell_source()
    rating = _region(shell, "private void SetReviewRating", "private void OnReviewAgainClick")

    assert "_activeReviewRating = rating;" in rating
    assert "ReviewOutcomeBox.SelectedIndex" not in rating
    assert "FSRS" in rating


def test_review_submission_requires_an_explicit_fsrs_rating() -> None:
    shell = _shell_source()
    submit = _region(shell, "private async void OnSubmitReviewClick")

    assert "if (_activeReviewRating is null)" in submit
    assert "var rating = _activeReviewRating.Value;" in submit
    assert "_activeReviewRating ?? (correct ? 3 : 1)" not in submit


def test_learning_queue_is_selectable_instead_of_fixing_the_first_core_item() -> None:
    shell = _shell_source()
    xaml = (ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml").read_text(encoding="utf-8")

    assert 'x:Name="LearningQueueList"' in xaml
    assert 'SelectionChanged="OnLearningQueueSelectionChanged"' in xaml
    assert "LearningQueueRow" in shell
    assert "_selectedLearningItemKey" in shell
    assert "LearningQueueList.ItemsSource = queueRows;" in shell
    assert "string.Equals(_selectedLearningItemKey, itemKey" in shell


def test_learning_queue_and_inspector_wrap_long_projection_values() -> None:
    xaml = (ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml").read_text(encoding="utf-8")

    queue = xaml.split('x:Name="LearningQueueList"', 1)[1].split("</ListBox>", 1)[0]
    assert '<DataTemplate x:DataType="{x:Type local:LearningQueueRow}">' in queue
    assert "{Binding DisplayText}" in queue
    assert 'TextWrapping="Wrap"' in queue
    assert 'x:Name="InspectorObjectText"' in xaml
    assert 'x:Name="InspectorObjectText" Text="未选择对象" TextWrapping="Wrap"' in xaml


def test_a_new_presentation_starts_a_new_exposure() -> None:
    shell = _shell_source()
    learning = _region(
        shell,
        "private async void OnLearningClick",
        "private async void OnSubmitReviewClick",
    )

    assert learning.count("_activeReviewEventId = null;") == 2, (
        "presenting an item and finding an empty queue must both start a fresh exposure"
    )
    assert learning.count("_activeExposureId = null;") == 2


def test_headless_learning_smoke_covers_cold_restart_readback_without_claiming_mastery() -> None:
    program = PROGRAM.read_text(encoding="utf-8")

    assert 'args[0] == "--learning-smoke"' in program
    assert '"/api/v1/knowledge-items"' in program
    assert '"/api/v1/learning/items/' in program
    assert '}/assessment"' in program
    assert '"/api/v1/learning/reviews"' in program
    assert '"/api/v1/learning/events/' in program
    assert '"assessment_id"' in program
    assert '"schedule_authority"' in program
    assert '"fsrs"' in program
    assert '"mastery_projection"' in program
    assert '"closed"' in program
    assert '"projection"' in program
    assert "LEARNING SMOKE OK" in program
    assert "synthetic" in program.casefold()
    assert "Guid.NewGuid" in program
    assert "runSuffix" in program
    assert "p3-headless-learning-card-" in program
    assert "p3-headless-learning-review-" in program


def test_headless_learning_smoke_replays_review_idempotently_and_reads_one_event() -> None:
    program = PROGRAM.read_text(encoding="utf-8")

    assert program.count('PostJsonAsync(supervisor, "/api/v1/learning/reviews"') == 2
    assert 'replay.RootElement.TryGetProperty("duplicate", out var duplicate)' in program
    assert "duplicate.ValueKind != JsonValueKind.True" in program
    assert 'RequiredInt64(events[0], "event_id")' in program
    assert 'RequiredInt64(latest, "event_id") != reviewEventId' in program
    assert "events.GetArrayLength() != 1" in program


def test_review_failure_paths_never_report_success_and_keep_retry_identity() -> None:
    shell = _shell_source()
    submit = _region(shell, "private async void OnSubmitReviewClick")

    assert "SetStatus(LearningReviewStatusText, \"复习提交失败：请先载入复习项目。\", \"error\")" in submit
    assert "SetStatus(LearningReviewStatusText, \"复习提交失败：请输入回答。\", \"error\")" in submit
    assert "permissionDenied ?" in submit
    assert "复习提交被 Core 拒绝：请检查会话或权限范围。" in submit
    assert 'permissionDenied ? "permission" : "error"' in submit
    assert "复习提交中断；请以 Core 回执为准。" in submit
    assert submit.index("_activeReviewEventId ??=") < submit.index("var payload =")
    assert "SubmitReviewButton.IsEnabled = true;" in submit
    assert "LearningAnswerBox.Text = string.Empty;" in submit
    assert submit.index("if (response.IsSuccessStatusCode)") < submit.index("ShowToast(\"复习结果已由 Core 记录\")")
    assert submit.index("ShowToast(\"复习结果已由 Core 记录\")") < submit.index("_activeReviewEventId = null;")
