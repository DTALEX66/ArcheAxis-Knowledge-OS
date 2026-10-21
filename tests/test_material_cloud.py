"""Dormant protocol qualification: synthetic material, no network or native secrets."""
import json
import copy
import hashlib
import importlib.util
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "services/python-workers/machine/worker_machine_answer.py"


def invoke(tmp_path, worker=WORKER, extra=()):
    env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if k in os.environ}
    env.update({k: str(tmp_path) for k in ("HOME", "USERPROFILE", "TMP", "TEMP", "TMPDIR", "APPDATA", "LOCALAPPDATA")})
    # Child-local network trap: even accidental discovery cannot send a packet.
    marker = tmp_path / "network-attempt"
    boot = ("import socket,runpy,sys;from pathlib import Path\n"
            f"marker=Path({str(marker)!r})\n"
            "def blocked(*a,**k):\n marker.touch();raise AssertionError('network forbidden')\n"
            "socket.getaddrinfo=socket.create_connection=socket.socket.connect=blocked\n"
            f"sys.argv=[{str(worker)!r},'--material-cloud-preflight']+{list(extra)!r}\n"
            f"runpy.run_path({str(worker)!r},run_name='__main__')\n")
    result = subprocess.run([sys.executable, "-I", "-B", "-c", boot], env=env,
                            input=b"", capture_output=True, timeout=5, check=False,
                            creationflags=0x08000000 if sys.platform == "win32" else 0)
    assert not marker.exists(), "input-free preflight attempted network discovery"
    return result


def test_input_free_owned_worker_preflight_declares_not_activated(tmp_path):
    result = invoke(tmp_path)
    assert result.returncode == 0, "input-free dormant preflight unavailable"
    value = json.loads(result.stdout)
    assert value == {"schema": "archeaxis.material-cloud-preflight/v1", "purpose": "material",
                     "activation": "NOT_ACTIVATED", "protocol": "openai-buffered",
                     "network_performed": False, "model_executed": False,
                     "secret_accessed": False, "task_executed": False}


def test_preflight_staged_layout_requires_actual_helper_and_safe_http(tmp_path):
    root = tmp_path / "candidate"
    worker = root / "workers/machine/worker_machine_answer.py"
    spec = importlib.util.spec_from_file_location("material_cloud_stager", ROOT / "scripts/release/stage_backend_runtime.py")
    stager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stager)
    # Exercise the actual production worker copy rule, not a handpicked helper
    # list; only source workers are copied, never a full runtime or model.
    stager.copy_tree(ROOT / "services/python-workers", root / "workers")
    (root / "shared").mkdir()
    helper = worker.with_name("material_cloud.py")
    assert helper.read_bytes() == WORKER.with_name("material_cloud.py").read_bytes()
    assert worker.read_bytes() == WORKER.read_bytes()
    donor = root / "shared/safe_http.py"
    shutil.copy2(ROOT / "shared/safe_http.py", donor)
    assert json.loads(invoke(tmp_path, worker).stdout)["activation"] == "NOT_ACTIVATED"
    donor.unlink()
    missing = invoke(tmp_path, worker)
    assert missing.returncode == 1
    assert json.loads(missing.stdout) == {"reason_code": "MATERIAL_CLOUD_PREFLIGHT_UNAVAILABLE"}
    shutil.copy2(ROOT / "shared/safe_http.py", donor)
    helper.unlink()
    assert invoke(tmp_path, worker).returncode == 1
    assert invoke(tmp_path, WORKER, ("--probe",)).returncode != 0


@pytest.fixture
def cloud():
    spec = importlib.util.spec_from_file_location("tested_material_cloud", WORKER.with_name("material_cloud.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail("test attempted real network")
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)


def intent():
    context = "Synthetic selected material 合成😀"
    digest = hashlib.sha256(context.encode()).hexdigest()
    return {"schema": "archeaxis.material-cloud-simulation/v1", "request_id": "synthetic_request",
            "configuration": {"schema": "archeaxis.resolved-model/v1", "workspace_id": "a"*32,
                              "restore_epoch": "initial", "configuration_revision": 1,
                              "configuration_sha256": "b"*64, "purpose": "material", "lane": "fast",
                              "profile_id": "synthetic_cloud", "profile": {"endpoint": "https://synthetic.invalid/v1",
                              "protocol": "openai", "model": "synthetic-model", "credential_ref": "aak_cred_"+"c"*32,
                              "max_tokens": 256, "timeout_s": 30}},
            "context_proof": {"material": {"kind": "document", "document_id": "doc_synthetic", "version": 1,
                                          "content_sha256": "d"*64, "block_id": None},
                              "selection": {"start_utf16": 7, "end_utf16": 7+len(context.encode("utf-16-le"))//2,
                                            "quote_sha256": digest},
                              "provenance": {"source_id": None, "source_revision": None},
                              "context_sha256": digest, "bytes": len(context.encode()), "authority": "unverified_material"},
            "context": context, "question": "Synthetic question", "max_tokens": 128, "timeout_s": 5,
            "simulation_grant": {"evidence_scope": "SYNTHETIC", "material_upload_authorized": True,
                                 "accept_unknown_cost": True, "hard_currency_cap": None}}


class Harness:
    def __init__(self, cloud, request=None):
        self.cloud, self.request = cloud, request or intent()
        self.now, self.cancel, self.current = 100.0, False, True
        self.secret = bytearray(b"SYNTHETIC_PRIVATE_KEY")
        self.calls, self.refs = [], []
        self.payload = {"model": "synthetic-model", "choices": [{"message": {"content": "Synthetic answer"}, "finish_reason": "stop"}]}
        self.after = lambda: None

    def resolve(self, reference):
        self.refs.append(reference)
        return self.secret

    def transport(self, url, **kwargs):
        self.calls.append((url, kwargs))
        self.after()
        return SimpleNamespace(url=url, status=200, headers={"content-type": "application/json"},
                               body=json.dumps(self.payload).encode())

    def run(self, **kwargs):
        return self.cloud.simulate_once(self.request, self.cloud.preview(self.request)["plan_sha256"],
            _test_transport=kwargs.pop("transport", self.transport), _test_resolve_credential=self.resolve,
            _test_assert_current=lambda plan: self.current, cancelled=lambda: self.cancel,
            deadline=kwargs.pop("deadline", 105), clock=lambda: self.now, **kwargs)


def test_production_entry_has_no_activation_transport_or_secret_default(cloud):
    def forbidden(*args, **kwargs):
        pytest.fail("production dormant entry consumed material or a resolver")
    for args, kwargs in [((), {}), ((intent(),), {"activated": True, "transport": forbidden, "resolve_credential": forbidden})]:
        with pytest.raises(cloud.CloudFailure, match="^MATERIAL_CLOUD_NOT_ACTIVATED$"):
            cloud.execute(*args, **kwargs)


def test_simulation_freezes_only_selected_material_and_reuses_http_policy(cloud):
    h = Harness(cloud)
    preview = cloud.preview(h.request)
    assert "context" not in preview["plan"]
    assert preview["plan"]["context_proof"] == h.request["context_proof"]
    result = h.run()
    assert result["authority"] == "candidate" and result["grants_knowledge_acceptance"] is False
    assert result["evidence_scope"] == "SYNTHETIC" and result["activation"] == "NOT_ACTIVATED"
    assert result["usage"] is None and result["cost"] is None
    assert result["usage_status"] == result["cost_status"] == result["provider_stop_state"] == "UNKNOWN"
    assert h.refs == [h.request["configuration"]["profile"]["credential_ref"]]
    assert not any(h.secret)
    assert len(h.calls) == 1
    url, call = h.calls[0]
    assert url == "https://synthetic.invalid/v1/chat/completions"
    policy = call["policy"]
    assert isinstance(policy, cloud.http.SafeHTTPPolicy)
    assert policy.max_redirects == 0 and policy.allowed_hosts == ("synthetic.invalid",)
    assert policy.allowed_ports == (443,) and policy.allowed_content_types == ("application/json",)
    assert policy.max_bytes == cloud.MAX_RESPONSE and policy.timeout == 5
    assert call["headers"]["Authorization"] == "Bearer SYNTHETIC_PRIVATE_KEY"
    body = json.loads(call["body"])
    assert body["stream"] is False and body["model"] == "synthetic-model"
    assert h.request["context"] in body["messages"][0]["content"]
    assert "SYNTHETIC_PRIVATE_KEY" not in json.dumps(preview) + json.dumps(result)


@pytest.mark.parametrize("endpoint", ["http://synthetic.invalid/v1", "https://127.0.0.1/v1",
    "https://10.0.0.1/v1", "https://[::1]/v1", "https://169.254.169.254/v1", "https://2130706433/v1",
    "https://user:password@synthetic.invalid/v1", "https://synthetic.invalid:444/v1",
    "https://synthetic.invalid/v1?key=private", "https://synthetic.invalid/v1#fragment",
    "https://synthetic.invalid/%2e%2e/v1", "https://synthetic.invalid/../v1",
    "https://synthetic.invalid./v1", "https://SYNTHETIC.invalid/v1"])
def test_endpoint_policy_refuses_before_any_resolver_or_transport(cloud, endpoint):
    h = Harness(cloud)
    h.request["configuration"]["profile"]["endpoint"] = endpoint
    with pytest.raises(cloud.CloudFailure):
        h.run()
    assert not h.refs and not h.calls


@pytest.mark.parametrize("case", ["purpose", "upload", "unknown_cost", "numeric_grant", "real_grant", "hard_cap",
    "context_hash", "material_version", "quote", "range", "secret_field", "tokens", "timeout", "protocol"])
def test_scope_grant_and_budget_fail_before_secret_access(cloud, case):
    h = Harness(cloud)
    r = h.request
    if case == "purpose": r["configuration"]["purpose"] = "answer"
    elif case == "upload": r["simulation_grant"]["material_upload_authorized"] = False
    elif case == "unknown_cost": r["simulation_grant"]["accept_unknown_cost"] = False
    elif case == "numeric_grant": r["simulation_grant"]["material_upload_authorized"] = 1
    elif case == "real_grant": r["simulation_grant"]["evidence_scope"] = "REAL"
    elif case == "hard_cap": r["simulation_grant"]["hard_currency_cap"] = 1
    elif case == "context_hash": r["context"] += "different material"
    elif case == "material_version": r["context_proof"]["material"]["version"] = 0
    elif case == "quote": r["context_proof"]["selection"]["quote_sha256"] = "0"*64
    elif case == "range": r["context_proof"]["selection"]["end_utf16"] -= 1
    elif case == "secret_field": r["context_proof"]["secret"] = "SYNTHETIC_PRIVATE_KEY"
    elif case == "tokens": r["max_tokens"] = 257
    elif case == "timeout": r["timeout_s"] = 61
    else: r["configuration"]["profile"]["protocol"] = "ollama"
    with pytest.raises(cloud.CloudFailure): h.run()
    assert not h.refs and not h.calls


def test_confirmation_includes_question_configuration_epoch_and_proof(cloud):
    original = intent()
    old = cloud.preview(original)["plan_sha256"]
    for change in ("question", "configuration_revision", "restore_epoch", "material"):
        changed = copy.deepcopy(original)
        if change == "question": changed["question"] += "changed"
        elif change == "material": changed["context_proof"]["material"]["version"] += 1
        elif change == "restore_epoch": changed["configuration"][change] = "e"*32
        else: changed["configuration"][change] += 1
        assert cloud.preview(changed)["plan_sha256"] != old
        with pytest.raises(cloud.CloudFailure):
            cloud.simulate_once(changed, old, _test_transport=lambda *a, **k: pytest.fail("unconfirmed transport"),
                _test_resolve_credential=lambda *a: pytest.fail("unconfirmed credential"),
                _test_assert_current=lambda _: True, cancelled=lambda: False, deadline=105, clock=lambda: 100)


@pytest.mark.parametrize("when", ["pre_cancel", "pre_expired", "post_cancel", "post_expired", "post_fence"])
def test_cancellation_deadline_and_fence_reject_late_publication(cloud, when):
    h = Harness(cloud)
    if when == "pre_cancel": h.cancel = True
    if when == "pre_expired": h.now = 105
    def after():
        if when == "post_cancel": h.cancel = True
        if when == "post_expired": h.now = 105
        if when == "post_fence": h.current = False
    h.after = after
    with pytest.raises(cloud.CloudFailure) as error: h.run()
    assert error.value.provider_stop_state == "UNKNOWN" and error.value.answer_published is False
    assert not h.calls if when.startswith("pre_") else len(h.calls) == 1
    if h.refs: assert not any(h.secret)


def test_request_budget_caps_an_overlong_caller_deadline(cloud):
    h = Harness(cloud)
    h.after = lambda: setattr(h, "now", 106)
    with pytest.raises(cloud.CloudFailure, match="MATERIAL_CLOUD_TIMEOUT"): h.run(deadline=10000)
    assert not any(h.secret)


@pytest.mark.parametrize("case", ["wrong_model", "missing_model", "reasoning_only", "malformed", "duplicate",
    "nan", "overflow", "redirect", "http_429", "transport_error"])
def test_response_failures_are_safe_single_attempt_without_fallback(cloud, case):
    h = Harness(cloud)
    if case == "wrong_model": h.payload["model"] = "different"
    elif case == "missing_model": del h.payload["model"]
    elif case == "reasoning_only": h.payload["choices"][0]["message"] = {"content": "", "reasoning_content": "PRIVATE_REASONING"}
    def transport(url, **kwargs):
        response = h.transport(url, **kwargs)
        if case == "malformed": response.body = b"PRIVATE_BODY not JSON"
        elif case == "duplicate": response.body = b'{"model":"one","model":"two"}'
        elif case == "nan": response.body = b'{"model":NaN}'
        elif case == "overflow": response.body = b"x"*(cloud.MAX_RESPONSE+1)
        elif case == "redirect": response.url = "https://different.invalid/v1/chat/completions"
        elif case == "http_429": response.status = 429
        elif case == "transport_error": raise RuntimeError("PRIVATE_BODY SYNTHETIC_PRIVATE_KEY")
        return response
    with pytest.raises(cloud.CloudFailure) as error: h.run(transport=transport)
    assert len(h.calls) == 1 and not any(h.secret)
    assert "PRIVATE" not in str(error.value) + repr(error.value)


def test_reported_usage_and_truncation_remain_distinct_from_cost(cloud):
    h = Harness(cloud)
    h.payload["usage"] = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30, "cost": 0}
    h.payload["choices"][0]["finish_reason"] = "length"
    result = h.run()
    assert result["usage"] == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    assert result["usage_status"] == "REPORTED" and result["cost_status"] == "UNKNOWN"
    assert result["cost"] is None and result["truncated"] is True


@pytest.mark.parametrize("case", ["missing", "invalid", "cancelled"])
def test_secret_resolution_failure_never_reaches_transport(cloud, case):
    h = Harness(cloud)
    if case == "missing":
        def missing(reference):
            raise RuntimeError("SYNTHETIC_PRIVATE_KEY unavailable")
        h.resolve = missing
    elif case == "invalid":
        h.secret = bytearray(b"invalid\r\nheader")
    else:
        original = h.resolve
        def cancelled(reference):
            h.cancel = True
            return original(reference)
        h.resolve = cancelled
    with pytest.raises(cloud.CloudFailure) as error:
        h.run()
    assert not h.calls
    assert "PRIVATE" not in str(error.value)
    if case != "missing": assert not any(h.secret)


@pytest.mark.parametrize("kind", ["document", "transform"])
def test_whole_fixed_material_uses_same_proof_without_knowledge_acceptance(cloud, kind):
    h = Harness(cloud)
    proof = h.request["context_proof"]
    proof["selection"] = None
    if kind == "transform":
        proof["material"] = {"kind": "transform", "source_id": "src_synthetic", "raw_sha256": "e"*64,
                             "job_id": "job_synthetic", "transform_id": "transform_synthetic", "transform_sha256": "f"*64}
        proof["provenance"] = {"source_id": "src_synthetic", "source_revision": "e"*64,
                               "job_id": "job_synthetic", "transform_id": "transform_synthetic"}
    result = h.run()
    assert result["evidence_scope"] == "SYNTHETIC" and result["grants_knowledge_acceptance"] is False
