"""Two real local answers across a synthetic rule revision, using only Core writers.

Run through dev.py with a contemporaneously qualified Core release receipt. This is a
new finite scenario, not a retry of the historical co-learning experiments. The
scripted reviewer updates a fictional policy; it never invents a model failure.
Importing this module performs no IO, model discovery, inference or configuration.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request

from scripts.probes.workspace_path_report import checked_workspace_report

REPO = Path(__file__).resolve().parents[2]
PURPOSE = "synthetic library policy version update and independent application"
REVIEWER = "scripted-human-fixture"
ASSET = "archeaxis_ai_asset"
KG = "archeaxis_context_grant"
AG = "archeaxis_asset_context_grant"
# 2026-11-14 real local run: qwen3.5-4b consumed all 2048 output tokens on
# reasoning_content for the grounded two-field v2 question (finish_reason=length,
# NO_FINAL_ANSWER). The existing worker explicitly requires a larger budget for
# reasoning models. Keep the strict answer/evaluation contract unchanged.
BUDGET = {"max_tokens": 2900, "timeout_s": 120}
MATERIALS = {
    "v1": "SYNTHETIC FICTIONAL POLICY v1. The Lumen library lends books for 7 days. "
          "A borrower may renew each loan once, for 7 additional days. "
          "These are fixture rules, not facts about a real library.",
    "v2": "SYNTHETIC FICTIONAL POLICY v2 replaces v1. The Lumen library now lends books "
          "for 10 days. A borrower may renew each loan once, for 5 additional days. "
          "A second renewal is not allowed. These are fixture rules, not facts about a real library.",
}
QUESTIONS = {
    "v1": "Under the supplied current Lumen policy, what is the initial loan duration? "
          "Return only JSON with loan_days (integer).",
    "v2": "A Lumen borrower has already renewed this loan once. Under the supplied current "
          "policy, may they renew it again, and how many days did the permitted renewal add? "
          "Return only JSON with another_renewal_allowed (boolean) and renewal_days (integer).",
}
EXPECTED = {"v1": {"loan_days": 7}, "v2": {"another_renewal_allowed": False, "renewal_days": 5}}
CONTRACT = {"schema": "archeaxis.synthetic-policy-revision/v1", "materials": MATERIALS,
            "questions": QUESTIONS, "expected": EXPECTED, "budget": BUDGET,
            "purpose": PURPOSE, "model_request_ceiling": 2,
            "intervention": "scripted policy update, not correction of a purported model failure",
            "learning_improvement": "NOT_ESTABLISHED", "owner_acceptance": False}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("required local module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha(value):
    return text_sha(canonical(value))


def snapshot(document):
    result = {key: document[key] for key in ("document_id", "version", "content_sha256")}
    require(isinstance(result["document_id"], str) and bool(result["document_id"])
            and type(result["version"]) is int and result["version"] > 0
            and isinstance(result["content_sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", result["content_sha256"]), "invalid Core snapshot")
    return result


def editor(namespace, value):
    return {"type": "doc", "content": [], "attrs": {namespace: value}}


def material_editor(text):
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


def strict_object(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate output field")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("non-finite output")
    value = json.loads(text, object_pairs_hook=unique, parse_constant=invalid)
    require(type(value) is dict, "output is not an object")
    return value


def score(text, version):
    try:
        value = strict_object(text)
        expected = EXPECTED[version]
        if set(value) != set(expected) or any(type(value[k]) is not type(v) for k, v in expected.items()):
            return "REVIEW_REQUIRED"
        return "CORRECT" if value == expected else "INCORRECT"
    except (ValueError, TypeError, UnicodeError):
        return "REVIEW_REQUIRED"


def response_format(version):
    properties = {key: {"type": "boolean" if type(value) is bool else "integer"}
                  for key, value in EXPECTED[version].items()}
    return {"type": "json_schema", "json_schema": {"name": "archeaxis_response", "strict": True,
            "schema": {"type": "object", "properties": properties, "required": sorted(properties),
                       "additionalProperties": False}}}


def checked_packet(body, asset, grant, knowledge_id, material, currentness="current", successor=None):
    """Compare the full current Core projection, including dynamic reference states."""
    packet = body["packet"]
    require(packet["schema"] == "archeaxis.ai-context-packet/v1"
            and body["packet_sha256"] == sha(packet), "packet bytes differ from Core digest")
    require(packet["asset"] == snapshot(asset) and packet["grant"] == snapshot(grant)
            and packet["consumer"] == "local-machine" and packet["purpose"] == PURPOSE
            and packet["operation"] == "read_packet", "packet authorization differs")
    require(packet["reference_only_sources"] is True and packet["private_session_access"] is False
            and packet["tool_execution"] == "NOT_EXECUTED"
            and all(packet[k] is False for k in ("machine_qualification", "human_mastery", "professional_truth")),
            "packet authority widened")
    meta = asset["editor_json"]["attrs"][ASSET]
    require(len(packet["items"]) == 1, "unexpected package expansion")
    item = packet["items"][0]
    require(item["snapshot"] == snapshot(asset)
            and all(item[k] == meta[k] for k in ("kind", "content", "purpose", "scope", "provenance")),
            "packet content differs from fixed asset")
    require(item["engine_execution"] == "NOT_EXECUTED"
            and all(item[k] is False for k in ("grants_professional_truth", "grants_human_mastery", "grants_machine_qualification")),
            "packet item authority widened")
    references = [{"kind": "knowledge", "knowledge_id": knowledge_id},
                  {"kind": "document", "document_id": material["document_id"],
                   "version": material["version"], "block_id": None}]
    states = item["reference_states"]
    require(len(states) == 2 and [v["reference"] for v in states] == references,
            "packet reference states absent or rebound")
    require(states[0]["readable"] is True and states[0]["currentness"] == currentness
            and states[0]["active"] is (currentness == "current")
            and states[0]["superseded_by"] == successor
            and states[1] == {"reference": references[1], "readable": True, "currentness": "not_applicable"},
            "packet knowledge currentness or pinned document changed")
    require(body["receipt"]["packet_sha256"] == body["packet_sha256"]
            and body["receipt"]["asset"] == packet["asset"] and body["receipt"]["grant"] == packet["grant"]
            and body["receipt"]["model_execution"] == "NOT_EXECUTED"
            and body["receipt"]["delivery_status"] == "PREPARED_NOT_SENT_TO_PEER",
            "packet preparation mislabeled as inference")
    return copy.deepcopy(packet)


def checked_answer(result, sent, packet, knowledge_text, knowledge_grant, route):
    request = result["request"]
    require(result["knowledge_id"] == sent["knowledge_id"] and result["question"] == sent["question"]
            and result["client_request_id"] == sent["client_request_id"], "answer identity differs")
    for key in ("knowledge_id", "question", "model", "context_grant", "asset_context_grant",
                "max_tokens", "timeout_s", "response_format"):
        require(request[key] == sent[key], "persisted request differs: " + key)
    require(request["response_format_sha256"] == sha(sent["response_format"]), "output shape hash differs")
    answer_packet = copy.deepcopy(packet)
    answer_packet["operation"] = "answer"
    proof = {"schema": "archeaxis.machine-asset-context/v1", "asset": packet["asset"],
             "grant": packet["grant"], "consumer": "local-machine", "operation": "answer",
             "packet_sha256": sha(answer_packet), "member_snapshots": [x["snapshot"] for x in packet["items"]],
             "tool_execution": "NOT_EXECUTED", "private_session_access": False}
    require(request["asset_context"] == proof, "actual answer packet/member binding differs")
    context = ("CANONICAL_KNOWLEDGE:\n" + knowledge_text
               + "\n\nAI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n"
               + canonical(answer_packet))
    require(request["knowledge_context_sha256"] == text_sha(knowledge_text)
            and request["context_sha256"] == text_sha(context), "actual merged model context differs")
    auth = result["context_authorization"]
    require(snapshot(auth) == snapshot(knowledge_grant)
            and auth["authorization"] == knowledge_grant["editor_json"]["attrs"][KG]
            and auth["current_permission_valid"] is True and auth["operation"] == "answer",
            "actual knowledge authorization differs")
    answer = result["answer"]
    require(all(answer.get(key) == value for key, value in route.items()), "observed model route differs")
    require(answer.get("requested_model") == answer.get("observed_model") == route["model"]
            and answer.get("finish_reason") == "stop" and answer.get("truncated") is False
            and answer.get("max_tokens") == BUDGET["max_tokens"]
            and answer.get("response_format_sha256") == sha(sent["response_format"])
            and answer.get("format_validation") == "VALID"
            and isinstance(answer.get("answer"), str) and bool(answer["answer"].strip()),
            "missing complete real model/structured output identity")
    require(re.fullmatch(r"answer_req_[0-9a-f]{64}", result["answer_id"]), "invalid answer identity")
    return {"task_id": result["answer_id"], "knowledge_id": result["knowledge_id"],
            "answer_sha256": text_sha(answer["answer"]), "request_sha256": sha(request),
            "packet_sha256": proof["packet_sha256"], "context_sha256": request["context_sha256"]}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("local inventory redirect refused")


def loaded_inventory(route):
    """Only LM Studio GET inventory; never JIT/load/unload or contact another host."""
    require(route["endpoint"] == "http://127.0.0.1:1234/v1" and route["protocol"] == "openai",
            "this finite probe requires the existing declared loopback LM Studio route")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open("http://127.0.0.1:1234/api/v1/models", timeout=5) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    require(len(raw) <= 2 * 1024 * 1024, "model inventory exceeds bound")
    catalog = json.loads(raw)
    matches = [{"key": model["key"], "instance_id": instance["id"]}
               for model in catalog["models"] for instance in model.get("loaded_instances", [])
               if instance.get("id") == route["model"]]
    require(len(matches) == 1, "frozen model is not one already loaded instance; no JIT/load attempted")
    return matches[0]


def declared_route(worker):
    lanes = worker._declared_lanes()  # Declaration only, unlike _endpoint()/probe().
    require(len(lanes) == 1, "ambiguous existing local runtime declaration")
    lane = lanes[0]
    endpoint = os.environ.get("ARCHEAXIS_MACHINE_ENDPOINT", "").strip()
    require(not endpoint or endpoint.rstrip("/") == lane["base"].rstrip("/"), "existing endpoint override differs")
    protocol = os.environ.get("ARCHEAXIS_MACHINE_PROTOCOL", "").strip()
    require(not protocol or protocol == lane["protocol"], "existing protocol override differs")
    # Match the existing worker's effective override semantics; never set environment variables.
    model = (os.environ.get("ARCHEAXIS_MACHINE_MODEL", "").strip() if endpoint else "") or lane["model"]
    return {"model": model, "endpoint": lane["base"], "protocol": lane["protocol"],
            "prompt_version": worker.PROMPT_VERSION, "answer_policy": "grounded",
            "engine": worker.ENGINE, "engine_version": worker.ENGINE_VERSION}


def bind_staged_runtime(runtime_root, manifest_sha256, qualified_core, paths, dev, resources):
    """Read the formal payload in place; never synthesize a developer worker profile."""
    require(Path(runtime_root).is_absolute(), "runtime root must be an explicit absolute path")
    root = resources.checked(Path(runtime_root))
    relative = root.relative_to(paths["run"].parent)
    require(len(relative.parts) >= 3 and relative.parts[1] == "artifacts",
            "runtime must be inside this worktree's canonical run artifacts")
    require(re.fullmatch(r"[0-9a-f]{64}", manifest_sha256 or ""), "runtime manifest SHA-256 required")
    manifest_path = resources.regular(root / "backend-runtime-manifest.json")
    manifest = dev.build_file_identity(manifest_path)
    require(manifest["sha256"] == manifest_sha256, "runtime manifest differs from explicit pin")
    backend = resources.verify_runtime_resources(root, resources.RESOURCES)
    profile_path = resources.regular(root / "worker-profile.json")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    routes = [row for row in profile["routes"] if row["capability"] == "machine.answer"]
    require(len(routes) == 1, "formal runtime must contain one machine.answer route")
    members = {"core": "core/archeaxis-api.exe", "python": profile["python"],
               "profile": "worker-profile.json", "worker": routes[0]["script"],
               "transport": profile["script"], "launcher": "start-backend.py"}
    identities = {}
    for name, member in members.items():
        member = resources.relative_path(member)
        path = resources.regular(root / member)
        path.relative_to(root)
        require(member in backend["files"], "launch input missing from formal manifest")
        identities[name] = dev.build_file_identity(path)
    require(all(identities["core"][key] == qualified_core[key] for key in ("bytes", "sha256")),
            "staged Core differs from qualified Core build")
    source_worker = dev.build_file_identity(REPO / "services/python-workers/machine/worker_machine_answer.py")
    require(all(identities["worker"][key] == source_worker[key] for key in ("bytes", "sha256")),
            "staged machine worker differs from current source")
    require(dev.build_file_identity(manifest_path) == manifest, "runtime manifest changed while binding")
    return {"schema": "archeaxis.probe-runtime-binding/v1", "mode": "FORMAL_STAGED_RUNTIME",
            "root": str(root), "manifest": manifest, "member_count": len(backend["files"]),
            "current_source_worker": source_worker, **identities}


class Journey:
    """Reusable exercise over an already owned Core; lifecycle remains in main()."""
    def __init__(self, client, receipt, route, checkpoint=lambda: None):
        self.client, self.receipt, self.route = client, receipt, route
        self.checkpoint = checkpoint
        self.base, self.tokens = None, None
        self.model_requests = 0
        self.readbacks = {}

    def call(self, name, method, path, body=None, expected=(200,), role="human", headers=None):
        timeout = BUDGET["timeout_s"] + 15 if path == "/api/v1/machine/answers" else 30
        if path == "/api/v1/machine/answers":
            require(self.model_requests < 2, "two model request ceiling exceeded")
            self.model_requests += 1
            self.receipt["model_request_count"] = self.model_requests
            self.receipt["last_dispatch"] = {"stage": name, "request": copy.deepcopy(body),
                                              "state": "DISPATCH_PLANNED_OUTCOME_UNKNOWN"}
            self.checkpoint()
        try:
            status, result = self.client.call(self.base, method, path, self.tokens[role], body,
                                               timeout=timeout, extra_headers=headers)
        except (OSError, TimeoutError) as error:
            self.receipt["transport_unknown"] = {"stage": name, "error_type": type(error).__name__}
            raise ValueError("request outcome UNKNOWN; no retry") from None
        self.receipt["stages"].append({"stage": name, "method": method, "path": path,
                                        "request_sha256": sha(body), "status": status, "body": result})
        self.receipt["model_request_count"] = self.model_requests
        if status == 0:
            self.receipt["transport_unknown"] = {"stage": name, "error_type": "CLIENT_TRANSPORT_STATUS_ZERO"}
        require(status != 0, "request outcome UNKNOWN; no retry")
        require(status in expected, name + ": unexpected HTTP status " + str(status))
        return result

    def pin(self, path, value):
        require(self.call("fixed_readback", "GET", path) == value, "fixed readback differs")
        self.readbacks[path] = copy.deepcopy(value)
        return value

    def create(self, name, value, source=None):
        return self.call(name, "POST", "/api/v1/documents", {"create_request_id": "revision-" + name,
                         "title": name, "editor_json": value, **(source or {})}, (201,))

    def save(self, name, doc, value):
        return self.call(name, "PUT", "/api/v1/documents/" + doc["document_id"] + "/draft",
                         {"expected_version": doc["version"], "editor_json": value})

    def pin_document(self, doc):
        return self.pin(f"/api/v1/documents/{doc['document_id']}/versions/{doc['version']}", doc)

    def rubric(self, name, expectation, sources):
        return self.call(name, "POST", "/api/v1/machine/rubrics", {
            "schema": "archeaxis.machine-rubric/v1", "request_id": "revision-" + name,
            "title": name, "purpose": PURPOSE, "sources": sources,
            "criteria": [{"criterion_id": "fit", "label": "fixed synthetic criterion", "expectation": expectation}]}, (201,))

    def review_knowledge(self, knowledge_id, action, text=None):
        current = self.call("knowledge_review_basis", "GET", f"/api/v1/knowledge-items/{knowledge_id}/v3")
        changed = self.call("knowledge_" + action, "POST", f"/api/v1/knowledge/{knowledge_id}/review/versioned", {
            "action": action, "reviewer": REVIEWER, "expected_version": current["version"],
            "note": "Synthetic policy update; not Owner acceptance or a measured model failure", "new_body": text})
        return changed["knowledge_id"]

    def adopt(self, name, doc, rubric):
        value = copy.deepcopy(doc["editor_json"])
        value["attrs"][ASSET].update(state="adopted", review={
            "asset": snapshot(doc), "rubric": snapshot(rubric), "reviewer": REVIEWER,
            "basis": "Exact synthetic policy, inert scope and version fit; not Owner quality acceptance",
            "judgments": [{"criterion_id": "fit", "outcome": "passed", "basis": "Matches frozen synthetic rule"}],
            "outcome": "passed"})
        return self.save(name, doc, value)

    def grants(self, version, knowledge_id, asset):
        knowledge_grant = self.create("knowledge-grant-" + version, editor(KG, {
            "schema": "archeaxis.context-grant/v1", "purpose": PURPOSE, "consumer": "local-machine",
            "operations": ["answer"], "knowledge_id": knowledge_id, "provenance": [],
            "authorization_basis": "Owned synthetic fixture only", "expires_at": None, "state": "granted"}))
        asset_grant = self.create("asset-grant-" + version, editor(AG, {
            "schema": "archeaxis.asset-context-grant/v1", "asset": snapshot(asset), "purpose": PURPOSE,
            "consumer": "local-machine", "operations": ["answer", "read_packet"],
            "authorization_basis": "Owned synthetic fixture only", "expires_at": None, "state": "granted"}))
        return knowledge_grant, asset_grant

    def packet(self, name, asset, grant, expected=(200,)):
        return self.call(name, "POST", "/api/v1/ai/context-packets", {
            "request_id": "revision-packet-" + name, "asset": snapshot(asset), "grant": snapshot(grant),
            "purpose": PURPOSE, "consumer": "local-machine", "operation": "read_packet"}, expected, role="machine")

    def answer(self, version, knowledge_id, asset, material, kg, ag, rubric):
        self.receipt["inventories"].append(loaded_inventory(self.route))
        packet = checked_packet(self.packet("before-" + version, asset, ag), asset, ag, knowledge_id, material)
        sent = {"client_request_id": "revision-answer-" + version, "knowledge_id": knowledge_id,
                "question": QUESTIONS[version], "model": self.route["model"], "response_format": response_format(version),
                "context_grant": {**snapshot(kg), "purpose": PURPOSE}, **BUDGET,
                "asset_context_grant": {"request_id": "revision-use-" + version, "asset": snapshot(asset),
                                        "grant": snapshot(ag), "purpose": PURPOSE,
                                        "consumer": "local-machine", "operation": "answer"}}
        self.receipt.setdefault("frozen_model_requests", []).append({"request": copy.deepcopy(sent),
            "read_packet": packet, "knowledge_sha256": text_sha(MATERIALS[version]), "expected": EXPECTED[version]})
        try:
            result = self.call("answer-" + version, "POST", "/api/v1/machine/answers", sent, role="machine")
        except ValueError:
            latest = self.receipt["stages"][-1] if self.receipt["stages"] else {}
            self.receipt["quality"][version] = ("REVIEW_REQUIRED" if "INVALID_OUTPUT" in canonical(latest.get("body"))
                                                 else "NO_ACCEPTED_FINAL_ANSWER")
            raise
        binding = checked_answer(result, sent, packet, MATERIALS[version], kg, self.route)
        self.receipt["last_dispatch"]["state"] = "COMPLETE_BOUND_CORE_RESPONSE"
        self.receipt["answers"].append(binding)
        self.receipt["quality"][version] = score(result["answer"]["answer"], version)
        self.checkpoint()
        stored = self.call("answer_readback", "GET", "/api/v1/machine/tasks/" + binding["task_id"])
        conditions = stored["conditions"]
        require((json.loads(conditions) if isinstance(conditions, str) else conditions) == result,
                "persisted answer differs")
        self.readbacks["/api/v1/machine/tasks/" + binding["task_id"]] = stored
        original = self.call("answer_snapshot", "GET", "/api/v1/machine/answers/" + binding["task_id"] + "/snapshot")
        require(original["original_answer_sha256"] == binding["answer_sha256"]
                and original["knowledge_id"] == knowledge_id, "evaluation snapshot rebound")
        self.readbacks["/api/v1/machine/answers/" + binding["task_id"] + "/snapshot"] = copy.deepcopy(original)
        binding["task_receipt_sha256"] = original["task_receipt_sha256"]
        quality = self.receipt["quality"][version]
        outcome = {"CORRECT": "passed", "INCORRECT": "failed", "REVIEW_REQUIRED": "unmeasured"}[quality]
        evaluation = self.call("evaluate-" + version, "POST", "/api/v1/machine/evaluations", {
            "request_id": "revision-evaluation-" + version, "task_id": binding["task_id"],
            "rubric": snapshot(rubric), "reviewer": REVIEWER,
            "basis": "Scripted finite comparison: " + quality + "; no Owner acceptance or learning claim",
            "judgments": [{"criterion_id": "fit", "outcome": outcome, "basis": quality}], "outcome": outcome}, (201,))
        saved = evaluation["editor_json"]["attrs"]["archeaxis_machine_evaluation"]
        require(saved["task_id"] == binding["task_id"] and saved["knowledge_id"] == knowledge_id
                and saved["original_answer_sha256"] == binding["answer_sha256"]
                and saved["task_receipt_sha256"] == binding["task_receipt_sha256"]
                and saved["outcome"] == outcome and saved["rubric"] == snapshot(rubric), "evaluation binding differs")
        self.pin_document(evaluation)
        return binding, evaluation


def exercise(journey):
    """Only Core APIs; callable with the same owned Core from a later journey."""
    j = journey
    imported = j.call("source_import", "POST", "/api/v1/imports",
                      j.client.import_request("lumen-synthetic-policy-v1.txt", MATERIALS["v1"].encode("utf-8")), (202,))
    source_id, source_sha = imported["source_id"], imported["sha256"]
    require(source_sha == text_sha(MATERIALS["v1"]), "imported original hash differs")
    job_id = "revision-policy-text"
    j.call("source_text_job", "POST", "/api/v1/jobs", {"job_id": job_id, "kind": "text", "input_ref": source_id}, (202,))
    j.call("source_text_execution", "POST", f"/api/v1/jobs/{job_id}/executions",
           {"deadline_ms": 120000}, (202,), headers={"idempotency-key": job_id})
    deadline = time.monotonic() + 125
    while True:
        job = j.call("source_text_state", "GET", f"/api/v1/jobs/{job_id}")
        if job.get("state") in {"succeeded", "failed", "cancelled"}:
            break
        require(time.monotonic() < deadline, "text job outcome unresolved; no replay")
        time.sleep(0.25)
    require(job["state"] == "succeeded", "new synthetic source text conversion failed")
    transform_path = f"/api/v1/sources/{source_id}/jobs/{job_id}/transform"
    transform = j.call("source_transform", "GET", transform_path)
    content = transform["content"]
    require(content.strip() == MATERIALS["v1"], "source text projection differs from synthetic policy")
    created = j.call("knowledge_candidate", "POST", "/api/v1/knowledge-items/from-transform", {
        "knowledge_type": "FACTUAL_CLAIM", "body": MATERIALS["v1"], "source_id": source_id,
        "job_id": job_id, "transform_id": transform["transform_id"], "selection_start_utf16": 0,
        "selection_end_utf16": len(content.encode("utf-16-le")) // 2, "quote": content}, (201,))
    k1 = created["knowledge_id"]
    require(created["raw_sha256"] == source_sha and bool(created["anchor_id"]), "candidate lacks fixed original anchor")
    source = {"source_id": source_id, "source_revision": source_sha, "sha256": source_sha,
              "job_id": job_id, "transform_id": transform["transform_id"], "anchor_id": created["anchor_id"]}
    m1 = j.create("material-v1", material_editor(MATERIALS["v1"]),
                  {"source_id": source_id, "source_revision": source_sha})
    original = j.call("source_metadata", "GET", f"/api/v1/sources/{source_id}")
    require(original["source_revision"] == source_sha, "original source revision differs")
    j.readbacks[f"/api/v1/sources/{source_id}"] = original
    j.readbacks[transform_path] = transform
    require(j.review_knowledge(k1, "accepted") == k1, "acceptance changed knowledge identity")

    def asset_value(version, material, knowledge_id, prior=None):
        return {"schema": "archeaxis.ai-asset/v1", "kind": "rule", "content": MATERIALS[version],
                "purpose": PURPOSE, "scope": [{"kind": "knowledge", "knowledge_id": knowledge_id}],
                "provenance": [{"kind": "document", "document_id": material["document_id"],
                                "version": material["version"], "block_id": None}], "state": "candidate",
                "members": [], "conflicts": [], "expires_at": None, "review": None,
                "revises": snapshot(prior) if prior else None,
                "source_payload": {"synthetic": True, "source": "scripted policy memo, not a private AI session"}}

    r1 = j.rubric("admission-v1", MATERIALS["v1"], [])
    r2 = j.rubric("admission-v2", MATERIALS["v2"], [])
    q1 = j.rubric("answer-v1", canonical({"question": QUESTIONS["v1"], "expected": EXPECTED["v1"]}), [])
    q2 = j.rubric("answer-v2", canonical({"question": QUESTIONS["v2"], "expected": EXPECTED["v2"]}), [])
    a1 = j.create("asset-candidate", editor(ASSET, asset_value("v1", m1, k1)))
    a2 = j.adopt("adopt-v1", a1, r1)
    kg1, ag1 = j.grants("v1", k1, a2)
    j.receipt["pre_inference_bindings"] = {"material": snapshot(m1), "knowledge_id": k1,
        "asset": snapshot(a2), "knowledge_grant": snapshot(kg1), "asset_grant": snapshot(ag1),
        "rubrics": [snapshot(v) for v in (r1, r2, q1, q2)]}
    j.checkpoint()
    b1, e1 = j.answer("v1", k1, a2, m1, kg1, ag1, q1)
    m2 = j.save("material-v2", m1, material_editor(MATERIALS["v2"]))
    k2 = j.review_knowledge(k1, "modified", MATERIALS["v2"])
    require(k2 != k1 and j.review_knowledge(k2, "accepted") == k2, "knowledge successor absent")
    # Read the old asset while still current: its knowledge reference must now be superseded.
    checked_packet(j.packet("old-knowledge-currentness", a2, ag1), a2, ag1, k1, m1, "superseded", k2)
    a3 = j.save("asset-revision-candidate", a2, editor(ASSET, asset_value("v2", m2, k2, a2)))
    j.packet("old-asset-version-denied", a2, ag1, (403,))
    a4 = j.adopt("adopt-v2", a3, r2)
    revoked = []
    for name, doc, namespace in (("knowledge", kg1, KG), ("asset", ag1, AG)):
        value = copy.deepcopy(doc["editor_json"])
        value["attrs"][namespace]["state"] = "revoked"
        revoked.append(j.save("revoke-old-" + name, doc, value))
    kg2, ag2 = j.grants("v2", k2, a4)
    require(kg2["document_id"] != kg1["document_id"] and ag2["document_id"] != ag1["document_id"],
            "new authority reused revoked identity")
    # Both snapshots are historical here. This proves the old pair is denied,
    # not an isolated test of the current grant's revoked-state condition.
    j.packet("old-asset-and-grant-pair-denied-after-revocation", a2, ag1, (403,))
    b2, e2 = j.answer("v2", k2, a4, m2, kg2, ag2, q2)
    knowledge = []
    for kid, version, successor in ((k1, "v1", k2), (k2, "v2", None)):
        view = j.call("knowledge_currentness", "GET", f"/api/v1/knowledge-items/{kid}/qualification")
        require(view["exists"] is True and view["active"] is (successor is None)
                and view["currentness"] == ("superseded" if successor else "current")
                and view["superseded_by"] == successor, "knowledge currentness differs")
        j.readbacks[f"/api/v1/knowledge-items/{kid}/qualification"] = view
        doc = j.call("knowledge_body", "GET", f"/api/v1/knowledge-items/{kid}/v3")
        require(doc["body"] == MATERIALS[version] and doc["source_id"] == source_id
                and doc["anchor_id"] == created["anchor_id"], "knowledge body/source/anchor changed")
        j.readbacks[f"/api/v1/knowledge-items/{kid}/v3"] = doc
        knowledge.append({"knowledge_id": kid, "review_version": doc["version"], "body_sha256": text_sha(doc["body"]),
                          "source_id": source_id, "source_revision": source_sha, "anchor_id": created["anchor_id"]})
    for doc in (m1, m2, a1, a2, a3, a4, kg1, ag1, kg2, ag2, *revoked, r1, r2, q1, q2):
        j.pin_document(doc)
    for doc in (m2, a4, kg2, ag2, *revoked):
        j.pin("/api/v1/documents/" + doc["document_id"], doc)
    state = j.call("workspace_identity", "GET", "/api/v1/workspace/ui-state")
    require(isinstance(state["workspace_id"], str) and isinstance(state["restore_epoch"], str), "workspace identity absent")
    return {"workspace_id": state["workspace_id"], "restore_epoch": state["restore_epoch"],
            "snapshots": {"source": source, "material_v1": snapshot(m1), "material_v2": snapshot(m2),
                "knowledge_v1": knowledge[0], "knowledge_v2": knowledge[1],
                "asset_candidate_v1": snapshot(a1), "asset_adopted_v1": snapshot(a2),
                "asset_candidate_v2": snapshot(a3), "asset_adopted_v2": snapshot(a4),
                "knowledge_grants": [snapshot(kg1), snapshot(revoked[0]), snapshot(kg2)],
                "asset_grants": [snapshot(ag1), snapshot(revoked[1]), snapshot(ag2)],
                "answers": [b1, b2], "evaluations": [snapshot(e1), snapshot(e2)]}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, help="Optional canonical build output cross-check; never the launch root")
    parser.add_argument("--core-build-receipt", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True, help="Explicit formal stage in canonical run artifacts")
    parser.add_argument("--runtime-manifest-sha256", required=True)
    args = parser.parse_args(argv)
    require(os.environ.get("ARCHEAXIS_RUN_ROOT") and os.environ.get("ARCHEAXIS_RUN_ID"), "run this probe through dev.py")
    dev = load("revision_dev", REPO / "scripts/runtime/dev.py")
    paths = dev.layout(REPO, os.environ["ARCHEAXIS_RUN_ID"])
    require(dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"])) == paths["run"], "foreign run root")
    require(os.environ.get("PYTHONDONTWRITEBYTECODE") == "1" and sys.dont_write_bytecode,
            "dev.py bytecode isolation is required; stage must remain read-only")
    output = dev.artifact_directory(REPO, "colearning-asset-revision")
    receipt = {"schema": "archeaxis.asset-revision-observation/v1", "engineering_status": "INCOMPLETE",
        "source_worktree": str(REPO), "source_commit": os.environ["ARCHEAXIS_SOURCE_COMMIT"],
        "source_patch_sha256": os.environ["ARCHEAXIS_SOURCE_PATCH_SHA256"], "stages": [], "answers": [],
        "inventories": [], "quality": {}, "model_request_count": 0, "contract": CONTRACT,
        "contract_sha256": sha(CONTRACT), "synthetic": True, "human_review": REVIEWER,
        "owner_acceptance": False, "learning_improvement": "NOT_ESTABLISHED", "generalization": "NOT_ESTABLISHED",
        "model_request_ceiling": 2, "raw_private_context_access": False,
        "limits": ["Finite synthetic rule update, not model training or a same-question improvement comparison",
                   "Core packet/context binding, not a claim of directly instrumented provider internals",
                   "No native/installed acceptance; future restore must reauthorize fenced grants"]}
    from scripts.runtime import runtime_resources
    client = load("revision_client", REPO / "shared/core_client.py")
    launcher = None
    child = None
    j = None
    code = 1
    try:
        core = dev.read_core_build(args.core_build_receipt, paths, os.environ)
        if args.core is not None:
            require(dev.build_file_identity(args.core) == core, "selected executable differs from qualified Core")
        receipt["core"] = core
        receipt["core_build_receipt"] = dev.build_file_identity(args.core_build_receipt)
        runtime = bind_staged_runtime(args.runtime_root, args.runtime_manifest_sha256, core, paths, dev, runtime_resources)
        receipt["runtime_binding"] = runtime
        receipt["evidence_level"] = "FORMAL_STAGED_CORE_PYTHON_WORKERS_REAL_LOCAL_MODEL"
        stage_root = Path(runtime["root"])
        require(not output.is_relative_to(stage_root), "probe data must be outside the immutable stage")
        launcher = load("revision_launcher", Path(runtime["launcher"]["path"]))
        launcher.ROOT = stage_root
        resolved_profile = launcher.load_profile(stage_root)
        require(resolved_profile["python"] == Path(runtime["python"]["path"])
                and resolved_profile["script"] == Path(runtime["transport"]["path"])
                and [row["script"] for row in resolved_profile["routes"] if row["capability"] == "machine.answer"]
                == [Path(runtime["worker"]["path"])], "launcher resolves different staged inputs")
        worker_path = Path(runtime["worker"]["path"])
        worker = load("revision_worker", worker_path)
        route = declared_route(worker)
        receipt["route"] = route
        receipt["worker"] = dev.build_file_identity(worker_path)
        receipt["prompt_sha256"] = text_sha(worker.PROMPT_TEMPLATE)
        receipt["inventories"].append(loaded_inventory(route))
        def checkpoint():
            staging = output / "receipt.json.tmp"
            staging.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            staging.replace(output / "receipt.json")

        j = Journey(client, receipt, route, checkpoint)

        def start():
            nonlocal child
            child, j.base, launched, j.tokens = launcher.start(output / "data", 0)
            require(launched["text_worker"]["python"] == runtime["python"]["path"]
                    and launched["text_worker"]["script"] == runtime["transport"]["path"]
                    and [row["script"] for row in launched["text_worker"].get("routes", []) if row["capability"] == "machine.answer"]
                    == [runtime["worker"]["path"]], "launched worker differs from pinned runtime")
            receipt.setdefault("launches", []).append({"runtime_root": str(stage_root),
                "workspace": launched["workspace"], "text_worker": copy.deepcopy(launched["text_worker"])})
            version = j.call("session_identity", "GET", "/api/v1/system/version")
            expected_workspace = checked_workspace_report(
                launched["workspace"], output / "data" / "workspace.sqlite", repo=REPO)
            workspace = dev.safe_path(checked_workspace_report(
                version["workspace_db"], expected_workspace, repo=REPO))
            workspace.relative_to(output)
            require(re.fullmatch(r"[0-9a-f]{32}", version["session_id"]), "session identity absent")
            return version, workspace

        def stop(version):
            nonlocal child
            response = j.call("normal_shutdown", "POST", "/api/v1/system/shutdown", {"session_id": version["session_id"]}, (202,))
            require(response["state"] == "draining", "shutdown was not acknowledged")
            exit_code = child.wait(timeout=30)
            receipt.setdefault("shutdowns", []).append({"acknowledged": True, "exit_code": exit_code, "forced": False})
            launcher.stop(child)  # Already exited: only join owned pipe readers/close handles.
            child = None
            require(exit_code == 0, "Core did not exit successfully after draining")

        version, workspace = start()
        seed = exercise(j)
        backup = j.call("formal_backup", "POST", "/api/v1/workspace/backups", {}, (201,))
        require(backup["verified"] is True and backup["schema"] == "archeaxis-core-backup-1"
                and re.fullmatch(r"[0-9a-f]{32}\.sqlite", backup["filename"]), "unverified Core backup")
        backup_path = dev.safe_path(workspace.parent / "backups" / backup["filename"])
        backup_path.relative_to(output)
        actual = dev.build_file_identity(backup_path)
        require(actual["sha256"] == backup["sha256"] and actual["bytes"] == backup["bytes"], "backup artifact differs")
        listed = j.call("formal_backup_readback", "GET", "/api/v1/workspace/backups")
        require(backup in listed["backups"] and not listed["unavailable_backups"], "Core backup verification changed")
        receipt["backup"] = {"path": str(backup_path), "sha256": backup["sha256"], "receipt": backup}
        stop(version)
        before_restart = j.model_requests
        restarted, same_workspace = start()
        require(same_workspace == workspace and restarted["session_id"] != version["session_id"], "restart workspace/session differs")
        for path, value in j.readbacks.items():
            require(j.call("restart_readback", "GET", path) == value, "restart lost fixed history/currentness")
        state = j.call("restart_workspace_identity", "GET", "/api/v1/workspace/ui-state")
        require(state["workspace_id"] == seed["workspace_id"] and state["restore_epoch"] == seed["restore_epoch"], "ordinary restart changed workspace identity")
        stop(restarted)
        require(j.model_requests == before_restart == 2, "restart issued another inference")
        require(dev.read_core_build(args.core_build_receipt, paths, os.environ) == core
                and dev.build_file_identity(worker_path) == receipt["worker"], "qualified runtime changed")
        require(bind_staged_runtime(args.runtime_root, args.runtime_manifest_sha256, core, paths, dev, runtime_resources)
                == runtime, "formal staged runtime changed during observation")
        _, patch = dev.worktree_identity(REPO)
        require(patch == receipt["source_patch_sha256"] and dev.git(REPO, "rev-parse", "HEAD") == receipt["source_commit"], "source changed during observation")
        receipt["source_consistent"] = True
        receipt["engineering_status"] = "CORE_REVISION_AND_RESTART_OBSERVED"
        receipt["native_seed"] = {"schema": "archeaxis.v3-native-seed/v1",
            "source_worktree": str(REPO), "source_commit": receipt["source_commit"],
            "source_patch_sha256": patch, "core_sha256": core["sha256"], "synthetic": True,
            "runtime_manifest_sha256": runtime["manifest"]["sha256"], "runtime_binding": runtime,
            "owner_acceptance": False, "backup": receipt["backup"], **seed}
        (output / "native-seed.json").write_text(json.dumps(receipt["native_seed"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # Process success describes the observed engineering path; quality is separately retained.
        code = 0
    except Exception as error:  # Preserve partial evidence and never retry a potentially dispatched call.
        receipt["failure"] = {"type": type(error).__name__,
                              "reason": str(error) if isinstance(error, ValueError) else "see stage; external error detail withheld"}
    finally:
        if child is not None:
            try:
                receipt["fallback_cleanup"] = {"exit_code": launcher.stop(child), "forced": True,
                                                "normal_shutdown_proven": False}
            except Exception as error:
                receipt["fallback_cleanup"] = {"state": "UNKNOWN", "error_type": type(error).__name__}
        if j is not None:
            receipt["model_request_count"] = j.model_requests
        receipt["observed_bound_model_response_count"] = len(receipt["answers"])
        receipt["exit_code"] = code
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"receipt": str(output / "receipt.json"), "exit_code": code,
                          "engineering_status": receipt["engineering_status"], "quality": receipt["quality"]}))
    return code


if __name__ == "__main__":
    sys.exit(main())
