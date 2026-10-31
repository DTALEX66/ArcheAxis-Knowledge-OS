"""Canonical DTO bounds for explicit forum selection and honest research fallback."""
import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "packages/contracts/v1/core-document.schema.json").read_text("utf-8"))


def validator(name):
    return Draft202012Validator({"$defs": SCHEMA["$defs"], "$ref": f"#/$defs/{name}"})


def test_optional_forum_selection_preserves_legacy_request_and_rejects_arbitrary_sites():
    request = {"workspace_id": "workspace", "restore_epoch": "epoch", "request_id": "query",
               "query": "synthetic public terms", "families": ["community"], "limit": 3}
    check = validator("PublicResearchRequest")
    assert not list(check.iter_errors(request))
    for site in ["academia", "stats"]:
        assert not list(check.iter_errors({**request, "community_site": site}))
    for site in ["stackoverflow", "https://private.invalid", None, []]:
        assert list(check.iter_errors({**request, "community_site": site}))


def test_receipt_allows_four_explicit_provider_channels_but_no_unbounded_or_unknown_pool():
    channel = {"family": "research", "provider": "crossref", "status": "complete",
               "retrieved_at": "2026-10-26T00:00:00Z", "request_url": "https://api.crossref.org/works",
               "retry_after_seconds": None, "error_code": None, "hits": [], "raw_source": None,
               "raw_representation": "http_entity_body_bytes"}
    check = validator("PublicResearchChannelDto")
    assert not list(check.iter_errors(channel))
    assert list(check.iter_errors({**channel, "provider": "arbitrary_search_engine"}))
    receipt = {"schema": "archeaxis.public-research-receipt/v1", "workspace_id": "workspace",
               "restore_epoch": "epoch", "request_id": "query", "query": "synthetic public terms",
               "families": ["encyclopedia", "community", "research"], "limit": 3, "state": "partial",
               "channels": [copy.deepcopy(channel) for _ in range(4)], "reason_code": None,
               "provider_stop_state": "unknown", "knowledge_admission": "not_executed", "community_site": "stats"}
    check = validator("PublicResearchReceiptDto")
    assert not list(check.iter_errors(receipt))
    receipt["channels"].append(copy.deepcopy(channel))
    assert list(check.iter_errors(receipt))
