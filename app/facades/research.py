"""Public facade for generating and persisting research intake candidates."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from app.research.github import research_github_repository as _research_github_repository
from inspiration_research.intake.generator import generate_intake_card
from shared.research_store import ResearchBeforeCommit, ResearchPackageGraph, load_research_package
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


def research_github_repository(
    repository_url: str,
    *,
    fetcher=None,
    db_path: str | Path | None = None,
    before_commit: ResearchBeforeCommit | None = None,
) -> ResearchPackageGraph:
    """Run the Phase 4 GitHub URL -> persisted candidate package workflow."""

    return _research_github_repository(
        repository_url,
        fetcher=fetcher,
        db_path=db_path,
        before_commit=before_commit,
    )


def get_research_package(
    package_id: str,
    *,
    db_path: str | Path | None = None,
) -> ResearchPackageGraph:
    """Load a persisted research package and all bound objects."""

    return load_research_package(package_id, db_path=db_path)
