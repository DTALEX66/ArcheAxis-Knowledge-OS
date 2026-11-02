"""Bounded, inert views of the DeepTutor 1.7.1 practice API.

This module does not start or identify a provider, call it, grant access, or
write learning data. The caller must separately qualify the running provider
and bind material, authorization, attempts and results through Rust Core.
The upstream question response contains the answer and explanation: only the
explicitly selected fields below may be passed to a learner before answering.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


class PracticePayloadError(ValueError):
    """An upstream practice payload is missing or outside this adapter's bounds."""


_MAX_TEXT_BYTES = 128_000
_MAX_OPTION_BYTES = 20_000
_MAX_OPTIONS = 64
_RATINGS = frozenset({"again", "hard", "good", "easy"})


def _text(value: Any, label: str, maximum: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise PracticePayloadError(f"invalid {label}")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise PracticePayloadError(f"invalid {label}") from exc
    if (not empty and not value.strip()) or size > maximum:
        raise PracticePayloadError(f"invalid {label}")
    return value


def _nonnegative_integer(value: Any, label: str, *, positive: bool = False) -> int:
    # bool is an int subclass in Python; it is never a valid upstream identity.
    if type(value) is not int or value < (1 if positive else 0) or value > 2**53 - 1:
        raise PracticePayloadError(f"invalid {label}")
    return value


def question_view(payload: Any) -> dict[str, Any]:
    """Return only the learner-visible portion of one upstream PracticeQuestion.

    ``visible_sha256`` binds the displayed text and options, not the withheld
    answer key, source Document, permission, or running-provider identity.
    ``provider_state_version`` is the upstream counter, not an AAOS revision.
    Neither value is sufficient on its own to authorize or persist an answer.
    """
    if not isinstance(payload, dict):
        raise PracticePayloadError("invalid practice question")
    entry, state = payload.get("entry"), payload.get("state")
    if not isinstance(entry, dict) or not isinstance(state, dict):
        raise PracticePayloadError("invalid practice question")
    entry_id = _nonnegative_integer(entry.get("id"), "entry id", positive=True)
    version = _nonnegative_integer(state.get("version"), "state version")
    question_id = _text(entry.get("question_id", ""), "question id", 1024, empty=True)
    question = _text(entry.get("question"), "question", _MAX_TEXT_BYTES)
    kind = _text(entry.get("question_type", ""), "question type", 256, empty=True)
    options = entry.get("options", {})
    if not isinstance(options, dict) or len(options) > _MAX_OPTIONS:
        raise PracticePayloadError("invalid options")
    safe_options: dict[str, str] = {}
    for key, value in options.items():
        key = _text(key, "option key", 256)
        value = _text(value, "option value", _MAX_OPTION_BYTES, empty=True)
        safe_options[key] = value
    visible = {
        "entry_id": entry_id,
        "question_id": question_id,
        "question": question,
        "question_type": kind,
        "options": safe_options,
    }
    encoded = json.dumps(visible, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "provider_contract": "deeptutor.practice/1.7.1",
        "provider_state_version": version,
        "visible_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        **visible,
    }


def check_observation(payload: Any) -> dict[str, Any]:
    """Preserve the upstream check's true/false/unknown distinction.

    The check endpoint does not take a question version. Its output alone does
    not prove it was computed for the question the learner saw.
    """
    if not isinstance(payload, dict) or set(payload) != {"correct"}:
        raise PracticePayloadError("invalid check result")
    correct = payload["correct"]
    if correct is not None and type(correct) is not bool:
        raise PracticePayloadError("invalid check result")
    return {
        "provider_correct": correct,
        "grading": "provider_objective" if correct is not None else "ungraded",
        "independent_mastery": "not_established",
    }


def review_observation(payload: Any) -> dict[str, Any]:
    """Map an upstream review without adopting its scheduling or mastery claim."""
    if not isinstance(payload, dict):
        raise PracticePayloadError("invalid review result")
    correct, self_report, rating = (
        payload.get("correct"),
        payload.get("self_report"),
        payload.get("rating"),
    )
    if (
        (correct is not None and type(correct) is not bool)
        or type(self_report) is not bool
        or not isinstance(rating, str)
        or rating not in _RATINGS
        or (self_report and correct is not None)
        or (correct is False and rating != "again")
    ):
        raise PracticePayloadError("invalid review result")
    return {
        "provider_correct": correct,
        "self_report": self_report,
        "rating": rating,
        "grading": "self_report" if self_report else "provider_objective" if correct is not None else "ungraded",
        "independent_mastery": "not_established",
    }
