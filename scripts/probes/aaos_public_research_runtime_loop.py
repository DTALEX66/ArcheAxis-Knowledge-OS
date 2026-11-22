"""J2 Core probe using an explicit public query and an isolated candidate workspace.

Run through scripts/runtime/dev.py. A new search requires --public-network.
A recorded search can be continued locally through Core. Any review decision
in this isolated workspace is simulated and carries no Owner acceptance.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

REPO = Path(__file__).resolve().parents[2]
FAMILIES = ("encyclopedia", "community", "research")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def citation_text(hit):
    if hit.get("excerpt", "").strip():
        return "excerpt", hit["excerpt"][:128]
    require(hit.get("content") == hit.get("representation") == "metadata" and hit.get("title", "").strip(),
            "selected hit has neither quotable content nor a bibliographic title")
    return "bibliographic_title", hit["title"][:128]


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
        citation_text(hit)
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


def admit_excerpt(call, choices):
    family = next((name for name in ("research", "encyclopedia", "community") if name in choices), None)
    if family is None:
        return {"state": "METADATA_ONLY_NO_CLAIM"}, None
    source, quote = choices[family]
    job_id = "j2-admission"
    call("admission_enqueue", "POST", "/api/v1/jobs",
         {"job_id": job_id, "kind": "text", "input_ref": source}, expected=202)
    call("admission_execute", "POST", f"/api/v1/jobs/{job_id}/executions",
         {"deadline_ms": 120000}, expected=202, headers={"idempotency-key": job_id})
    for _ in range(120):
        state = call("admission_status", "GET", f"/api/v1/jobs/{job_id}").get("state")
        if state in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(1)
    require(state == "succeeded", f"admission transform state {state}")
    transform = call("admission_transform", "GET", f"/api/v1/sources/{source}/jobs/{job_id}/transform")
    content = transform["content"]
    start = content.rfind(quote)
    require(start >= 0, "selected source excerpt missing from the text transform")
    utf16_start = len(content[:start].encode("utf-16-le")) // 2
    created = call("admission_knowledge", "POST", "/api/v1/knowledge-items/from-transform", {
        "knowledge_type": "FACTUAL_CLAIM", "body": quote, "source_id": source,
        "job_id": job_id, "transform_id": transform["transform_id"], "selection_start_utf16": utf16_start,
        "selection_end_utf16": utf16_start + len(quote.encode("utf-16-le")) // 2, "quote": quote,
    }, expected=(200, 201))
    knowledge_id = created["knowledge_id"]
    call("admission_review", "POST", f"/api/v1/knowledge-items/{knowledge_id}/review-decisions",
         {"action": "accepted", "reviewer": "SIMULATED_RESEARCH_REVIEW"}, expected=(200, 201))
    knowledge = call("admission_read", "GET", f"/api/v1/knowledge-items/{knowledge_id}/v3")
    require(knowledge["status"] == "accepted", "simulated review was not persisted")
    return {"state": "ACCEPTED", "reviewer_kind": "SIMULATED", "family": family, "knowledge_id": knowledge_id,
            "source_id": source, "job_id": job_id, "transform_id": transform["transform_id"],
            "quote_sha256": sha(quote.encode("utf-8"))}, knowledge


def hidden_start(office, candidate, work, launcher, core_executable=None):
    """Reuse the canonical launch handshake with Windows window suppression."""
    original = office.subprocess

    class Hidden:
        PIPE = original.PIPE

        @staticmethod
        def Popen(*args, **kwargs):
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | getattr(
                original, "CREATE_NO_WINDOW", 0
            )
            return original.Popen(*args, **kwargs)

    office.subprocess = Hidden
    try:
        return office.start(candidate, work, launcher, core_executable=core_executable)
    finally:
        office.subprocess = original


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
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--core-build-receipt", type=Path,
                        help="Run the qualified current Core with the candidate's workers in place")
    parser.add_argument("--public-query", required=True, help="Public text sent to all three providers")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--public-network", action="store_true", help="Explicitly enable new public requests")
    mode.add_argument("--resume-search-receipt", type=Path,
                      help="Continue an interrupted search-only run from its stored Core response without querying again")
    parser.add_argument("--backup", action="store_true", help="Also require Core backup creation")
    parser.add_argument("--families", nargs="+", choices=FAMILIES, default=list(FAMILIES),
                        help="Measured families; a subset records the rest as not measured, never as passed")
    args = parser.parse_args()
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
    candidate = dev.safe_path(args.candidate)
    candidate.relative_to(paths["dev"])
    recorded_search = None
    prior_path = None
    if args.resume_search_receipt:
        prior_path = dev.safe_path(args.resume_search_receipt)
        prior_path.relative_to(run.parent)
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        require(prior_path.name == "public-research-receipt.json" and prior_path.parent.name == "artifacts"
                and prior_path.parent.parent.parent == run.parent, "Foreign search receipt")
        require(prior.get("source_consistent") and prior.get("candidate_consistent")
                and dev.safe_path(Path(prior["candidate"])) == candidate, "Search candidate identity differs")
        require(prior.get("stopped") and all(p.get("wait_reaped") for p in prior["stopped"]), "Prior Core still active")
        steps = prior["steps"]
        require([s.get("label") for s in steps] == ["version", "workspace", "public_search"]
                and steps[-1].get("status") == 200, "Expected a recorded search before its first selection")
        recorded_search = steps[-1]["body"]
        require(recorded_search["query"] == args.public_query and sorted(recorded_search["families"]) == families,
                "Query or family set differs from the recorded search")
        work = dev.safe_path(Path(prior["workspace"]))
        require(work == prior_path.parent / "public-research-workspace" and work.is_dir(), "Search workspace missing")
    else:
        work = dev.safe_path(paths["artifacts"] / "public-research-workspace")
        work.mkdir(exist_ok=False)
    output = paths["artifacts"] / "public-research-receipt.json"
    require(not output.exists(), "receipt already exists; choose a new run ID")
    receipt = {
        "ok": False, "status": "RUNNING", "evidence_level": "NOT_EXECUTED",
        "candidate": str(candidate), "workspace": str(work), "query": args.public_query,
        "steps": [], "knowledge_admission": "NOT_EXECUTED",
        "limitations": [
            "Core integration only; no installed Tauri/UI acceptance",
            "Draft support/opposition labels are questions, not verified semantic conclusions",
            "Text anchors address selected derived snapshots, not upstream HTTP byte offsets",
            "Package checks fixed source bytes only; other document/knowledge dependencies are not rebuilt",
            "Workspace restore and restore-epoch recovery are NOT_EXECUTED",
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
        profile = launcher.load_profile(candidate)
        files = {candidate / "backend-runtime-manifest.json", candidate / "worker-profile.json",
                 core_executable, profile["python"], profile["script"]}
        files.update(route["script"] for route in profile["routes"])
        files.update((candidate / "workers").rglob("*.py"))
        return [office.identity(dev.safe_path(path)) for path in sorted(files)]

    def original(reference, label):
        source_id = reference["source_id"]
        require(re.fullmatch(r"[A-Za-z0-9_-]+", source_id), "unsafe source identifier")
        body = call(label, "GET", f"/api/v1/sources/{source_id}/original")
        return body, checked_original(body, reference)

    core_executable = candidate / "core/archeaxis-api.exe"
    try:
        if args.core_build_receipt:
            core = dev.read_core_build(args.core_build_receipt, paths, os.environ)
            core_executable = Path(core["path"])
            receipt["core_build"] = core
            receipt["core_build_receipt"] = dev.build_file_identity(args.core_build_receipt)
            receipt["runtime_scope"] = "QUALIFIED_CORE_WITH_IN_PLACE_WORKERS"
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
        child, base, token, worker = hidden_start(office, candidate, work, launcher, core_executable)
        receipt.update({"pid": child.pid, "launch_worker": worker})
        call("version", "GET", "/api/v1/system/version")
        state = call("workspace", "GET", "/api/v1/workspace/ui-state")
        scope = {key: state[key] for key in ("workspace_id", "restore_epoch")}
        if recorded_search is not None:
            require(all(recorded_search[k] == v for k, v in scope.items()), "Recorded workspace or restore epoch differs")
            request_id = recorded_search["request_id"]
            target = {**scope, "request_id": request_id}
            search = call("resume_stored_search", "POST", "/api/v1/research/public/read", target)
            require(search == recorded_search, "Stored search differs from acquisition receipt")
            receipt["resumed_from"] = office.identity(prior_path)
        else:
            request_id = "public-loop-" + uuid.uuid4().hex
            target = {**scope, "request_id": request_id}
            search = call("public_search", "POST", "/api/v1/research/public/search",
                          {**target, "query": args.public_query, "families": families, "limit": 1}, timeout=180)
        receipt["evidence_level"] = "REAL_CORE_PUBLIC_NETWORK"
        require(search.get("request_id") == request_id, "search receipt identity mismatch")
        channels = checked_channels(search, families)
        receipt["channel_statuses"] = [
            {"family": c["family"], "provider": c["provider"], "status": c["status"],
             "error_code": c.get("error_code")}
            for c in search.get("channels", [])]
        materials, selected, anchors = [], [], []
        admission_choices = {}
        receipt["citation_basis"] = {}
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
            basis, quote = citation_text(hit)
            receipt["citation_basis"][family] = basis
            quote_bytes = quote.encode("utf-8")
            prefix = ("\n标题：" if basis == "bibliographic_title" else "\n\n内容：\n").encode("utf-8")
            start = data.index(prefix + quote_bytes) + len(prefix)
            if basis == "excerpt":
                admission_choices[family] = (ref["source_id"], quote)
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
                "id": family, "note": selection["note"] + (" 仅引用题名，未取得正文或摘要。" if basis == "bibliographic_title" else ""),
                "reference": ref,
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
        admission, knowledge_before = admit_excerpt(call, admission_choices)
        receipt["knowledge_admission"] = admission
        stop()
        child, base, token, _ = hidden_start(office, candidate, work, launcher, core_executable)
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
        if knowledge_before is not None:
            knowledge_path = f"/api/v1/knowledge-items/{admission['knowledge_id']}/v3"
            require(call("restart_knowledge_admission", "GET", knowledge_path) == knowledge_before,
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
        receipt.update({"ok": True, "status": "PARTIAL", "verified_subset": [
            f"{len(families)} live public channel(s) of {len(FAMILIES)}", "raw and derived original hashes",
            "fixed source references",
            "derived text anchors and original readback", "research draft save",
            admission["state"], "restart equal readback",
            "document package and Markdown manifest",
            "per-channel statuses recorded; a failed primary channel stays failed and is not renamed as success",
        ]})
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
