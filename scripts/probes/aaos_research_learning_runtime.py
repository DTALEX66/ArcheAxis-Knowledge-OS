"""Continue recorded public research into one candidate's format/learning workspace.

Run through runtime/dev.py. Public failures remain failures. Only authored local
samples receive a SIMULATED human review; public knowledge stays candidate.
No direct database access, model calls, native UI or Owner acceptance claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import aaos01_office_runtime_loop as office
import aaos_public_research_runtime_loop as helper

ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    parser.add_argument("--format-receipt", type=Path, required=True)
    parser.add_argument("--continue-partial-public", action="store_true")
    args = parser.parse_args()
    dev = office.load("research_learning_dev", ROOT / "scripts/runtime/dev.py")
    require(os.environ.get("ARCHEAXIS_RUN_ROOT"), "Use runtime/dev.py")
    run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
    paths = dev.layout(ROOT, run.name)
    require(run == paths["run"], "Foreign run")
    candidate = dev.safe_path(args.candidate)
    candidate.relative_to(paths["dev"] / "runs")

    def local_receipt(path):
        path = dev.safe_path(path)
        path.relative_to(paths["dev"] / "runs")
        return json.loads(path.read_text(encoding="utf-8")), office.identity(path)

    public, public_identity = local_receipt(args.public_receipt)
    formats, formats_identity = local_receipt(args.format_receipt)
    require(formats.get("ok") and formats.get("source_consistent"), "Unqualified format input")
    require(public.get("source_consistent") and public.get("candidate_consistent"), "Unqualified public input")
    require(dev.safe_path(Path(public["candidate"])) == candidate, "Different public candidate")
    require(office.identity(candidate / "core/archeaxis-api.exe") == formats["core"], "Different format Core")
    require(office.identity(candidate / "backend-runtime-manifest.json") == formats["manifest"], "Different runtime")
    require(all(row.get("wait_reaped") for row in public["stopped"]), "Public Core still live")
    search = next(step["body"] for step in public["steps"] if step["label"] == "public_search")
    complete = search["state"] == "complete"
    require(complete or args.continue_partial_public, "Partial public channels require explicit continuation")
    workspace = dev.safe_path(Path(public["workspace"]))
    workspace.relative_to(paths["dev"] / "runs")
    require(workspace.is_dir(), "Public workspace missing")
    output = paths["artifacts"] / "research-learning-runtime.json"
    require(not output.exists(), "Choose a new run ID")
    receipt = {
        "schema": "archeaxis.research-learning-runtime/v1", "status": "RUNNING",
        "evidence_level": "INTEGRATED_CORE_PUBLIC_AND_AUTHORED_MATERIAL",
        "candidate": str(candidate), "workspace": str(workspace), "steps": [], "stopped": [],
        "inputs": [public_identity, formats_identity], "public_channels_complete": complete,
        "public_channels": [{key: channel.get(key) for key in ("family", "status", "error_code")}
                            for channel in search["channels"]],
        "human_review": "SIMULATED_AUTHORED_FIXTURE_ONLY", "public_knowledge_acceptance": "NOT_EXECUTED",
        "limitations": ["Partial public channels do not pass J2", "No independent semantic comparison or truth validation",
                        "Authored formats, not source-application fidelity", "No native/install/model/Owner acceptance",
                        "Terminate/wait is not normal host exit", "Package dependency roundtrip is not claimed"],
    }
    launcher = office.load("research_learning_launcher", ROOT / "scripts/release/backend_launcher.py")
    client = office.load("research_learning_client", ROOT / "shared/core_client.py")
    child = None
    base = token = None
    identity_paths = ("ArcheAxis.exe", "core/archeaxis-api.exe", "backend-runtime-manifest.json", "worker-profile.json")
    before = [office.identity(candidate / name) for name in identity_paths]
    receipt["candidate_files"] = before

    def checkpoint():
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def call(label, method, path, body=None, expected=200, headers=None):
        status, value = client.call(base, method, path, token, body, timeout=45, extra_headers=headers)
        receipt["steps"].append({"label": label, "method": method, "path": path, "status": status})
        checkpoint()
        require(status == expected, f"{label}: expected {expected}, got {status}: {str(value)[:300]}")
        return value

    def stop():
        nonlocal child
        helper.stop_owned(child, launcher, receipt["stopped"])
        child = None
        checkpoint()

    def transform(label, source, kind):
        job = "journey-" + uuid.uuid4().hex
        call(label + "_job", "POST", "/api/v1/jobs", {"job_id": job, "kind": kind, "input_ref": source["source_id"]}, 202)
        call(label + "_execute", "POST", f"/api/v1/jobs/{job}/executions", {"deadline_ms": 30000},
             202, {"Idempotency-Key": job})
        deadline = time.monotonic() + 45
        while True:
            current = call(label + "_poll", "GET", f"/api/v1/jobs/{job}")
            if current["state"] in {"succeeded", "failed", "cancelled", "rejected"}:
                break
            require(time.monotonic() < deadline, "Worker timeout")
            time.sleep(0.25)
        require(current["state"] == "succeeded", label + " worker did not succeed")
        result = call(label + "_transform", "GET", f"/api/v1/sources/{source['source_id']}/jobs/{job}/transform")
        require(result["content"].strip(), "Empty content")
        return job, result

    def knowledge(label, source, job, transformed, kind, body):
        text = transformed["content"]
        created = call(label + "_candidate", "POST", "/api/v1/knowledge-items/from-transform", {
            "knowledge_type": kind, "body": body, "source_id": source["source_id"], "job_id": job,
            "transform_id": transformed["transform_id"], "selection_start_utf16": 0,
            "selection_end_utf16": len(text.encode("utf-16-le")) // 2, "quote": text}, 201)
        require(created["status"] == "candidate" and created["requires_human_review"], "Candidate guard missing")
        item = call(label + "_read", "GET", f"/api/v1/knowledge-items/{created['knowledge_id']}/v3")
        require(item["status"] == "candidate", "Unexpected public promotion")
        return item

    try:
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        scope = call("workspace", "GET", "/api/v1/workspace/ui-state")
        target = {key: search[key] for key in ("workspace_id", "restore_epoch", "request_id")}
        require(all(scope[key] == target[key] for key in ("workspace_id", "restore_epoch")), "Public workspace basis changed")
        require(call("public_receipt", "POST", "/api/v1/research/public/read", target) == search, "Public receipt changed")
        materials, originals, public_selection = [], {}, []
        for channel in search["channels"]:
            family = channel["family"]
            raw = channel.get("raw_source")
            if raw:
                originals[raw["source_id"]] = call(family + "_raw", "GET", f"/api/v1/sources/{raw['source_id']}/original")
                helper.checked_original(originals[raw["source_id"]], raw)
                materials.append({"id": family + "_raw", "note": "公开API原始响应；未接纳", "reference": raw})
            for hit in channel.get("hits", []):
                if channel["status"] != "complete" or not hit.get("excerpt", "").strip():
                    continue
                selected = call(family + "_select", "POST", "/api/v1/research/public/materialize",
                                {**target, "family": family, "hit_id": hit["id"]})
                ref = selected["reference"]
                original = call(family + "_original", "GET", f"/api/v1/sources/{ref['source_id']}/original")
                helper.checked_original(original, ref)
                originals[ref["source_id"]] = original
                materials.append({"id": family, "note": selected["note"], "reference": ref})
                public_selection.append(ref)
        require(public_selection, "No public content available for continuation")
        # Continue the same actual candidate with all four previously authored format samples.
        docx = None
        for item in formats["formats"]:
            file = dev.safe_path(Path(item["input"]["path"]))
            file.relative_to(paths["dev"] / "runs")
            require(office.identity(file) == item["input"], "Authored input changed")
            source = call(item["extension"] + "_import", "POST", "/api/v1/imports", client.import_request(file.name, file.read_bytes()), 202)
            require(source["sha256"] == item["original_sha"], "Format source changed")
            ref = {"kind": "source", "source_id": source["source_id"], "sha256": source["sha256"]}
            original = call(item["extension"] + "_original", "GET", f"/api/v1/sources/{source['source_id']}/original")
            require(helper.checked_original(original, ref) == file.read_bytes(), "Format custody mismatch")
            originals[source["source_id"]] = original
            materials.append({"id": "personal_" + item["extension"], "note": "项目自编合成资料", "reference": ref})
            job, transformed = transform(item["extension"], source, "pdf" if item["extension"] == "pdf" else "office")
            expected_text = item["first"]["snapshot"]["text"]["body"]["content"]
            require(transformed["content"] == expected_text, "Copied format content changed")
            if item["extension"] == "docx":
                docx = (source, job, transformed)
        require(docx is not None, "Missing authored DOCX")
        personal = knowledge("personal", *docx, "PERSONAL_DEFINITION", "合成个人定义：正文甲是本例正文，表格乙是本例表格。仅验证流程。")
        personal_path = f"/api/v1/knowledge-items/{personal['knowledge_id']}/v3"
        review = {"action": "accepted", "reviewer": "SIMULATED_AUTHORED_FIXTURE",
                  "note": "Synthetic engineering review only; not Owner acceptance or public truth approval.",
                  "expected_version": personal["version"]}
        call("fixture_accept", "POST", f"/api/v1/knowledge/{personal['knowledge_id']}/review/versioned", review)
        accepted = call("personal_accepted", "GET", personal_path)
        require(accepted["status"] == "accepted", "Fixture not accepted")
        call("stale_review", "POST", f"/api/v1/knowledge/{personal['knowledge_id']}/review/versioned", review, 409)
        public_source = public_selection[0]
        job, transformed = transform("public", public_source, "text")
        pending = knowledge("public", public_source, job, transformed, "OBSERVATION", "公开来源摘录候选；内容待人工核验，未接纳。")
        pending_path = f"/api/v1/knowledge-items/{pending['knowledge_id']}/v3"
        key = "journey_personal_" + uuid.uuid4().hex
        item_path = f"/api/v1/learning/items/{key}"
        call("learning_reference", "POST", item_path + "/references", {"knowledge_id": accepted["knowledge_id"]}, 201)
        assessment = call("learning_assessment", "POST", item_path + "/assessment", {"knowledge_id": accepted["knowledge_id"]}, 201)
        require(assessment["source_id"] == docx[0]["source_id"] and assessment["anchor_id"] == personal["anchor_id"], "Assessment lost original location")
        event = {"item_key": key, "client_event_id": "journey-" + uuid.uuid4().hex, "correct": True, "rating": 3,
                 "answer": "正文甲为正文，表格乙为表格；这是合成练习答案。", "assessment_id": assessment["assessment_id"],
                 "knowledge_version": assessment["knowledge_version"], "assist_strategy": "SIMULATED_AUTHORED_FIXTURE"}
        first = call("learning_review", "POST", "/api/v1/learning/reviews", event, 201)
        require(first["next_review"] and first["schedule_state"] and first["answer"] == event["answer"], "Actual scheduler or answer missing")
        replay = call("learning_retry", "POST", "/api/v1/learning/reviews", event)
        require(replay["duplicate"] and replay["event_id"] == first["event_id"], "Review retry duplicated event")
        call("learning_conflict", "POST", "/api/v1/learning/reviews", {**event, "answer": "different"}, 409)
        for identity, item in (("accepted", accepted), ("pending", pending)):
            materials.append({"id": identity, "note": "合成个人定义" if identity == "accepted" else "公开候选未接纳",
                              "reference": {"kind": "knowledge", "knowledge_id": item["knowledge_id"]}})
        refs = [item["reference"] for item in materials]
        research = {"schema": "archeaxis.research/v1", "question": search["query"], "materials": materials,
                    "hypotheses": [], "counterevidence": [], "methods": [], "experiments": [], "conclusions": [],
                    "unresolved": [{"id": "verification_pending",
                                    "text": ("三类公开检索已完成；公开结论尚待人工核验。" if complete else
                                             "部分公开检索未完成；公开结论尚待人工核验。"),
                                    "references": public_selection}]}
        editor = {"type": "doc", "attrs": {"archeaxis_research": research,
                  "archeaxis_relations": {"schema": "archeaxis.relations/v1", "relations": [
                      {"id": "fixed_" + str(i), "kind": "related", "label": "固定资料", "target": ref,
                       **({"presentation": "embed"} if ref["kind"] == "knowledge" else {})} for i, ref in enumerate(refs)]}},
                  "content": [{"type": "paragraph", "content": [{"type": "text", "text": "公开研究与合成个人资料贯穿；未形成已核实公开结论。"}]}]}
        document = call("unified_document", "POST", "/api/v1/documents", {"create_request_id": "journey-" + uuid.uuid4().hex,
                        "title": "研究与个人学习贯穿", "editor_json": editor}, 201)
        document_path = f"/api/v1/documents/{document['document_id']}"
        # Freeze readback after all writes: relation scan hashes include workspace versions.
        expected = {"document": (document_path, document), "accepted": (personal_path, accepted), "pending": (pending_path, pending)}
        for label, path in (("assessment", item_path + "/assessment"), ("learning", item_path + "/state"),
                            ("history", f"/api/v1/learning/events/{key}"), ("relations", document_path + "/relations"),
                            ("export", document_path + "/export?format=markdown")):
            expected[label] = (path, call("baseline_" + label, "GET", path))
        require(expected["learning"][1]["learner"]["event_count"] == 1, "Learning retry added an event")
        require(call("pending_unchanged", "GET", pending_path) == pending, "Public knowledge was promoted")
        for source_id, original in originals.items():
            expected["original_" + source_id] = (f"/api/v1/sources/{source_id}/original", original)
        receipt.update({"document_id": document["document_id"], "item_key": key,
                        "personal_knowledge_id": accepted["knowledge_id"], "pending_public_knowledge_id": pending["knowledge_id"],
                        "original_count": len(originals), "schedule_authority": first["schedule_authority"]})
        stop()
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        for label, (path, value) in expected.items():
            require(call("restart_" + label, "GET", path) == value, "Restart changed " + label)
        backup = call("backup", "POST", "/api/v1/workspace/backups", {}, 201)
        require(backup["verified"], "Backup not verified")
        preview = call("restore_preview", "POST", "/api/v2/workspace/restore/preview",
                       {"backup_id": backup["backup_id"], "expected_sha256": backup["sha256"]})
        require(preview["verified"] and preview["compatible"], "Restore preflight failed")
        backup_file = dev.safe_path(workspace / "backups" / backup["filename"])
        backup_file.relative_to(workspace)
        require(sha(backup_file.read_bytes()) == backup["sha256"], "Backup bytes mismatch")
        receipt["backup"] = backup
        stop()
        restored = paths["artifacts"] / "independent-restore"
        restored.mkdir(exist_ok=False)
        operation = subprocess.run([str(candidate / "core/archeaxis-api.exe"), "--maintenance-restore",
                                    str(restored / "workspace.sqlite"), str(backup_file)],
                                   capture_output=True, text=True, encoding="utf-8", timeout=90,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        receipt["maintenance_restore"] = {"exit_code": operation.returncode, "stdout": operation.stdout, "stderr": operation.stderr}
        require(operation.returncode == 0 and json.loads(operation.stdout).get("verified"), "Restore failed")
        child, base, token, _ = helper.hidden_start(office, candidate, restored, launcher)
        for label, (path, value) in expected.items():
            require(call("restore_" + label, "GET", path) == value, "Restore changed " + label)
        receipt.update({"status": "PASS_DECLARED_INTEGRATED_SUBSET", "independent_workspace": str(restored),
                        "restart_equal": True, "independent_restore_equal": True,
                        "whole_CL_J": "PARTIAL", "public_knowledge_status": pending["status"]})
    except Exception as error:
        receipt.update({"status": "FAIL", "error": f"{type(error).__name__}: {error}"})
    finally:
        if child is not None:
            try:
                stop()
            except Exception as error:
                receipt.update({"status": "FAIL", "cleanup_error": str(error)})
        receipt["candidate_files_unchanged"] = before == [office.identity(candidate / name) for name in identity_paths]
        if not receipt["candidate_files_unchanged"]:
            receipt["status"] = "FAIL"
        checkpoint()
        print(json.dumps({"status": receipt["status"], "requests": len(receipt["steps"]), "receipt": str(output)}, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS_DECLARED_INTEGRATED_SUBSET" else 1


if __name__ == "__main__":
    raise SystemExit(main())
