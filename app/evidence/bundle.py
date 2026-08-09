"""AXW-024B: CrossValidation and EvidenceBundle.

A bundle groups evidence about one claim with explicit relations
(supports/refutes/qualifies), cross-source comparison, conflict detection, and
a human-review gate. Caller-supplied bundles require review (fail-closed);
invalid relations and unknown-evidence references are rejected.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.evidence.graph import EvidenceNode

_VALID_KINDS = {"supports", "refutes", "qualifies"}


class EvidenceBundleError(ValueError):
    """Raised when an evidence bundle is invalid."""


@dataclass(frozen=True)
class BundleRelation:
    evidence_id: str
    kind: str


@dataclass(frozen=True)
class EvidenceBundle:
    claim_id: str
    evidence: list[EvidenceNode] = field(default_factory=list)
    relations: list[BundleRelation] = field(default_factory=list)

    def relation_for(self, evidence_id: str) -> str | None:
        for r in self.relations:
            if r.evidence_id == evidence_id:
                return r.kind
        return None

    @property
    def has_conflict(self) -> bool:
        kinds = {r.kind for r in self.relations}
        return "supports" in kinds and "refutes" in kinds

    @property
    def conflict_reason(self) -> str:
        kinds = sorted({r.kind for r in self.relations})
        return "mixed relations: " + ", ".join(kinds)


def build_evidence_bundle(
    *,
    claim_id: str,
    evidence: list[EvidenceNode],
    relations: list[BundleRelation],
) -> EvidenceBundle:
    """Validate and build an EvidenceBundle.

    Fail-closed: every relation must reference bundle evidence with a valid
    kind, and a caller-supplied bundle (any evidence without human review)
    must require review.
    """
    evidence_by_id = {e.evidence_id: e for e in evidence}
    if not evidence_by_id:
        raise EvidenceBundleError("bundle requires at least one evidence")

    for relation in relations:
        if relation.kind not in _VALID_KINDS:
            raise EvidenceBundleError(f"invalid relation kind: {relation.kind}")
        if relation.evidence_id not in evidence_by_id:
            raise EvidenceBundleError(
                f"relation references unknown evidence: {relation.evidence_id}"
            )

    for node in evidence:
        if node.claim_id != claim_id:
            raise EvidenceBundleError("evidence belongs to a different claim")
        if node.provenance_status == "caller_supplied" and not node.requires_human_review:
            raise EvidenceBundleError(
                "caller-supplied bundle requires human review"
            )

    return EvidenceBundle(
        claim_id=claim_id,
        evidence=list(evidence),
        relations=list(relations),
    )
