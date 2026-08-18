"""Learning path builder — absorbed from OpenTutor / adaptive-knowledge-graph.

Uses the prerequisite graph (concept → prerequisite edges, e.g. from
app.memory.graph_db) plus per-concept mastery to produce a personalized,
ordered learning path: prerequisites come first, weak areas are scheduled
early, already-mastered concepts are skipped (or turned into review).

Pure function over a plain graph representation so it is fully testable
without a database:
    graph = {"nodes": ["a", "b", "c"], "edges": [("a", "b"), ("b", "c")]}
    (edge source → target means source is a prerequisite of target)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PathKind = Literal["must_learn", "review", "prerequisite_gap"]


class LearningPathError(ValueError):
    """Raised when the path builder receives invalid input."""


@dataclass(frozen=True)
class PathStep:
    concept: str
    kind: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {"concept": self.concept, "kind": self.kind, "reason": self.reason}


@dataclass(frozen=True)
class LearningPath:
    goal: str
    steps: tuple[PathStep, ...]

    def as_list(self) -> list[dict[str, Any]]:
        return [step.as_dict() for step in self.steps]


def _validate_graph(graph: dict[str, Any]) -> tuple[list[str], list[tuple[str, str]]]:
    nodes = list(graph.get("nodes", []))
    edges = [tuple(e) for e in graph.get("edges", [])]
    if not nodes:
        raise LearningPathError("graph requires at least one node")
    node_set = set(nodes)
    for src, tgt in edges:
        if src not in node_set or tgt not in node_set:
            raise LearningPathError(f"edge references unknown node: ({src}, {tgt})")
    return nodes, edges


def _mastery_of(mastery_map: dict[str, Any], concept: str) -> float:
    value = mastery_map.get(concept, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_path(
    *,
    goal: str,
    graph: dict[str, Any],
    mastery_map: dict[str, Any] | None = None,
    weak_threshold: float = 0.5,
) -> LearningPath:
    """Return an ordered learning path toward *goal*.

    Steps:
      1. collect the dependency closure of the goal (prerequisites),
      2. order by topological constraints (prerequisites first),
      3. annotate each step: must_learn (weak), review (mastered), or
         prerequisite_gap (missing entirely from mastery map).
    """
    if not goal.strip():
        raise LearningPathError("goal is required")
    nodes, edges = _validate_graph(graph)
    mastery_map = mastery_map or {}
    if not 0.0 <= weak_threshold <= 1.0:
        raise LearningPathError("weak_threshold must be in [0,1]")
    if goal not in nodes:
        raise LearningPathError(f"goal not in graph: {goal}")

    # dependency closure: reverse edges (target ← source prerequisites)
    prereqs: dict[str, set[str]] = {n: set() for n in nodes}
    for src, tgt in edges:
        prereqs[tgt].add(src)

    closure: set[str] = set()
    stack = [goal]
    while stack:
        current = stack.pop()
        for p in prereqs.get(current, set()):
            if p not in closure:
                closure.add(p)
                stack.append(p)
    closure.add(goal)

    # topological order (Kahn) restricted to the closure
    closure_list = sorted(closure)
    indegree = {n: 0 for n in closure_list}
    dependents: dict[str, list[str]] = {n: [] for n in closure_list}
    for src, tgt in edges:
        if src in closure and tgt in closure:
            indegree[tgt] += 1
            dependents[src].append(tgt)
    ready = sorted([n for n in closure_list if indegree[n] == 0])
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for dep in sorted(dependents.get(node, [])):
            indegree[dep] -= 1
            if indegree[dep] == 0:
                ready.append(dep)
    if len(order) != len(closure_list):
        raise LearningPathError("prerequisite graph contains a cycle")

    steps: list[PathStep] = []
    for concept in order:
        mastery = _mastery_of(mastery_map, concept)
        if concept == goal:
            steps.append(PathStep(concept=concept, kind="must_learn",
                                  reason="目标概念"))
        elif concept not in mastery_map:
            steps.append(PathStep(concept=concept, kind="prerequisite_gap",
                                  reason="先修缺口（无掌握数据）"))
        elif mastery < weak_threshold:
            steps.append(PathStep(concept=concept, kind="must_learn",
                                  reason=f"先修薄弱（掌握度 {mastery:.2f}）"))
        else:
            steps.append(PathStep(concept=concept, kind="review",
                                  reason=f"先修已掌握（{mastery:.2f}），复习即可"))
    return LearningPath(goal=goal, steps=tuple(steps))
