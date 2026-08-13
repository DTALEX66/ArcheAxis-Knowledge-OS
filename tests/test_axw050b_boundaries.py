"""AXW-050B: fail-safe boundary tests for grounded answers.

Each failure mode must produce a structured verdict and must never fall
through to an ungrounded completion: provider down → failed; scope
mismatch → forbidden; expired/revoked → stale; conflicting evidence →
conflict; thin context → insufficient_context; unresolvable anchors →
refused.
"""

from __future__ import annotations

import pytest

from app.answer.boundaries import BoundaryError, answer_with_boundaries
from app.answer.grounded import GroundedClaim
from app.evidence.anchor import build_evidence_anchor, store_evidence_anchor
from app.evidence.relations import record_relation
from app.knowledge.freshness import record_event


@pytest.fixture()
def dbs(tmp_path) -> dict[str, str]:
    evidence = str(tmp_path / "evidence.sqlite")
    freshness = str(tmp_path / "freshness.sqlite")
    relations = str(tmp_path / "relations.sqlite")
    anchor = build_evidence_anchor("a" * 64, "rev1", {"page_number": 1})
    store_evidence_anchor(evidence, anchor)
    # unit u1: activated, scoped to "math", one supporting relation.
    record_event(freshness, unit_id="u1", event_type="activate", actor="sys", scope="math")
    record_relation(relations, claim_id="u1", evidence_id=anchor.anchor_id, kind="supports", actor="sys", reviewed=True)
    return {"evidence": evidence, "freshness": freshness, "relations": relations}


def _claims(anchor_id: str) -> list[GroundedClaim]:
    return [GroundedClaim(statement="A grounded fact.", anchor_id=anchor_id)]


def _happy(dbs: dict[str, str], anchor_id: str, **overrides) -> dict:
    params = dict(
        evidence_db=dbs["evidence"],
        freshness_db=dbs["freshness"],
        relation_db=dbs["relations"],
        claim_id="u1",
        scope="math",
        claims=_claims(anchor_id),
        context_score=0.9,
        provider_available=True,
    )
    params.update(overrides)
    return params


def test_success_grounded(dbs: dict[str, str]) -> None:
    anchor_id = build_evidence_anchor("a" * 64, "rev1", {"page_number": 1}).anchor_id
    verdict = answer_with_boundaries(**_happy(dbs, anchor_id))
    assert verdict.status == "success"
    assert verdict.answer is not None and verdict.answer.grounded is True


def test_provider_unavailable_fails_closed(dbs: dict[str, str]) -> None:
    anchor_id = build_evidence_anchor("a" * 64, "rev1", {"page_number": 1}).anchor_id
    verdict = answer_with_boundaries(**_happy(dbs, anchor_id, provider_available=False))
    assert verdict.status == "failed"
    assert verdict.answer is None


def test_scope_mismatch_forbidden(dbs: dict[str, str]) -> None:
    anchor_id = build_evidence_anchor("a" * 64, "rev1", {"page_number": 1}).anchor_id
    verdict = answer_with_boundaries(**_happy(dbs, anchor_id, scope="history"))
    assert verdict.status == "forbidden"
    assert verdict.answer is None


def test_revoked_evidence_is_stale(dbs: dict[str, str]) -> None:
    record_event(dbs["freshness"], unit_id="u1", event_type="revoke", actor="human")
    anchor_id = build_evidence_anchor("a" * 64, "rev1", {"page_number": 1}).anchor_id
    verdict = answer_with_boundaries(**_happy(dbs, anchor_id))
    assert verdict.status == "stale"
    assert verdict.answer is None


def test_conflicting_evidence_requires_adjudication(dbs: dict[str, str]) -> None:
    anchor_id = build_evidence_anchor("a" * 64, "rev1", {"page_number": 1}).anchor_id
    # Second active relation refutes the claim → conflict.
    record_relation(dbs["relations"], claim_id="u1", evidence_id="e-other", kind="refutes", actor="sys2")
    verdict = answer_with_boundaries(**_happy(dbs, anchor_id))
    assert verdict.status == "conflict"
    assert verdict.answer is None


def test_insufficient_context(dbs: dict[str, str]) -> None:
    anchor_id = build_evidence_anchor("a" * 64, "rev1", {"page_number": 1}).anchor_id
    verdict = answer_with_boundaries(**_happy(dbs, anchor_id, context_score=0.1))
    assert verdict.status == "insufficient_context"
    assert verdict.answer is None


def test_ungrounded_refused(dbs: dict[str, str]) -> None:
    # Claim references an anchor that was never stored in evidence_db.
    verdict = answer_with_boundaries(**_happy(dbs, "ev_ghost_anchor"))
    assert verdict.status == "refused"
    assert verdict.answer is None
    assert any("ungrounded" in r for r in verdict.reasons)


def test_missing_claim_id_is_configuration_error(dbs: dict[str, str]) -> None:
    with pytest.raises(BoundaryError, match="claim_id"):
        answer_with_boundaries(
            evidence_db=dbs["evidence"],
            freshness_db=dbs["freshness"],
            relation_db=dbs["relations"],
            claim_id="",
            scope=None,
            claims=[],
        )
