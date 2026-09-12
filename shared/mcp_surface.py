"""R11: the capability surface an external MCP client talks to.

This module is the surface itself: the tools, their input schemas, and the dispatch that turns
one tool call into exactly one Core request. It imports nothing from the MCP SDK, so its rules
can be tested without a client, and it holds no database handle, so the Core stays the only
writer.

Two boundaries are declared here, and both are re-enforced by the Core, which is the authority:

* **No human review action.** Acceptance, rejection, deprecation and modification are human
  decisions, so they have no tool at all, and a call naming one is refused by name instead of
  being silently ignored. A machine principal may propose a candidate and read qualification.
* **An outcome is a measurement.** ``unmeasured`` is a first-class outcome, a failed task must
  state why, and nothing here may be presented as weight training or as accuracy.
"""

from __future__ import annotations

from typing import Any, Protocol

SEARCH = "archeaxis_search"
QUALIFICATION = "archeaxis_qualification"
RECORD_TASK = "archeaxis_record_task"
TASK_RECEIPT = "archeaxis_task_receipt"

OUTCOMES = ("succeeded", "failed", "unmeasured")

# The human review actions and the words a caller might use to reach for one, kept as data so a
# test can assert that neither a tool name nor a tool description offers any of them.
HUMAN_ONLY_ACTIONS = ("accepted", "rejected", "deprecated", "modified")
HUMAN_ONLY_HINTS = (
    "accept",
    "reject",
    "deprecat",
    "modif",
    "review",
    "curate",
    "promote",
    "approve",
)

MEASUREMENT_NOTE = (
    "a task receipt is a measurement fact: it is not a claim that weights were trained, and it "
    "does not turn a candidate into an accepted fact"
)

HEAD_NOTE = (
    "a returned item is a candidate or an accepted fact; the head is the first 60 characters of "
    "the body (crates/archeaxis-domain/src/search.rs), so it identifies a document without "
    "quoting it"
)

QUALIFICATION_NOTE = "check qualification before reusing a fact: an inactive revision is superseded"


class CorePort(Protocol):
    """What the surface needs from the Core. The server supplies an HTTP implementation."""

    def search(self, query: str, active_only: bool) -> tuple[int, Any]: ...

    def qualification(self, knowledge_id: str) -> tuple[int, Any]: ...

    def record_task(self, body: dict[str, Any]) -> tuple[int, Any]: ...

    def task_receipt(self, task_id: str) -> tuple[int, Any]: ...


def _spec(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TOOLS: list[dict[str, Any]] = [
    _spec(
        SEARCH,
        "Search the workspace's trusted knowledge. Returns candidates and accepted facts with "
        "the qualification flag of each. Read-only.",
        {
            "query": {"type": "string", "description": "search terms; matched as whole tokens"},
            "active_only": {
                "type": "boolean",
                "description": "only current revisions (default true)",
                "default": True,
            },
        },
        ["query"],
    ),
    _spec(
        QUALIFICATION,
        "Read whether a knowledge item exists and whether it is currently active. Read-only, and "
        "the check a consumer should make before reusing a fact.",
        {"knowledge_id": {"type": "string", "description": "knowledge id, such as k_..."}},
        ["knowledge_id"],
    ),
    _spec(
        RECORD_TASK,
        "Record a machine task receipt: conditions, versions, scope and outcome. The receipt is "
        "written by a machine principal only and is a measurement fact, never a claim that "
        "weights were trained.",
        {
            "task_id": {"type": "string", "description": "stable identifier for this task"},
            "conditions": {"type": "string", "description": "what the task was asked to do"},
            "model_version": {"type": "string", "description": "model identifier and version"},
            "scope": {"type": "string", "description": "what was in scope for the call"},
            "outcome": {"type": "string", "enum": list(OUTCOMES)},
            "knowledge_version": {"type": "string"},
            "method_version": {"type": "string"},
            "tool_version": {"type": "string"},
            "failure": {"type": "string", "description": "required when the outcome is failed"},
            "retest_of": {"type": "string", "description": "the task id this one retests"},
        },
        ["task_id", "conditions", "model_version", "scope", "outcome"],
    ),
    _spec(
        TASK_RECEIPT,
        "Read a machine task receipt back. Available to any principal, because a receipt is "
        "evidence about the machine side and grants no authority.",
        {"task_id": {"type": "string"}},
        ["task_id"],
    ),
]


class ToolError(Exception):
    """A refusal made by the surface itself, before any request reaches the Core."""


def tool_names() -> list[str]:
    return [tool["name"] for tool in TOOLS]


def tool_specs() -> list[dict[str, Any]]:
    """The tool descriptors, as data, so a server or a test can read them."""
    return [{**tool, "inputSchema": dict(tool["inputSchema"])} for tool in TOOLS]


def human_only_reach(name: str) -> str | None:
    """The human review action a tool name reaches for, or None when it reaches for none."""
    cleaned = name.lower().replace("-", "_").replace(".", "_")
    tokens = [token for token in cleaned.split("_") if token]
    for hint in HUMAN_ONLY_HINTS:
        if any(token.startswith(hint) for token in tokens):
            return hint
    return None


def _text(arguments: dict[str, Any], key: str, *, required: bool = True) -> str | None:
    value = arguments.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ToolError(f"{key!r} is required and must be a non-empty string")
        return None
    if not isinstance(value, str):
        raise ToolError(f"{key!r} must be a string")
    return value


def _flag(arguments: dict[str, Any], key: str, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ToolError(f"{key!r} must be a boolean")
    return value


def unknown_arguments(arguments: dict[str, Any], name: str) -> list[str]:
    """Argument names this tool does not declare, so a typo is refused instead of ignored."""
    declared: set[str] = set()
    for tool in TOOLS:
        if tool["name"] == name:
            declared = set(tool["inputSchema"]["properties"])
    return sorted(key for key in arguments if key not in declared)


def dispatch(name: str, arguments: dict[str, Any] | None, port: CorePort) -> dict[str, Any]:
    """Run one tool call. Refusals raise ToolError; a Core response is returned as it came."""
    arguments = {} if arguments is None else arguments
    if not isinstance(arguments, dict):
        raise ToolError("tool arguments must be an object")

    reach = human_only_reach(name)
    if reach is not None:
        raise ToolError(
            f"{name!r} is not on this surface: {reach!r} names a human review action "
            f"({', '.join(HUMAN_ONLY_ACTIONS)}), and a machine principal may only propose "
            "candidates and read qualification"
        )
    if name not in tool_names():
        raise ToolError(f"unknown tool {name!r}; this surface exposes {', '.join(tool_names())}")

    stray = unknown_arguments(arguments, name)
    if stray:
        raise ToolError(f"{name!r} does not take {', '.join(stray)}")

    if name == SEARCH:
        query = _text(arguments, "query")
        active_only = _flag(arguments, "active_only", True)
        status, payload = port.search(query, active_only)
        return {
            "tool": name,
            "request": {"method": "GET", "query": query, "active_only": active_only},
            "status": status,
            "result": payload,
            "note": HEAD_NOTE,
        }

    if name == QUALIFICATION:
        knowledge_id = _text(arguments, "knowledge_id")
        status, payload = port.qualification(knowledge_id)
        return {
            "tool": name,
            "request": {"method": "GET", "knowledge_id": knowledge_id},
            "status": status,
            "result": payload,
            "note": QUALIFICATION_NOTE,
        }

    if name == TASK_RECEIPT:
        task_id = _text(arguments, "task_id")
        status, payload = port.task_receipt(task_id)
        return {
            "tool": name,
            "request": {"method": "GET", "task_id": task_id},
            "status": status,
            "result": payload,
        }

    outcome = _text(arguments, "outcome")
    if outcome not in OUTCOMES:
        raise ToolError(f"'outcome' must be one of {', '.join(OUTCOMES)}, not {outcome!r}")
    failure = _text(arguments, "failure", required=False)
    if outcome == "failed" and failure is None:
        raise ToolError("a failed task must say why: 'failure' is required when outcome is failed")
    if outcome != "failed" and failure is not None:
        raise ToolError(f"a {outcome!r} task must not carry a failure reason")

    body = {
        "task_id": _text(arguments, "task_id"),
        "conditions": _text(arguments, "conditions"),
        "model_version": _text(arguments, "model_version"),
        "scope": _text(arguments, "scope"),
        "outcome": outcome,
        "knowledge_version": _text(arguments, "knowledge_version", required=False),
        "method_version": _text(arguments, "method_version", required=False),
        "tool_version": _text(arguments, "tool_version", required=False),
        "failure": failure,
        "retest_of": _text(arguments, "retest_of", required=False),
    }
    status, payload = port.record_task({key: value for key, value in body.items() if value is not None})
    return {
        "tool": name,
        "request": {"method": "POST", "task_id": body["task_id"], "outcome": outcome},
        "status": status,
        "result": payload,
        "note": MEASUREMENT_NOTE,
    }
