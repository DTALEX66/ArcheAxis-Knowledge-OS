"""Real check worker + real adapter; only SDK transport is replaced. No paid call."""

import base64
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2] if "tests" in Path(__file__).parts else Path.cwd()


def test_dispatch_without_core_fails_closed(worker, monkeypatch):
    monkeypatch.setattr(worker, "_DISPATCH_REQUIRED", True)
    monkeypatch.delenv("ARCHEAXIS_DOCUMENT_CHECK_DISPATCH_DIR", raising=False)
    with pytest.raises(worker.CheckExecutionError, match="dispatch_unavailable"):
        worker.authorize_dispatch("model", "https://fixture.invalid/v1", {"payload": "synthetic"})


@pytest.mark.parametrize("tamper", [None, "destination", "material", "sequence", "egress_sha256", "attempt_id"])
def test_dispatch_binds_exact_operation_and_consumes_one_approval(worker, monkeypatch, tmp_path, tamper):
    monkeypatch.setattr(worker, "_DISPATCH_REQUIRED", True)
    monkeypatch.setattr(worker, "_DISPATCH_IDENTITY", {"attempt_id":"synthetic", "egress_sha256":"a" * 64})
    monkeypatch.setenv("ARCHEAXIS_DOCUMENT_CHECK_DISPATCH_DIR", str(tmp_path))
    result = Future()

    def call():
        try:
            worker.authorize_dispatch("model", "https://fixture.invalid/v1", {"payload": "synthetic"})
        except BaseException as exc:
            result.set_exception(exc)
        else:
            result.set_result("approved")

    thread = threading.Thread(target=call)
    thread.start()
    try:
        deadline = time.monotonic() + 2
        request_path = tmp_path / "request.json"
        while not request_path.exists() and time.monotonic() < deadline:
            if result.done():
                result.result()  # Surface the original worker exception in this test.
            time.sleep(.01)
        assert request_path.is_file(), "worker did not publish its dispatch request"
        assert not result.done()
        frame = json.loads(request_path.read_text(encoding="utf8"))
        assert frame["material_sha256"] == hashlib.sha256(b'{"payload":"synthetic"}').hexdigest()
        assert frame["material"] == {"payload": "synthetic"}
        assert frame["sequence"] == 1 and frame["destination"] == "https://fixture.invalid/v1"
        assert frame["kind"] == "model"
        assert frame["attempt_id"] == "synthetic" and frame["egress_sha256"] == "a" * 64
        approval = dict(frame)
        if tamper is not None:
            approval[tamper] = {
                "destination": "https://other.invalid/v1",
                "material": {"payload": "different"},
                "sequence": 2,
                "egress_sha256": "b" * 64,
                "attempt_id": "different",
            }[tamper]
        # Mirror Core dispatch.rs: write the complete frame before publishing it
        # with a same-directory rename. exists() is the worker's readiness signal.
        temporary = tmp_path / "approval.tmp"
        temporary.write_text(json.dumps(approval), encoding="utf8")
        assert not (tmp_path / "approval.json").exists()
        temporary.replace(tmp_path / "approval.json")
        if tamper is None:
            assert result.result(timeout=2) == "approved"
        else:
            with pytest.raises(worker.CheckExecutionError, match="dispatch_identity_mismatch"):
                result.result(timeout=2)
    finally:
        # authorize_dispatch has its own five-second deadline. Also join on an
        # assertion failure so monkeypatch/tmp_path cannot outlive the worker.
        thread.join(6)
        assert not thread.is_alive(), "dispatch worker did not stop by its deadline"
    assert not (tmp_path / "approval.json").exists()


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
        assert policy.max_redirects == 0, "redirects must not bypass a new Core dispatch decision"
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


@pytest.mark.parametrize("query", ["", " " * 3, "x" * 1001])
def test_search_query_is_rejected_before_network_without_silent_truncation(worker, monkeypatch, query):
    calls = []
    monkeypatch.setattr(worker, "donor", lambda name: calls.append(name))
    with pytest.raises(worker.CheckExecutionError, match="invalid_search_query"):
        worker.retrieve_context(query, 10, 1, [])
    assert calls == []


def test_professional_check_without_independent_query_never_searches(worker, monkeypatch):
    calls = []
    monkeypatch.setattr(worker, "retrieve_context", lambda *args: calls.append(args))
    req = request()
    req["dimension"] = "professional_basis"
    assert worker.execute(req)["reason"] == "search_query_required"
    assert calls == []


@pytest.mark.parametrize("usage,expected", [(None, None), ({}, None), ({"total_tokens": None}, None), ({"total_tokens": 0}, 0), ({"total_tokens": 5}, 5)])
def test_independent_query_is_the_only_search_payload(worker, monkeypatch, usage, expected):
    queries = []
    monkeypatch.setattr(worker, "retrieve_context", lambda query, *args: queries.append(query) or "Public synthetic context")
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=lambda **kwargs: {
        "model": "fixture-model",
        "choices": [{"finish_reason": "stop", "message": {"content": '{"status":"supported","basis":"Synthetic context"}'}}],
        "usage": usage,
    }))
    req = request()
    req.update(dimension="professional_basis", text="PRIVATE synthetic body must not become a query", search_query="public terminology")
    result = worker.execute(req)
    assert result["outcome"] == "succeeded"
    assert result["engine_receipt"]["tokens_used"] == expected
    assert queries == ["public terminology"]


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
        assert result["retrieval_receipts"] == []
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


@pytest.mark.parametrize("tokens", [True, False, -1, 1.5, "9"])
def test_invalid_provider_usage_is_not_coerced_to_valid_evidence(worker, monkeypatch, tokens):
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=lambda **kwargs: {
        "model": "fixture-model",
        "choices": [{"finish_reason": "stop", "message": {"content": '{"status":"faithful","basis":"Synthetic comparison"}'}}],
        "usage": {"total_tokens": tokens},
    }))
    result = worker.execute(request())
    assert result["outcome"] == "failed"
    assert result["reason"] == "invalid_engine_receipt"
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
        req["original"]["media_type"] = "audio/wav"
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


def test_actual_cli_input_byte_budget_before_sdk(worker, tmp_path):
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "services/python-workers/machine/document_check.py")],
        input=b"x" * (worker.MAX_INPUT + 1),
        env={**os.environ, "ARCHEAXIS_DOCUMENT_CHECK_DISPATCH_DIR": str(tmp_path),
             "ARCHEAXIS_DOCUMENT_CHECK_DISPATCH_HASH": "a" * 64},
        capture_output=True,
        timeout=10,
    )
    assert json.loads((tmp_path / "ready.json").read_text()) == {
        "schema": "archeaxis.egress-dispatch/v1", "egress_sha256": "a" * 64}
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


@pytest.mark.parametrize(
    "message,code,stage,status",
    [
        ("HTTP total timeout exceeded", "timeout", "transport", None),
        ("DNS resolution failed for secret.example", "dns", "dns", None),
        ("blocked address: private-address", "policy", "policy", None),
        ("HTTP status 503", "http_status", "http_response", 503),
    ],
    ids=["timeout", "dns", "policy", "status"],
)
def test_retrieval_failure_safe_classification_is_durable(
    worker, monkeypatch, message, code, stage, status
):
    # SIMULATED transport failure; no request or SDK call.
    http = load(ROOT / "shared/safe_http.py", "classified_http_fixture")

    def fail(*args, **kwargs):
        raise http.SafeHTTPError(message)

    monkeypatch.setattr(http, "fetch", fail)
    monkeypatch.setattr(
        worker,
        "donor",
        lambda name: (
            http if name == "safe_http" else (_ for _ in ()).throw(AssertionError("SDK forbidden"))
        ),
    )
    req = request()
    req["dimension"] = "professional_basis"
    req["search_query"] = "public background terminology"
    result = worker.execute(req)
    assert result["outcome"] == "failed" and result["reason"] == "retrieval_failed"
    failure = result["retrieval_receipts"][-1]
    assert failure == {
        "kind": "retrieval_failure",
        "reason": "retrieval_failed",
        "failure_code": code,
        "failure_stage": stage,
        **({"http_status": status} if status else {}),
    }
    assert message not in json.dumps(failure)


def test_untyped_transport_module_failure_never_discloses_messages(worker, monkeypatch):
    # SIMULATED custom donor lacks SafeHTTPError; fallback must stay compatible.
    http = load(ROOT / "shared/safe_http.py", "generic_http_policy_fixture")
    secret_message = "https://private.invalid/?token=fixture-secret proxy-address"

    def fail(*args, **kwargs):
        raise RuntimeError(secret_message)

    fake = SimpleNamespace(SafeHTTPPolicy=http.SafeHTTPPolicy, fetch=fail)
    monkeypatch.setattr(worker, "donor", lambda name: fake)
    req = request()
    req["dimension"] = "professional_basis"
    req["search_query"] = "public background terminology"
    result = worker.execute(req)
    assert result["outcome"] == "failed" and result["reason"] == "retrieval_failed"
    assert result["retrieval_receipts"] == [
        {
            "kind": "retrieval_failure",
            "reason": "retrieval_failed",
            "failure_code": "transport",
            "failure_stage": "transport",
        }
    ]
    encoded = json.dumps(result)
    assert "private.invalid" not in encoded and "fixture-secret" not in encoded
    assert "proxy-address" not in encoded
