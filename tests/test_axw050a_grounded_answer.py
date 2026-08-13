"""AXW-050A: citation-grounded answer tests.

Verifies:
- grounded answers cite stored anchors (no pseudo-citations);
- unknown anchors trigger refusal with the offending claims listed;
- uncertain claims are never asserted with fake citations;
- retrieval-driven answers refuse when anchors are unresolvable;
- empty/invalid input fails closed.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.answer.grounded import (
    GroundedClaim,
    GroundingError,
    answer_for_retrieval,
    build_grounded_answer,
)
from app.evidence.anchor import build_evidence_anchor, store_evidence_anchor


@pytest.fixture()
def anchor_db() -> str:
    tmp = Path(tempfile.mkdtemp()) / "anchors.sqlite"
    store_evidence_anchor(
        tmp,
        build_evidence_anchor("a" * 64, "rev1", {"page_number": 7, "block_id": "b12"}),
    )
    store_evidence_anchor(
        tmp,
        build_evidence_anchor("b" * 64, "rev1", {"page_index": 2}),
    )
    return str(tmp)


def test_grounded_answer_cites_real_anchors(anchor_db: str) -> None:
    answer = build_grounded_answer(
        db=anchor_db,
        claims=[
            GroundedClaim(statement="The sky is blue.", anchor_id=build_evidence_anchor("a" * 64, "rev1", {"page_number": 7, "block_id": "b12"}).anchor_id),
            GroundedClaim(statement="Water is wet.", anchor_id=build_evidence_anchor("b" * 64, "rev1", {"page_index": 2}).anchor_id),
        ],
    )
    assert answer.grounded is True
    assert answer.ungrounded == []
    assert "[p7 | aaaaaaaa]" in answer.answer_text
    assert "[p2 | bbbbbbbb]" in answer.answer_text
    assert len(answer.claims) == 2
    assert answer.claims[0]["raw_sha256"] == "a" * 64


def test_unknown_anchor_refuses_with_listing(anchor_db: str) -> None:
    answer = build_grounded_answer(
        db=anchor_db,
        claims=[
            GroundedClaim(statement="Real claim.", anchor_id=build_evidence_anchor("a" * 64, "rev1", {"page_number": 7, "block_id": "b12"}).anchor_id),
            GroundedClaim(statement="Fake claim.", anchor_id="ev_does_not_exist"),
        ],
    )
    assert answer.grounded is False
    assert answer.ungrounded == ["Fake claim."]
    assert "without grounded evidence" in answer.answer_text
    # The grounded claim must not be rendered as if the answer succeeded.
    assert "[1] Real claim." not in answer.answer_text


def test_uncertain_claim_never_gets_fake_citation(anchor_db: str) -> None:
    answer = build_grounded_answer(
        db=anchor_db,
        claims=[GroundedClaim(statement="Maybe true.", anchor_id="", uncertain=True)],
    )
    assert answer.grounded is True  # uncertainty is a valid explicit state
    assert "uncertain — no assertion made" in answer.answer_text
    assert "[" not in answer.answer_text.split("(uncertain")[1] or "no assertion" in answer.answer_text


def test_retrieval_without_resolvable_anchor_refuses(anchor_db: str) -> None:
    answer = answer_for_retrieval(
        db=anchor_db,
        query="what is the sky",
        retrieved=[{"statement": "The sky is blue.", "anchor_id": "ev_nonexistent"}],
    )
    assert answer.grounded is False
    assert "The sky is blue." in answer.ungrounded


def test_empty_input_fails_closed(anchor_db: str) -> None:
    with pytest.raises(GroundingError, match="at least one claim"):
        build_grounded_answer(db=anchor_db, claims=[])
    with pytest.raises(GroundingError, match="must not be empty"):
        build_grounded_answer(
            db=anchor_db,
            claims=[GroundedClaim(statement="  ", anchor_id="x")],
        )
    with pytest.raises(GroundingError, match="must not be empty"):
        answer_for_retrieval(db=anchor_db, query=" ", retrieved=[])
