"""IntakeCard generator from research notes and project profiles."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IntakeCard:
    intake_id: str = ""
    title: str = ""
    why: str = ""
    what_to_absorb: list = field(default_factory=list)
    what_not_to_absorb: list = field(default_factory=list)
    source_ids: list = field(default_factory=list)
    risk_level: str = "low"
    target_repo: str = ""

    def to_dict(self) -> dict:
        return {
            "intake_id": self.intake_id,
            "title": self.title,
            "why": self.why,
            "what_to_absorb": self.what_to_absorb,
            "what_not_to_absorb": self.what_not_to_absorb,
            "source_ids": self.source_ids,
            "risk_level": self.risk_level,
            "target_repo": self.target_repo,
        }


def generate_intake_card(
    title: str,
    why: str,
    what_to_absorb: list,
    what_not_to_absorb: Optional[list] = None,
    risk_level: str = "low",
    target_repo: str = "Knowledge-Base",
) -> IntakeCard:
    import uuid
    return IntakeCard(
        intake_id=f"intake_{uuid.uuid4().hex[:12]}",
        title=title,
        why=why,
        what_to_absorb=what_to_absorb,
        what_not_to_absorb=what_not_to_absorb or [],
        risk_level=risk_level,
        target_repo=target_repo,
    )
