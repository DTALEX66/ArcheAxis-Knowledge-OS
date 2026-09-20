"""R6 A11 local model capability pool tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.model_pool_v1 import ModelCapabilityPoolV1

ROOT = Path(__file__).resolve().parents[1]


def test_repository_model_pool_has_role_specific_fallbacks():
    payload = json.loads((ROOT / "config/model-profiles/r6-capability-pool.json").read_text(encoding="utf-8"))
    pool = ModelCapabilityPoolV1.model_validate(payload)
    assert {entry.role for entry in pool.entries} >= {"asr", "ocr", "vision_caption", "llm_text", "embedding"}
    assert all(entry.fallback for entry in pool.entries)
    assert any(entry.status == "unmeasured" for entry in pool.entries)
    assert pool.benchmark_status == "partial"


def test_model_entry_rejects_missing_fallback_and_negative_memory():
    payload = json.loads((ROOT / "config/model-profiles/r6-capability-pool.json").read_text(encoding="utf-8"))
    bad = {**payload, "entries": [{**payload["entries"][0], "fallback": ""}]}
    with pytest.raises(ValidationError):
        ModelCapabilityPoolV1.model_validate(bad)
    bad_memory = {**payload, "entries": [{**payload["entries"][0], "memory_mib": -1}]}
    with pytest.raises(ValidationError):
        ModelCapabilityPoolV1.model_validate(bad_memory)


@pytest.mark.parametrize("status", ["measured_current", "measured_historical"])
def test_measured_model_entry_requires_evidence_reference(status):
    payload = json.loads((ROOT / "config/model-profiles/r6-capability-pool.json").read_text(encoding="utf-8"))
    bad = {
        **payload,
        "entries": [{**payload["entries"][0], "status": status, "evidence_refs": []}],
    }
    with pytest.raises(ValidationError, match="evidence_refs"):
        ModelCapabilityPoolV1.model_validate(bad)


def test_versioned_schema_is_present_and_declares_benchmark_status():
    schema = json.loads((ROOT / "packages/contracts/v1/model-capability-pool.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.model-capability-pool/v1"
    assert "benchmark_status" in schema["required"]
