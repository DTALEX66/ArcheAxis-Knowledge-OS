"""Continue an integrated research/learning receipt through actual course consumers.

Uses the prior independently restored authored workspace. No new public query,
knowledge approval, model request or database access. All human actions remain
SIMULATED authored-fixture actions; course candidates are never auto-approved.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import uuid

import aaos01_office_runtime_loop as office
import aaos_public_research_runtime_loop as helper
from aaos_research_learning_runtime import require, sha

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--input-receipt", type=Path, required=True)
    args = parser.parse_args()
    dev = office.load("course_continuation_dev", ROOT / "scripts/runtime/dev.py")
    require(os.environ.get("ARCHEAXIS_RUN_ROOT"), "Use runtime/dev.py")
    run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
    paths = dev.layout(ROOT, run.name)
    require(run == paths["run"], "Foreign run")

    def owned(path):
        path = dev.safe_path(path)
        path.relative_to(paths["dev"] / "runs")
        return path

    source_receipt = owned(args.input_receipt)
    prior = json.loads(source_receipt.read_text(encoding="utf-8"))
    require(prior["status"] == "PASS_DECLARED_INTEGRATED_SUBSET"
            and prior["independent_restore_equal"] and prior["candidate_files_unchanged"], "Unqualified input")
    wrapper = json.loads((source_receipt.parent / "execution.json").read_text(encoding="utf-8"))
    require(wrapper["status"] == "LOCAL_PASS" and wrapper["source_consistent"], "Input source not qualified")
    candidate, previous = owned(args.candidate), owned(Path(prior["candidate"]))
    workspace = owned(Path(prior["independent_workspace"]))
    current_manifest = json.loads((candidate / "candidate-manifest.json").read_text(encoding="utf-8"))
    old_manifest = json.loads((previous / "candidate-manifest.json").read_text(encoding="utf-8"))
    require(current_manifest["files"].keys() == old_manifest["files"].keys(), "Different runtime member set")
    changed = [name for name, value in current_manifest["files"].items() if value != old_manifest["files"][name]]
    require(set(changed) <= {"ArcheAxis.exe"}, "Backend changed since prior integration")
    identity_names = ("ArcheAxis.exe", "core/archeaxis-api.exe", "backend-runtime-manifest.json", "worker-profile.json")
    before = [office.identity(candidate / name) for name in identity_names]
    for name, value in zip(identity_names, before):
        require(value["sha256"] == current_manifest["files"][name]["sha256"], "Candidate identity mismatch")
    launcher = office.load("course_continuation_launcher", ROOT / "scripts/release/backend_launcher.py")
    client = office.load("course_continuation_client", ROOT / "shared/core_client.py")
    output = paths["artifacts"] / "course-continuation-runtime.json"
    require(not output.exists(), "Choose a new run ID")
    receipt = {"schema": "archeaxis.course-continuation-runtime/v1", "status": "RUNNING",
               "evidence_level": "INTEGRATED_CORE_AUTHORED_FIXTURE",
               "candidate": str(candidate), "workspace": str(workspace), "steps": [], "stopped": [],
               "input": office.identity(source_receipt), "candidate_files": before,
               "backend_changed_members": changed, "human_review": "SIMULATED_AUTHORED_FIXTURE_ONLY",
               "public_knowledge_acceptance": "NOT_EXECUTED", "whole_CL_J": "PARTIAL",
               "limitations": ["No independent learning/content quality or Owner acceptance",
                               "No public query, model, native IPC or installation",
                               "Course candidate is derived content, not knowledge acceptance",
                               "Terminate/wait is not normal host exit"]}
    child = None
    base = token = None

    def checkpoint():
        output.write_bytes((json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode())

    def call(label, method, path, body=None, expected=200):
        status, value = client.call(base, method, path, token, body, timeout=45)
        receipt["steps"].append({"label": label, "method": method, "path": path, "status": status})
        checkpoint()
        require(status == expected, f"{label}: expected {expected}, got {status}: {str(value)[:250]}")
        return value

    def stop():
        nonlocal child
        helper.stop_owned(child, launcher, receipt["stopped"])
        child = None
        checkpoint()

    try:
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        knowledge_path = f"/api/v1/knowledge-items/{prior['personal_knowledge_id']}/v3"
        pending_path = f"/api/v1/knowledge-items/{prior['pending_public_knowledge_id']}/v3"
        accepted = call("accepted", "GET", knowledge_path)
        pending = call("pending", "GET", pending_path)
        require(accepted["status"] == "accepted" and pending["status"] == "candidate", "Knowledge boundary changed")
        call("pending_course_refused", "POST", "/api/v1/courses/from-knowledge",
             {"knowledge_id": pending["knowledge_id"]}, 409)
        created = call("course_create", "POST", "/api/v1/courses/from-knowledge",
                       {"knowledge_id": accepted["knowledge_id"]}, 201)
        require(created["human_review_required"], "Course review boundary missing")
        course, target = created["course"], created["suggested_learning_item"]
        manifest = course["manifest"]
        artifact = manifest["artifacts"][0]
        course_id, artifact_id = manifest["manifest_id"], artifact["artifact_id"]
        key = target["item_key"]
        require(key == f"course:{course_id}:artifact:{artifact_id}", "Core learning identity mismatch")
        require(course["status"] == manifest["status"] == "candidate" and not course["stale"], "Course not current candidate")
        require(target["knowledge_id"] == target["knowledge_version"] == accepted["knowledge_id"]
                and target["source_id"] == accepted["source_id"], "Course lost knowledge/source binding")
        require(len(course["bindings"]) == 1 and len(manifest["artifacts"]) == 1, "Unexpected course multiplicity")
        require(artifact["renderer"] == "native-lesson" and artifact["derived_only"]
                and artifact["human_review_required"], "Unexpected renderer/authority")
        require(manifest["knowledge_components"][0]["statement"] == accepted["body"], "Lesson changed knowledge content")
        require(call("course_retry", "POST", "/api/v1/courses/from-knowledge",
                     {"knowledge_id": accepted["knowledge_id"]}, 201) == created, "Course retry changed identity")
        course_path = f"/api/v1/courses/{course_id}"
        require(call("course_read", "GET", course_path) == course, "Course persistence differs")
        rendered = call("course_render", "POST", course_path + "/render", {"artifact_id": artifact_id})
        require(rendered["canonical_bindings_verified"] and rendered["derived_only"] and rendered["human_review_required"],
                "Unverified lesson render")
        require(rendered["course"] == course and rendered["render"]["manifest"] == manifest
                and rendered["render"]["artifact"] == artifact, "Renderer changed canonical course")
        call("unknown_artifact_refused", "POST", course_path + "/render", {"artifact_id": "missing_artifact"}, 404)
        item_path = f"/api/v1/learning/items/{key}"
        call("course_learning_reference", "POST", item_path + "/references", {"knowledge_id": target["knowledge_id"]}, 201)
        assessment = call("course_assessment", "POST", item_path + "/assessment", {"knowledge_id": target["knowledge_id"]}, 201)
        require(assessment["knowledge_id"] == assessment["knowledge_version"] == target["knowledge_id"]
                and assessment["source_id"] == accepted["source_id"] and assessment["anchor_id"] == accepted["anchor_id"],
                "Course assessment lost exact source/knowledge")
        event = {"item_key": key, "client_event_id": "course-fixture-" + uuid.uuid4().hex, "correct": True, "rating": 3,
                 "answer": "SIMULATED authored course exercise: 正文甲是正文，表格乙是表格。",
                 "assessment_id": assessment["assessment_id"], "knowledge_version": target["knowledge_id"],
                 "assist_strategy": "SIMULATED_AUTHORED_FIXTURE"}
        first = call("course_review", "POST", "/api/v1/learning/reviews", event, 201)
        require(first["schedule_authority"] == "fsrs" and first["next_review"] and first["schedule_state"], "Real FSRS schedule missing")
        repeated = call("course_review_retry", "POST", "/api/v1/learning/reviews", event)
        require(repeated["duplicate"] and repeated["event_id"] == first["event_id"], "Review duplicated")
        expected = {"course": (course_path, course), "accepted": (knowledge_path, accepted), "pending": (pending_path, pending)}
        for label, path in (("courses", "/api/v1/courses"), ("assessment", item_path + "/assessment"),
                            ("learning", item_path + "/state"), ("history", f"/api/v1/learning/events/{key}"),
                            ("previous_learning", f"/api/v1/learning/items/{prior['item_key']}/state"),
                            ("research", f"/api/v1/documents/{prior['document_id']}"),
                            ("research_export", f"/api/v1/documents/{prior['document_id']}/export?format=markdown")):
            expected[label] = (path, call("baseline_" + label, "GET", path))
        require(expected["learning"][1]["learner"]["event_count"] == 1, "Duplicate course review event")
        require(any(row["manifest_id"] == course_id for row in expected["courses"][1]["items"]), "Course absent from normal catalog")
        # The existing research document enumerates exactly the original sources.
        materials = expected["research"][1]["editor_json"]["attrs"]["archeaxis_research"]["materials"]
        source_refs = {m["reference"]["source_id"]: m["reference"] for m in materials if m["reference"]["kind"] == "source"}
        require(len(source_refs) == prior["original_count"], "Lost prior material references")
        for source_id, reference in source_refs.items():
            path = f"/api/v1/sources/{source_id}/original"
            value = call("baseline_original", "GET", path)
            helper.checked_original(value, reference)
            expected["original_" + source_id] = (path, value)
        receipt.update({"course_id": course_id, "artifact_id": artifact_id, "item_key": key,
                        "knowledge_id": accepted["knowledge_id"], "pending_knowledge_id": pending["knowledge_id"],
                        "assessment_id": assessment["assessment_id"], "document_id": prior["document_id"],
                        "course_title": manifest["title"], "original_count": len(source_refs)})
        stop()
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        for label, (path, value) in expected.items():
            require(call("restart_" + label, "GET", path) == value, "Restart changed " + label)
        require(call("restart_render", "POST", course_path + "/render", {"artifact_id": artifact_id}) == rendered, "Restart render changed")
        backup = call("backup", "POST", "/api/v1/workspace/backups", {}, 201)
        require(backup["verified"], "Unverified backup")
        preview = call("restore_preview", "POST", "/api/v2/workspace/restore/preview",
                       {"backup_id": backup["backup_id"], "expected_sha256": backup["sha256"]})
        require(preview["verified"] and preview["compatible"], "Restore preflight failed")
        backup_file = dev.safe_path(workspace / "backups" / backup["filename"])
        backup_file.relative_to(workspace)
        require(sha(backup_file.read_bytes()) == backup["sha256"], "Backup bytes changed")
        receipt["backup"] = backup
        stop()
        restored = paths["artifacts"] / "independent-course-restore"
        restored.mkdir(exist_ok=False)
        operation = subprocess.run([str(candidate / "core/archeaxis-api.exe"), "--maintenance-restore",
                                    str(restored / "workspace.sqlite"), str(backup_file)],
                                   capture_output=True, text=True, encoding="utf-8", timeout=90,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        receipt["maintenance_restore"] = {"exit_code": operation.returncode, "stdout": operation.stdout, "stderr": operation.stderr}
        require(operation.returncode == 0 and json.loads(operation.stdout).get("verified"), "Independent restore failed")
        child, base, token, _ = helper.hidden_start(office, candidate, restored, launcher)
        for label, (path, value) in expected.items():
            require(call("restore_" + label, "GET", path) == value, "Restore changed " + label)
        require(call("restore_render", "POST", course_path + "/render", {"artifact_id": artifact_id}) == rendered, "Restored render differs")
        receipt.update({"status": "PASS_DECLARED_INTEGRATED_SUBSET", "restart_equal": True,
                        "independent_restore_equal": True, "independent_workspace": str(restored), "course_status": "candidate"})
    except Exception as error:
        receipt.update({"status": "FAIL", "error": f"{type(error).__name__}: {error}"})
    finally:
        if child is not None:
            try:
                stop()
            except Exception as error:
                receipt.update({"status": "FAIL", "cleanup_error": str(error)})
        receipt["candidate_files_unchanged"] = before == [office.identity(candidate / name) for name in identity_names]
        if not receipt["candidate_files_unchanged"]:
            receipt["status"] = "FAIL"
        checkpoint()
        print(json.dumps({"status": receipt["status"], "requests": len(receipt["steps"]), "receipt": str(output)}, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS_DECLARED_INTEGRATED_SUBSET" else 1


if __name__ == "__main__":
    raise SystemExit(main())
