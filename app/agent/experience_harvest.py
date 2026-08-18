"""Experience harvesting — absorbed from Meta Knowledge Graph (neo4j-labs).

A harness-agnostic memory layer captures agent-session lifecycle events,
distills durable learnings, and injects them back as reusable principles
(report §3.7). This module converts raw lifecycle events into trajectories
and reuses the reasoning-memory engine (ReasoningBank-style) for reflection:

    lifecycle events (task_started / tool_called / task_ended / observation)
        → trajectory draft → reasoning_memory.save_trajectory + reflect
        → principles (success_pattern / failure_pattern / strategy)

Deterministic; LLM reflection is optional and never required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.memory.reasoning_memory import (
    ReasoningPrinciple,
    reflect,
    save_trajectory,
)

_TASK_START = "task_started"
_TASK_END = "task_ended"
_TOOL_CALL = "tool_called"
_OBSERVATION = "observation"


class HarvestError(ValueError):
    """Raised when lifecycle events cannot be harvested."""


@dataclass(frozen=True)
class LifecycleEvent:
    kind: str
    ts: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def started(cls, goal: str, ts: str) -> "LifecycleEvent":
        return cls(kind=_TASK_START, ts=ts, payload={"goal": goal})

    @classmethod
    def tool_called(cls, tool: str, ts: str) -> "LifecycleEvent":
        return cls(kind=_TOOL_CALL, ts=ts, payload={"tool": tool})

    @classmethod
    def ended(cls, outcome: str, ts: str, error: str | None = None) -> "LifecycleEvent":
        return cls(kind=_TASK_END, ts=ts, payload={"outcome": outcome, "error": error})


@dataclass(frozen=True)
class TrajectoryDraft:
    goal: str
    steps: list[str]
    outcome: str
    error_pattern: str | None


def events_to_trajectory(events: list[LifecycleEvent]) -> TrajectoryDraft:
    """Convert lifecycle events into one trajectory draft (pure)."""
    if not events:
        raise HarvestError("events must be non-empty")
    goal = ""
    steps: list[str] = []
    outcome = "success"
    error: str | None = None
    for event in events:
        if event.kind == _TASK_START:
            goal = str(event.payload.get("goal", "")).strip()
        elif event.kind == _TOOL_CALL:
            tool = str(event.payload.get("tool", "")).strip()
            if tool:
                steps.append(tool)
        elif event.kind == _TASK_END:
            outcome = str(event.payload.get("outcome", "success")).strip()
            error = event.payload.get("error")
    if not goal:
        raise HarvestError("events must include a task_started with a goal")
    return TrajectoryDraft(goal=goal, steps=steps or ["run"],
                           outcome=outcome, error_pattern=error)


def capture(
    db: str | Path,
    events: list[LifecycleEvent],
    *,
    llm_reflection: str | None = None,
) -> list[ReasoningPrinciple]:
    """Harvest one session: save trajectory + reflect into a principle."""
    draft = events_to_trajectory(events)
    if draft.outcome == "failure" and not draft.error_pattern:
        raise HarvestError("failed trajectories require a task_ended error payload")
    trajectory = save_trajectory(
        db, goal=draft.goal, steps=draft.steps, outcome=draft.outcome,  # type: ignore[arg-type]
        error_pattern=draft.error_pattern, importance=0.6,
    )
    principle = reflect(db, trajectory.trajectory_id, llm_reflection=llm_reflection)
    return [principle]
