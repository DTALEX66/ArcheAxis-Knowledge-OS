"""R6 A09 domain pack contract and manifest tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.domain_pack_v1 import DomainPackV1

ROOT = Path(__file__).resolve().parents[1]


def test_four_domain_manifests_validate_under_one_contract():
    paths = sorted((ROOT / "config" / "domain-packs").glob("*.json"))
    assert [p.stem for p in paths] == ["design", "general", "math-physics", "programming"]
    packs = [DomainPackV1.model_validate(json.loads(p.read_text(encoding="utf-8"))) for p in paths]
    assert {p.domain for p in packs} == {"general", "math_physics", "programming", "design"}
    assert all(p.status == "contract_only" for p in packs)
    assert all(p.source_policy == "canonical_only" for p in packs)


def test_domain_pack_rejects_unknown_learning_mode_and_status():
    payload = json.loads((ROOT / "config/domain-packs/general.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        DomainPackV1.model_validate({**payload, "learning_modes": ["watch_only"]})
    with pytest.raises(ValidationError):
        DomainPackV1.model_validate({**payload, "status": "published"})


def test_versioned_schema_is_present_and_requires_canonical_policy():
    schema = json.loads((ROOT / "packages/contracts/v1/domain-pack.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.domain-pack/v1"
    assert "source_policy" in schema["required"]
