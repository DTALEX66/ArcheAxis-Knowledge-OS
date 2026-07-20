from __future__ import annotations

import pytest
from pydantic import ValidationError


def _approval(**overrides):
    from app.knowledge.promotion import ResearchKnowledgeApproval

    payload = {
        "approval_id": "approval-phase5-001",
        "package_id": "research-package-001",
        "reviewer_id": "human-reviewer-001",
        "decision": "approved",
        "rationale": "Reviewed the candidate research evidence; create candidate knowledge only.",
        "reviewed_at": "2026-07-20T10:00:00+00:00",
    }
    payload.update(overrides)
    return ResearchKnowledgeApproval(**payload)


def test_research_knowledge_approval_is_explicit_and_auditable() -> None:
    approval = _approval()

    assert approval.decision == "approved"
    assert approval.package_id == "research-package-001"
    assert approval.reviewer_id == "human-reviewer-001"
    assert approval.rationale


@pytest.mark.parametrize(
    "overrides",
    [
        {"approval_id": ""},
        {"package_id": ""},
        {"reviewer_id": ""},
        {"rationale": ""},
        {"decision": "auto_approved"},
        {"reviewed_at": ""},
    ],
)
def test_research_knowledge_approval_rejects_missing_or_implicit_governance(overrides) -> None:
    with pytest.raises(ValidationError):
        _approval(**overrides)
