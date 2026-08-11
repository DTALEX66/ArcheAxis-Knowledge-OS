"""AXW-024A: Claim/Evidence core graph.

A Claim may be backed by multiple Evidence items; each Evidence must be
traceable to a source, a generation method, a review state and provenance.
The graph validator rejects evidence that points at a different claim or
that carries inconsistent provenance/review governance.
"""
from __future__ import annotations

import pytest

from app.evidence.graph import (
    EvidenceNode,
    build_claim_evidence_graph,
)


def _evidence(evidence_id, claim_id="claim-1", provenance="caller_supplied"):
    return EvidenceNode(
        evidence_id=evidence_id,
        claim_id=claim_id,
        source_locator="local-content://sha256/" + "a" * 64,
        generation="workspace-local-intake-v1",
        requires_human_review=(provenance == "caller_supplied"),
        provenance_status=provenance,
    )


def test_claim_backed_by_multiple_evidence() -> None:
    graph = build_claim_evidence_graph(
        claim_id="claim-1",
        claim_statement="PDF extraction works",
        evidence=[
            _evidence("ev-1"),
            _evidence("ev-2"),
            _evidence("ev-3"),
        ],
    )
    assert graph.claim_id == "claim-1"
    assert len(graph.evidence) == 3
    assert graph.evidence_count == 3
    assert {e.evidence_id for e in graph.evidence} == {"ev-1", "ev-2", "ev-3"}


def test_evidence_must_belong_to_the_claim() -> None:
    with pytest.raises(ValueError, match="evidence belongs to a different claim"):
        build_claim_evidence_graph(
            claim_id="claim-1",
            claim_statement="statement",
            evidence=[_evidence("ev-other", claim_id="claim-2")],
        )


def test_evidence_provenance_governance_is_enforced() -> None:
    # caller-supplied evidence must require human review; the graph builder
    # rejects it fail-closed.
    with pytest.raises(ValueError, match="caller_supplied evidence requires human review"):
        build_claim_evidence_graph(
            claim_id="claim-1",
            claim_statement="statement",
            evidence=[
                EvidenceNode(
                    evidence_id="ev-bad",
                    claim_id="claim-1",
                    source_locator="local-content://sha256/" + "b" * 64,
                    generation="workspace-local-intake-v1",
                    requires_human_review=False,
                    provenance_status="caller_supplied",
                )
            ],
        )


def test_each_evidence_is_traceable() -> None:
    graph = build_claim_evidence_graph(
        claim_id="claim-1",
        claim_statement="statement",
        evidence=[
            _evidence("ev-1"),
            _evidence("ev-2"),
        ],
    )
    for node in graph.evidence:
        # Every evidence has a source locator, generation method, review state
        # and provenance — all required for traceability.
        assert node.source_locator.startswith("local-content://")
        assert node.generation
        assert isinstance(node.requires_human_review, bool)
        assert node.provenance_status in {"caller_supplied", "server_verified"}


def test_empty_evidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="claim requires at least one evidence"):
        build_claim_evidence_graph(
            claim_id="claim-1", claim_statement="statement", evidence=[]
        )
