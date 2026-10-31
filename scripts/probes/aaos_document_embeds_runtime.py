"""Qualify fixed embeds through real Core HTTP in an isolated current candidate.

Authored source bytes and explicit human document/block bindings only. This does
not claim original-app parsing fidelity, native UI, inference or installation.
Run through scripts/runtime/dev.py; no downloads or external network requests.
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
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    dev = load("embeds_runtime_dev", ROOT / "scripts/runtime/dev.py")
    require(os.environ.get("ARCHEAXIS_RUN_ROOT"), "Use runtime/dev.py")
    run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
    paths = dev.layout(ROOT, run.name)
    require(paths["run"] == run, "Foreign run")
    candidate = dev.safe_path(args.candidate)
    candidate.relative_to(paths["dev"] / "runs")
    assembler = load("embeds_runtime_assembler", ROOT / "scripts/release/tauri_portable_candidate.py")
    manifest = assembler.verify(candidate)
    # Bind the actual candidate to its canonical completed build. A correction
    # to this probe need not rebuild unchanged product bytes; both source
    # identities are recorded separately rather than silently called identical.
    build_path = dev.safe_path(Path(manifest["build_receipt"]["path"]))
    build_path.relative_to(paths["dev"] / "runs")
    require(hashlib.sha256(build_path.read_bytes()).hexdigest() == manifest["build_receipt"]["sha256"],
            "Canonical build receipt changed")
    build = json.loads(build_path.read_text(encoding="utf-8"))
    require(build.get("status") == "PASS" and build.get("source_consistent") is True
            and build.get("source_patch_sha256") == manifest["source_patch_sha256"]
            and build.get("host_sha256") == manifest["host_sha256"]
            and build.get("core_sha256") == manifest["core_sha256"], "Candidate build binding mismatch")
    office = load("embeds_runtime_office", ROOT / "scripts/probes/aaos01_office_runtime_loop.py")
    helper = load("embeds_runtime_helper", ROOT / "scripts/probes/aaos_public_research_runtime_loop.py")
    launcher = load("embeds_runtime_launcher", ROOT / "scripts/release/backend_launcher.py")
    client = load("embeds_runtime_client", ROOT / "shared/core_client.py")
    workspace = paths["artifacts"] / "embed-workspace"
    workspace.mkdir(exist_ok=False)
    output = paths["artifacts"] / "document-embeds-runtime.json"
    receipt = {"schema": "archeaxis.document-embeds-runtime/v1", "status": "RUNNING",
               "evidence_level": "INTEGRATED_REAL_CORE_AUTHORED_MATERIAL",
               "candidate": str(candidate), "workspace": str(workspace), "steps": [],
               "host_sha256": manifest["host_sha256"], "core_sha256": manifest["core_sha256"],
               "source_patch_sha256": manifest["source_patch_sha256"],
               "probe_source_patch_sha256": os.environ["ARCHEAXIS_SOURCE_PATCH_SHA256"], "stopped": [],
               "limitations": ["Authored UTF-8 samples, not original-application fidelity",
                               "Explicit document and block bindings; no parser quality claim",
                               "No UI/native/install/model qualification", "Terminate/wait is not graceful host exit"]}
    child = None
    base = token = None

    def checkpoint():
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def call(label, method, path, body=None, expected=200):
        status, value = client.call(base, method, path, token, body, timeout=45)
        receipt["steps"].append({"label": label, "method": method, "path": path, "status": status})
        checkpoint()
        require(status == expected, f"{label}: expected {expected}, got {status}")
        return value

    def stop():
        nonlocal child
        helper.stop_owned(child, launcher, receipt["stopped"])
        child = None
        checkpoint()

    try:
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        receipt["pid"] = child.pid
        call("version", "GET", "/api/v1/system/version")
        state = call("workspace", "GET", "/api/v1/ingest-batches")
        scope = {key: state[key] for key in ("workspace_id", "restore_epoch")}
        files = [("index.md", "![[peer#^named]]\n![[assets/evidence.txt]]\n[[peer]]"),
                 ("peer.md", "旧版固定块内容 ^named"),
                 ("assets/evidence.txt", "已校验附件原文 <script>不执行</script>")]
        batch_path = "/api/v1/ingest-batches/embeds"
        call("batch_register", "POST", "/api/v1/ingest-batches",
             {**scope, "batch_id": "embeds", "folder_label": "Authored selected copy", "expected_members": 3,
              "members": [{"ordinal": i, "relative_path": path, "byte_length": len(text.encode()),
                           "disposition": "pending"} for i, (path, text) in enumerate(files)]})
        sources, documents, originals = [], [], []
        for ordinal, (path, text) in enumerate(files):
            raw = text.encode()
            source = call(f"source_{ordinal}", "POST", batch_path + "/imports",
                          {**scope, "ordinal": ordinal, "expected_sha256": hashlib.sha256(raw).hexdigest(),
                           "content_base64": base64.b64encode(raw).decode()}, 202)
            sources.append(source)
            original = call(f"original_{ordinal}", "GET", f"/api/v1/sources/{source['source_id']}/original")
            require(original["sha256"] == hashlib.sha256(raw).hexdigest()
                    and base64.b64decode(original["content_base64"], validate=True) == raw, "Original bytes lost")
            originals.append(original)
            if ordinal < 2:
                document = call(f"document_{ordinal}", "POST", "/api/v1/documents",
                                {"source_id": source["source_id"], "source_revision": source["sha256"], "title": path,
                                 "editor_json": {"type": "doc", "attrs": {"unrelated": {"keep": True}},
                                                 "content": [{"type": "paragraph", "attrs": {"block_id": "selected_block"},
                                                              "content": [{"type": "text", "text": text}]}]}}, 201)
                documents.append(document)
        main, peer = documents
        main_path = f"/api/v1/documents/{main['document_id']}"
        peer_path = f"/api/v1/documents/{peer['document_id']}"
        target = {"document_id": peer["document_id"], "version": 1, "content_sha256": peer["content_sha256"]}
        body = {**scope, "source_id": sources[0]["source_id"], "source_revision": sources[0]["sha256"],
                "document_id": main["document_id"], "expected_version": 1, "content_sha256": main["content_sha256"],
                "targets": [{"ordinal": i, "source_id": sources[i]["source_id"], "source_revision": sources[i]["sha256"],
                             "document": target if i == 1 else None} for i in (1, 2)],
                "fragment_bindings": [{"link_ordinal": 0, "target_ordinal": 1, "fragment": "named",
                                       "fragment_is_block": True, "block_id": "selected_block"}]}
        mapped = call("map_embeds", "POST", batch_path + "/members/0/relations", body)
        current = mapped["document"]
        relations = current["editor_json"]["attrs"]["archeaxis_relations"]["relations"]
        require(mapped["added_relations"] == 3 and mapped["updated_relations"] == 0 and current["version"] == 2,
                "Mapping counters/version differ")
        require([r.get("presentation") for r in relations] == ["embed", "embed", None], "Embed markers lost")
        require(mapped["links"][0]["reason"] == mapped["links"][1]["reason"] == "embed_presentation_requested",
                "Runtime reason differs from generated contract")
        require(current["editor_json"]["content"] == main["editor_json"]["content"]
                and current["editor_json"]["attrs"]["unrelated"] == {"keep": True}, "Authored body/attrs changed")
        call("stale_mapping_refused", "POST", batch_path + "/members/0/relations", body, 409)
        repeat_body = {**body, "expected_version": current["version"], "content_sha256": current["content_sha256"]}
        repeated = call("repeat_mapping", "POST", batch_path + "/members/0/relations", repeat_body)
        require(repeated["added_relations"] == repeated["updated_relations"] == 0 and repeated["document"] == current,
                "No-op mapping wrote a new version")
        changed_editor = copy.deepcopy(peer["editor_json"])
        changed_editor["content"][0]["content"][0]["text"] = "新版目标内容，不应替换固定v1。"
        newer_peer = call("target_save_v2", "PUT", peer_path + "/draft", {"expected_version": 1, "editor_json": changed_editor})
        require(newer_peer["version"] == 2, "Target did not update")
        require(call("fixed_target_v1", "GET", peer_path + "/versions/1") == peer, "Fixed target changed to current")
        call("relation_projection", "GET", main_path + "/relations")
        exported = call("obsidian_export", "GET", main_path + "/export?format=obsidian")
        package = call("package", "GET", main_path + "/package")
        require(package["document"] == current, "Package lost embed metadata")
        for index in (0, 2):
            require(any(obj["source_id"] == sources[index]["source_id"] and obj["sha256"] == sources[index]["sha256"]
                        and bytes(obj["bytes"]) == files[index][1].encode() for obj in package["objects"]),
                    "Package lost declared source bytes")
        # A single-document package deliberately excludes Document/Knowledge
        # dependencies. Do not invent portability from same-workspace ID matches.
        call("unbundled_dependency_refused", "POST", "/api/v1/document-packages/import",
             {"request_id": "unbundled_embed", "package": package}, 400)
        require(call("refusal_keeps_main", "GET", main_path) == current, "Refused import changed document")
        source_only = call("source_only_document", "POST", "/api/v1/documents",
                           {"title": "附件嵌入往返", "editor_json": {"type": "doc", "content": [], "attrs": {
                               "archeaxis_relations": {"schema": "archeaxis.relations/v1", "relations": [relations[1]]}}}}, 201)
        source_package = call("source_only_package", "GET", f"/api/v1/documents/{source_only['document_id']}/package")
        restored = call("source_package_import", "POST", "/api/v1/document-packages/import",
                        {"request_id": "source_embed_roundtrip", "package": source_package}, 201)["document"]
        restored_relations = restored["editor_json"]["attrs"]["archeaxis_relations"]["relations"]
        require([r.get("presentation") for r in restored_relations] == ["embed"], "Source roundtrip lost marker")
        require(restored_relations[0]["target"]["sha256"] == relations[1]["target"]["sha256"], "Source roundtrip changed hash")
        restored_source = call("imported_source_original", "GET", f"/api/v1/sources/{restored_relations[0]['target']['source_id']}/original")
        require(base64.b64decode(restored_source["content_base64"], validate=True) == files[2][1].encode(),
                "Source roundtrip changed bytes")
        restored_path = f"/api/v1/documents/{restored['document_id']}"
        # The graph hash and scan count cover current workspace documents, not
        # just the center. Capture only after the two package-test writes.
        graph = call("post_write_projection_baseline", "GET", main_path + "/relations")
        receipt["comparison_baselines"] = {"main": current, "peer_v1": peer, "peer_v2": newer_peer, "graph": graph}
        checkpoint()
        stop()
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        receipt["restart_pid"] = child.pid
        for label, path, expected in [("current", main_path, current), ("history", main_path + "/versions/1", main),
                                      ("fixed_peer", peer_path + "/versions/1", peer), ("latest_peer", peer_path, newer_peer),
                                      ("graph", main_path + "/relations", graph),
                                      ("export", main_path + "/export?format=obsidian", exported),
                                      ("package", main_path + "/package", package), ("restored", restored_path, restored)]:
            require(call("restart_" + label, "GET", path) == expected, "Restart changed " + label)
        for index, source in enumerate(sources):
            require(call(f"restart_original_{index}", "GET", f"/api/v1/sources/{source['source_id']}/original") == originals[index],
                    "Restart changed original")
        backup = call("workspace_backup", "POST", "/api/v1/workspace/backups", {}, 201)
        require(backup.get("verified") is True, "Backup not verified by Core")
        preview = call("restore_preview", "POST", "/api/v2/workspace/restore/preview",
                       {"backup_id": backup["backup_id"], "expected_sha256": backup["sha256"]})
        require(preview.get("verified") is True and preview.get("compatible") is True, "Restore preview failed")
        backup_file = dev.safe_path(workspace / "backups" / backup["filename"])
        backup_file.relative_to(workspace)
        require(hashlib.sha256(backup_file.read_bytes()).hexdigest() == backup["sha256"], "Backup hash mismatch")
        receipt["backup"] = backup
        stop()
        independent = dev.safe_path(paths["artifacts"] / "independent-restore")
        independent.mkdir(exist_ok=False)
        operation = subprocess.run([str(candidate / "core/archeaxis-api.exe"), "--maintenance-restore",
                                    str(independent / "workspace.sqlite"), str(backup_file)],
                                   capture_output=True, text=True, encoding="utf-8", timeout=90,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        receipt["maintenance_restore"] = {"exit_code": operation.returncode, "stdout": operation.stdout,
                                           "stderr": operation.stderr}
        require(operation.returncode == 0, "Independent restore command failed")
        restored_metadata = json.loads(operation.stdout)
        require(restored_metadata.get("ok") and restored_metadata.get("verified"), "Independent restore not verified")
        child, base, token, _ = helper.hidden_start(office, candidate, independent, launcher)
        receipt["independent_restore_pid"] = child.pid
        receipt["independent_workspace"] = str(independent)
        for label, path, expected in [("main", main_path, current), ("history", main_path + "/versions/1", main),
                                      ("fixed_peer", peer_path + "/versions/1", peer), ("latest_peer", peer_path, newer_peer),
                                      ("graph", main_path + "/relations", graph),
                                      ("package", main_path + "/package", package), ("source_roundtrip", restored_path, restored)]:
            require(call("independent_" + label, "GET", path) == expected, "Independent restore changed " + label)
        for index, source in enumerate(sources):
            require(call(f"independent_original_{index}", "GET", f"/api/v1/sources/{source['source_id']}/original") == originals[index],
                    "Independent restore changed original")
        receipt.update({"status": "PASS", "main_document_id": main["document_id"], "main_version": 2,
                        "target_document_id": peer["document_id"], "target_current_version": 2,
                        "fixed_target_version": 1, "embedded_count": 2, "ordinary_relation_count": 1,
                        "verified_subset": ["original custody", "explicit fragment/source embed mapping", "strict runtime reason",
                                            "ordinary relation unchanged", "stale 409", "idempotence", "fixed v1 despite target v2",
                                            "unbundled document dependency refusal", "Source embed package roundtrip",
                                            "restart equality", "full workspace backup/independent restore equality"]})
    except Exception as error:
        receipt.update({"status": "FAIL", "error": f"{type(error).__name__}: {error}"})
    finally:
        if child is not None:
            try:
                stop()
            except Exception as error:
                receipt.update({"status": "FAIL", "cleanup_error": str(error)})
        try:
            require(assembler.verify(candidate) == manifest, "Candidate members changed")
            receipt["candidate_unchanged"] = True
        except Exception as error:
            receipt.update({"status": "FAIL", "candidate_unchanged": False, "identity_error": str(error)})
        checkpoint()
        print(json.dumps({"status": receipt["status"], "requests": len(receipt["steps"]), "receipt": str(output)}, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
