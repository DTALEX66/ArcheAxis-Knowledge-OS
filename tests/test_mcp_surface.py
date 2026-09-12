"""R11: the MCP surface exposes capabilities, not authority.

The surface is what an external client can reach, so its rules have to hold on their own: no
human review action may exist as a tool, a typo must be refused rather than ignored, an outcome
must stay a measurement, and a Core refusal must reach the client as a refusal. These tests run
without the MCP SDK, because the surface is data plus dispatch; the SDK path is exercised by
``scripts/probes/r11_mcp_client_smoke.py`` against a real Core.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "shared" / "mcp_surface.py"


def _load():
    spec = importlib.util.spec_from_file_location("mcp_surface_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


surface = _load()


class FakePort:
    """Records what the surface asked for, and answers with whatever the test decided."""

    def __init__(self, responses: dict[str, tuple[int, object]] | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.responses = responses or {}

    def _answer(self, name: str, **kwargs):
        self.calls.append((name, kwargs))
        return self.responses.get(name, (200, {"ok": True}))

    def search(self, query: str, active_only: bool):
        return self._answer("search", query=query, active_only=active_only)

    def qualification(self, knowledge_id: str):
        return self._answer("qualification", knowledge_id=knowledge_id)

    def record_task(self, body: dict):
        return self._answer("record_task", body=body)

    def task_receipt(self, task_id: str):
        return self._answer("task_receipt", task_id=task_id)


def test_the_surface_declares_exactly_the_four_capabilities():
    assert surface.tool_names() == [
        surface.SEARCH,
        surface.QUALIFICATION,
        surface.RECORD_TASK,
        surface.TASK_RECEIPT,
    ]


def test_the_surface_exposes_no_human_review_power():
    """A machine surface may propose and read; accepting stays a human decision.

    A description may *mention* accepted facts, because that is what a search result holds. What
    no tool may do is be named after a review action, or offer one to the client.
    """
    for tool in surface.tool_specs():
        assert surface.human_only_reach(tool["name"]) is None, tool["name"]
        text = tool["description"].lower()
        for action in surface.HUMAN_ONLY_ACTIONS:
            verb = action[:-2] if action.endswith("ed") else action
            for offer in (f"{verb} the", f"{verb} a", f"{verb} any", f"{verb} its"):
                assert offer not in text, f"{tool['name']} offers {offer!r}"


def test_calling_a_human_review_action_is_refused_by_name():
    port = FakePort()
    for name in ("archeaxis_accept", "archeaxis_review_decision", "archeaxis_modify_item"):
        try:
            surface.dispatch(name, {}, port)
        except surface.ToolError as refusal:
            assert "human review action" in str(refusal)
        else:
            raise AssertionError(f"{name} was not refused")
    assert port.calls == [], "a refused call must not reach the Core"


def test_an_unknown_tool_is_refused_and_told_what_exists():
    try:
        surface.dispatch("archeaxis_teleport", {}, FakePort())
    except surface.ToolError as refusal:
        assert "unknown tool" in str(refusal)
        assert surface.SEARCH in str(refusal)


def test_a_misspelled_argument_is_refused_rather_than_ignored():
    try:
        surface.dispatch(surface.SEARCH, {"querry": "aurora"}, FakePort())
    except surface.ToolError as refusal:
        assert "querry" in str(refusal)


def test_search_reads_current_revisions_unless_asked_otherwise():
    port = FakePort()
    surface.dispatch(surface.SEARCH, {"query": "aurora"}, port)
    surface.dispatch(surface.SEARCH, {"query": "aurora", "active_only": False}, port)
    assert [call[1]["active_only"] for call in port.calls] == [True, False]


def test_search_requires_a_non_empty_query():
    for arguments in ({}, {"query": ""}, {"query": "   "}):
        try:
            surface.dispatch(surface.SEARCH, arguments, FakePort())
        except surface.ToolError as refusal:
            assert "query" in str(refusal)
        else:
            raise AssertionError(f"{arguments} was accepted")


def test_a_failed_task_must_say_why():
    try:
        surface.dispatch(
            surface.RECORD_TASK,
            {"task_id": "t1", "conditions": "c", "model_version": "m", "scope": "s", "outcome": "failed"},
            FakePort(),
        )
    except surface.ToolError as refusal:
        assert "failure" in str(refusal)
    else:
        raise AssertionError("a failed task without a reason was accepted")


def test_a_successful_task_must_not_carry_a_failure_reason():
    try:
        surface.dispatch(
            surface.RECORD_TASK,
            {
                "task_id": "t1",
                "conditions": "c",
                "model_version": "m",
                "scope": "s",
                "outcome": "succeeded",
                "failure": "something",
            },
            FakePort(),
        )
    except surface.ToolError as refusal:
        assert "failure" in str(refusal)
    else:
        raise AssertionError("a successful task carrying a failure reason was accepted")


def test_unmeasured_is_a_first_class_outcome():
    port = FakePort()
    outcome = surface.dispatch(
        surface.RECORD_TASK,
        {"task_id": "t1", "conditions": "c", "model_version": "m", "scope": "s", "outcome": "unmeasured"},
        port,
    )
    assert outcome["status"] == 200
    assert port.calls[0][1]["body"]["outcome"] == "unmeasured"


def test_an_unknown_outcome_is_refused():
    try:
        surface.dispatch(
            surface.RECORD_TASK,
            {"task_id": "t1", "conditions": "c", "model_version": "m", "scope": "s", "outcome": "passed"},
            FakePort(),
        )
    except surface.ToolError as refusal:
        assert "outcome" in str(refusal)
    else:
        raise AssertionError("an outcome outside the vocabulary was accepted")


def test_absent_optional_arguments_are_left_out_of_the_receipt():
    port = FakePort()
    outcome = surface.dispatch(
        surface.RECORD_TASK,
        {"task_id": "t1", "conditions": "c", "model_version": "m", "scope": "s", "outcome": "succeeded"},
        port,
    )
    body = port.calls[0][1]["body"]
    assert set(body) == {"task_id", "conditions", "model_version", "scope", "outcome"}
    assert "measurement fact" in outcome["note"]
    assert "not a claim that weights were trained" in outcome["note"]


def test_a_core_refusal_is_returned_as_it_came_and_not_hidden():
    port = FakePort({"record_task": (400, "machine task receipts are written by a machine principal only")})
    outcome = surface.dispatch(
        surface.RECORD_TASK,
        {"task_id": "t1", "conditions": "c", "model_version": "m", "scope": "s", "outcome": "succeeded"},
        port,
    )
    assert outcome["status"] == 400
    assert "machine principal only" in outcome["result"]


def test_no_tool_promises_accuracy():
    for tool in surface.tool_specs():
        assert "accuracy" not in tool["description"].lower()


def test_every_tool_declares_arguments_a_client_can_validate():
    for tool in surface.tool_specs():
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert schema["required"], f"{tool['name']} requires nothing"
        assert set(schema["required"]) <= set(schema["properties"])
        assert schema["additionalProperties"] is False


def test_the_human_only_reach_helper_sees_through_naming_styles():
    assert surface.human_only_reach("archeaxis_accept_item") == "accept"
    assert surface.human_only_reach("archeaxis-review-decision") == "review"
    assert surface.human_only_reach("archeaxis_promote") == "promote"
    assert surface.human_only_reach(surface.SEARCH) is None
    assert surface.human_only_reach(surface.RECORD_TASK) is None
