"""J2 Core probe using an explicit public query and an isolated candidate workspace.

Run through scripts/runtime/dev.py. No database access, fixtures, knowledge
admission, provider changes or installed-desktop qualification. Network execution
requires --public-network; --help and importing this module never launch Core.
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
import uuid

REPO = Path(__file__).resolve().parents[2]
FAMILIES = ("encyclopedia", "community", "research")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_channels(receipt):
    require(receipt.get("state") == "complete", "public search is not complete")
    channels = receipt.get("channels", [])
    require(len(channels) == 3, "expected exactly three public channels")
    require({c.get("family") for c in channels} == set(FAMILIES), "channel identity mismatch")
    for channel in channels:
        require(channel.get("status") == "complete", "channel is not complete")
        require(len(channel.get("hits", [])) == 1, "each channel must return one real hit")
        require(channel.get("raw_source"), "raw response source missing")
        hit = channel["hits"][0]
        require(hit.get("family") == channel["family"], "hit family mismatch")
        require(bool(hit.get("excerpt", "").strip()), "selected hit has no quotable content")
    return channels


def checked_original(original, reference):
    require(reference.get("kind") == "source", "expected fixed source reference")
    source_id, digest = reference["source_id"], reference["sha256"]
    require(re.fullmatch(r"[A-Za-z0-9_-]+", source_id), "unsafe source identifier")
    require(re.fullmatch(r"[a-f0-9]{64}", digest), "invalid source fingerprint")
    raw = base64.b64decode(original["content_base64"], validate=True)
    require(original.get("source_id") == source_id, "original source identity mismatch")
    require(original.get("sha256") == digest == sha(raw), "original source bytes mismatch")
    return raw


def hidden_start(office, candidate, work, launcher):
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
        return office.start(candidate, work, launcher)
    finally:
        office.subprocess = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--public-query", required=True, help="Public text sent to all three providers")
    parser.add_argument("--public-network", action="store_true", help="Explicitly enable public requests")
    parser.add_argument("--backup", action="store_true", help="Also require Core backup creation")
    args = parser.parse_args()
    if not args.public_network:
        parser.error("execution requires --public-network; no request has been sent")
    if not args.public_query.strip() or len(args.public_query.encode("utf-8")) > 512:
        parser.error("public-query must contain 1-512 UTF-8 bytes")
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

    def call(label, method, path, body=None, expected=200, timeout=30):
        step = {"label": label, "method": method, "path": path, "state": "STARTED"}
        receipt["steps"].append(step)
        checkpoint()
        status, response = client.call(base, method, path, token, body, timeout=timeout)
        step.update({"status": status, "body": response, "state": "RETURNED"})
        checkpoint()
        require(status == expected, f"{label}: expected HTTP {expected}, received {status}")
        return response

    def source_identity():
        dirty, patch = dev.worktree_identity(REPO)
        return {"commit": dev.git(REPO, "rev-parse", "HEAD"), "dirty": dirty,
                "patch_sha256": patch, "changes": office.source_changes(dev)}

    def candidate_identity():
        profile = launcher.load_profile(candidate)
        files = {candidate / "backend-runtime-manifest.json", candidate / "worker-profile.json",
                 candidate / "core/archeaxis-api.exe", profile["python"], profile["script"]}
        files.update(route["script"] for route in profile["routes"])
        files.update((candidate / "workers").rglob("*.py"))
        return [office.identity(dev.safe_path(path)) for path in sorted(files)]

    def original(reference, label):
        source_id = reference["source_id"]
        require(re.fullmatch(r"[A-Za-z0-9_-]+", source_id), "unsafe source identifier")
        body = call(label, "GET", f"/api/v1/sources/{source_id}/original")
        return body, checked_original(body, reference)

    try:
        source_before = source_identity()
        candidate_before = candidate_identity()
        receipt.update({"source": source_before, "candidate_files": candidate_before,
                        "probe": office.identity(Path(__file__)),
                        "lockfile": office.identity(REPO / "uv.lock")})
        child, base, token, worker = hidden_start(office, candidate, work, launcher)
        receipt.update({"pid": child.pid, "launch_worker": worker})
        call("version", "GET", "/api/v1/system/version")
        state = call("workspace", "GET", "/api/v1/workspace/ui-state")
        scope = {key: state[key] for key in ("workspace_id", "restore_epoch")}
        request_id = "public-loop-" + uuid.uuid4().hex
        target = {**scope, "request_id": request_id}
        search = call("public_search", "POST", "/api/v1/research/public/search",
                      {**target, "query": args.public_query, "families": list(FAMILIES), "limit": 1},
                      timeout=180)
        receipt["evidence_level"] = "REAL_CORE_PUBLIC_NETWORK"
        require(search.get("request_id") == request_id, "search receipt identity mismatch")
        channels = checked_channels(search)
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
        launcher.stop(child)
        child = None
        child, base, token, _ = hidden_start(office, candidate, work, launcher)
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
            "three live public channels", "raw and derived original hashes", "fixed source references",
            "derived text anchors and original readback", "research draft save",
            "restart equal readback", "document package and Markdown manifest",
        ]})
    except Exception as error:
        receipt.update({"status": "FAIL", "error": f"{type(error).__name__}: {error}"})
    finally:
        if child is not None:
            try:
                launcher.stop(child)
            except Exception as error:
                receipt.update({"ok": False, "status": "FAIL", "cleanup_error": type(error).__name__})
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
