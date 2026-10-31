"""Exercise Stitch research consumer semantics against an isolated real Core.

Authored UTF-8 materials only. No public network, model inference, database access,
knowledge admission or installed/UI qualification. Run through runtime/dev.py.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def preserved(sent, received):
    """Core assigns stable block IDs; every authored field must survive."""
    if isinstance(sent, dict):
        return isinstance(received, dict) and all(key in received and preserved(value, received[key])
                                                  for key, value in sent.items())
    if isinstance(sent, list):
        return isinstance(received, list) and len(sent) == len(received) and all(
            preserved(a, b) for a, b in zip(sent, received))
    return sent == received


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    dev = load("stitch_dev", repo / "scripts/runtime/dev.py")
    inherited = os.environ.get("ARCHEAXIS_RUN_ROOT")
    require(inherited, "run through scripts/runtime/dev.py")
    run = dev.safe_path(Path(inherited))
    paths = dev.layout(repo, run.name)
    require(run == paths["run"], "run ownership mismatch")
    candidate = dev.safe_path(args.candidate)
    candidate.relative_to(paths["dev"])
    work = dev.safe_path(paths["artifacts"] / "stitch-consumer-workspace")
    work.mkdir(exist_ok=False)
    output = paths["artifacts"] / "stitch-consumer-receipt.json"
    office = load("stitch_office", repo / "scripts/probes/aaos01_office_runtime_loop.py")
    helper = load("stitch_public_helper", repo / "scripts/probes/aaos_public_research_runtime_loop.py")
    launcher = load("stitch_launcher", repo / "scripts/release/backend_launcher.py")
    client = load("stitch_client", repo / "shared/core_client.py")
    receipt = {"ok": False, "status": "RUNNING", "evidence_level": "REAL_CORE_AUTHORED_MATERIAL",
               "candidate": str(candidate), "workspace": str(work), "steps": [],
               "knowledge_admission": "NOT_EXECUTED", "network": "NOT_EXECUTED",
               "model_inference": "NOT_EXECUTED", "installed_ui": "NOT_EXECUTED",
               "limitations": ["Synthetic authored material; not external evidence or professional truth",
                               "Existing candidate binary; no assertion it was built from current source",
                               "HTTP Core consumer integration; finite bridge/UI not executed",
                               "Restart uses terminate/wait, not native host graceful shutdown"]}
    child = None
    base = token = None

    def checkpoint():
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def call(label, method, path, body=None, expected=200):
        status, value = client.call(base, method, path, token, body, timeout=45)
        receipt["steps"].append({"label": label, "method": method, "path": path, "status": status})
        checkpoint()
        require(status == expected, f"{label}: expected {expected}, got {status}: {value}")
        return value

    def stop():
        nonlocal child
        helper.stop_owned(child, launcher, receipt.setdefault("stopped", []))
        child = None
        checkpoint()

    def candidate_identity():
        return [office.identity(candidate / name) for name in
                ("backend-runtime-manifest.json", "worker-profile.json", "core/archeaxis-api.exe")]

    initial_identity = candidate_identity()
    receipt["candidate_files"] = initial_identity
    receipt["probe"] = office.identity(Path(__file__))
    receipt["source_commit_observed"] = dev.git(repo, "rev-parse", "HEAD")
    try:
        child, base, token, _ = helper.hidden_start(office, candidate, work, launcher)
        receipt["pid"] = child.pid
        call("version", "GET", "/api/v1/system/version")
        state = call("workspace", "GET", "/api/v1/workspace/ui-state")
        scope = {key: state[key] for key in ("workspace_id", "restore_epoch")}
        raw = "合成研究材料：支持方向仍需核验。\n反对方向：样本不足，不能推广。\n".encode("utf-8")
        imported = call("import_authored_material", "POST", "/api/v1/imports",
                        {"name": "stitch-authored-evidence.txt", "content_base64": base64.b64encode(raw).decode()}, 202)
        source_id, revision = imported["source_id"], imported["sha256"]
        require(re.fullmatch(r"[A-Za-z0-9_-]+", source_id) and revision == sha(raw), "source identity")
        source_path = f"/api/v1/sources/{source_id}/original"
        original = call("fixed_original", "GET", source_path)
        require(original["source_id"] == source_id and original["sha256"] == revision
                and base64.b64decode(original["content_base64"], validate=True) == raw, "original custody")
        quote = "反对方向：样本不足，不能推广。"
        quote_bytes = quote.encode("utf-8")
        start = raw.index(quote_bytes)
        anchor = call("quote_anchor", "POST", f"/api/v1/sources/{source_id}/anchors",
                      {"revision": revision, "checksum": sha(quote_bytes),
                       "position": json.dumps({"type": "text", "start": start, "end": start + len(quote_bytes)})}, 201)
        anchor_path = f"/api/v1/sources/{source_id}/anchors/{anchor['anchor_id']}/resolve"
        resolved = call("quote_resolve", "GET", anchor_path)
        require(resolved["status"] == "CURRENT" and resolved["scope"] == "locator_provenance_only"
                and resolved["position"] == anchor["position"], "quote locator")
        ref = {"kind": "source", "source_id": source_id, "sha256": revision}
        citation = {"schema": "archeaxis.research-citation/v1", "anchor_id": anchor["anchor_id"],
                    "source_sha256": revision, "anchor_position_sha256": sha(anchor["position"].encode()),
                    "quote": quote, "quote_sha256": sha(quote_bytes), "read_snapshot_sha256": revision}
        basis_editor = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "相关资料：作者笔记，未专业核验。"}]}]}
        basis = call("related_document", "POST", "/api/v1/documents",
                     {"create_request_id": "stitch_basis_" + uuid.uuid4().hex, "title": "相关资料", "editor_json": basis_editor}, 201)
        basis_ref = {"kind": "document", "document_id": basis["document_id"], "version": basis["version"], "block_id": None}
        research = {"schema": "archeaxis.research/v1", "question": "这些材料能否支持该假设？",
                    "materials": [{"id": "material_1", "note": "作者笔记；合成材料", "reference": ref, "citation": citation},
                                  {"id": "related_1", "note": "固定版本的相关资料", "reference": basis_ref}],
                    "hypotheses": [{"id": "support_1", "text": "作者判断支持；未核验", "references": [ref]}],
                    "counterevidence": [{"id": "opposes_1", "text": "作者判断反对；未核验", "references": [ref]}],
                    "methods": [], "experiments": [], "conclusions": [],
                    "unresolved": [{"id": "conflict_1", "text": "材料冲突待处理", "references": [ref, basis_ref]}]}
        editor = {"type": "doc", "attrs": {"archeaxis_research": research,
                  "archeaxis_relations": {"schema": "archeaxis.relations/v1", "relations": [
                      {"id": "related_basis", "kind": "related", "label": "相关资料", "target": basis_ref},
                      {"id": "opposition_source", "kind": "contradicts", "label": "作者判断反对；未核验", "target": ref}]}},
                  "content": [{"type": "paragraph", "content": [{"type": "text", "text": "研究笔记第一版；未知识接纳。"}]}]}
        create_body = {"create_request_id": "stitch_research_" + uuid.uuid4().hex,
                       "title": "Stitch 研究消费者回归", "editor_json": editor}
        v1 = call("research_save_v1", "POST", "/api/v1/documents", create_body, 201)
        doc_path = f"/api/v1/documents/{v1['document_id']}"
        require(preserved(editor, v1["editor_json"]) and v1["version"] == 1, "v1 content")
        require(call("create_retry_idempotent", "POST", "/api/v1/documents", create_body, 201) == v1, "create replay")
        require(call("read_v1", "GET", doc_path) == v1, "v1 readback")
        next_editor = copy.deepcopy(v1["editor_json"])
        next_editor["attrs"]["archeaxis_research"]["materials"][0]["note"] += "；追加笔记"
        next_editor["attrs"]["archeaxis_research"]["conclusions"] = [
            {"id": "conclusion_1", "text": "作者结论：目前证据不足；不代表知识接纳。", "sources": [ref], "basis": [basis_ref]}]
        v2 = call("notes_conclusion_save_v2", "PUT", doc_path + "/draft",
                  {"expected_version": 1, "editor_json": next_editor})
        require(v2["version"] == 2 and preserved(next_editor, v2["editor_json"]), "v2 content")
        conflicting_editor = copy.deepcopy(next_editor)
        conflicting_editor["content"][0]["content"][0]["text"] = "旧客户端不可覆盖"
        call("stale_writer_refused", "PUT", doc_path + "/draft",
             {"expected_version": 1, "editor_json": conflicting_editor}, 409)
        require(call("conflict_keeps_v2", "GET", doc_path) == v2, "conflict overwrote current version")
        require(call("history_keeps_v1", "GET", doc_path + "/versions/1") == v1, "history changed")
        graph = call("relations_projection", "GET", doc_path + "/relations")
        exported = call("export_v2", "GET", doc_path + "/export?format=markdown")
        require(exported["version"] == 2, "export wrong version")
        package = call("package_v2", "GET", doc_path + "/package")
        require(package["document"] == v2, "package loses notes/conclusion")
        require(any(item["source_id"] == source_id and item["sha256"] == revision
                    and bytes(item["bytes"]) == raw for item in package["objects"]), "package loses source")
        stop()
        child, base, token, _ = helper.hidden_start(office, candidate, work, launcher)
        receipt["restart_pid"] = child.pid
        restarted = call("restart_workspace", "GET", "/api/v1/workspace/ui-state")
        require({key: restarted[key] for key in scope} == scope, "restart scope changed")
        for label, path, expected in [
            ("document", doc_path, v2), ("history", doc_path + "/versions/1", v1),
            ("original", source_path, original), ("anchor", anchor_path, resolved),
            ("basis_version", f"/api/v1/documents/{basis['document_id']}/versions/1", basis),
            ("graph", doc_path + "/relations", graph), ("export", doc_path + "/export?format=markdown", exported),
            ("package", doc_path + "/package", package)]:
            require(call("restart_" + label, "GET", path) == expected, f"restart changed {label}")
        receipt.update({"ok": True, "status": "PASS", "verified_subset": [
            "fixed authored source bytes and quote locator", "versioned related material",
            "research/citation/opposition/conflict metadata save", "notes and conclusion update",
            "stale writer 409 preserves latest version", "immutable history", "Core graph/export/package",
            "restart equal readback"]})
    except Exception as error:
        receipt.update({"ok": False, "status": "FAIL", "error": f"{type(error).__name__}: {error}"})
    finally:
        if child is not None:
            try:
                stop()
            except Exception as error:
                receipt.update({"ok": False, "status": "FAIL", "cleanup_error": str(error)})
        receipt["candidate_files_after"] = candidate_identity()
        receipt["candidate_unchanged"] = receipt["candidate_files_after"] == initial_identity
        if not receipt["candidate_unchanged"]:
            receipt.update({"ok": False, "status": "FAIL", "identity_error": "candidate changed"})
        checkpoint()
        print(json.dumps({"ok": receipt["ok"], "status": receipt["status"], "receipt": str(output)}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
