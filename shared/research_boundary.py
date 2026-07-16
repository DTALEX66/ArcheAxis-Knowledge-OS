"""Shared boundary for unreviewed external and Phase 4 candidate references."""

from __future__ import annotations

from collections.abc import Iterable

_BLOCKED_REFERENCE_PREFIXES = (
    "research_package_",
    "intake_",
    "source_",
    "claim_",
    "evidence_",
    "finding_",
    "http://",
    "https://",
)


def unreviewed_research_references(references: Iterable[object]) -> tuple[str, ...]:
    """Return explicit candidate/external references that require Phase 5 review provenance."""
    blocked: list[str] = []
    for raw in references:
        value = str(raw).strip()
        if value.lower().startswith(_BLOCKED_REFERENCE_PREFIXES):
            blocked.append(value)
    return tuple(blocked)
