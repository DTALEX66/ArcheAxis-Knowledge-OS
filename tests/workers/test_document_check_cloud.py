"""Real check worker + real adapter; only SDK transport is replaced. No paid call."""

import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2] if "tests" in Path(__file__).parts else Path.cwd()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def worker(monkeypatch):
    worker = load(
        ROOT / "services/python-workers/machine/document_check.py", "real_document_check_fixture"
    )
    http = load(ROOT / "shared/safe_http.py", "actual_cloud_http_transport_fixture")
    original_donor = worker.donor

    def fetch(url, *, policy):
        assert isinstance(policy, http.SafeHTTPPolicy)
        body = (
            b'<a class="result-link" href="https://example.org/background">Background</a>'
            if "duckduckgo" in url
            else (
                "<html><body><main><article><p>"
                + "Background terminology. " * 30
                + "</p></article></main></body></html>"
            ).encode()
        )
        return http.SafeHTTPResponse(
            url=url, status=200, headers={"content-type": "text/html"}, body=body
        )

    monkeypatch.setattr(http, "fetch", fetch)
    monkeypatch.setattr(
        worker, "donor", lambda name: http if name == "safe_http" else original_donor(name)
    )
    return worker


def request():
    raw = b"Original"
    return {
        "schema": "archeaxis.document-check.request/v1",
        "attempt_id": "attempt",
        "request_check_id": "pending",
        "document_id": "document",
        "version": 1,
        "content_sha256": "a" * 64,
        "dimension": "recognition_fidelity",
        "text": "Original",
        "original": {
            "media_type": "text/plain",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "content_base64": base64.b64encode(raw).decode(),
        },
        "recognition": {"job_id": "job", "result_sha256": "b" * 64, "text": "Original"},
        "config": {
            "provider": "openai",
            "model": "openai/explicit-model",
            "endpoint": None,
            "max_tokens": 512,
            "timeout_seconds": 10,
            "search_limit": 1,
        },
    }


@pytest.mark.parametrize("finish", ["missing", None, "", "length", "tool_calls", "stop"])
def test_actual_sdk_finish_field_cannot_be_fabricated(worker, monkeypatch, finish):
    choice = {
        "message": {"content": json.dumps({"status": "faithful", "basis": "SDK transport fixture"})}
    }
    if finish != "missing":
        choice["finish_reason"] = finish
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)
        return {"choices": [choice], "model": "actual-sdk-model", "usage": {"total_tokens": 9}}

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=completion))
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    result = worker.execute(request())
    assert calls[0]["model"] == "openai/explicit-model"
    if finish == "stop":
        assert result["outcome"] == "succeeded"
        assert result["engine_receipt"]["model"] == "actual-sdk-model"
        assert (
            result["engine_receipt"]["response_sha256"]
            == hashlib.sha256(result["raw_response"].encode()).hexdigest()
        )
    else:
        assert result["outcome"] == "failed"
        if finish in ("length", "tool_calls"):
            assert result["engine_receipt"]["finish_reason"] == finish
            assert result["raw_response"] == choice["message"]["content"]
        else:
            assert result["engine_receipt"] is None


@pytest.mark.parametrize("model", ["missing", None, ""])
def test_actual_sdk_model_missing_is_not_requested_model(worker, monkeypatch, model):
    payload = {
        "choices": [
            {
                "message": {"content": '{"status":"faithful","basis":"fixture"}'},
                "finish_reason": "stop",
            }
        ]
    }
    if model != "missing":
        payload["model"] = model
    monkeypatch.setitem(
        sys.modules, "litellm", SimpleNamespace(completion=lambda **kwargs: payload)
    )
    assert worker.execute(request())["reason"] == "actual_model_unverified"


@pytest.mark.parametrize(
    "case,reason",
    [
        ("config", "not_configured"),
        ("original", "original_digest_mismatch"),
        ("media", "unsupported_original_media"),
    ],
)
def test_invalid_bound_input_never_calls_sdk(worker, monkeypatch, case, reason):
    def forbidden(**kwargs):
        raise AssertionError("SDK must not be reached")

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=forbidden))
    req = request()
    if case == "config":
        req["config"]["model"] = ""
    if case == "original":
        req["original"]["sha256"] = "c" * 64
    if case == "media":
        req["original"]["media_type"] = "application/pdf"
    assert worker.execute(req)["reason"] == reason


def test_actual_safe_http_policy_response_and_restricted_url():
    http = load(ROOT / "shared/safe_http.py", "real_check_safe_http_fixture")
    policy = http.SafeHTTPPolicy(
        timeout=10,
        max_bytes=500000,
        allowed_hosts=("lite.duckduckgo.com",),
        allowed_content_types=("text/html",),
    )
    response = http.SafeHTTPResponse(
        url="https://lite.duckduckgo.com/lite/", status=200, headers={}, body=b"<html></html>"
    )
    assert response.body == b"<html></html>" and policy.max_bytes == 500000
    with pytest.raises(http.SafeHTTPError):
        http._validate_url("http://127.0.0.1/", policy)


def test_actual_cli_input_byte_budget_before_sdk(worker):
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "services/python-workers/machine/document_check.py")],
        input=b"x" * (worker.MAX_INPUT + 1),
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert len(result.stdout) < worker.MAX_OUTPUT
    assert json.loads(result.stdout)["reason"] == "invalid_request"


@pytest.mark.parametrize(
    "raw,finish,reason",
    [
        ("not JSON", "stop", "execution_failed"),
        ('{"status":"faithful","basis":"partial"}', "length", "model_response_truncated"),
        ('{"status":"supported","basis":"wrong dimension"}', "stop", "invalid_model_verdict"),
        ("界" * 11000, "stop", "invalid_model_response"),
    ],
    ids=["invalid-json", "truncated", "wrong-status", "oversize-utf8"],
)
def test_failed_provider_output_retained_with_budget(worker, monkeypatch, raw, finish, reason):
    # SIMULATED SDK transport; no network/model accuracy assertion.
    payload = {
        "choices": [{"message": {"content": raw}, "finish_reason": finish}],
        "model": "actual-sdk-model",
        "usage": {"total_tokens": 9},
    }
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=lambda **kw: payload))
    result = worker.execute(request())
    assert result["outcome"] == "failed" and result["reason"] == reason
    engine = result["engine_receipt"]
    encoded = raw.encode("utf8")
    assert engine["response_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert engine["response_bytes"] == len(encoded)
    assert engine["model"] == "actual-sdk-model"
    assert engine["raw_response_stored"] is (len(encoded) <= 32000)
    assert result["raw_response"] == (raw if len(encoded) <= 32000 else "")
    if len(encoded) > 32000:
        assert engine["raw_response_omission_reason"] == "response_budget_exceeded"
