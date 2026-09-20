from __future__ import annotations

import pytest

from shared.provider_routing import (
    ProviderRoutingError,
    ProviderRoutingSnapshot,
)


def _valid() -> dict:
    return {
        "schema_version": "archeaxis.provider-routing/v1",
        "generation": 3,
        "providers": {
            "text-v1": {
                "version": "1.0.0",
                "manifest_version": "1.0",
                "manifest_sha256": "a" * 64,
                "manifest_ref": "installed/text-v1/plugin-manifest.json",
                "installed": True,
                "enabled": True,
                "health": {"status": "healthy", "receipt_ref": "receipts/text-v1.json"},
            },
            "text-v0": {
                "version": "0.9.0",
                "manifest_version": "1.0",
                "manifest_sha256": "b" * 64,
                "manifest_ref": "installed/text-v0/plugin-manifest.json",
                "installed": True,
                "enabled": True,
                "health": {"status": "healthy", "receipt_ref": "receipts/text-v0.json"},
            },
        },
        "routes": {
            "text.extract": {
                "default_provider": "text-v1",
                "fallback_providers": ["text-v0"],
            }
        },
    }


def test_valid_snapshot_preserves_generation_and_order() -> None:
    snapshot = ProviderRoutingSnapshot.from_mapping(_valid())
    assert snapshot.generation == 3
    assert snapshot.routes["text.extract"].fallback_providers == ("text-v0",)
    assert snapshot.providers["text-v1"].health.status == "healthy"


@pytest.mark.parametrize("field", ["schema_version", "generation"])
def test_snapshot_rejects_invalid_top_level(field: str) -> None:
    data = _valid()
    data[field] = "wrong" if field == "schema_version" else -1
    with pytest.raises(ProviderRoutingError):
        ProviderRoutingSnapshot.from_mapping(data)


def test_snapshot_rejects_default_provider_that_is_not_enabled() -> None:
    data = _valid()
    data["providers"]["text-v1"]["enabled"] = False
    with pytest.raises(ProviderRoutingError, match="enabled"):
        ProviderRoutingSnapshot.from_mapping(data)


def test_snapshot_rejects_duplicate_or_overlapping_fallbacks() -> None:
    data = _valid()
    data["routes"]["text.extract"]["fallback_providers"] = ["text-v0", "text-v0"]
    with pytest.raises(ProviderRoutingError, match="duplicate"):
        ProviderRoutingSnapshot.from_mapping(data)

    data = _valid()
    data["routes"]["text.extract"]["fallback_providers"] = ["text-v1"]
    with pytest.raises(ProviderRoutingError, match="default"):
        ProviderRoutingSnapshot.from_mapping(data)


@pytest.mark.parametrize("field", ["manifest_ref", "health_receipt"])
def test_snapshot_rejects_unsafe_relative_references(field: str) -> None:
    data = _valid()
    if field == "manifest_ref":
        data["providers"]["text-v1"]["manifest_ref"] = "../outside.json"
    else:
        data["providers"]["text-v1"]["health"]["receipt_ref"] = "C:/outside.json"
    with pytest.raises(ProviderRoutingError, match="reference"):
        ProviderRoutingSnapshot.from_mapping(data)


@pytest.mark.parametrize("reference", ["folder\\file.json", "folder\x00file.json"])
def test_snapshot_rejects_backslash_or_nul_references(reference: str) -> None:
    data = _valid()
    data["providers"]["text-v1"]["manifest_ref"] = reference
    with pytest.raises(ProviderRoutingError, match="reference"):
        ProviderRoutingSnapshot.from_mapping(data)


def test_snapshot_rejects_whitespace_identity_keys() -> None:
    data = _valid()
    data["routes"][" text.extract "] = data["routes"].pop("text.extract")
    with pytest.raises(ProviderRoutingError, match="identity"):
        ProviderRoutingSnapshot.from_mapping(data)


def test_snapshot_rejects_whitespace_fallback_identity() -> None:
    data = _valid()
    data["routes"]["text.extract"]["fallback_providers"] = [" text-v0 "]
    with pytest.raises(ProviderRoutingError, match="identity"):
        ProviderRoutingSnapshot.from_mapping(data)


def test_unknown_health_is_not_promoted_to_healthy() -> None:
    data = _valid()
    data["providers"]["text-v1"]["health"] = {"status": "unknown"}
    snapshot = ProviderRoutingSnapshot.from_mapping(data)
    assert snapshot.providers["text-v1"].health.status == "unknown"
    assert snapshot.providers["text-v1"].health.is_healthy is False
