"""Public facade for generating and persisting research intake candidates."""

from __future__ import annotations

from pydantic import BaseModel, Field

from inspiration_research.intake.generator import generate_intake_card
from shared.storage import insert


class ResearchIntakeResult(BaseModel):
    intake_id: str
    title: str
    why: str
    what_to_absorb: list[str] = Field(default_factory=list)
    what_not_to_absorb: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    target_repo: str = "Knowledge-Base"


def ingest_candidate(
    *,
    title: str,
    why: str,
    what_to_absorb: list[str],
    what_not_to_absorb: list[str] | None = None,
    risk_level: str = "low",
    target_repo: str = "Knowledge-Base",
) -> ResearchIntakeResult:
    """Generate one real IntakeCard candidate and persist it under its public ID."""
    card = generate_intake_card(
        title=title,
        why=why,
        what_to_absorb=what_to_absorb,
        what_not_to_absorb=what_not_to_absorb,
        risk_level=risk_level,
        target_repo=target_repo,
    )
    payload = card.to_dict()
    row = {
        "id": payload["intake_id"],
        **{key: value for key, value in payload.items() if key != "intake_id"},
    }
    insert("ir_intake_cards", row)
    return ResearchIntakeResult(**payload)
