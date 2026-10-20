"""Dormant Material-only protocol adapter; production execute always refuses.

The explicit simulation seam has no default transport or secret resolver. It is
not an egress grant or native Vault integration. Future production activation
still needs Owner service/material/cost choices, a Core fence and a bounded owned
worker/secret channel. No provider identity, URL, key or proxy is inferred here.
"""
from __future__ import annotations

import hashlib
import importlib.util
import ipaddress
import json
import math
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

MAX_CONTEXT = 128000
MAX_RESPONSE = 128000
MAX_ANSWER = 64000


class CloudFailure(ValueError):
    provider_stop_state = "UNKNOWN"
    answer_published = False

    def __init__(self, code):
        super().__init__(code)
        self.reason_code = code


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CloudFailure("MATERIAL_CLOUD_DEPENDENCY_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_here = Path(__file__).resolve()
_safe_path = next((p for p in (_here.parents[2] / "shared/safe_http.py",
                              _here.parents[3] / "shared/safe_http.py") if p.is_file()), None)
if _safe_path is None:
    raise CloudFailure("MATERIAL_CLOUD_DEPENDENCY_UNAVAILABLE")
http = _load("material_cloud_safe_http", _safe_path)
machine = _load("material_cloud_machine_protocol", _here.with_name("worker_machine_answer.py"))


def preflight():
    return {"schema": "archeaxis.material-cloud-preflight/v1", "purpose": "material",
            "activation": "NOT_ACTIVATED", "protocol": "openai-buffered",
            "network_performed": False, "model_executed": False,
            "secret_accessed": False, "task_executed": False}


def execute(*_args, **_kwargs):
    # No flag/environment/credential reference can activate this entry point.
    raise CloudFailure("MATERIAL_CLOUD_NOT_ACTIVATED")


def _require(ok):
    if not ok:
        raise CloudFailure("MATERIAL_CLOUD_INVALID_INTENT")


def _keys(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()))


def _token(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is not None


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _endpoint(base):
    _require(isinstance(base, str) and 0 < len(base) <= 256 and base.isascii()
             and not any(c.isspace() for c in base) and not any(c in base for c in "\\%?#"))
    try:
        url = urlsplit(base)
        _require(url.scheme == "https" and not url.username and not url.password
                 and url.port in (None, 443) and bool(url.hostname))
        host = url.hostname
        try:
            ipaddress.ip_address(host)
            http._validate_address(host)
        except ValueError:
            _require(not re.fullmatch(r"[0-9.]+", host)
                     and re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", host) is not None
                     and not host.endswith((".localhost", ".local", ".internal")))
        authority = (f"[{host}]" if ":" in host else host)
        _require(url.netloc in (authority, authority + ":443"))
        _require(not url.path.endswith("/") and all(re.fullmatch(r"[A-Za-z0-9_-]+", p)
                 for p in url.path.split("/")[1:]))
        return host
    except (ValueError, TypeError):
        raise CloudFailure("MATERIAL_CLOUD_INVALID_INTENT") from None


def _prepare(intent):
    _keys(intent, "schema request_id configuration context_proof context question max_tokens timeout_s simulation_grant")
    _require(intent["schema"] == "archeaxis.material-cloud-simulation/v1" and _token(intent["request_id"]))
    config = intent["configuration"]
    _keys(config, "schema workspace_id restore_epoch configuration_revision configuration_sha256 purpose lane profile_id profile")
    _require(config["schema"] == "archeaxis.resolved-model/v1" and config["purpose"] == "material"
             and config["lane"] in ("fast", "deep") and _token(config["profile_id"])
             and re.fullmatch(r"[a-f0-9]{32}", config["workspace_id"]) is not None
             and (config["restore_epoch"] == "initial" or re.fullmatch(r"[a-f0-9]{32}", config["restore_epoch"]) is not None)
             and _integer(config["configuration_revision"], 0, 2**53-1) and _sha(config["configuration_sha256"]))
    profile = config["profile"]
    _keys(profile, "endpoint protocol model credential_ref max_tokens timeout_s")
    host = _endpoint(profile["endpoint"])
    _require(profile["protocol"] == "openai" and isinstance(profile["model"], str)
             and re.fullmatch(r"[A-Za-z0-9_.:/@+-]{1,256}", profile["model"]) is not None
             and isinstance(profile["credential_ref"], str)
             and re.fullmatch(r"aak_cred_[a-f0-9]{32}", profile["credential_ref"]) is not None
             and _integer(profile["max_tokens"], 128, 4096) and _integer(profile["timeout_s"], 1, 120)
             and _integer(intent["max_tokens"], 128, profile["max_tokens"])
             and _integer(intent["timeout_s"], 1, min(60, profile["timeout_s"])))
    proof = intent["context_proof"]
    _keys(proof, "material selection provenance context_sha256 bytes authority")
    context, question = intent["context"], intent["question"]
    _require(isinstance(context, str) and context.strip() and "\0" not in context
             and isinstance(question, str) and question.strip() and "\0" not in question)
    _require(0 < len(context.encode("utf-8")) <= MAX_CONTEXT and len(question.encode("utf-8")) <= 8192
             and proof["bytes"] == len(context.encode("utf-8")) and type(proof["bytes"]) is int
             and proof["context_sha256"] == hashlib.sha256(context.encode("utf-8")).hexdigest()
             and proof["authority"] == "unverified_material")
    material = proof["material"]
    _require(type(material) is dict)
    if material.get("kind") == "document":
        _keys(material, "kind document_id version content_sha256 block_id")
        _require(_token(material["document_id"]) and _integer(material["version"], 1, 2**53-1)
                 and _sha(material["content_sha256"]) and (material["block_id"] is None or _token(material["block_id"])))
        _keys(proof["provenance"], "source_id source_revision")
        _require((proof["provenance"]["source_id"] is None and proof["provenance"]["source_revision"] is None)
                 or (_token(proof["provenance"]["source_id"]) and _sha(proof["provenance"]["source_revision"])))
    else:
        _keys(material, "kind source_id raw_sha256 job_id transform_id transform_sha256")
        _require(material["kind"] == "transform" and all(_token(material[k]) for k in ("source_id", "job_id", "transform_id"))
                 and _sha(material["raw_sha256"]) and _sha(material["transform_sha256"]))
        _require(proof["provenance"] == {"source_id": material["source_id"], "source_revision": material["raw_sha256"],
                                      "job_id": material["job_id"], "transform_id": material["transform_id"]})
    selection = proof["selection"]
    if selection is not None:
        _keys(selection, "start_utf16 end_utf16 quote_sha256")
        _require(_integer(selection["start_utf16"], 0, 2**53-1)
                 and _integer(selection["end_utf16"], selection["start_utf16"]+1, 2**53-1)
                 and selection["end_utf16"]-selection["start_utf16"] == len(context.encode("utf-16-le"))//2
                 and selection["quote_sha256"] == proof["context_sha256"])
    grant = intent["simulation_grant"]
    _keys(grant, "evidence_scope material_upload_authorized accept_unknown_cost hard_currency_cap")
    _require(grant["evidence_scope"] == "SYNTHETIC" and grant["material_upload_authorized"] is True
             and grant["accept_unknown_cost"] is True and grant["hard_currency_cap"] is None)
    prompt, version = machine.answer_prompt(context, question, "grounded")
    body = _encoded({"model": profile["model"], "max_tokens": intent["max_tokens"], "stream": False,
                     "messages": [{"role": "user", "content": prompt}]})
    _require(len(body) <= 192000)
    plan = {k: v for k, v in intent.items() if k not in ("context", "schema")}
    plan.update(schema="archeaxis.material-cloud-plan/v1", activation="NOT_ACTIVATED", purpose="material",
                prompt_version=version, body_sha256=hashlib.sha256(body).hexdigest(), usage=None, cost=None,
                usage_status="UNKNOWN", cost_status="UNKNOWN", provider_stop_state="UNKNOWN")
    # Snapshot caller objects before a resolver/transport callback can mutate them.
    return json.loads(_encoded(plan)), body, host


def preview(intent):
    try:
        plan, _, _ = _prepare(intent)
        return {"plan": plan, "plan_sha256": hashlib.sha256(_encoded(plan)).hexdigest()}
    except CloudFailure:
        raise
    except Exception:
        raise CloudFailure("MATERIAL_CLOUD_INVALID_INTENT") from None


def simulate_once(intent, confirmed_plan_sha256, *, _test_transport, _test_resolve_credential,
                  _test_assert_current, cancelled, deadline, clock=time.monotonic):
    """SYNTHETIC seam only: no default fetch/Vault, retry, fallback or activation.

    In-flight blocking transport cancellation belongs to a future Core-owned
    worker bridge; here pre/post checks reject cancellation and late publication.
    """
    secret = None
    try:
        started = clock()
        plan, body, host = _prepare(intent)
        _require(confirmed_plan_sha256 == hashlib.sha256(_encoded(plan)).hexdigest())
        _require(type(deadline) in (int, float) and math.isfinite(deadline))
        deadline = min(deadline, started + plan["timeout_s"])

        def check_time():
            if cancelled():
                raise CloudFailure("MATERIAL_CLOUD_CANCELLED")
            if clock() >= deadline:
                raise CloudFailure("MATERIAL_CLOUD_TIMEOUT")

        def guard():
            check_time()
            if _test_assert_current(json.loads(_encoded(plan))) is not True:
                raise CloudFailure("MATERIAL_CLOUD_FENCE_CHANGED")
            check_time()

        guard()
        config = plan["configuration"]
        try:
            secret = _test_resolve_credential(config["profile"]["credential_ref"])
        except Exception:
            raise CloudFailure("MATERIAL_CLOUD_CREDENTIAL_UNAVAILABLE") from None
        _require(type(secret) is bytearray and 0 < len(secret) <= 2560 and all(33 <= c <= 126 for c in secret))
        guard()
        remaining = deadline-clock()
        if remaining <= 0:
            raise CloudFailure("MATERIAL_CLOUD_TIMEOUT")
        policy = http.SafeHTTPPolicy(timeout=min(plan["timeout_s"], remaining), max_bytes=MAX_RESPONSE,
                                     max_redirects=0, allowed_ports=(443,), allowed_hosts=(host,),
                                     allowed_content_types=("application/json",))
        url = config["profile"]["endpoint"] + "/chat/completions"
        try:
            response = _test_transport(url, method="POST", body=body,
                                       headers={"Content-Type": "application/json", "Authorization": "Bearer " + secret.decode("ascii")},
                                       policy=policy)
        except Exception:
            raise CloudFailure("MATERIAL_CLOUD_TRANSPORT_FAILED") from None
        guard()
        _require(response.url == url and 200 <= response.status < 300 and type(response.body) is bytes
                 and len(response.body) <= MAX_RESPONSE
                 and response.headers.get("content-type", "").split(";", 1)[0].lower() == "application/json")

        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result

        payload = json.loads(response.body, object_pairs_hook=pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON constant")))
        _require(type(payload) is dict and payload.get("model") == config["profile"]["model"])
        choices = payload.get("choices")
        _require(type(choices) is list and len(choices) == 1 and type(choices[0]) is dict)
        choice = choices[0]
        message = choice.get("message")
        _require(type(message) is dict and choice.get("finish_reason") in ("stop", "length"))
        answer = message.get("content")
        _require(isinstance(answer, str) and answer.strip() and len(answer.encode("utf-8")) <= MAX_ANSWER)
        guard()
        usage = machine.reported_usage(payload, "openai")
        return {"activation": "NOT_ACTIVATED", "evidence_scope": "SYNTHETIC", "plan_sha256": confirmed_plan_sha256,
                "answer": answer, "authority": "candidate", "grants_knowledge_acceptance": False,
                "requested_model": config["profile"]["model"], "observed_model": payload["model"],
                "finish_reason": choice["finish_reason"], "truncated": choice["finish_reason"] == "length",
                "usage": usage, "usage_status": "REPORTED" if usage is not None else "UNKNOWN",
                "cost": None, "cost_status": "UNKNOWN", "provider_stop_state": "UNKNOWN"}
    except CloudFailure:
        raise
    except Exception:
        raise CloudFailure("MATERIAL_CLOUD_INVALID_RESPONSE_OR_FENCE") from None
    finally:
        if type(secret) is bytearray:
            secret[:] = b"\0" * len(secret)
