"""TaskPack builder — executable task definitions for Cognitive-OS."""
from dataclasses import dataclass, field


@dataclass
class TaskPack:
    task_id: str = ""
    context_id: str = ""
    goal: str = ""
    steps: list = field(default_factory=list)
    allowed_tools: list = field(default_factory=list)
    blocked_tools: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    success_criteria: list = field(default_factory=list)
    risk_level: str = "low"
    requires_review: bool = False

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "context_id": self.context_id,
            "goal": self.goal, "steps": self.steps,
            "allowed_tools": self.allowed_tools, "blocked_tools": self.blocked_tools,
            "constraints": self.constraints, "success_criteria": self.success_criteria,
            "risk_level": self.risk_level, "requires_review": self.requires_review,
        }


def build_taskpack(goal: str, steps: list = None, allowed_tools: list = None,
                   risk_level: str = "low") -> TaskPack:
    import uuid
    return TaskPack(
        task_id=f"task_{uuid.uuid4().hex[:12]}",
        goal=goal, steps=steps or [],
        allowed_tools=allowed_tools or ["echo", "file_read"],
        blocked_tools=["shell_exec", "code_exec", "delete_file"],
        risk_level=risk_level,
    )
