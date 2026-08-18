"""Learning capabilities registry + orchestrator — absorbed from DeepTutor.

DeepTutor routes requests to the right capability via a ChatOrchestrator and
gates teaching order by mastery. This module provides the same shape as a
local, deterministic registry (NOT an agent harness — report §3.5, A4):

    CapabilityRegistry
        register(name, description, handler, risk)
        route(intent, context)      → capability (keyword intent matching)
        list() / get(name)

    mastery_gate(node_state, registry)
        → ordered capability names gated by the mastery-gap action
          (TEACH_HUMAN → learn/quiz/teach_back; DISTILL_HUMAN → distill;
           REVIEW_EVIDENCE → evidence_review; …)

Handlers are plain callables over existing modules; nothing auto-executes
high-risk capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.knowledge.dual_mastery import GapAction, KnowledgeNodeState

Handler = Callable[[dict[str, Any]], dict[str, Any]]

_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "learn": ("学", "learn", "teach", "教", "讲解", "tutor", "explain"),
    "quiz": ("测验", "quiz", "练习", "practice", "做题", "test"),
    "path": ("路径", "path", "计划", "plan", "先修", "prerequisite", "路线"),
    "teach_back": ("复述", "teach", "teach-back", "检验", "check", "讲给"),
    "review": ("复习", "review", "recall", "遗忘", "due"),
    "distill": ("蒸馏", "distill", "经验", "规则", "采访", "interview", "沉淀"),
    "evidence": ("证据", "evidence", "核验", "过时", "outdated", "验证"),
}


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    handler: Handler
    risk: str = "low"

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.risk == "high":
            raise ValueError(f"high-risk capability requires review: {self.name}")
        return self.handler(payload)


class CapabilityError(ValueError):
    """Raised when a registry operation is invalid."""


class CapabilityRegistry:
    """Name-keyed registry of learning capabilities with intent routing."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        if not capability.name.strip():
            raise CapabilityError("capability name is required")
        if capability.name in self._capabilities:
            raise CapabilityError(f"capability already registered: {capability.name}")
        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Capability:
        if name not in self._capabilities:
            raise CapabilityError(f"unknown capability: {name}")
        return self._capabilities[name]

    def list(self) -> list[dict[str, Any]]:
        return [{"name": c.name, "description": c.description, "risk": c.risk}
                for c in sorted(self._capabilities.values(), key=lambda c: c.name)]

    def route(self, intent: str) -> Capability:
        """Pick the capability whose intent keywords best match the request."""
        if not intent.strip():
            raise CapabilityError("intent is required")
        text = intent.lower()
        # score = sum of matched keyword lengths: longer, more specific
        # phrases ("学习路径" → path via "路径") outrank single-char hits.
        best: tuple[int, str] = (0, "")
        for name, keywords in _INTENT_KEYWORDS.items():
            score = sum(len(k) for k in keywords if k in text)
            if score > best[0]:
                best = (score, name)
        if best[0] <= 0:
            raise CapabilityError(f"no capability matched intent: {intent}")
        return self.get(best[1])


def mastery_gate(node: KnowledgeNodeState, registry: CapabilityRegistry) -> list[str]:
    """Order capabilities by the node's mastery-gap action (teaching order)."""
    order: dict[GapAction, tuple[str, ...]] = {
        GapAction.TEACH_HUMAN: ("learn", "quiz", "teach_back"),
        GapAction.DISTILL_HUMAN: ("distill",),
        GapAction.COLLABORATE: ("quiz", "teach_back"),
        GapAction.LEARN_FIRST: ("learn", "quiz"),
        GapAction.REVIEW_EVIDENCE: ("evidence",),
    }
    desired = order.get(node.action, ())
    available = [name for name in desired if name in registry._capabilities]
    return available


def default_registry() -> CapabilityRegistry:
    """Registry wired to the existing learning modules (thin adapters)."""
    from app.learning.learning_path import build_path
    from app.learning.quiz import generate_quiz

    registry = CapabilityRegistry()

    def learn_handler(payload: dict[str, Any]) -> dict[str, Any]:
        concept = str(payload["concept"])
        reference = str(payload["reference"])
        items = generate_quiz(concept=concept, reference=reference,
                              key_terms=payload.get("key_terms"))
        return {"kind": "learn", "plan": {"concept": concept,
                                          "teach_back_reference": reference},
                "quiz": [i.as_dict() for i in items]}

    def quiz_handler(payload: dict[str, Any]) -> dict[str, Any]:
        items = generate_quiz(concept=str(payload["concept"]),
                              reference=str(payload["reference"]),
                              key_terms=payload.get("key_terms"),
                              other_concepts=payload.get("other_concepts"))
        return {"kind": "quiz", "items": [i.as_dict() for i in items]}

    def path_handler(payload: dict[str, Any]) -> dict[str, Any]:
        path = build_path(goal=str(payload["goal"]),
                          graph=dict(payload.get("graph") or {}),
                          mastery_map=dict(payload.get("mastery_map") or {}))
        return {"kind": "path", "goal": path.goal, "steps": path.as_list()}

    def teach_back_handler(payload: dict[str, Any]) -> dict[str, Any]:
        from app.knowledge.teach_back_eval import score_teach_back
        evaluation = score_teach_back(
            record_id=str(payload.get("record_id", "orchestrator")),
            concept=str(payload["concept"]), restatement=str(payload["restatement"]),
            reference=str(payload["reference"]), key_terms=payload.get("key_terms"))
        return {"kind": "teach_back", "overall": evaluation.overall,
                "passes": evaluation.passes()}

    def distill_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return {"kind": "distill", "status": "distill_required",
                "statement": payload.get("statement") or "（待补充专家原则）",
                "note": "调用 distillation.record_principle 记录候选原则"}

    def evidence_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return {"kind": "evidence_review", "status": "review_required",
                "reason": "证据非 current：核验 valid_to/supersedes/contradicts"}

    registry.register(Capability("learn", "生成学习计划与入门测验", learn_handler))
    registry.register(Capability("quiz", "生成测验题目", quiz_handler))
    registry.register(Capability("path", "构建个性化学习路径", path_handler))
    registry.register(Capability("teach_back", "Teach-Back 理解检验", teach_back_handler))
    registry.register(Capability("distill", "人机蒸馏：候选原则→规则→技能", distill_handler))
    registry.register(Capability("evidence", "证据核验（过时/冲突）", evidence_handler))
    return registry
