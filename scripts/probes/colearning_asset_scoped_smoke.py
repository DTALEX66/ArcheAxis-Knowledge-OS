"""Opt-in finite asset/scoped journey; existing Core is the only business writer.

The rubric, source, asset content and budgets are frozen before baseline inference.
Adoption/use authority changes are the intervention. No accepted knowledge rewrite,
parameter learning, private session access, general learning or human review is claimed.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "asset_legacy_contract", Path(__file__).with_name("colearning_real_model_smoke.py"))
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)
PURPOSE = "finite synthetic store and release application"
NAMESPACE = "archeaxis_ai_asset"
PACKAGE_CONTENT = "Finite inert synthetic store and release rules."
BUDGET = {"max_tokens": 2048, "timeout_s": 120}
ROUTE = {"model": "qwen3.5-4b", "endpoint": "http://127.0.0.1:1234/v1", "protocol": "openai",
         "prompt_version": "archeaxis.vnext/v1 2026-10-02", "answer_policy": "grounded",
         "engine": "python-worker-machine-answer", "engine_version": "0.1.0"}
METHOD_MAPPING = {"design_label": "method", "actual_kind": "rule",
                  "basis": "inert decision rule over supplied facts, no new enum or executable skill"}
CONTRACT = {"schema": "aaos.asset-scoped-frozen/v1", "rubric": legacy.RUBRIC,
            "knowledge": legacy.CONTEXT, "rule_content": legacy.CORRECTED_CONTEXT,
            "package_content": PACKAGE_CONTENT, "purpose": PURPOSE, "budget": BUDGET, "route": ROUTE,
            "method_mapping": METHOD_MAPPING, "independent_sample_count": 1,
            "intervention": "package adoption and scoped asset use only; same knowledge/question/model/budget"}

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def text_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def snapshot(doc):
    result = {k: doc[k] for k in ("document_id", "version", "content_sha256")}
    require(isinstance(result["document_id"], str) and result["document_id"]
            and type(result["version"]) is int and result["version"] > 0
            and isinstance(result["content_sha256"], str)
            and len(result["content_sha256"]) == 64
            and all(c in "0123456789abcdef" for c in result["content_sha256"]),
            "invalid saved snapshot")
    return result

def editor(namespace, value):
    return {"type": "doc", "content": [], "attrs": {namespace: value}}

def asset(kind, content, members=()):
    return {"schema": "archeaxis.ai-asset/v1", "kind": kind, "content": content,
            "purpose": PURPOSE, "scope": [], "provenance": [], "state": "candidate",
            "members": list(members), "conflicts": [], "expires_at": None,
            "review": None, "revises": None, "source_payload": None}

def packet(package, member, grant, operation):
    # Exact serde_json projection from existing ai_asset::packet_items/admit.
    items = []
    for doc in (package, member):
        meta = doc["editor_json"]["attrs"][NAMESPACE]
        items.append({"snapshot": snapshot(doc), **{k: meta[k] for k in
                     ("kind", "content", "purpose", "scope", "provenance")},
                     "engine_execution": "NOT_EXECUTED", "grants_professional_truth": False,
                     "grants_human_mastery": False, "grants_machine_qualification": False})
    return {"schema": "archeaxis.ai-context-packet/v1", "asset": snapshot(package),
            "consumer": "local-machine", "purpose": PURPOSE, "operation": operation,
            "items": items, "grant": snapshot(grant), "reference_only_sources": True,
            "private_session_access": False, "tool_execution": "NOT_EXECUTED",
            "machine_qualification": False, "human_mastery": False, "professional_truth": False}

def verify_answer(body, sent, task, knowledge_grant, expected_packet=None, *, retest=False):
    execution = body["execution_request"] if retest else body["request"]
    request = execution["request"] if retest else execution
    operation = "retest" if retest else "answer"
    require(body["question"] == sent["question"] == legacy.RUBRIC[task]["question"],
            "question differs from frozen task")
    require(body["knowledge_id"] == sent["knowledge_id"] == request["knowledge_id"],
            "knowledge identity changed")
    for key in ("question", "context_grant", "max_tokens"):
        require(request.get(key) == sent[key], "persisted request mismatch: " + key)
    require(execution.get("timeout_s") == sent["timeout_s"] == BUDGET["timeout_s"]
            and request["max_tokens"] == BUDGET["max_tokens"], "generation budget changed")
    auth = body["context_authorization"]
    require({k: auth[k] for k in ("document_id", "version", "content_sha256")} ==
            snapshot(knowledge_grant), "knowledge grant snapshot mismatch")
    require(auth["authorization"] == knowledge_grant["editor_json"]["attrs"]["archeaxis_context_grant"]
            and auth["current_permission_valid"] is True and auth["operation"] == operation,
            "scoped authorization mismatch")
    expected_context = legacy.CONTEXT
    if expected_packet is not None:
        incoming = sent["asset_context_grant"]
        require(request.get("asset_context_grant") == incoming, "asset consumption not persisted")
        require(incoming["asset"] == expected_packet["asset"]
                and incoming["grant"] == expected_packet["grant"]
                and incoming["purpose"] == PURPOSE
                and incoming["consumer"] == expected_packet["consumer"] == "local-machine"
                and incoming["operation"] == expected_packet["operation"] == operation,
                "asset identity/purpose/consumer/operation mismatch")
        proof = {"schema": "archeaxis.machine-asset-context/v1",
                 "asset": expected_packet["asset"], "grant": expected_packet["grant"],
                 "consumer": "local-machine", "operation": operation,
                 "packet_sha256": sha(expected_packet),
                 "member_snapshots": [item["snapshot"] for item in expected_packet["items"]],
                 "tool_execution": "NOT_EXECUTED", "private_session_access": False}
        require(execution.get("asset_context") == proof, "packet SHA/member snapshot mismatch")
        require(execution.get("knowledge_context_sha256") == text_sha(legacy.CONTEXT),
                "knowledge body changed during asset intervention")
        expected_context = ("CANONICAL_KNOWLEDGE:\n" + legacy.CONTEXT +
                            "\n\nAI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n"
                            + canonical(expected_packet))
    else:
        require("asset_context" not in execution and "asset_context_grant" not in request,
                "asset present in no-asset baseline")
    require(execution.get("context_sha256") == text_sha(expected_context),
            "merged worker input digest mismatch")
    answer = body["answer"]
    require(isinstance(answer.get("answer"), str) and answer["answer"].strip()
            and answer.get("model") and answer.get("finish_reason") == "stop"
            and answer.get("truncated") is not True, "incomplete/unidentified answer")
    require({key: answer.get(key) for key in ROUTE} == ROUTE
            and answer.get("requested_model") == answer.get("observed_model") == ROUTE["model"]
            and answer.get("max_tokens") == BUDGET["max_tokens"],
            "worker model/route/prompt/budget identity mismatch")
    identity = body["retest_task_id"] if retest else body["answer_id"]
    require(isinstance(identity, str) and identity, "missing answer identity")
    if not retest:
        require(body.get("client_request_id") == sent["client_request_id"],
                "client request identity mismatch")
    return {"answer_id": identity, "answer_sha256": sha(answer["answer"]),
            "request_sha256": sha(execution), "request": execution,
            "authorization_sha256": sha(auth), "authorization": auth,
            "context_sha256": execution["context_sha256"], "model": answer["model"],
            "generation_identity": {key: answer[key] for key in ROUTE},
            "score": legacy.score(answer["answer"], task),
            "packet_sha256": sha(expected_packet) if expected_packet else None,
            "asset_members": expected_packet["items"] if expected_packet else []}

def compare(before, after, transfer_before, transfer_after):
    scores = [b["score"] for b in (before, after, transfer_before, transfer_after)]
    result = {"status": "REVIEW_REQUIRED", "original": scores[:2], "independent_task": scores[2:],
              "learning_improvement": "NOT_ESTABLISHED", "generalization": "NOT_ESTABLISHED",
              "sample_count_original": 1, "sample_count_independent_task": 1,
              "original_observation": "UNCOMPARABLE", "transfer_observation": "UNCOMPARABLE"}
    require(len({canonical(b["generation_identity"]) for b in (before, after, transfer_before, transfer_after)}) == 1,
            "model changed across comparison")
    require(len({b["answer_id"] for b in (before, after, transfer_before, transfer_after)}) == 4,
            "independent/post-intervention task identity reused")
    if "REVIEW_REQUIRED" in scores:
        result["status"] = "UNSCORABLE_COMPARISON"
        return result
    result["original_observation"] = ("NO_FAILURE_OBSERVED" if before["score"] == "CORRECT"
                                      else "FINITE_TASK_DELTA" if after["score"] == "CORRECT"
                                      else "NO_IMPROVEMENT")
    result["transfer_observation"] = ("NO_MEASURED_DELTA" if transfer_before["score"] == "CORRECT"
                                      else "FINITE_INDEPENDENT_TASK_DELTA"
                                      if transfer_after["score"] == "CORRECT" else "NO_IMPROVEMENT")
    if after["score"] != "CORRECT":
        result["status"] = "ORIGINAL_TASK_FAILURE_REVIEW"
    elif transfer_after["score"] != "CORRECT":
        result["status"] = "TRANSFER_FAILURE_REVIEW"
    else:
        result["status"] = "FINITE_ASSET_COMPARISON_RECORDED"
    return result


def verify_correction(response, sent, original):
    """A self-consistent persisted prior cannot legitimize a different correction."""
    require(legacy.score(original["answer"]["answer"], "original") == "INCORRECT",
            "correct/unscorable original cannot be corrected as failure")
    require(sent["answer_id"] == original["answer_id"]
            and sent["knowledge_id"] == original["knowledge_id"]
            and sent["question"] == original["question"] == legacy.QUESTION
            and sent["machine_answer"] == original["answer"]["answer"]
            and sent["corrected_answer"] == legacy.CORRECTED_CONTEXT,
            "correction request differs from frozen measured failure")
    for key in ("answer_id", "question", "machine_answer", "corrected_answer", "reviewer", "error_note"):
        require(response.get(key) == sent[key], "correction response mismatch: " + key)
    candidate = response.get("correction_candidate_id")
    require(response.get("corrects_knowledge_id") == sent["knowledge_id"]
            and response.get("failed_task_id") == "evaluation_" + original["answer_id"]
            and isinstance(candidate, str) and candidate
            and candidate not in {original["knowledge_id"], original["answer_id"]}
            and response.get("schema") == "archeaxis.machine-correction/v1"
            and response.get("status") == response.get("authority") == "candidate",
            "correction identity/state does not bind original failure")

def run(call, receipt, knowledge_id, human, machine_token, run_root, repo_root):
    """Called after the existing main import/review path; no extra Runtime or writer."""
    bindings = {}
    frozen = None
    comparison = {"status": "INCOMPLETE", "learning_improvement": "NOT_ESTABLISHED"}
    model_requests = 0
    failure = None
    exit_code = 1
    checks = []
    persisted = {}
    sent_requests = {}
    expected_packets = {}
    try:
        # Read only the existing public worker declaration; never discover/load a model here.
        worker_path = repo_root / "services/python-workers/machine/worker_machine_answer.py"
        worker = legacy._load("asset_worker_contract", worker_path)
        lanes = worker._declared_lanes()
        require(len(lanes) == 1 and lanes[0]["model"] == ROUTE["model"]
                and lanes[0]["base"] == ROUTE["endpoint"] and lanes[0]["protocol"] == ROUTE["protocol"],
                "current declared route differs from frozen finite fixture")
        for key, value in (("ARCHEAXIS_MACHINE_MODEL", ROUTE["model"]),
                           ("ARCHEAXIS_MACHINE_ENDPOINT", ROUTE["endpoint"]),
                           ("ARCHEAXIS_MACHINE_PROTOCOL", ROUTE["protocol"])):
            require(not os.environ.get(key, "").strip() or os.environ[key].strip() == value,
                    "existing process route override differs: " + key)
        require(ROUTE["prompt_version"] == worker.PROMPT_VERSION,
                "production prompt version differs")
        worker_identity = {"path": worker_path.relative_to(repo_root).as_posix(),
                           "sha256": hashlib.sha256(worker_path.read_bytes()).hexdigest(),
                           "prompt_template_sha256": text_sha(worker.PROMPT_TEMPLATE),
                           "route": ROUTE}
        def api(name, method, path, body=None, expected=(200,), token=None):
            status, response = call(method, path, human if token is None else token, body)
            receipt.stage(name, status=status, expected_status=list(expected), body=response,
                          request_sha256=sha(body))
            require(status in expected, name + ": unexpected HTTP status " + str(status))
            return response

        def create(name, namespace, value):
            return api(name, "POST", "/api/v1/documents",
                       {"create_request_id": "asset-probe-" + name, "title": name,
                        "editor_json": editor(namespace, value)}, expected=(201,))

        def save(name, doc, edit):
            return api(name, "PUT", "/api/v1/documents/" + doc["document_id"] + "/draft",
                       {"expected_version": doc["version"], "editor_json": edit})

        rubric_doc = api("asset_fixed_rubric", "POST", "/api/v1/machine/rubrics", {
            "schema": "archeaxis.machine-rubric/v1", "request_id": "asset-probe-fixed-rubric",
            "title": "Frozen synthetic rule fit", "purpose": PURPOSE, "sources": [],
            "criteria": [{"criterion_id": "fit", "label": "inert supplied-fact rule",
                          "expectation": canonical(CONTRACT)}]}, expected=(201,))

        def adopt(name, doc):
            changed = copy.deepcopy(doc["editor_json"])
            meta = changed["attrs"][NAMESPACE]
            meta["state"] = "adopted"
            meta["review"] = {"asset": snapshot(doc), "rubric": snapshot(rubric_doc),
                             "reviewer": "scripted-human-fixture", "basis": "exact frozen inert synthetic content; NOT measured learning",
                             "judgments": [{"criterion_id": "fit", "outcome": "passed",
                                            "basis": "exact finite supplied-fact rule, no executable authority"}],
                             "outcome": "passed"}
            return save(name, doc, changed)

        knowledge_grant = create("knowledge-grant", "archeaxis_context_grant", {
            "schema": "archeaxis.context-grant/v1", "purpose": PURPOSE, "consumer": "local-machine",
            "operations": ["answer", "retest"], "knowledge_id": knowledge_id, "provenance": [],
            "authorization_basis": "explicit owned synthetic fixture use", "expires_at": None,
            "state": "granted"})
        kg = {**snapshot(knowledge_grant), "purpose": PURPOSE}
        member = adopt("adopt-rule", create("rule-candidate", NAMESPACE,
                                         asset("rule", legacy.CORRECTED_CONTEXT)))
        candidate = create("package-candidate", NAMESPACE,
                           asset("knowledge_package", PACKAGE_CONTENT, [snapshot(member)]))

        def grant(name, package, *, expires=None, consumer="local-machine", state="granted"):
            return create(name, "archeaxis_asset_context_grant", {
                "schema": "archeaxis.asset-context-grant/v1", "asset": snapshot(package),
                "purpose": PURPOSE, "consumer": consumer,
                "operations": ["read_packet"] if consumer == "manual-context-packet" else ["answer", "retest"],
                "authorization_basis": "explicit owned synthetic asset fixture use",
                "expires_at": expires, "state": state})

        def consumption(name, package, grant_doc, operation="answer"):
            return {"request_id": "asset-use-" + name, "asset": snapshot(package),
                    "grant": snapshot(grant_doc), "purpose": PURPOSE, "consumer": "local-machine",
                    "operation": operation}

        def answer_request(name, task, asset_use=None):
            body = {"client_request_id": "asset-answer-" + name, "knowledge_id": knowledge_id,
                    "question": legacy.RUBRIC[task]["question"], "context_grant": kg, **BUDGET}
            if asset_use is not None:
                body["asset_context_grant"] = asset_use
            return body

        candidate_grant = grant("candidate-grant", candidate)
        frozen = {"contract": copy.deepcopy(CONTRACT), "contract_sha256": sha(CONTRACT),
                  "rubric": snapshot(rubric_doc), "worker_identity": worker_identity, "knowledge_grant": snapshot(knowledge_grant),
                  "member": snapshot(member), "candidate_package": snapshot(candidate),
                  "member_payload_sha256": sha(member["editor_json"]["attrs"][NAMESPACE]),
                  "candidate_package_payload_sha256": sha(candidate["editor_json"]["attrs"][NAMESPACE])}
        receipt.stage("asset_frozen_before_baseline", body=frozen)
        (run_root / "asset-frozen.json").write_text(json.dumps(frozen, indent=2), encoding="utf-8")
        api("candidate_cannot_be_consumed", "POST", "/api/v1/machine/answers",
            answer_request("candidate-negative", "original",
                           consumption("candidate-negative", candidate, candidate_grant)), expected=(403,))
        checks.append("candidate_denied")

        def execute(name, task, body, expected_packet=None, retest=False):
            nonlocal model_requests
            model_requests += 1
            require(model_requests <= 5, "fixed five model request ceiling")
            response = api(name, "POST", "/api/v1/machine/retests" if retest else "/api/v1/machine/answers", body)
            binding = verify_answer(response, body, task, knowledge_grant, expected_packet, retest=retest)
            readback = api(name + "_readback", "GET",
                           "/api/v1/machine/tasks/" + binding["answer_id"], token=machine_token)
            conditions = readback["conditions"]
            if isinstance(conditions, str):
                conditions = json.loads(conditions)
            require(conditions == response and readback["task_id"] == binding["answer_id"],
                    "persistent answer/readback differs")
            persisted[name] = (response, readback)
            bindings[name] = binding
            sent_requests[name] = body
            expected_packets[name] = expected_packet
            return response

        original = execute("asset_original_before", "original", answer_request("original-before", "original"))
        require(bindings["asset_original_before"]["score"] != "REVIEW_REQUIRED",
                "baseline requires review; comparison cannot be scored")
        execute("asset_abstention_before", "abstention", answer_request("abstention-before", "abstention"))
        require(bindings["asset_abstention_before"]["score"] == "CORRECT", "grounding control failed fixed rubric")
        execute("asset_transfer_before", "transfer", answer_request("transfer-before", "transfer"))
        require(bindings["asset_transfer_before"]["score"] != "REVIEW_REQUIRED",
                "baseline requires review; comparison cannot be scored")
        require(len({b["model"] for b in bindings.values()}) == 1, "baseline model changed")
        package = adopt("adopt-package", candidate)
        use_grant = grant("adopted-grant", package)
        # Semantic content is fixed: adoption changes state/review only.
        before_meta = copy.deepcopy(candidate["editor_json"]["attrs"][NAMESPACE])
        after_meta = copy.deepcopy(package["editor_json"]["attrs"][NAMESPACE])
        for value in (before_meta, after_meta):
            value.pop("state")
            value.pop("review")
        require(before_meta == after_meta, "asset content changed after baseline")

        correction = None
        if bindings["asset_original_before"]["score"] == "INCORRECT":
            correction_request = {
                "answer_id": original["answer_id"], "knowledge_id": knowledge_id,
                "question": legacy.QUESTION, "machine_answer": original["answer"]["answer"],
                "corrected_answer": legacy.CORRECTED_CONTEXT, "reviewer": "scripted-human-fixture",
                "error_note": "frozen bounded original rubric differs; no accepted knowledge rewrite"}
            correction = api("asset_failed_answer_correction", "POST", "/api/v1/machine/corrections", correction_request)
            verify_correction(correction, correction_request, original)
            body = {"retest_of": correction["failed_task_id"], "knowledge_id": knowledge_id,
                    "question": legacy.QUESTION, "context_grant": kg, **BUDGET,
                    "asset_context_grant": consumption("original-retest", package, use_grant, "retest")}
            after = execute("asset_original_after", "original", body,
                            packet(package, member, use_grant, "retest"), retest=True)
            prior = copy.deepcopy(original)
            prior["correction"] = correction
            require(after["prior"]["conditions"] == prior
                    and after["retest_of"] == correction["failed_task_id"],
                    "retest prior failure binding mismatch")
        else:
            after = execute("asset_original_after", "original",
                            answer_request("original-after", "original",
                                           consumption("original-after", package, use_grant)),
                            packet(package, member, use_grant, "answer"))
        execute("asset_transfer_after", "transfer",
                answer_request("transfer-after", "transfer", consumption("transfer-after", package, use_grant)),
                packet(package, member, use_grant, "answer"))
        comparison = compare(bindings["asset_original_before"], bindings["asset_original_after"],
                             bindings["asset_transfer_before"], bindings["asset_transfer_after"])

        # Fixed real API negative controls, after observations; never use rejection as improvement.
        positive = sent_requests["asset_transfer_after"]
        require(api("asset_exact_retry", "POST", "/api/v1/machine/answers", positive)
                == persisted["asset_transfer_after"][0], "exact retry differs")
        omitted = copy.deepcopy(positive)
        omitted.pop("asset_context_grant")
        api("asset_omission_conflict", "POST", "/api/v1/machine/answers", omitted, expected=(409,))
        if correction:
            retest_body = sent_requests["asset_original_after"]
            require(api("asset_retest_exact_retry", "POST", "/api/v1/machine/retests", retest_body)
                    == after, "retest retry differs")
        for name, field, bad in (("consumer", "consumer", "manual-context-packet"),
                                 ("purpose", "purpose", "different-purpose"),
                                 ("operation", "operation", "read_packet"),
                                 ("cross-package", "asset", snapshot(member))):
            use = consumption(name, package, use_grant)
            use[field] = bad
            api("asset_" + name + "_denied", "POST", "/api/v1/machine/answers",
                answer_request(name, "original", use), expected=(403,))
            checks.append(name + "_denied")
        expired = grant("expired-grant", package, expires=1)
        api("asset_expiry_denied", "POST", "/api/v1/machine/answers",
            answer_request("expiry", "original", consumption("expiry", package, expired)), expected=(403,))
        manual = grant("manual-grant", package, consumer="manual-context-packet")
        api("asset_manual_grant_denied", "POST", "/api/v1/machine/answers",
            answer_request("manual", "original", consumption("manual", package, manual)), expected=(403,))
        changed = copy.deepcopy(positive)
        changed["question"] = legacy.QUESTION
        api("asset_frozen_request_conflict", "POST", "/api/v1/machine/answers", changed, expected=(409,))
        # Withdrawing a used member invalidates the same current packet, including cached results.
        withdrawn_editor = copy.deepcopy(member["editor_json"])
        withdrawn_editor["attrs"][NAMESPACE]["state"] = "withdrawn"
        save("withdraw_used_member", member, withdrawn_editor)
        api("asset_withdrawal_denied", "POST", "/api/v1/machine/answers", positive, expected=(403,))
        if correction:
            api("asset_withdrawn_retest_denied", "POST", "/api/v1/machine/retests",
                sent_requests["asset_original_after"], expected=(403,))
        for name, (_response, original_readback) in persisted.items():
            reread = api(name + "_prior_preserved", "GET",
                         "/api/v1/machine/tasks/" + bindings[name]["answer_id"], token=machine_token)
            require(reread == original_readback, "prior answer mutated after negative controls")
        checks += ["expiry_denied", "manual_grant_denied", "frozen_request_conflict",
                   "omission_conflict", "exact_retry", "withdrawal_denied", "all_prior_answers_preserved"]
        require(frozen["contract"] == CONTRACT and frozen["contract_sha256"] == sha(CONTRACT),
                "frozen contract changed")
        exit_code = 0 if comparison["status"] == "FINITE_ASSET_COMPARISON_RECORDED" else 1
    except Exception as exc:
        # Preserve partial stages and fail; never print transport/token exception contents.
        failure = {"type": type(exc).__name__, "reason": str(exc) if isinstance(exc, ValueError) else "unverified failure"}
        receipt.stage("asset_journey_failure", problem=failure["reason"], error_type=failure["type"])
        exit_code = 3 if receipt.blocked else 1
    observed = [name for name, (body, _) in persisted.items()
                if receipt.live_execution and body["answer"].get("engine") == "python-worker-machine-answer"]
    document = {"schema": "aaos.colearning-asset-scoped-receipt/v1",
                "evidence_class": "LIVE_CORE_MODEL_RESPONSE_OBSERVED" if observed else "SYNTHETIC_OR_UNVERIFIED",
                "observed_model_response_stages": observed,
                "main_exit": exit_code, "frozen": frozen, "quality_assessment": comparison,
                "bindings": bindings, "stages": receipt.stages, "negative_checks": checks,
                "model_candidate_request_count": model_requests, "blocked": receipt.blocked,
                "failure": failure, "asset_effect": "FINITE_SYNTHETIC_OBSERVATION_ONLY" if not observed else "FINITE_TASK_OBSERVATION_ONLY",
                "full_f05": "PARTIAL", "human_review": "SCRIPTED_FIXTURE",
                "real1_previous_failure": "PRESERVED_NOT_REPLACED", "learning_improvement": "NOT_ESTABLISHED",
                "what_is_not_proven": ["general learning", "model parameter changes", "human mastery",
                                       "whole CL/J", "installation", "external peer consumption"]}
    (run_root / "receipt.json").write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"schema": document["schema"], "main_exit": exit_code,
                      "quality_status": comparison["status"], "failure": failure,
                      "model_candidate_request_count": model_requests,
                      "evidence_class": document["evidence_class"]}, ensure_ascii=False))
    return exit_code
