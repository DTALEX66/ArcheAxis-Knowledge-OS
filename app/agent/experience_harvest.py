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

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.contracts.machine_growth_v1 import GrowthStepV1, MachineGrowthReceiptV1
from app.memory.reasoning_memory import (
    ReasoningPrinciple,
    reflect,
    save_trajectory,
)

_TASK_START = "task_started"
_TASK_END = "task_ended"
_TOOL_CALL = "tool_called"
_OBSERVATION = "observation"
_LIFECYCLE_KINDS = {_TASK_START, _TASK_END, _TOOL_CALL, _OBSERVATION}


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
        if event.kind not in _LIFECYCLE_KINDS:
            raise HarvestError(f"unknown lifecycle event: {event.kind}")
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
    principles, _receipt = capture_with_receipt(
        db, events, llm_reflection=llm_reflection
    )
    return principles


def capture_with_receipt(
    db: str | Path,
    events: list[LifecycleEvent],
    *,
    llm_reflection: str | None = None,
) -> tuple[list[ReasoningPrinciple], MachineGrowthReceiptV1]:
    """Harvest one session and return its explicit machine-growth trace.

    The trace records what this local harvester actually did.  Candidate
    promotion, human review, and reuse remain ``skipped`` until their own
    governed storage paths execute; they are never inferred from reflection.
    """
    draft = events_to_trajectory(events)
    if draft.outcome == "failure" and not draft.error_pattern:
        raise HarvestError("failed trajectories require a task_ended error payload")
    trajectory = save_trajectory(
        db, goal=draft.goal, steps=draft.steps, outcome=draft.outcome,  # type: ignore[arg-type]
        error_pattern=draft.error_pattern, importance=0.6,
    )
    principle = reflect(db, trajectory.trajectory_id, llm_reflection=llm_reflection)
    source_event_ids: list[str] = []
    seen_event_ids: dict[str, int] = {}
    for index, event in enumerate(events):
        base_id = event.ts.strip() or f"event-{index}"
        occurrence = seen_event_ids.get(base_id, 0)
        seen_event_ids[base_id] = occurrence + 1
        source_event_ids.append(base_id if occurrence == 0 else f"{base_id}-{occurrence}")
    receipt_seed = "\0".join([trajectory.trajectory_id, *source_event_ids])
    outcome = draft.outcome if draft.outcome in {"success", "failure", "partial"} else "unknown"
    receipt = MachineGrowthReceiptV1(
        receipt_id="growth_" + hashlib.sha256(receipt_seed.encode("utf-8")).hexdigest()[:24],
        source_event_ids=source_event_ids,
        goal=draft.goal,
        outcome=outcome,
        steps=[
            GrowthStepV1(stage="experience", state="observed", actor="system", evidence_refs=source_event_ids),
            GrowthStepV1(stage="lesson", state="created", actor="system", evidence_refs=[principle.principle_id]),
            GrowthStepV1(stage="skill_candidate", state="skipped", actor="system"),
            GrowthStepV1(stage="review", state="skipped", actor="system"),
            GrowthStepV1(stage="reuse", state="skipped", actor="system"),
        ],
    )
    return [principle], receipt
