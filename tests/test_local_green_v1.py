"""R6 A13 Local Green identity and candidate evidence tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.local_green_v1 import LocalGreenIdentityV1


def _identity(**overrides):
    payload = {
        "distribution": "local-green",
        "public_release_base": "v0.6.14",
        "source_commit": "a" * 40,
        "source_tree": "b" * 40,
        "build_timestamp": "2026-09-19T00:00:00+00:00",
        "runtime_manifest_digest": "c" * 64,
        "candidate_status": "staged",
    }
    payload.update(overrides)
    return payload


def test_local_green_identity_is_not_a_public_release():
    identity = LocalGreenIdentityV1.model_validate(_identity())
    assert identity.distribution == "local-green"
    assert identity.public_release_base == "v0.6.14"
    assert identity.published is False


def test_identity_requires_exact_source_and_runtime_digests():
    with pytest.raises(ValidationError):
        LocalGreenIdentityV1.model_validate(_identity(source_commit="short"))
    with pytest.raises(ValidationError):
        LocalGreenIdentityV1.model_validate(_identity(runtime_manifest_digest="short"))


def test_versioned_schema_is_present_and_release_is_frozen():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "packages/contracts/v1/local-green-identity.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.local-green-identity/v1"
    assert schema["properties"]["published"]["const"] is False
