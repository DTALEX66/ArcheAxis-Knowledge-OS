"""EngineeringContract generator from IntakeCard."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EngineeringContract:
    contract_id: str = ""
    goal: str = ""
    deliverables: list = field(default_factory=list)
    acceptance_criteria: list = field(default_factory=list)
    blocked_actions: list = field(default_factory=list)
    target_repo: str = ""
    risk_level: str = "low"

    def to_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "goal": self.goal,
            "deliverables": self.deliverables,
            "acceptance_criteria": self.acceptance_criteria,
            "blocked_actions": self.blocked_actions,
            "target_repo": self.target_repo,
            "risk_level": self.risk_level,
        }


def generate_contract(
    goal: str,
    deliverables: list,
    acceptance_criteria: Optional[list] = None,
    blocked_actions: Optional[list] = None,
    risk_level: str = "low",
    target_repo: str = "Cognitive-OS",
) -> EngineeringContract:
    import uuid
    return EngineeringContract(
        contract_id=f"contract_{uuid.uuid4().hex[:12]}",
        goal=goal,
        deliverables=deliverables,
        acceptance_criteria=acceptance_criteria or [],
        blocked_actions=blocked_actions or [],
        risk_level=risk_level,
        target_repo=target_repo,
    )
