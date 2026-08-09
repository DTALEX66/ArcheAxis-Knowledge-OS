"""AXW-024A: Claim/Evidence core graph.

A Claim may be backed by multiple Evidence items. Every Evidence node must be
traceable to a source locator, a generation method, a review state and
provenance. The validator rejects evidence that points at a different claim,
that is caller-supplied without human review, or a claim with no evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class ClaimEvidenceError(ValueError):
    """Raised when a Claim/Evidence graph is invalid."""


@dataclass(frozen=True)
class EvidenceNode:
    evidence_id: str
    claim_id: str
    source_locator: str
    generation: str
    requires_human_review: bool
    provenance_status: str


@dataclass(frozen=True)
class ClaimEvidenceGraph:
    claim_id: str
    claim_statement: str
    evidence: list[EvidenceNode] = field(default_factory=list)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)


def _validate_evidence_node(node: EvidenceNode) -> None:
    if not node.source_locator:
        raise ClaimEvidenceError("evidence requires a source locator")
    if not node.generation:
        raise ClaimEvidenceError("evidence requires a generation method")
    if node.provenance_status == "caller_supplied" and not node.requires_human_review:
        raise ClaimEvidenceError("caller_supplied evidence requires human review")


def build_claim_evidence_graph(
    *, claim_id: str, claim_statement: str, evidence: list[EvidenceNode]
) -> ClaimEvidenceGraph:
    """Validate and build a Claim/Evidence graph.

    Fail-closed: a claim must have at least one evidence, every evidence must
    belong to the same claim, and each node must satisfy provenance/review
    governance.
    """
    if not claim_id:
        raise ClaimEvidenceError("claim requires an id")
    if not claim_statement:
        raise ClaimEvidenceError("claim requires a statement")
    if not evidence:
        raise ClaimEvidenceError("claim requires at least one evidence")

    for node in evidence:
        if node.claim_id != claim_id:
            raise ClaimEvidenceError("evidence belongs to a different claim")
        _validate_evidence_node(node)

    return ClaimEvidenceGraph(
        claim_id=claim_id,
        claim_statement=claim_statement,
        evidence=list(evidence),
    )
