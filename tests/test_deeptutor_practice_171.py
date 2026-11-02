"""Boundaries of the DeepTutor 1.7.1 practice payload projection."""

import importlib.util
import json
from pathlib import Path

import pytest

_module_path = Path(__file__).resolve().parents[1] / "services" / "learning-providers" / "deeptutor" / "practice_171.py"
_spec = importlib.util.spec_from_file_location("deeptutor_practice_171", _module_path)
assert _spec is not None and _spec.loader is not None
_practice = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_practice)
PracticePayloadError = _practice.PracticePayloadError
check_observation = _practice.check_observation
question_view = _practice.question_view
review_observation = _practice.review_observation


def upstream_question():
    return {
        "entry": {
            "id": 17,
            "question_id": "q-one",
            "question": "Which answer is correct?",
            "question_type": "single_choice",
            "options": {"A": "first", "B": "second"},
            "correct_answer": "SENTINEL_SECRET_ANSWER",
            "explanation": "SENTINEL_SECRET_EXPLANATION",
            "user_answer": "SENTINEL_OLD_ANSWER",
            "nested": {"answer": "SENTINEL_NESTED"},
        },
        "state": {"version": 2, "secret": "SENTINEL_STATE"},
        "content_workspace_name": "SENTINEL_WORKSPACE",
    }


def test_question_view_returns_only_visible_fields_and_does_not_mutate_payload():
    payload = upstream_question()
    before = json.dumps(payload, sort_keys=True)
    result = question_view(payload)
    assert result["entry_id"] == 17
    assert result["provider_state_version"] == 2
    assert result["options"] == {"A": "first", "B": "second"}
    assert "SENTINEL" not in json.dumps(result)
    assert json.dumps(payload, sort_keys=True) == before
    assert result["visible_sha256"] == question_view(payload)["visible_sha256"]
    payload["entry"]["question"] = "A different question"
    assert result["visible_sha256"] != question_view(payload)["visible_sha256"]


@pytest.mark.parametrize("bad", [True, 0, -1, 2**53, "17", None])
def test_bad_entry_ids_are_rejected(bad):
    payload = upstream_question()
    payload["entry"]["id"] = bad
    with pytest.raises(PracticePayloadError):
        question_view(payload)


@pytest.mark.parametrize("bad", [True, -1, 2**53, "2", None])
def test_bad_provider_versions_are_rejected(bad):
    payload = upstream_question()
    payload["state"]["version"] = bad
    with pytest.raises(PracticePayloadError):
        question_view(payload)


def test_unknown_grade_is_never_converted_into_correct_or_mastered():
    assert check_observation({"correct": None}) == {
        "provider_correct": None,
        "grading": "ungraded",
        "independent_mastery": "not_established",
    }
    result = review_observation(
        {"correct": None, "self_report": True, "rating": "easy", "mastered": True}
    )
    assert result["provider_correct"] is None
    assert result["grading"] == "self_report"
    assert result["independent_mastery"] == "not_established"
    assert "mastered" not in result


@pytest.mark.parametrize("bad", [1, "true", [], {}])
def test_malformed_or_ambiguous_grades_are_rejected(bad):
    with pytest.raises(PracticePayloadError):
        check_observation({"correct": bad})
    with pytest.raises(PracticePayloadError):
        review_observation({"correct": bad, "self_report": False, "rating": "good"})


def test_self_report_and_wrong_answer_cannot_claim_inconsistent_objective_results():
    with pytest.raises(PracticePayloadError):
        review_observation({"correct": True, "self_report": True, "rating": "good"})
    with pytest.raises(PracticePayloadError):
        review_observation({"correct": False, "self_report": False, "rating": "easy"})


def test_unknown_check_fields_and_unsafe_option_shapes_fail_closed():
    with pytest.raises(PracticePayloadError):
        check_observation({"correct": True, "mastered": True})
    payload = upstream_question()
    payload["entry"]["options"] = {"A": {"answer": "not a string"}}
    with pytest.raises(PracticePayloadError):
        question_view(payload)
