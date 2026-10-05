import base64
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("failure", "retrieval_failed"),
        ("zero", "no_search_results"),
        ("truncated", "retrieval_truncated"),
        ("success", None),
    ],
)
def test_fidelity_public_background_never_replaces_original(monkeypatch, mode, reason):
    worker = load(
        ROOT / "services/python-workers/machine/document_check.py", "prepared_fidelity_network"
    )
    http = load(ROOT / "shared/safe_http.py", "actual_http_network_fixture")
    adapter = load(
        ROOT / "shared-contracts/adapters/llm/litellm_adapter.py", "actual_llm_network_fixture"
    )
    original = "Original exact words"
    article = (
        "Background terminology description. " * 300
        if mode == "truncated"
        else "Background terminology description. " * 30
    )

    def fetch(url, *, policy):
        assert isinstance(policy, http.SafeHTTPPolicy) and policy.max_bytes == 500000
        if mode == "failure":
            raise http.SafeHTTPError("fixture network failure")
        body = (
            (
                b"<html></html>"
                if mode == "zero"
                else b'<a class="result-link" href="https://example.org/article">Background</a>'
            )
            if "duckduckgo" in url
            else (
                "<html><head><title>Background</title></head><body><main><article><p>"
                + article
                + "</p></article></main></body></html>"
            ).encode()
        )
        return http.SafeHTTPResponse(
            url=url, status=200, headers={"content-type": "text/html"}, body=body
        )

    monkeypatch.setattr(http, "fetch", fetch)
    monkeypatch.setattr(worker, "donor", lambda name: http if name == "safe_http" else adapter)
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)
        return {
            "model": "actual-fixture",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '{"status":"faithful","basis":"Only original comparison"}'
                    },
                }
            ],
            "usage": {"total_tokens": 10},
        }

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=completion))
    req = {
        "schema": "archeaxis.document-check.request/v1",
        "attempt_id": "attempt",
        "request_check_id": "check",
        "document_id": "document",
        "version": 1,
        "content_sha256": "a" * 64,
        "dimension": "recognition_fidelity",
        "text": original,
        "original": {
            "media_type": "text/plain",
            "sha256": hashlib.sha256(original.encode()).hexdigest(),
            "content_base64": base64.b64encode(original.encode()).decode(),
        },
        "recognition": {"job_id": "job", "result_sha256": "b" * 64, "text": original},
        "config": {
            "provider": "openai",
            "model": "openai/explicit",
            "endpoint": None,
            "max_tokens": 512,
            "timeout_seconds": 10,
            "search_limit": 1,
        },
    }
    result = worker.execute(req)
    if reason:
        assert (
            result["outcome"] == "failed"
            and result["reason"] == reason
            and result["engine_receipt"] is None
        )
        assert not calls
        if mode == "zero":
            assert (
                result["status"] == "uncertain"
                and result["retrieval_receipts"][0]["result_count"] == 0
            )
        if mode == "truncated":
            assert result["status"] == "uncertain" and any(
                x.get("truncated") for x in result["retrieval_receipts"]
            )
    else:
        assert result["outcome"] == "succeeded"
        prompt = calls[0]["messages"][0]["content"]
        assert "ORIGINAL:\n" + original in prompt
        assert (
            "AUXILIARY TERMINOLOGY/BACKGROUND ONLY" in prompt
            and "Never replace or repair original words using search" in prompt
        )
        assert len(result["retrieval_receipts"]) == 2
