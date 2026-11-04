"""J1 mixed-format folder chain over a real Core: batch, failure, resume, knowledge, export, backup, restore.

The closed loop's J1 row asks for a folder of mixed common materials to be processed
file by file with failures localised, then read/edited, searched and cited, turned
into knowledge, restarted, continued, exported, backed up and restored. This probe
runs that sequence against one real Core process and its configured workers.

The folder is built by the same generator the four-format probe uses, plus a text
note, one file whose extension no kind maps, one file the Core accepts but whose
worker must fail, and a private-state directory that must be excluded. The batch
driver is the shipped `scripts/ingest/directory_batch.py`; this probe only executes
the jobs it enqueued and records what the Core answered.

Nothing here is installed, rendered or model-produced. Media, OCR and live formula
calculation stay out; those have their own probes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path

import aaos01_common_formats_runtime_loop as formats
import aaos01_office_runtime_loop as office

REPO = Path(__file__).resolve().parents[2]
DOC_FORMATS = ("docx", "xlsx", "pptx", "pdf")
TERMINAL = ("succeeded", "failed", "cancelled", "rejected")

FIX_DOCX = r"""
import sys, zipfile
from pathlib import Path
target = Path(sys.argv[1])
xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
       '<w:body><w:p><w:r><w:t>修复后的DOCX正文</w:t></w:r></w:p></w:body></w:document>')
with zipfile.ZipFile(target, "w") as archive:
    archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    archive.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rMain" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    archive.writestr("word/document.xml", xml)
"""


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_extras(corpus: Path, python: Path) -> None:
    """Add the text note, the unmappable file, the corrupt container and private state."""
    (corpus / "notes.md").write_text(
        "# 批次笔记\n\n混合资料批次记录：可引用短语 mappable-phrase-41。\n", encoding="utf-8")
    (corpus / "mystery.qzx").write_text("an extension nobody can name\n", encoding="utf-8")
    (corpus / "corrupt.docx").write_bytes(b"deliberately invalid docx container")
    (corpus / ".git").mkdir(exist_ok=True)
    (corpus / ".git" / "config").write_text("[core]\n", encoding="utf-8")


def fix_docx(corpus: Path, python: Path) -> Path:
    target = corpus / "corrupt.docx"
    result = subprocess.run([str(python), "-B", "-I", "-c", FIX_DOCX, str(target)],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stderr
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()

    dev = office.load("j1_batch_dev", REPO / "scripts/runtime/dev.py")
    launcher = office.load("j1_batch_launcher", REPO / "scripts/release/backend_launcher.py")
    client = office.load("j1_batch_client", REPO / "shared/core_client.py")
    batch = office.load("j1_batch_driver", REPO / "scripts/ingest/directory_batch.py")

    paths = dev.layout(REPO)
    dev.prepare(paths)
    work, artifacts = paths["run"], paths["artifacts"]
    corpus = work / "corpus"
    manifest = artifacts / "batch-manifest.jsonl"
    receipt = {
        "ok": False, "task": "J1", "materials": "SYNTHETIC_AUTHORED",
        "evidence_level": "REAL_CORE_BATCH_FOLDER_CHAIN",
        "limits": ["No installed UI or source-application rendering", "Text PDF only; OCR separate",
                   "Formula text and cached chart data are not live calculation",
                   "Batch failure localisation is the job terminal state the Core reports"],
        "candidate": str(candidate), "formats": [], "runs": [],
    }
    child = None
    try:
        profile = launcher.load_profile(candidate)
        dirty, patch_sha = dev.worktree_identity(REPO)
        receipt["source"] = {"commit": dev.git(REPO, "rev-parse", "HEAD"), "dirty": dirty,
                             "patch_sha256": patch_sha, "changes": office.source_changes(dev)}
        receipt["core"] = office.identity(candidate / "core/archeaxis-api.exe")
        receipt["manifest"] = office.identity(candidate / "backend-runtime-manifest.json")
        receipt["interpreter"] = office.identity(profile["python"])
        receipt["worker_profile"] = office.identity(candidate / "worker-profile.json")

        generated = subprocess.run([str(profile["python"]), "-B", "-I", "-c", formats.GENERATOR, str(corpus)],
                                   capture_output=True, text=True, encoding="utf-8", timeout=60)
        receipt["generator"] = {"exit": generated.returncode, "stdout": generated.stdout,
                                "stderr": generated.stderr}
        assert generated.returncode == 0, "candidate fixture generation failed"
        build_extras(corpus, profile["python"])

        child, base, token, _ = office.start(candidate, work, launcher)

        def call(method, path, body=None, expected=200, headers=None):
            status, result = client.call(base, method, path, token, body, extra_headers=headers)
            allowed = expected if isinstance(expected, tuple) else (expected,)
            assert status in allowed, {"path": path, "status": status, "result": result}
            return result

        calls = []

        def counted(method, path, body=None):
            calls.append(path)
            return client.call(base, method, path, token, body)

        def run_batch():
            before = len(calls)
            result = batch.run_batch(corpus, core_call=counted, manifest_path=manifest, job_prefix="j1")
            result["core_calls"] = len(calls) - before
            return result

        def execute(job_id):
            call("POST", f"/api/v1/jobs/{job_id}/executions", {"deadline_ms": 180000},
                 expected=202, headers={"idempotency-key": job_id})
            deadline = time.monotonic() + 200
            while True:
                state = call("GET", f"/api/v1/jobs/{job_id}")
                if state["state"] in TERMINAL:
                    return state
                assert time.monotonic() < deadline, f"job {job_id} did not settle"
                time.sleep(.1)

        def locate(source, job_snapshot, position, native_pdf):
            text = job_snapshot["text"]["body"]["content"]
            excerpt = text[position["char_start"]:position["char_end"]]
            locator = {"type": "pdf_line" if native_pdf else "worker_structure",
                       "job_id": job_snapshot["job_id"],
                       "attempt": job_snapshot["job"]["body"]["attempt"],
                       "kind": position["kind"], "path": position["path"]}
            if native_pdf:
                locator.update({"char_start": position["char_start"], "char_end": position["char_end"],
                                "result_sha256": job_snapshot["document_structure"]["body"]["metadata"]["sha256"]})
            body = {"revision": source["sha256"], "checksum": sha(excerpt.encode()),
                    "position": json.dumps(locator)}
            path = f"/api/v1/sources/{source['source_id']}/anchors"
            anchor = call("POST", path, body, expected=201)
            assert anchor["location_status"] == "located"
            resolution = call("GET", path + f"/{anchor['anchor_id']}/resolve")
            assert resolution["status"] == "CURRENT", resolution
            return {"anchor": anchor, "resolution": resolution}

        # 1. The first folder pass only imports and enqueues; the Core refuses no import.
        first = run_batch()
        receipt["runs"].append({"pass": 1, "counts": first["counts"], "core_calls": first["core_calls"],
                                "excluded": first["excluded_paths"]})
        assert first["counts"]["refused"] == 0
        assert first["counts"]["imported_no_job"] == 1
        assert first["counts"]["enqueued"] == 6
        assert any(".git" in row for row in first["excluded_paths"])

        # 2. Every enqueued job is executed; the corrupt container must fail in the
        #    Core's own words, the rest must produce readable projections and anchors.
        entries = {entry["path"]: entry for entry in first["entries"]}
        for path, entry in entries.items():
            if entry["status"] != "enqueued":
                continue
            state = execute(entry["job_id"])
            snapshot = office.capture(client, base, token, entry["job_id"])
            extension = Path(path).suffix.lower().lstrip(".")
            original = call("GET", f"/api/v1/sources/{entry['source_id']}/original")
            assert sha(base64.b64decode(original["content_base64"])) == entry["sha256"]
            if path == "corrupt.docx":
                assert state["state"] == "failed" and state.get("error"), state
                assert snapshot["text"]["status"] == 404, "failed sample published text"
                receipt["formats"].append({"path": path, "kind": entry["kind"], "job_id": entry["job_id"],
                                           "state": state["state"], "error": state["error"],
                                           "failure_localised": True})
                continue
            assert state["state"] == "succeeded", state
            if extension in DOC_FORMATS:
                formats.validate_outputs(extension, snapshot)
                reported = (json.loads(snapshot["document_structure"]["body"]["content"]) if extension == "pdf"
                            else json.loads(snapshot["loss_report"]["body"]["content"])["params"]["worker_structure"])
                positions = [p for p in reported
                             if p.get("path") and snapshot["text"]["body"]["content"][p["char_start"]:p["char_end"]].strip()]
                assert positions, f"{extension} reported no locatable structure"
                located = [locate({"source_id": entry["source_id"], "sha256": entry["sha256"]},
                                  {**snapshot, "job_id": entry["job_id"]}, p, extension == "pdf")
                           for p in positions[:2]]
            else:
                text = snapshot["text"]["body"]["content"]
                assert "mappable-phrase-41" in text, text
                located = []
            receipt["formats"].append({"path": path, "kind": entry["kind"], "job_id": entry["job_id"],
                                       "state": state["state"], "source_id": entry["source_id"],
                                       "original_sha256": entry["sha256"], "located": located})

        # 3. A second pass over the unchanged folder must cost the Core nothing.
        second = run_batch()
        receipt["runs"].append({"pass": 2, "counts": second["counts"], "core_calls": second["core_calls"]})
        assert second["core_calls"] == 0
        assert second["counts"]["skipped_unchanged"] == 7

        # 4. Fixing one file must re-process exactly that file, so the task continues.
        fix_docx(corpus, profile["python"])
        third = run_batch()
        receipt["runs"].append({"pass": 3, "counts": third["counts"], "core_calls": third["core_calls"]})
        assert third["counts"]["enqueued"] == 1 and third["counts"]["skipped_unchanged"] == 6
        fixed = next(entry for entry in third["entries"] if entry["status"] == "enqueued")
        state = execute(fixed["job_id"])
        assert state["state"] == "succeeded", state
        receipt["continued_after_fix"] = {"path": fixed["path"], "job_id": fixed["job_id"],
                                           "state": state["state"]}

        # 5. The text note becomes accepted knowledge through the ordinary transform path.
        note = entries["notes.md"]
        transform = call("GET", f"/api/v1/sources/{note['source_id']}/jobs/{note['job_id']}/transform")
        content = transform["content"]
        created = call("POST", "/api/v1/knowledge-items/from-transform", {
            "knowledge_type": "FACTUAL_CLAIM", "body": content, "source_id": note["source_id"],
            "job_id": note["job_id"], "transform_id": transform["transform_id"],
            "selection_start_utf16": 0,
            "selection_end_utf16": len(content.encode("utf-16-le")) // 2, "quote": content,
        }, expected=(200, 201))
        knowledge_id = created["knowledge_id"]
        call("POST", f"/api/v1/knowledge-items/{knowledge_id}/review-decisions",
             {"action": "accepted", "reviewer": "owner"}, expected=(200, 201))
        knowledge = call("GET", f"/api/v1/knowledge-items/{knowledge_id}/v3")
        receipt["knowledge"] = {"knowledge_id": knowledge_id, "state": "ACCEPTED",
                                "quote_sha256": sha(content.encode())}

        # 6. Search reaches both the accepted knowledge and the saved document.
        found = call("GET", "/api/v1/search?q=mappable-phrase-41")
        assert any(item.get("knowledge_id") == knowledge_id for item in found["items"]), found

        # 7. Read and edit through the ordinary document routes, then export it.
        editor = {"type": "doc", "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "批次材料编辑前正文 mappable-phrase-41"}]}]}
        document = call("POST", "/api/v1/documents", {
            "create_request_id": "j1-" + uuid.uuid4().hex, "title": "J1 批次材料",
            "editor_json": editor}, expected=201)
        doc_path = f"/api/v1/documents/{document['document_id']}"
        edited = call("PUT", doc_path + "/draft", {"expected_version": document["version"], "editor_json": {
            "type": "doc", "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "批次材料编辑后正文 edited-phrase-77"}]}]}})
        found_after_edit = call("GET", "/api/v1/search?q=edited-phrase-77")
        assert any(row.get("document_id") == document["document_id"] for row in found_after_edit["documents"]), \
            found_after_edit
        exported = call("GET", doc_path + "/export?format=markdown")
        files = {item["path"]: item["content"] for item in exported["files"]}
        assert set(files) == {"document.md", "manifest.json"}
        for name, content in files.items():
            (artifacts / name).write_text(content, encoding="utf-8")

        # 8. Back up, then restore into an independent database and read it back there.
        backup = call("POST", "/api/v1/workspace/backups", {}, expected=201)
        assert backup["verified"] is True, backup
        listed = call("GET", "/api/v1/workspace/backups")
        assert backup in listed["backups"]
        preview = call("POST", "/api/v2/workspace/restore/preview",
                       {"backup_id": backup["backup_id"], "expected_sha256": backup["sha256"]})
        assert preview["verified"] is True and preview["compatible"] is True, preview
        artifact = work / "backups" / backup["filename"]
        assert artifact.is_file(), artifact

        # 9. Restart: the same objects, anchors, export, knowledge and batch state read back.
        launcher.stop(child)
        child = None
        child, base, token, _ = office.start(candidate, work, launcher)
        receipt["restart_pid"] = child.pid
        assert call("GET", doc_path) == edited
        assert call("GET", doc_path + "/export?format=markdown") == exported
        assert call("GET", f"/api/v1/knowledge-items/{knowledge_id}/v3") == knowledge
        restored_batch = batch.read_manifest(manifest)
        assert restored_batch == first["entries"] + second["entries"] + third["entries"]
        for record in receipt["formats"]:
            after = office.capture(client, base, token, record["job_id"])
            assert after["job"]["status"] == 200
            for located in record.get("located", []):
                actual = call("GET", f"/api/v1/sources/{record['source_id']}/anchors/"
                                    f"{located['anchor']['anchor_id']}/resolve")
                assert actual == located["resolution"]
        receipt["restart_equal"] = True

        # 10. The restore artifact becomes a second database; a fresh Core serves it.
        restored_dir = work / "restored"
        restored_dir.mkdir(parents=True, exist_ok=True)
        restored = subprocess.run([str(candidate / "core/archeaxis-api.exe"),
                                   "--maintenance-restore", str(restored_dir / "workspace.sqlite"), str(artifact)],
                                  capture_output=True, text=True, timeout=180)
        restored_receipt = json.loads(restored.stdout) if restored.stdout.strip() else {}
        assert restored.returncode == 0 and restored_receipt.get("ok") is True, restored_receipt
        launcher.stop(child)
        child = None
        child, base, token, _ = office.start(candidate, restored_dir, launcher)
        receipt["restored"] = {"verified": restored_receipt.get("verified"), "pid": child.pid}
        assert call("GET", doc_path) == edited
        assert call("GET", f"/api/v1/knowledge-items/{knowledge_id}/v3") == knowledge
        restored_search = call("GET", "/api/v1/search?q=edited-phrase-77")
        assert any(row.get("document_id") == document["document_id"] for row in restored_search["documents"])

        receipt["batch_state"] = {"manifest": str(manifest),
                                  "lines": len(batch.read_manifest(manifest)),
                                  "passes": [run["counts"] for run in receipt["runs"]]}
        receipt["ok"] = True
        receipt["qualification"] = "INTEGRATED_MIXED_FOLDER_BATCH_KNOWLEDGE_EXPORT_BACKUP_RESTORE"
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        if child is not None:
            try:
                launcher.stop(child)
            except Exception as error:
                receipt["ok"] = False
                receipt["cleanup_error"] = f"{type(error).__name__}: {error}"
        receipt["source_consistent"] = (
            dev.worktree_identity(REPO) == (dirty, patch_sha) if "source" in receipt else False
        )
        if not receipt["source_consistent"]:
            receipt["ok"] = False
            receipt["qualification"] = "NOT_QUALIFIED_SOURCE_CHANGED_OR_UNVERIFIED"
        output = artifacts / "j1-batch-folder.json"
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": receipt["ok"], "receipt": str(output), "error": receipt.get("error")}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
