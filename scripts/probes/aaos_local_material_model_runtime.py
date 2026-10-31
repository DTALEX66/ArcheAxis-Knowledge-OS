"""Current-candidate local material answers over already recorded public sources.

Run through runtime/dev.py. Restores an isolated copy through the Core's existing
maintenance command, never SQLite directly. Two real local requests cover a
public abstract and an authored scope supplement; neither promotes knowledge.
No cloud egress, fabricated model error, agent configuration or native UI claim.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

import aaos01_office_runtime_loop as office
import aaos_public_research_runtime_loop as helper
from aaos_research_learning_runtime import require, sha

ROOT = Path(__file__).resolve().parents[2]
ENDPOINT = "http://127.0.0.1:1234/v1"
MODEL = "aaos-fast-4b"
SUPPLEMENT = "作者补充的范围约束：这段摘要不能单独证明对所有学科或某位个人同样有效；不得编造个人成绩、学习经历或已完成的独立核验。"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-receipt", type=Path, required=True)
    parser.add_argument("--model-load-receipt", type=Path, required=True)
    parser.add_argument("--resume-receipt", type=Path)
    args = parser.parse_args()
    dev = office.load("local_material_dev", ROOT / "scripts/runtime/dev.py")
    run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
    paths = dev.layout(ROOT, run.name)
    require(paths["run"] == run, "Foreign run")

    def owned(path):
        path = dev.safe_path(path)
        path.relative_to(paths["dev"] / "runs")
        return path

    input_path, load_path = owned(args.input_receipt), owned(args.model_load_receipt)
    prior = json.loads(input_path.read_text(encoding="utf-8"))
    loaded = json.loads(load_path.read_text(encoding="utf-8"))
    require(prior["status"] == "PASS_DECLARED_INTEGRATED_SUBSET"
            and prior["public_channels_complete"] and prior["independent_restore_equal"]
            and prior["candidate_files_unchanged"], "Unqualified integration input")
    require(loaded["status"] == "PASS_LOAD_READBACK" and loaded["identifier"] == MODEL
            and loaded["model_key"] == "qwen3.5-4b", "Unqualified FAST instance")
    candidate = owned(Path(prior["candidate"]))
    names = ("ArcheAxis.exe", "core/archeaxis-api.exe", "backend-runtime-manifest.json", "worker-profile.json")
    before = [office.identity(candidate / name) for name in names]
    require(before == prior["candidate_files"], "Candidate changed since input")
    backup = prior["backup"]
    previous_work = owned(Path(prior["workspace"]))
    backup_file = owned(previous_work / "backups" / backup["filename"])
    require(sha(backup_file.read_bytes()) == backup["sha256"], "Backup hash mismatch")
    resumed = None
    if args.resume_receipt:
        resume_path = owned(args.resume_receipt)
        resumed = json.loads(resume_path.read_text(encoding="utf-8"))
        require(resumed["status"] == "FAIL" and "scope_supplement: HTTP 405" in resumed.get("error", "")
                and resumed["candidate_files"] == before and resumed["candidate_files_unchanged"]
                and len(resumed["model_calls"]) == 1
                and resumed["model_calls"][0]["result"]["outcome"] == "succeeded",
                "Only the recorded draft-route failure may resume without another first inference")
        workspace = owned(Path(resumed["workspace"]))
    else:
        workspace = paths["artifacts"] / "model-workspace"
        workspace.mkdir(exist_ok=False)
    output = paths["artifacts"] / "local-material-model-runtime.json"
    receipt = {"schema": "archeaxis.local-material-model-runtime/v1", "status": "RUNNING",
               "candidate": str(candidate), "workspace": str(workspace), "inputs": [office.identity(input_path), office.identity(load_path)],
               "candidate_files": before, "steps": [], "stopped": [], "model_calls": [],
               "evidence_level": "REAL_LOCAL_CORE_WORKER_MODEL_PUBLIC_MATERIAL",
               "cloud": "NOT_EXECUTED", "knowledge_acceptance": "NOT_EXECUTED", "whole_CL_J": "PARTIAL",
               "limitations": ["No independent quality, Owner, native or installed acceptance",
                              "Supplement is authored scope clarification, not a fabricated discovered error",
                              "Model output is candidate; cancellation and cloud are not exercised here",
                              "Terminate/wait is not normal host exit"]}
    if resumed:
        receipt["resume_input"] = office.identity(resume_path)
        receipt["model_calls"] = copy.deepcopy(resumed["model_calls"])
    launcher = office.load("local_material_launcher", ROOT / "scripts/release/backend_launcher.py")
    client = office.load("local_material_client", ROOT / "shared/core_client.py")
    child = None
    base = token = None

    def checkpoint():
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    def call(label, method, path, body=None, expected=200, timeout=30):
        status, value = client.call(base, method, path, token, body, timeout=timeout)
        receipt["steps"].append({"label": label, "method": method, "path": path, "status": status})
        checkpoint()
        require(status == expected, f"{label}: HTTP {status}, expected {expected}: {str(value)[:180]}")
        return value

    def stop():
        nonlocal child
        helper.stop_owned(child, launcher, receipt["stopped"])
        child = None
        checkpoint()

    def material_answer(label, document, question, resolved):
        request = {"request_id": label + "_" + uuid.uuid4().hex,
                   "material": {"kind": "document", "document_id": document["document_id"], "version": document["version"],
                                "content_sha256": document["content_sha256"], "block_id": None},
                   "selection": None, "question": question, "purpose": "public-abstract-study",
                   "model": MODEL, "model_configuration": resolved, "max_tokens": 2048, "timeout_s": 120,
                   "preview": True, "confirmed_plan_sha256": None, "execution_mode": "async"}
        preview = call(label + "_preview", "POST", "/api/v1/material/questions", request)
        require(preview["plan"]["destination_candidates"] == [ENDPOINT]
                and preview["plan"]["request"]["model_configuration"] == resolved,
                "Preview changed destination or purpose binding")
        request.update(preview=False, confirmed_plan_sha256=preview["plan_sha256"])
        started = time.monotonic()
        admission = call(label + "_submit", "POST", "/api/v1/material/questions/submissions", request, 202)
        require(admission["request_id"] == request["request_id"] and not admission["answer_published"], "Admission is not a result")
        deadline = time.monotonic() + 135
        delay = 0.5
        while True:
            status = call(label + "_status", "POST", "/api/v1/material/questions/status", {"request_id": request["request_id"]})
            if status.get("schema") == "archeaxis.material-answer/v1":
                break
            require(time.monotonic() < deadline, "Owned request has not become terminal; retain identity")
            time.sleep(delay)
            delay = min(4, delay * 2)
        record = {"request": request, "preview": preview, "admission": admission, "result": status,
                  "elapsed_s": round(time.monotonic() - started, 4)}
        receipt["model_calls"].append(record)
        checkpoint()
        require(status["outcome"] == "succeeded", f"{label}: {status.get('reason_code')}")
        answer = status["answer"]
        require(answer["answer"].strip() and answer["model"] == MODEL and answer["endpoint"] == ENDPOINT,
                "Final answer or local model identity missing")
        require(answer["answer_source"] == "content" and answer["finish_reason"] == "stop"
                and not answer["truncated"], "No finished final answer")
        require(status["authority"] == "candidate" and not status["grants_knowledge_acceptance"]
                and status["answer_sha256"] == sha(answer["answer"].encode()), "Candidate or answer hash changed")
        require(call(label + "_terminal_read", "POST", "/api/v1/material/questions/status",
                     {"request_id": request["request_id"]}) == status, "Terminal read differs")
        return record

    try:
        if not resumed:
            operation = subprocess.run([str(candidate / "core/archeaxis-api.exe"), "--maintenance-restore",
                                        str(workspace / "workspace.sqlite"), str(backup_file)],
                                       capture_output=True, text=True, encoding="utf-8", timeout=90,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            receipt["input_restore"] = {"exit_code": operation.returncode, "stdout": operation.stdout, "stderr": operation.stderr}
            require(operation.returncode == 0 and json.loads(operation.stdout)["verified"], "Input restore failed")
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
                "http://127.0.0.1:1234/api/v1/models", timeout=5) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
            require(len(raw) <= 2 * 1024 * 1024, "Inventory limit")
            catalog = json.loads(raw)
        matches = [instance for model in catalog["models"] if model["key"] == "qwen3.5-4b"
                   for instance in model["loaded_instances"] if instance["id"] == MODEL]
        require(len(matches) == 1, "Explicit FAST instance no longer loaded; do not JIT another model")
        receipt["loaded_instance_at_start"] = MODEL
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        configuration = call("configuration", "GET", "/api/v1/model-configuration")
        if resumed:
            require(configuration["revision"] == 1, "Resumed configuration changed")
            saved_config = configuration
        else:
            require(configuration["revision"] == 0 and not configuration["profiles"] and not configuration["bindings"],
                    "Do not replace pre-existing product profiles")
            next_config = copy.deepcopy(configuration)
            next_config["profiles"] = {"local_fast": {"endpoint": ENDPOINT, "protocol": "openai", "model": MODEL,
                                                      "credential_ref": None, "max_tokens": 2048, "timeout_s": 120}}
            next_config["bindings"] = [{"purpose": "material", "lane": "fast", "profile_id": "local_fast"}]
            saved_config = call("configuration_save", "PUT", "/api/v1/model-configuration",
                                {"expected_revision": 0, "configuration": next_config})
        resolved = call("material_fast_resolve", "POST", "/api/v1/model-configuration/resolve", {"purpose": "material", "lane": "fast"})
        require(saved_config["revision"] == resolved["configuration_revision"] == 1, "Configuration not frozen")
        main = call("research_baseline", "GET", f"/api/v1/documents/{prior['document_id']}")
        materials = main["editor_json"]["attrs"]["archeaxis_research"]["materials"]
        source = next(m["reference"] for m in materials if m["id"] == "research")
        original = call("public_original", "GET", f"/api/v1/sources/{source['source_id']}/original")
        raw = helper.checked_original(original, source)
        text = raw.decode("utf-8")
        require("A Trainable Spaced Repetition Model for Language Learning" in text and len(raw) <= 4096,
                "Unexpected public abstract or material budget")
        editor = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}
        if resumed:
            first = receipt["model_calls"][0]
            material = first["request"]["material"]
            document = call("resumed_document", "GET", f"/api/v1/documents/{material['document_id']}")
            require(document["version"] == material["version"] == 1
                    and document["content_sha256"] == material["content_sha256"]
                    and document["text_projection"] == text and first["request"]["model_configuration"] == resolved,
                    "Resumed material or configuration changed")
            require(call("resumed_terminal", "POST", "/api/v1/material/questions/status",
                         {"request_id": first["request"]["request_id"]}) == first["result"], "First answer changed")
        else:
            document = call("public_document", "POST", "/api/v1/documents",
                            {"create_request_id": "local-model-" + uuid.uuid4().hex, "title": "公开科研摘要 · 本地模型研读",
                             "source_id": source["source_id"], "source_revision": source["sha256"], "editor_json": editor}, 201)
            first = material_answer("public_first", document,
                                    "只根据材料，用中文两句话说明这项研究的模型名称、使用情境和衡量目标；不要添加材料之外的结论。", resolved)
        supplement = copy.deepcopy(document["editor_json"])
        supplement["content"].append({"type": "paragraph", "content": [{"type": "text", "text": SUPPLEMENT}]})
        updated = call("scope_supplement", "PUT", f"/api/v1/documents/{document['document_id']}/draft",
                       {"expected_version": document["version"], "editor_json": supplement})
        second = material_answer("public_supplement", updated,
                                 "只依据当前材料，简述研究使用的模型与情境，再说明为什么不能据此断言所有学科或某位个人同样有效。用中文三句话。", resolved)
        receipt["document_id"] = document["document_id"]
        receipt["configuration"] = saved_config
        receipt["resolved"] = resolved
        receipt["public_source"] = source
        receipt["answer_observations"] = [{"request_id": r["request"]["request_id"], "final_answer": r["result"]["answer"]["answer"],
                                            "usage": r["result"]["answer"].get("usage"), "quality": "NOT_INDEPENDENTLY_ACCEPTED"} for r in (first, second)]
        export = call("export", "GET", f"/api/v1/documents/{document['document_id']}/export?format=markdown")
        require(json.loads(next(f["content"] for f in export["files"] if f["path"] == "manifest.json"))["document"] == updated,
                "Export lost supplemented document")
        expected = [("configuration", "/api/v1/model-configuration", saved_config),
                    ("research", f"/api/v1/documents/{prior['document_id']}", main),
                    ("document", f"/api/v1/documents/{document['document_id']}", updated),
                    ("document_v1", f"/api/v1/documents/{document['document_id']}/versions/1", document),
                    ("public_original", f"/api/v1/sources/{source['source_id']}/original", original)]
        for label, path in (("pending", f"/api/v1/knowledge-items/{prior['pending_public_knowledge_id']}/v3"),
                            ("learning", f"/api/v1/learning/items/{prior['item_key']}/state")):
            value = call(label + "_baseline", "GET", path)
            if label == "pending":
                require(value["status"] == "candidate", "Public knowledge was promoted")
            expected.append((label, path, value))
        stop()
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        for label, path, value in expected:
            require(call("restart_" + label, "GET", path) == value, "Restart changed " + label)
        for record in (first, second):
            require(call("restart_answer", "POST", "/api/v1/material/questions/status",
                         {"request_id": record["request"]["request_id"]}) == record["result"], "Restart lost final answer")
        receipt["restart_equal"] = True
        receipt["status"] = "PASS_DECLARED_LOCAL_MODEL_SUBSET"
    except Exception as error:
        receipt.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    finally:
        if child is not None:
            try:
                stop()
            except Exception as error:
                receipt.update(status="FAIL", cleanup_error=str(error))
        receipt["candidate_files_unchanged"] = before == [office.identity(candidate / name) for name in names]
        if not receipt["candidate_files_unchanged"]:
            receipt["status"] = "FAIL"
        checkpoint()
        print(json.dumps({"status": receipt["status"], "model_calls": len(receipt["model_calls"]),
                          "requests": len(receipt["steps"]), "receipt": str(output)}, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS_DECLARED_LOCAL_MODEL_SUBSET" else 1


if __name__ == "__main__":
    raise SystemExit(main())
