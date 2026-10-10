"""G4: a machine answer is a labelled candidate, and a broken call is a named failure.

The answer's wording is not pinned here - a model's phrasing is not a fact this repository can fix -
but the failure paths and the labelling are, because "the model produced nothing" must never become
an empty answer, and a truncated answer must never look like a finished one.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "machine" / "worker_machine_answer.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


machine = _load("worker_machine_under_test", WORKER)


def test_a_question_is_required_rather_than_answering_nothing():
    # An answer to no question is not a task, so the route refuses instead of returning model noise.
    with pytest.raises(ValueError) as raised:
        machine.answer("some context", "")
    assert "question is required" in str(raised.value)


def test_a_context_is_required_rather_than_answering_ungrounded():
    # The whole point of grounding is that the answer comes from accepted material. Without a context
    # the model would answer from its weights, which is a different capability with a different risk.
    with pytest.raises(ValueError) as raised:
        machine.answer("", "what is it?")
    assert "context is required" in str(raised.value)


def test_an_empty_model_answer_is_a_named_failure_not_an_empty_success(monkeypatch):
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *a, **k: ("", "length"))

    with pytest.raises(ValueError) as raised:
        machine.answer("context", "question", max_tokens=8)
    message = str(raised.value)
    # the budget is named, because that is what the caller has to change
    assert "no answer within 8 tokens" in message
    assert "length" in message


def test_a_truncated_answer_is_reported_as_a_loss_not_as_an_answer(monkeypatch):
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *a, **k: ("a partial answer", "length"))

    result = machine.answer("context", "question", max_tokens=16)
    receipt = result["loss_receipt"]
    assert result["truncated"] is True
    assert receipt["params"]["finish_reason"] == "length"
    assert receipt["params"]["max_tokens"] == 16
    kinds = [loss["kind"] for loss in receipt["losses"]]
    assert kinds == ["truncated_answer"], receipt


def test_a_finished_answer_carries_no_loss(monkeypatch):
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *a, **k: ("a complete answer", "stop"))

    result = machine.answer("context", "question")
    assert result["truncated"] is False
    assert result["loss_receipt"]["losses"] == []
    assert result["loss_receipt"]["params"]["finish_reason"] == "stop"


def test_the_answer_is_labelled_a_candidate_and_never_knowledge(monkeypatch):
    """The receipt is the promise: a reader must see that this is unreviewed model output."""
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *a, **k: ("an answer", "stop"))

    result = machine.answer("context", "question")
    receipt = result["loss_receipt"]
    assert receipt["params"]["authority"] == "candidate"
    assert "human review" in receipt["loss_note"]
    assert "not accepted knowledge" in receipt["loss_note"]
    # and nothing claims the model was trained or that knowledge changed
    blob = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in ("accuracy", "promoted", "trained"):
        assert forbidden not in blob, forbidden


def test_extract_forwards_the_token_budget(monkeypatch, tmp_path):
    """A budget that is accepted and then dropped makes the flag a lie.

    This is the bug the test exists for: `--max-tokens` was parsed, then `extract` did not take it,
    so every call silently used the default and a deliberately small budget still reported the
    default's finish reason.
    """
    seen: dict = {}

    def fake_call(endpoint, model, prompt, timeout_s, max_tokens):
        seen["max_tokens"] = max_tokens
        return "an answer", "stop"

    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", fake_call)

    context = tmp_path / "ctx.txt"
    context.write_text("some accepted material", encoding="utf-8")
    result = machine.extract(str(context), "question", max_tokens=777)

    assert seen["max_tokens"] == 777
    assert result["loss_receipt"]["params"]["max_tokens"] == 777
    assert result["max_tokens"] == 777
    assert result["finish_reason"] == "stop"
    assert result["truncated"] is False
    assert isinstance(result["elapsed_s"], (int, float))


def test_route_extraction_preserves_actual_truncation_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(machine, "_endpoint", lambda: {
        "protocol": "openai", "base": "http://127.0.0.1:1/v1", "model": "m", "discovered": True})
    monkeypatch.setattr(machine, "_call", lambda *args, **kwargs: ("partial answer", "length"))
    context = tmp_path / "ctx.txt"
    context.write_text("synthetic accepted material", encoding="utf-8")
    result = machine.extract(str(context), "question", max_tokens=128)
    assert result["finish_reason"] == result["loss_receipt"]["params"]["finish_reason"] == "length"
    assert result["truncated"] is True
    assert result["max_tokens"] == 128
    assert result["elapsed_s"] >= 0
    assert result["loss_receipt"]["losses"][0]["kind"] == "truncated_answer"


def test_a_missing_context_file_is_a_named_failure(tmp_path):
    with pytest.raises(ValueError) as raised:
        machine.extract(str(tmp_path / "absent.txt"), "question")
    assert "context file not found" in str(raised.value)


def test_extract_without_a_question_is_refused(tmp_path):
    context = tmp_path / "ctx.txt"
    context.write_text("some accepted material", encoding="utf-8")
    with pytest.raises(ValueError) as raised:
        machine.extract(str(context), None)
    assert "needs a question" in str(raised.value)


def test_the_worker_identity_and_engine_are_declared():
    assert machine.WORKER_IDENTITY == "python-worker-machine-answer-ndjson"
    assert machine.ENGINE == "python-worker-machine-answer"
    # the prompt version is part of reproducibility, so it must be non-empty and dated
    assert machine.PROMPT_VERSION.startswith("archeaxis.vnext/")
