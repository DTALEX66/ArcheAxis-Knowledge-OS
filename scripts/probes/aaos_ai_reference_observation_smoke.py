"""One opt-in synthetic asset observation through Core and its existing local model worker.

Run only through scripts/runtime/dev.py with a caller-supplied Core binary. The
probe creates an isolated synthetic workspace and does not change model settings.
The receipt contains hashes and bounded outcomes; the isolated Core workspace
retains its ordinary synthetic answer and transient launch documents.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.util
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.ci.real_core_grading_journey import Core  # noqa: E402

WORKER = ROOT / "services/python-workers/machine/worker_machine_answer.py"
PURPOSE = "synthetic reference state observation"
KNOWLEDGE = "Synthetic fixture: the approved example colour is blue."
MODEL = "qwen3.5-4b"  # Current worker's own declared default; not an override.
BASE = "http://127.0.0.1:1234/v1"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def snapshot(value):
    return {key: value[key] for key in ("document_id", "version", "content_sha256")}


class SyntheticCore(Core):
    with_machine = True

    def _launch_document(self):
        launch = super()._launch_document()
        launch["text_worker"]["routes"] = ([{"capability": "machine.answer", "script": str(WORKER)}]
                                            if self.with_machine else [])
        return launch


def request(core, method, path, body=None, timeout=20):
    connection = http.client.HTTPConnection("127.0.0.1", core.port, timeout=timeout)
    encoded = None if body is None else canonical(body)
    try:
        connection.request(method, path, body=encoded, headers={
            "content-type": "application/json", "x-archeaxis-launch-token": core.token})
        response = connection.getresponse()
        data = response.read()
        try:
            parsed = json.loads(data) if data else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = {}
        return response.status, parsed
    finally:
        connection.close()


def run(args, receipt):
    root = Path(os.environ["ARCHEAXIS_RUN_ROOT"])
    workspace = root / "artifacts/synthetic-workspace"
    workspace.mkdir(parents=True, exist_ok=False)
    core_exe = Path(args.core_exe).resolve(strict=True)
    receipt["core_binary_sha256"] = hashlib.sha256(core_exe.read_bytes()).hexdigest()
    receipt["worker_sha256"] = hashlib.sha256(WORKER.read_bytes()).hexdigest()

    # Do not change service/provider settings or follow an override to a different endpoint.
    if any(os.environ.get(key, "").strip() for key in
           ("ARCHEAXIS_MACHINE_ENDPOINT", "ARCHEAXIS_MACHINE_MODEL", "ARCHEAXIS_MACHINE_PROTOCOL")):
        raise RuntimeError("existing machine route override prevents this default-route sample")
    spec = importlib.util.spec_from_file_location("owned_machine_worker", WORKER)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    route = worker._endpoint()
    if route.get("base") != BASE or route.get("protocol") != "openai" or route.get("model") != MODEL:
        raise RuntimeError("current worker default route differs from the selected local sample")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(BASE + "/models", timeout=5) as response:
        inventory = json.load(response)
    if MODEL not in {row.get("id") for row in inventory.get("data", []) if isinstance(row, dict)}:
        raise RuntimeError("the existing default model is not advertised")
    receipt["route"] = {"base": BASE, "model": MODEL, "configuration_changed": False}

    core = SyntheticCore(core_exe, workspace, Path(sys.executable))
    try:
        core.start()

        def call(method, path, body=None, expected=200, timeout=20):
            status, result = request(core, method, path, body, timeout)
            if status != expected:
                receipt["last_http_status"] = status
                receipt["failure_code"] = result.get("reason_code") or result.get("code")
                raise RuntimeError("synthetic Core request did not meet its expected status")
            return result

        material = call("POST", "/api/v1/documents", {"title": "Synthetic pinned source",
            "editor_json": {"type": "doc", "content": []}}, expected=201)
        ref = {"kind": "document", "document_id": material["document_id"], "version": 1, "block_id": None}
        call("PUT", f"/api/v1/documents/{material['document_id']}/draft", {"expected_version": 1,
            "editor_json": {"type": "doc", "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "Synthetic source revision"}]}]}})
        knowledge = call("POST", "/api/v1/knowledge-items", {"knowledge_type": "FACTUAL_CLAIM",
            "body": KNOWLEDGE, "status": "accepted", "created_by": "synthetic fixture"}, expected=201)
        knowledge_grant = {"schema": "archeaxis.context-grant/v1", "purpose": PURPOSE,
            "consumer": "local-machine", "operations": ["answer"], "knowledge_id": knowledge["knowledge_id"],
            "provenance": [], "authorization_basis": "synthetic explicit grant", "expires_at": None, "state": "granted"}
        kg = call("POST", "/api/v1/documents", {"title": "Synthetic knowledge grant",
            "editor_json": {"type": "doc", "content": [], "attrs": {"archeaxis_context_grant": knowledge_grant}}}, expected=201)
        metadata = {"schema": "archeaxis.ai-asset/v1", "kind": "rule", "content": "Synthetic inert rule",
            "purpose": PURPOSE, "scope": [ref], "provenance": [], "expires_at": None, "state": "candidate",
            "members": [], "conflicts": [], "revises": None, "review": None, "source_payload": None}
        candidate = call("POST", "/api/v1/documents", {"title": "Synthetic asset",
            "editor_json": {"type": "doc", "content": [], "attrs": {"archeaxis_ai_asset": metadata}}}, expected=201)
        rubric = call("POST", "/api/v1/machine/rubrics", {"schema": "archeaxis.machine-rubric/v1",
            "request_id": "synthetic_observation_rubric", "title": "Synthetic rubric", "purpose": PURPOSE,
            "sources": [], "criteria": [{"criterion_id": "fit", "label": "fit",
                "expectation": "synthetic fixture"}]}, expected=201)
        editor = candidate["editor_json"]
        editor["attrs"]["archeaxis_ai_asset"]["state"] = "adopted"
        editor["attrs"]["archeaxis_ai_asset"]["review"] = {"asset": snapshot(candidate), "rubric": snapshot(rubric),
            "reviewer": "synthetic fixture", "basis": "synthetic review fixture", "outcome": "passed",
            "judgments": [{"criterion_id": "fit", "outcome": "passed", "basis": "synthetic fixture"}]}
        adopted = call("PUT", f"/api/v1/documents/{candidate['document_id']}/draft", {
            "expected_version": 1, "editor_json": editor})
        asset_grant = {"schema": "archeaxis.asset-context-grant/v1", "asset": snapshot(adopted),
            "purpose": PURPOSE, "consumer": "local-machine", "operations": ["answer"],
            "authorization_basis": "synthetic explicit grant", "expires_at": None, "state": "granted"}
        ag = call("POST", "/api/v1/documents", {"title": "Synthetic asset grant", "editor_json": {
            "type": "doc", "content": [], "attrs": {"archeaxis_asset_context_grant": asset_grant}}}, expected=201)
        asset_request = {"request_id": "synthetic_observed_asset", "asset": snapshot(adopted),
            "grant": snapshot(ag), "purpose": PURPOSE, "consumer": "local-machine", "operation": "answer",
            "reference_observation_mode": "document_versions_v1"}
        request_body = {"client_request_id": "synthetic_observed_answer", "knowledge_id": knowledge["knowledge_id"],
            "question": "According to the supplied synthetic context, what is the example colour?",
            "context_grant": {**snapshot(kg), "purpose": PURPOSE}, "asset_context_grant": asset_request}
        result = call("POST", "/api/v1/machine/answers", request_body, timeout=150)
        answer = result["answer"]
        if (answer.get("model") != MODEL or answer.get("requested_model") != MODEL
                or answer.get("observed_model") != MODEL or answer.get("endpoint") != BASE
                or answer.get("finish_reason") != "stop" or answer.get("truncated") is not False
                or not isinstance(answer.get("answer"), str) or not answer["answer"].strip()):
            raise RuntimeError("worker returned an incomplete or differently identified answer")

        packet = {"schema": "archeaxis.ai-context-packet/v1", "asset": snapshot(adopted),
            "consumer": "local-machine", "purpose": PURPOSE, "operation": "answer", "grant": snapshot(ag),
            "reference_only_sources": True, "private_session_access": False, "tool_execution": "NOT_EXECUTED",
            "machine_qualification": False, "human_mastery": False, "professional_truth": False,
            "reference_observation_mode": "document_versions_v1", "items": [{"snapshot": snapshot(adopted),
                "kind": "rule", "content": "Synthetic inert rule", "purpose": PURPOSE, "scope": [ref],
                "provenance": [], "reference_states": [{"reference": ref, "readable": True,
                    "currentness": "not_applicable", "version_relation": "historical", "current_version": 2}],
                "engine_execution": "NOT_EXECUTED", "grants_professional_truth": False,
                "grants_human_mastery": False, "grants_machine_qualification": False}]}
        packet_sha = digest(canonical(packet))
        context = ("CANONICAL_KNOWLEDGE:\n" + KNOWLEDGE +
            "\n\nAI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n" + canonical(packet))
        if result["request"]["asset_context"]["packet_sha256"] != packet_sha or result["request"]["context_sha256"] != digest(context):
            raise RuntimeError("bound asset packet or worker context digest did not match")
        receipt.update({"result": "MODEL_ANSWER_OBSERVED", "model": answer["model"],
            "requested_model": answer["requested_model"], "observed_model": answer["observed_model"],
            "finish_reason": answer.get("finish_reason"), "answer_sha256": digest(answer["answer"]),
            "packet_sha256": packet_sha, "context_sha256": digest(context),
            "document_relation": "historical", "document_current_version": 2})
        core.stop()
        core.with_machine = False
        core.start()
        status, _ = request(core, "GET", "/api/v1/capabilities/machine.answer")
        if status != 404:
            raise RuntimeError("machine worker remained registered after restart")
        replay = call("POST", "/api/v1/machine/answers", request_body, timeout=20)
        if replay != result:
            raise RuntimeError("restart did not return the original frozen answer")
        receipt["restart_without_machine_worker"] = "same_frozen_answer"
        receipt["result"] = "LOCAL_SAMPLE_OBSERVED"
    finally:
        core.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-exe", required=True)
    args = parser.parse_args()
    root = os.environ.get("ARCHEAXIS_RUN_ROOT")
    if not root:
        parser.error("use scripts/runtime/dev.py with a fresh run")
    receipt = {"schema": "aaos.ai-document-observation-local-sample/v1", "synthetic": True,
        "human_review": "SYNTHETIC_FIXTURE", "model_quality": "NOT_MEASURED",
        "installed_or_owner_acceptance": "NOT_ESTABLISHED", "result": "NOT_COMPLETED"}
    try:
        run(args, receipt)
        return 0
    except Exception as error:  # noqa: BLE001 - preserve a bounded failure without raw payloads
        receipt["failure_type"] = type(error).__name__
        print("Local synthetic sample did not complete; see bounded receipt.", file=sys.stderr)
        return 1
    finally:
        target = Path(root) / "artifacts/ai-document-observation-receipt.json"
        target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
