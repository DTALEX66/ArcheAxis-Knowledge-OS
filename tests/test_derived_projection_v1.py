"""R6 A06 derived retrieval/graph projection contract tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.derived_projection_v1 import DerivedProjectionReceiptV1


def _receipt(**overrides):
    payload = {
        "projection_id": "proj-1",
        "projection_kind": "hybrid",
        "query": "local source",
        "algorithm": "fts5+embedding+graph",
        "algorithm_version": "1.0.0",
        "canonical_source_ids": ["src-1"],
        "items": [{"source_id": "src-1", "source_revision": "rev-1", "score": 0.8, "anchor_id": "anc-1"}],
        "generated_at": "2026-09-19T00:00:00+00:00",
    }
    payload.update(overrides)
    return payload


def test_projection_receipt_is_rebuildable_and_read_only():
    receipt = DerivedProjectionReceiptV1.model_validate(_receipt())
    assert receipt.rebuildable is True
    assert receipt.writes_canonical is False
    assert receipt.items[0].source_id == "src-1"


def test_projection_cannot_reference_unknown_canonical_source():
    with pytest.raises(ValidationError, match="unknown canonical sources"):
        DerivedProjectionReceiptV1.model_validate(_receipt(
            items=[{"source_id": "src-foreign", "source_revision": "rev", "score": 0.4}]
        ))


def test_projection_requires_unique_canonical_sources_and_strict_fields():
    with pytest.raises(ValidationError, match="must be unique"):
        DerivedProjectionReceiptV1.model_validate(_receipt(canonical_source_ids=["src-1", "src-1"], items=[]))
    with pytest.raises(ValidationError):
        DerivedProjectionReceiptV1.model_validate(_receipt(invented="must fail"))


def test_versioned_schema_is_present_and_declares_projection_boundary():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "packages/contracts/v1/derived-projection.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.derived-projection/v1"
    assert schema["properties"]["writes_canonical"]["const"] is False
