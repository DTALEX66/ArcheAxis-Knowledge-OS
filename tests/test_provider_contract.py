"""Tests for Provider/Model capability contract."""

from __future__ import annotations

import pytest

from shared.provider_contract import (
    CapabilityStatus,
    DryRunRoute,
    ModelCapability,
    ProviderContract,
    ProviderKind,
)


def test_provider_contract_fields_are_frozen_and_non_empty():
    contract = ProviderContract(
        provider_id="deepseek",
        name="DeepSeek",
        kind=ProviderKind.LLM,
        capabilities=[
            ModelCapability(name="chat", status=CapabilityStatus.SUPPORTED),
            ModelCapability(name="tool_calling", status=CapabilityStatus.PLANNED),
        ],
    )
    assert contract.provider_id == "deepseek"
    assert contract.kind == ProviderKind.LLM
    assert contract.api_requires_key is True
    assert contract.requires_human_review is True
    assert len(contract.capabilities) == 2


def test_dry_run_routes_are_immutable():
    route = DryRunRoute(
        provider_id="deepseek",
        model_id="deepseek-v4-flash",
        kind=ProviderKind.LLM,
        status=CapabilityStatus.CANDIDATE,
    )
    assert route.provider_id == "deepseek"
    assert route.status == CapabilityStatus.CANDIDATE


def test_provider_kind_covers_all_known_domains():
    kinds = {k.value for k in ProviderKind}
    assert "llm" in kinds
    assert "embedding" in kinds
    assert "vision" in kinds
    assert "crawler" in kinds
    assert "vector_db" in kinds


def test_default_routes_start_empty():
    from shared.provider_contract import DEFAULT_ROUTES

    assert DEFAULT_ROUTES == []
    assert isinstance(DEFAULT_ROUTES, list)


@pytest.mark.parametrize(
    ("field", "value"),
    [("provider_id", "  "), ("name", "  ")],
)
def test_provider_contract_rejects_blank_identity(field, value):
    values = {
        "provider_id": "deepseek",
        "name": "DeepSeek",
        "kind": ProviderKind.LLM,
    }
    values[field] = value
    with pytest.raises(ValueError, match="required"):
        ProviderContract(**values)


def test_provider_contract_rejects_ambiguous_capabilities():
    with pytest.raises(ValueError, match="unique"):
        ProviderContract(
            provider_id="deepseek",
            name="DeepSeek",
            kind=ProviderKind.LLM,
            capabilities=[
                ModelCapability(name="chat"),
                ModelCapability(name="chat"),
            ],
        )


def test_dry_run_route_rejects_blank_model_identity():
    with pytest.raises(ValueError, match="model_id"):
        DryRunRoute(
            provider_id="deepseek",
            model_id="  ",
            kind=ProviderKind.LLM,
        )
