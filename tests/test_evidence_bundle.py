"""AXW-024B: CrossValidation and EvidenceBundle.

A bundle groups evidence about one claim with explicit relations
(supports/refutes/qualifies), cross-source comparison, conflict detection, and
a human-review gate. Untrusted (caller-supplied) bundles require review.
"""
from __future__ import annotations

import pytest

from app.evidence.bundle import (
    BundleRelation,
    EvidenceBundleError,
    build_evidence_bundle,
)


def _node(eid, claim="claim-1", provenance="server_verified"):
    from app.evidence.graph import EvidenceNode

    return EvidenceNode(
        evidence_id=eid,
        claim_id=claim,
        source_locator="local-content://sha256/" + eid.replace("-", "")[:64].ljust(64, "a"),
        generation="workspace-local-intake-v1",
        requires_human_review=(provenance == "caller_supplied"),
        provenance_status=provenance,
    )


def test_bundle_groups_relations_and_supports_cross_source() -> None:
    bundle = build_evidence_bundle(
        claim_id="claim-1",
        evidence=[
            _node("ev-1"),
            _node("ev-2"),
            _node("ev-3"),
        ],
        relations=[
            BundleRelation(evidence_id="ev-1", kind="supports"),
            BundleRelation(evidence_id="ev-2", kind="refutes"),
            BundleRelation(evidence_id="ev-3", kind="qualifies"),
        ],
    )
    assert bundle.claim_id == "claim-1"
    assert len(bundle.evidence) == 3
    assert bundle.relation_for("ev-1") == "supports"
    assert bundle.relation_for("ev-2") == "refutes"
    assert bundle.relation_for("ev-3") == "qualifies"
    # Cross-source: each node carries a distinct locator.
    assert len({e.source_locator for e in bundle.evidence}) == 3


def test_conflict_detection() -> None:
    bundle = build_evidence_bundle(
        claim_id="claim-1",
        evidence=[_node("ev-a"), _node("ev-b")],
        relations=[
            BundleRelation(evidence_id="ev-a", kind="supports"),
            BundleRelation(evidence_id="ev-b", kind="refutes"),
        ],
    )
    assert bundle.has_conflict is True
    assert "supports" in bundle.conflict_reason and "refutes" in bundle.conflict_reason


def test_caller_supplied_bundle_requires_review() -> None:
    from app.evidence.graph import EvidenceNode

    bad = EvidenceNode(
        evidence_id="ev-c-bad",
        claim_id="claim-1",
        source_locator="local-content://sha256/" + "c" * 64,
        generation="workspace-local-intake-v1",
        requires_human_review=False,
        provenance_status="caller_supplied",
    )
    with pytest.raises(EvidenceBundleError, match="caller-supplied bundle requires human review"):
        build_evidence_bundle(
            claim_id="claim-1",
            evidence=[bad],
            relations=[BundleRelation(evidence_id="ev-c-bad", kind="supports")],
        )


def test_invalid_relation_kind_rejected() -> None:
    with pytest.raises(EvidenceBundleError, match="invalid relation"):
        build_evidence_bundle(
            claim_id="claim-1",
            evidence=[_node("ev-d")],
            relations=[BundleRelation(evidence_id="ev-d", kind="uncertain")],
        )


def test_relation_must_reference_bundle_evidence() -> None:
    with pytest.raises(EvidenceBundleError, match="relation references unknown evidence"):
        build_evidence_bundle(
            claim_id="claim-1",
            evidence=[_node("ev-e")],
            relations=[BundleRelation(evidence_id="ev-missing", kind="supports")],
        )
