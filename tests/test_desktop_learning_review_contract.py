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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "apps" / "ArcheAxis.Desktop" / "MainWindow.axaml.cs"
CORE = ROOT / "crates" / "archeaxis-api" / "src" / "lib.rs"


def _shell_source() -> str:
    return SHELL.read_text(encoding="utf-8")


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
    assert "client_event_id = _activeReviewEventId" in payload
    assert "exposure_id = _activeExposureId" in payload
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
    assert "assessment_id = _activeAssessmentId" in submit
    assert "knowledge_version = _activeKnowledgeVersion" in submit


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
