"""J2 Core probe using an explicit public query and an isolated candidate workspace.

Run through scripts/runtime/dev.py. Canonical workspace writes use Core routes
or the explicit maintenance-restore operation; exported projections are saved in
the isolated probe folder. Knowledge admission uses a scripted human-principal
fixture, not an actual person's judgment. No provider settings are changed and
this is not installed-desktop qualification. Network execution requires
--public-network; --help and importing this module never launch Core.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FAMILIES = ("encyclopedia", "community", "research")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_channels(receipt, expected=FAMILIES):
    require(receipt.get("state") in {"complete", "partial"}, "public search failed")
    channels = receipt.get("channels", [])
    require({c.get("family") for c in channels} <= set(expected), "unexpected channel family")
    primary = {"encyclopedia": "wikipedia", "community": "stackexchange", "research": "openalex"}
    fallbacks = {"dbpedia": "encyclopedia", "crossref": "research"}
    selected = []
    for family in expected:
        candidates = [c for c in channels if c.get("family") == family]
        complete = [c for c in candidates if c.get("status") == "complete"]
        require(complete, f"{family} has no complete channel")
        require(any(c.get("provider") == primary[family] for c in candidates),
                f"{family} lost its primary channel")
        for channel in candidates:
            provider = channel.get("provider")
            if provider in fallbacks and fallbacks[provider] == family:
                require(channel.get("status") in {"complete", "limited", "failed", "offline"},
                        f"{provider} fallback has an invalid status")
        # Use the primary channel when it is complete; an incomplete primary keeps its
        # failed record and the complete fallback speaks for the family.
        channel = next((c for c in candidates if c.get("provider") == primary[family]
                        and c.get("status") == "complete"), complete[-1])
        require(len(channel.get("hits", [])) == 1, "each selected channel must return one real hit")
        require(channel.get("raw_source"), "raw response source missing")
        hit = channel["hits"][0]
        require(hit.get("family") == channel["family"], "hit family mismatch")
        require(bool(hit.get("excerpt", "").strip()), "selected hit has no quotable content")
        selected.append(channel)
    return selected


def checked_original(original, reference):
    require(reference.get("kind") == "source", "expected fixed source reference")
    source_id, digest = reference["source_id"], reference["sha256"]
    require(re.fullmatch(r"[A-Za-z0-9_-]+", source_id), "unsafe source identifier")
    require(re.fullmatch(r"[a-f0-9]{64}", digest), "invalid source fingerprint")
    raw = base64.b64decode(original["content_base64"], validate=True)
    require(original.get("source_id") == source_id, "original source identity mismatch")
    require(original.get("sha256") == digest == sha(raw), "original source bytes mismatch")
    return raw


def admission_material(materials):
    """Choose a selected derived source without assuming all families ran."""
    derived = [item for item in materials if item.get("id") in FAMILIES]
    require(derived, "no selected family is available for the admission fixture")
    selected = next((item for item in derived if item["id"] == "research"), derived[0])
    reference = selected.get("reference", {})
    require(reference.get("kind") == "source" and reference.get("source_id"),
            "admission fixture has no source identity")
    return selected["id"], reference["source_id"]


def verify_backup_objects(backup_file, object_dir, object_hashes, expected_sha256, filesystem_path):
    """Verify saved bytes using the launcher's Windows long-path I/O rules."""
    require(sha(filesystem_path(backup_file).read_bytes()) == expected_sha256, "backup bytes changed")
    for digest in object_hashes:
        require(re.fullmatch(r"[a-f0-9]{64}", digest), "unsafe backup object identity")
        require(sha(filesystem_path(object_dir / digest).read_bytes()) == digest,
                "backup source bytes changed")


def hidden_start(office, candidate, work, launcher):
    """Reuse the canonical launch handshake with Windows window suppression."""
    original = office.subprocess

    class Hidden:
        PIPE = original.PIPE

        @staticmethod
        def Popen(*args, **kwargs):  # noqa: N802 - mirrors subprocess.Popen for the launcher
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | getattr(
                original, "CREATE_NO_WINDOW", 0
            )
            return original.Popen(*args, **kwargs)

    office.subprocess = Hidden
    try:
        return office.start(candidate, work, launcher)
    finally:
        office.subprocess = original


def source_core_start(core_exe, work, launcher):
    """Launch an explicit Core with repository workers and no staged runtime."""
    staging = work / "worker-staging"
    launcher.filesystem_path(staging).mkdir(exist_ok=True)
    python = Path(sys.executable).resolve(strict=True)
    worker = {
        "python": str(python),
        "script": str((REPO / "services/python-workers/transport/text_ndjson.py").resolve(strict=True)),
        "staging": str(staging.absolute()),
        "routes": [{"capability": "research.public",
                    "script": str((REPO / "services/python-workers/machine/worker_machine_answer.py").resolve(strict=True))}],
    }
    token = secrets.token_hex(32)
    machine_token = secrets.token_hex(32)
    while machine_token == token:
        machine_token = secrets.token_hex(32)
    launch = {"launch_token": token, "machine_token": machine_token,
              "session_id": secrets.token_hex(16), "actor": "human",
              "protocol": launcher.LAUNCH_PROTOCOL, "text_worker": worker}
    environment = launcher.build_environment(REPO)
    environment["ARCHEAXIS_PYTHON"] = str(python)
    environment["ARCHEAXIS_SCHEDULER_WORKER"] = str(REPO / "services/python-workers/learning/worker_schedule.py")
    child = subprocess.Popen([str(core_exe), str(work / "workspace.sqlite"), "0"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding="utf-8", cwd=REPO, env=environment,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        child.stdin.write(json.dumps(launch) + "\n")
        child.stdin.close()
        base = launcher.wait_for_readiness(child, 0, 30)
        return child, base, token, worker
    except BaseException:
        launcher.stop(child)
        raise


def stop_owned(child, launcher, records):
    """Observe the existing terminate/wait/optional-kill path, not graceful exit."""
    record = {"pid": child.pid, "method": "backend_launcher.stop",
              "actions": [], "returncode": None, "wait_reaped": False,
              "graceful_exit_verified": False}
    records.append(record)

    class ObservedChild:
        def __getattr__(self, name):
            return getattr(child, name)

        def terminate(self):
            record["actions"].append("terminate")
            return child.terminate()

        def kill(self):
            record["actions"].append("kill")
            return child.kill()

        def wait(self, timeout=None):
            record["actions"].append({"wait_timeout_seconds": timeout})
            code = child.wait(timeout=timeout)
            record.update({"returncode": code, "wait_reaped": True})
            return code

    observed = ObservedChild()
    try:
        launcher.stop(observed)
        # The launcher skips wait when poll already observes an exited child.
        # Confirm reap explicitly without changing its termination behavior.
        if not record["wait_reaped"]:
            observed.wait(timeout=0)
        record["returncode"] = child.returncode
        require(record["returncode"] is not None, "owned Core termination is unconfirmed")
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
        record["returncode"] = child.returncode
        raise
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    runtime = parser.add_mutually_exclusive_group(required=True)
    runtime.add_argument("--candidate", type=Path, help="Existing staged candidate under project development root")
    runtime.add_argument("--core-exe", type=Path, help="Explicit Core executable with repository workers; not a staged candidate")
    parser.add_argument("--public-query", required=True, help="Public text sent to all three providers")
    parser.add_argument("--public-network", action="store_true", help="Explicitly enable public requests")
    parser.add_argument("--backup", action="store_true", help="Also require Core backup creation")
    parser.add_argument("--restore", action="store_true", help="Restore the verified backup to a separate workspace")
    parser.add_argument("--families", nargs="+", choices=FAMILIES, default=list(FAMILIES),
                        help="Measured families; a subset records the rest as not measured, never as passed")
    args = parser.parse_args()
    if not args.public_network:
        parser.error("execution requires --public-network; no request has been sent")
    if args.restore and not args.backup:
        parser.error("--restore requires --backup")
    if not args.public_query.strip() or len(args.public_query.encode("utf-8")) > 512:
        parser.error("public-query must contain 1-512 UTF-8 bytes")
    families = sorted(set(args.families))
    spec = importlib.util.spec_from_file_location(
        "public_loop_office", REPO / "scripts/probes/aaos01_office_runtime_loop.py"
    )
    office = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(office)
    dev = office.load("public_loop_dev", REPO / "scripts/runtime/dev.py")
    inherited_run = os.environ.get("ARCHEAXIS_RUN_ROOT")
    require(inherited_run, "run this probe through scripts/runtime/dev.py")
    run = dev.safe_path(Path(inherited_run))
    paths = dev.layout(REPO, run.name)
    require(run == paths["run"], "run ownership does not match this checkout")
    candidate = dev.safe_path(args.candidate) if args.candidate else None
    core_exe = dev.safe_path(args.core_exe) if args.core_exe else None
    if candidate is not None:
        candidate.relative_to(paths["dev"])
        core_exe = candidate / "core/archeaxis-api.exe"
    else:
        require(core_exe.is_file(), "explicit Core executable is missing")
    work = dev.safe_path(paths["artifacts"] / "public-research-workspace")
    work.mkdir(exist_ok=False)
    output = paths["artifacts"] / "public-research-receipt.json"
    require(not output.exists(), "receipt already exists; choose a new run ID")
    receipt = {
        "ok": False, "status": "RUNNING", "evidence_level": "NOT_EXECUTED",
        "candidate": str(candidate) if candidate else None,
        "runtime_kind": "STAGED_CANDIDATE" if candidate else "EXPLICIT_CORE_EXE",
        "core_exe": str(core_exe), "workspace": str(work), "query": args.public_query,
        "steps": [], "knowledge_admission": "NOT_EXECUTED",
        "limitations": [
            "Core integration only; no installed Tauri/UI acceptance",
            "Draft support/opposition labels are questions, not verified semantic conclusions",
            "Text anchors address selected derived snapshots, not upstream HTTP byte offsets",
            "Package checks fixed source bytes only; other document/knowledge dependencies are not rebuilt",
            "Knowledge admission is a scripted fixture, not actual human review or truth verification",
            *([] if args.restore else ["Workspace restore and restore-epoch recovery are NOT_EXECUTED"]),
            "Restart uses process terminate/wait with optional kill; normal host graceful exit awaits native verification",
        ],
        "backup": "NOT_EXECUTED", "restore": "NOT_EXECUTED",
    }
    launcher = office.load("public_loop_launcher", REPO / "scripts/release/backend_launcher.py")
    client = office.load("public_loop_client", REPO / "shared/core_client.py")
    child = None
    source_before = None
    candidate_before = None
    base = token = None

    def checkpoint():
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def stop():
        nonlocal child
        try:
            stop_owned(child, launcher, receipt.setdefault("stopped", []))
            child = None
        finally:
            checkpoint()

    def call(label, method, path, body=None, expected=200, timeout=30, headers=None):
        step = {"label": label, "method": method, "path": path, "state": "STARTED"}
        receipt["steps"].append(step)
        checkpoint()
        status, response = client.call(base, method, path, token, body, timeout=timeout,
                                       extra_headers=headers)
        step.update({"status": status, "body": response, "state": "RETURNED"})
        checkpoint()
        allowed = expected if isinstance(expected, (tuple, list)) else (expected,)
        require(status in allowed, f"{label}: expected HTTP {allowed}, received {status}")
        return response

    def source_identity():
        dirty, patch = dev.worktree_identity(REPO)
        return {"commit": dev.git(REPO, "rev-parse", "HEAD"), "dirty": dirty,
                "patch_sha256": patch, "changes": office.source_changes(dev)}

    def candidate_identity():
        if candidate:
            profile = launcher.load_profile(candidate)
            files = {candidate / "backend-runtime-manifest.json", candidate / "worker-profile.json",
                     core_exe, profile["python"], profile["script"]}
            files.update(route["script"] for route in profile["routes"])
            files.update((candidate / "workers").rglob("*.py"))
        else:
            files = {core_exe, Path(sys.executable).resolve(strict=True),
                     REPO / "services/python-workers/transport/text_ndjson.py",
                     REPO / "services/python-workers/machine/worker_machine_answer.py",
                     REPO / "services/python-workers/machine/public_research.py",
                     REPO / "services/python-workers/machine/public_research_proxy.py",
                     REPO / "shared/safe_http.py"}
        return [office.identity(dev.safe_path(path)) for path in sorted(files)]

    def start_runtime(target_work):
        if candidate:
            return hidden_start(office, candidate, target_work, launcher)
        return source_core_start(core_exe, target_work, launcher)

    def original(reference, label):
        source_id = reference["source_id"]
        require(re.fullmatch(r"[A-Za-z0-9_-]+", source_id), "unsafe source identifier")
        body = call(label, "GET", f"/api/v1/sources/{source_id}/original")
        return body, checked_original(body, reference)

    try:
        source_before = source_identity()
        candidate_before = candidate_identity()
        receipt.update({"source": source_before, "candidate_files": candidate_before,
                        "families": families,
                        "probe": office.identity(Path(__file__)),
                        "lockfile": office.identity(REPO / "uv.lock")})
        if len(families) != len(FAMILIES):
            receipt["limitations"].append(
                "Only the requested families were measured; the remaining public channels are NOT_EXECUTED "
                "in this run and are not reported as passed")
        child, base, token, worker = start_runtime(work)
        receipt.update({"pid": child.pid, "launch_worker": worker})
        call("version", "GET", "/api/v1/system/version")
        state = call("workspace", "GET", "/api/v1/workspace/ui-state")
        scope = {key: state[key] for key in ("workspace_id", "restore_epoch")}
        request_id = "public-loop-" + uuid.uuid4().hex
        target = {**scope, "request_id": request_id}
        search = call("public_search", "POST", "/api/v1/research/public/search",
                      {**target, "query": args.public_query, "families": families, "limit": 1},
                      timeout=180)
        receipt["evidence_level"] = "REAL_CORE_PUBLIC_NETWORK"
        require(search.get("request_id") == request_id, "search receipt identity mismatch")
        receipt["channel_statuses"] = [
            {"family": c["family"], "provider": c["provider"], "status": c["status"],
             "error_code": c.get("error_code")}
            for c in search.get("channels", [])]
        checkpoint()
        channels = checked_channels(search, families)
        materials, selected, anchors = [], [], []
        for channel in channels:
            family, hit = channel["family"], channel["hits"][0]
            raw_body, _ = original(channel["raw_source"], family + "_raw_original")
            selection = call(family + "_select", "POST", "/api/v1/research/public/materialize",
                             {**target, "family": family, "hit_id": hit["id"]})
            require(selection.get("raw_reference") == channel["raw_source"], "raw reference mismatch")
            require(selection.get("request_id") == request_id and selection.get("family") == family
                    and selection.get("hit_id") == hit["id"], "selection identity mismatch")
            ref = selection["reference"]
            body, data = original(ref, family + "_selected_original")
            quote = hit["excerpt"][:128]
            quote_bytes = quote.encode("utf-8")
            start = data.rfind(quote_bytes)
            require(start >= 0, "selected excerpt missing from derived original")
            position = {"type": "text", "start": start, "end": start + len(quote_bytes)}
            anchor = call(family + "_anchor", "POST", f"/api/v1/sources/{ref['source_id']}/anchors",
                          {"revision": ref["sha256"], "checksum": sha(quote_bytes),
                           "position": json.dumps(position)}, expected=201)
            require(anchor.get("location_status") == "located", "anchor was not verified")
            anchor_id = anchor["anchor_id"]
            require(re.fullmatch(r"[A-Za-z0-9_-]+", anchor_id), "unsafe anchor identity")
            path = f"/api/v1/sources/{ref['source_id']}/anchors/{anchor_id}/resolve"
            resolved = call(family + "_resolve", "GET", path)
            require(resolved.get("status") == "CURRENT"
                    and resolved.get("scope") == "locator_provenance_only"
                    and resolved.get("source_revision") == ref["sha256"]
                    and resolved.get("position") == anchor["position"], "anchor resolution mismatch")
            jump_body, jump_data = original(ref, family + "_original_jump")
            require(jump_body == body and jump_data[start:position["end"]] == quote_bytes,
                    "original jump does not reproduce quote bytes")
            materials.append({
                "id": family, "note": selection["note"], "reference": ref,
                "citation": {"schema": "archeaxis.research-citation/v1", "anchor_id": anchor_id,
                             "source_sha256": ref["sha256"],
                             "anchor_position_sha256": sha(anchor["position"].encode("utf-8")),
                             "quote": quote, "quote_sha256": sha(quote_bytes),
                             "read_snapshot_sha256": ref["sha256"]},
            })
            materials.append({
                "id": family + "_raw", "note": "原始公共 API 响应实体字节；未作专业核验。",
                "reference": channel["raw_source"],
            })
            selected.append((channel["raw_source"], raw_body, ref, body))
            anchors.append((path, resolved))
        refs = [material["reference"] for material in materials]
        research = {
            "schema": "archeaxis.research/v1", "question": args.public_query, "materials": materials,
            "hypotheses": [{"id": "support_draft", "text": "支持方向草稿：待人工判断这些材料能否支持问题。",
                            "references": refs}],
            "counterevidence": [{"id": "opposition_draft", "text": "反对方向草稿：待人工查找材料中的限制与反证。",
                                 "references": refs}],
            "unresolved": [{"id": "verification_pending", "text": "未核验：来源内容尚未进行专业核验或知识接纳。",
                            "references": refs}],
            "methods": [], "experiments": [], "conclusions": [],
        }
        editor = {"type": "doc", "attrs": {"archeaxis_research": research},
                  "content": [{"type": "paragraph", "content": [
                      {"type": "text", "text": "公开研究草稿；未核验、未接纳为知识。"}]}]}
        document = call("research_save", "POST", "/api/v1/documents",
                        {"create_request_id": request_id, "title": "J2 public research draft",
                         "editor_json": editor}, expected=201)
        require(document["editor_json"]["attrs"]["archeaxis_research"] == research,
                "saved research metadata differs")
        doc_id = document["document_id"]
        require(re.fullmatch(r"[A-Za-z0-9_-]+", doc_id), "unsafe document identity")
        doc_path = f"/api/v1/documents/{doc_id}"
        require(call("research_read", "GET", doc_path) == document, "document readback differs")
        package = call("package", "GET", doc_path + "/package")
        require(package["document"] == document, "package document differs")
        expected_objects = {}
        for raw_ref, raw_before, ref, before in selected:
            for reference, original_body in ((raw_ref, raw_before), (ref, before)):
                expected_objects[reference["source_id"]] = (
                    reference["sha256"], checked_original(original_body, reference)
                )
        require(len(package["objects"]) == len(expected_objects), "package source count mismatch")
        for item in package["objects"]:
            require(sha(bytes(item["bytes"])) == item["sha256"], "package object hash mismatch")
            require(expected_objects.get(item["source_id"]) == (item["sha256"], bytes(item["bytes"])),
                    "package lost or replaced a raw/derived research source")
        require({item["source_id"] for item in package["objects"]} == set(expected_objects),
                "package contains duplicate or missing sources")
        exported = call("export", "GET", doc_path + "/export?format=markdown")
        files = {item["path"]: item["content"] for item in exported["files"]}
        require(set(files) == {"document.md", "manifest.json"}, "unexpected export file set")
        manifest = json.loads(files["manifest.json"])
        require(manifest["document"] == document, "export lost research metadata")
        require(manifest["projection_sha256"] == sha(document["text_projection"].encode("utf-8")),
                "export projection fingerprint mismatch")
        for name, content in files.items():
            (work / name).write_text(content, encoding="utf-8")
        (work / "research-package.json").write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
        # A scripted human-principal fixture selects the research snapshot and
        # exercises the ordinary text-job and review path. It is not human review.
        admission_family, admission_source = admission_material(materials)
        job_id = "j2-admission"
        call("admission_enqueue", "POST", "/api/v1/jobs",
             {"job_id": job_id, "kind": "text", "input_ref": admission_source}, expected=202)
        call("admission_execute", "POST", f"/api/v1/jobs/{job_id}/executions",
             {"deadline_ms": 120000}, expected=202, headers={"idempotency-key": job_id})
        state = None
        for _ in range(120):
            job = call("admission_status", "GET", f"/api/v1/jobs/{job_id}")
            state = job.get("state") if isinstance(job, dict) else None
            if state in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(1)
        require(state == "succeeded", f"admission transform state {state}")
        transform = call("admission_transform", "GET",
                         f"/api/v1/sources/{admission_source}/jobs/{job_id}/transform")
        content = transform["content"]
        created = call("admission_knowledge", "POST", "/api/v1/knowledge-items/from-transform", {
            "knowledge_type": "FACTUAL_CLAIM", "body": content, "source_id": admission_source,
            "job_id": job_id, "transform_id": transform["transform_id"],
            "selection_start_utf16": 0,
            "selection_end_utf16": len(content.encode("utf-16-le")) // 2, "quote": content,
        }, expected=(200, 201))
        knowledge_id = created.get("knowledge_id") or created.get("id")
        require(isinstance(knowledge_id, str) and knowledge_id, "knowledge identity missing")
        call("admission_review", "POST", f"/api/v1/knowledge-items/{knowledge_id}/review-decisions",
             {"action": "accepted", "reviewer": "synthetic-fixture"}, expected=(200, 201))
        knowledge_before = call("admission_read", "GET", f"/api/v1/knowledge-items/{knowledge_id}/v3")
        receipt["knowledge_admission"] = {
            "state": "ACCEPTED", "knowledge_id": knowledge_id, "source_id": admission_source,
            "family": admission_family, "job_id": job_id, "transform_id": transform["transform_id"],
            "quote_sha256": sha(content.encode("utf-8")), "reviewer_kind": "synthetic_fixture",
        }
        stop()
        child, base, token, _ = start_runtime(work)
        receipt["restart_pid"] = child.pid
        restarted = call("restart_workspace", "GET", "/api/v1/workspace/ui-state")
        require({key: restarted[key] for key in scope} == scope, "restart changed workspace basis")
        require(call("restart_research_receipt", "POST", "/api/v1/research/public/read", target) == search,
                "persisted search receipt differs")
        for index, (raw_ref, raw_before, ref, before) in enumerate(selected):
            require(original(raw_ref, f"restart_raw_{index}")[0] == raw_before, "raw original changed")
            require(original(ref, f"restart_selected_{index}")[0] == before, "derived original changed")
        for index, (path, before) in enumerate(anchors):
            require(call(f"restart_anchor_{index}", "GET", path) == before, "anchor resolution changed")
        for name, path, before in (
            ("document", doc_path, document), ("package", doc_path + "/package", package),
            ("export", doc_path + "/export?format=markdown", exported),
        ):
            require(call("restart_" + name, "GET", path) == before, name + " changed after restart")
        receipt["same_objects_after_restart"] = True
        require(call("restart_knowledge_admission", "GET",
                     f"/api/v1/knowledge-items/{knowledge_id}/v3") == knowledge_before,
                "accepted knowledge changed after restart")
        if args.backup:
            backup = call("backup", "POST", "/api/v1/workspace/backups", {}, expected=201, timeout=180)
            receipt["backup"] = backup
            require(backup.get("verified") is True, "Core backup was not verified")
            require(set(backup["source_sha_list"]) == {item[0] for item in expected_objects.values()},
                    "backup source fingerprint set differs")
            listed = call("backup_list", "GET", "/api/v1/workspace/backups")
            require(backup in listed["backups"], "verified backup missing from list")
            preview = call("restore_preview", "POST", "/api/v2/workspace/restore/preview",
                           {"backup_id": backup["backup_id"], "expected_sha256": backup["sha256"]})
            require(preview.get("verified") is True and preview.get("compatible") is True,
                    "backup restore preflight failed")
        if args.restore:
            filename = backup.get("filename", "")
            require(isinstance(filename, str) and re.fullmatch(r"[a-f0-9]{32}\.sqlite", filename),
                    "unsafe backup filename")
            backup_file = dev.safe_path(work / "backups" / filename)
            object_dir = dev.safe_path(Path(str(backup_file) + ".objects"))
            object_hashes = backup["source_sha_list"]

            def verify_backup():
                verify_backup_objects(backup_file, object_dir, object_hashes, backup["sha256"],
                                      launcher.filesystem_path)

            verify_backup()
            stop()
            restored_work = dev.safe_path(work / "independent-restore")
            launcher.filesystem_path(restored_work).mkdir(exist_ok=False)
            receipt["restore"] = {"state": "STARTED", "destination": str(restored_work)}
            checkpoint()
            restored = subprocess.run(
                [str(core_exe), "--maintenance-restore", str(restored_work / "workspace.sqlite"), str(backup_file)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
            )
            restore_result = json.loads(restored.stdout) if restored.stdout else {}
            require(restored.returncode == 0 and restore_result.get("ok") is True,
                    "independent maintenance restore failed")
            require(restore_result.get("authorization_requires_new_grants") is True,
                    "restore did not require new authorization")
            child, base, token, _ = start_runtime(restored_work)
            restored_state = call("restore_workspace", "GET", "/api/v1/workspace/ui-state")
            require(restored_state["workspace_id"] == scope["workspace_id"]
                    and restored_state["restore_epoch"] != scope["restore_epoch"],
                    "restore workspace identity or epoch is invalid")
            call("restore_old_epoch_refused", "POST", "/api/v1/research/public/read", target, expected=409)
            restored_target = {**target, "restore_epoch": restored_state["restore_epoch"]}
            require(call("restore_research_receipt", "POST", "/api/v1/research/public/read", restored_target) == search,
                    "restored research receipt differs")
            for index, (raw_ref, raw_before, ref, before) in enumerate(selected):
                require(original(raw_ref, f"restore_raw_{index}")[0] == raw_before, "restored raw original differs")
                require(original(ref, f"restore_selected_{index}")[0] == before, "restored derived original differs")
            for index, (path, before) in enumerate(anchors):
                require(call(f"restore_anchor_{index}", "GET", path) == before, "restored anchor differs")
            for name, path, before in (
                ("document", doc_path, document), ("package", doc_path + "/package", package),
                ("export", doc_path + "/export?format=markdown", exported),
                ("knowledge", f"/api/v1/knowledge-items/{knowledge_id}/v3", knowledge_before),
            ):
                require(call("restore_" + name, "GET", path) == before, name + " differs after restore")
            stop()
            child, base, token, _ = start_runtime(restored_work)
            require(call("restore_restart_receipt", "POST", "/api/v1/research/public/read", restored_target) == search,
                    "restored receipt changed after restart")
            require(call("restore_restart_knowledge", "GET", f"/api/v1/knowledge-items/{knowledge_id}/v3")
                    == knowledge_before, "restored knowledge changed after restart")
            verify_backup()
            receipt["restore"] = {"state": "VERIFIED", "destination": str(restored_work),
                                  "old_epoch_refused": True, "new_epoch_readback": True,
                                  "source_objects_verified": len(object_hashes), "restart_verified": True,
                                  "authorization_requires_new_grants": True}
        receipt.update({"ok": True, "status": "PARTIAL", "verified_subset": [
            f"{len(families)} live public channel(s) of {len(FAMILIES)}", "raw and derived original hashes",
            "fixed source references",
            "derived text anchors and original readback", "research draft save",
            "scripted-fixture-accepted source-bound knowledge", "restart equal readback",
            "document package and Markdown manifest",
            "per-channel statuses recorded; a failed primary channel stays failed and is not renamed as success",
        ]})
        if args.restore:
            receipt["verified_subset"].append("independent backup restore, epoch fencing and restart")
    except Exception as error:
        receipt.update({"status": "FAIL", "error": f"{type(error).__name__}: {error}"})
    finally:
        if child is not None:
            try:
                stop()
            except Exception as error:
                receipt.update({"ok": False, "status": "FAIL",
                                "cleanup_error": f"{type(error).__name__}: {error}"})
        try:
            receipt["source_after"] = source_identity()
            receipt["candidate_files_after"] = candidate_identity()
            receipt["source_consistent"] = source_before == receipt["source_after"]
            receipt["candidate_consistent"] = candidate_before == receipt["candidate_files_after"]
            require(receipt["source_consistent"] and receipt["candidate_consistent"],
                    "source or candidate changed during execution")
        except Exception as error:
            receipt.update({"ok": False, "status": "FAIL", "identity_error": str(error)})
        checkpoint()
        print(json.dumps({"ok": receipt["ok"], "status": receipt["status"], "receipt": str(output)}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
