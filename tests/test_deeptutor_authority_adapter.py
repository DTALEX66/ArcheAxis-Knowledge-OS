"""DeepTutor authority bridge: projection-only and fail-closed truth firewall."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.adapters.deeptutor.authority import (
    AuthorityBoundaryError,
    DeepTutorAuthorityAdapter,
)


def _canonical_records() -> list[dict[str, object]]:
    return [
        {
            "source_id": "src-1",
            "sha256": "a" * 64,
            "rights": "owned",
            "anchors": [
                {
                    "anchor_id": "anchor-1",
                    "source_id": "src-1",
                    "selector": {"type": "TextQuoteSelector", "exact": "BKT"},
                }
            ],
        }
    ]


def test_projection_is_deterministic_and_rebuildable(tmp_path: Path):
    adapter = DeepTutorAuthorityAdapter(tmp_path)
    first = adapter.rebuild_projection(_canonical_records())
    first_bytes = (tmp_path / "authority-projection.json").read_bytes()

    adapter.delete_projection()
    assert not (tmp_path / "authority-projection.json").exists()

    second = adapter.rebuild_projection(_canonical_records())
    second_bytes = (tmp_path / "authority-projection.json").read_bytes()
    assert first["projection_sha256"] == second["projection_sha256"]
    assert first_bytes == second_bytes
    assert second["record_count"] == 1


def test_inbound_result_accepts_learning_event_but_rejects_truth_writes(tmp_path: Path):
    adapter = DeepTutorAuthorityAdapter(tmp_path)
    event = adapter.accept_learning_result(
        {
            "event_id": "evt-1",
            "learner_id": "learner-1",
            "source_ref": "anchor-1",
            "kind": "quiz_attempt",
            "outcome": {"score": 0.8},
        }
    )
    assert event["status"] == "candidate"
    assert event["kind"] == "quiz_attempt"

    for forbidden in (
        {"verified": True},
        {"machine_level": "K8"},
        {"knowledge_status": "verified"},
        {"human_mastery": "M7"},
    ):
        payload = {
            "event_id": "evt-bad",
            "learner_id": "learner-1",
            "source_ref": "anchor-1",
            "kind": "quiz_attempt",
            "outcome": {},
            **forbidden,
        }
        with pytest.raises(AuthorityBoundaryError, match="truth-bearing"):
            adapter.accept_learning_result(payload)


def test_projection_manifest_contains_no_absolute_paths(tmp_path: Path):
    adapter = DeepTutorAuthorityAdapter(tmp_path)
    adapter.rebuild_projection(_canonical_records())
    payload = json.loads((tmp_path / "projection-manifest.json").read_text(encoding="utf-8"))
    assert payload["data_scope"] == "derived-rebuildable"
    assert "D:/" not in json.dumps(payload)
    assert "C:/" not in json.dumps(payload)
