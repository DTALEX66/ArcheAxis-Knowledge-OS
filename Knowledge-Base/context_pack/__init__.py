"""ContextPack builder — assembles context for Cognitive-OS execution."""

from dataclasses import dataclass, field


@dataclass
class ContextPack:
    context_id: str = ""
    goal: str = ""
    sources: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    token_budget: int = 4000

    def to_dict(self) -> dict:
        return {
            "context_id": self.context_id,
            "goal": self.goal,
            "sources": self.sources,
            "evidence": self.evidence,
            "constraints": self.constraints,
            "token_budget": self.token_budget,
        }


def build_context_pack(goal: str, sources: list = None, constraints: list = None) -> ContextPack:
    import uuid

    return ContextPack(
        context_id=f"ctx_{uuid.uuid4().hex[:12]}",
        goal=goal,
        sources=sources or [],
        constraints=constraints or [],
    )
