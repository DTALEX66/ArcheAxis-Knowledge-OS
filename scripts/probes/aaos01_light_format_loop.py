"""Independent Q12 authored samples through the complete staged Rust candidate.

Records each format separately; no Q06 receipts substitute for these assertions.
No Python authority server, direct database write, or fabricated export is used.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import time
import uuid
import zipfile
from email.message import EmailMessage
from pathlib import Path

import aaos01_office_runtime_loop as office

REPO = Path(__file__).resolve().parents[2]
A_SAMPLES = {
    "txt": ("golden-text-anchor.txt", "text", "Plaintext evidence anchor"),
    "pdf": ("golden-journey-evidence.pdf", "pdf", "Golden Journey Evidence"),
    "png": ("golden-screenshot-ocr.png", "image", "OCR GOLDEN ANCHOR"),
    "docx": ("golden-docx-anchor.docx", "office", "Document evidence anchor"),
    "xlsx": ("golden-xlsx-anchor.xlsx", "office", "Sheet evidence anchor"),
    "pptx": ("golden-pptx-anchor.pptx", "office", "Slide evidence anchor"),
    "html": ("golden-web-anchor.html", "html", "Web evidence anchor"),
    "canvas": ("golden-canvas-anchor.canvas", "canvas", "Golden Journey Evidence"),
    "srt": ("golden-subtitles-anchor.srt", "subtitles", "Golden Journey Evidence"),
    "zip": ("golden-archive-anchor.zip", "archive", ".txt"),
    "wav": ("golden-audio-anchor.wav", "media", "container\twav"),
    "mp4": ("golden-video-anchor.mp4", "media", "container\tiso-base-media"),
}


def samples():
    values = {
        "csv": b"name,value\nGolden,42\n",
        "tsv": b"name\tvalue\nGolden\t42\n",
        "json": b'{"lesson":{"title":"Golden","value":42}}',
        "jsonl": b'{"title":"Golden","value":42}\n{"title":"Second","value":7}\n',
        "yaml": b"lesson:\n  title: Golden\n  value: 42\n",
        "toml": b'[lesson]\ntitle = "Golden"\nvalue = 42\n',
        "xml": b'<lesson><title>Golden</title><value>42</value></lesson>',
    }
    message = EmailMessage()
    message["From"] = "author@example.invalid"
    message["To"] = "reader@example.invalid"
    message["Subject"] = "Golden"
    message["Message-ID"] = "<q12@example.invalid>"
    message.set_content("Golden body 42")
    message.add_attachment(b"known attachment bytes", maintype="application", subtype="octet-stream", filename="evidence.bin")
    values["eml"] = message.as_bytes()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="OEBPS/book.opf"/></rootfiles></container>')
        archive.writestr("OEBPS/book.opf", '<package xmlns="http://www.idpf.org/2007/opf"><metadata/><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="chapter"/></spine></package>')
        archive.writestr("OEBPS/chapter.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Golden</h1><p>Chapter body 42</p></body></html>')
        archive.writestr("OEBPS/nav.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><nav><ol><li><a href="chapter.xhtml">Golden</a></li></ol></nav></body></html>')
    values["epub"] = buffer.getvalue()
    values["corrupt_epub"] = b"invalid epub container"
    values["corrupt_yaml"] = b"!!python/object/apply:os.system ['must never run']"
    values["corrupt_xml"] = b'<!DOCTYPE lesson [<!ENTITY unsafe SYSTEM "file:///must-never-read">]><lesson>&unsafe;</lesson>'
    values["corrupt_jsonl"] = b'{"title":"Golden"}\n{not valid JSON}\n'
    return values


def check(record):
    snap = record["snapshot"]
    if record.get("corrupt"):
        assert snap["job"]["body"]["state"] == "failed", snap["job"]
        assert "AAK-WORKER-003" in str(snap["job"]["body"].get("error"))
        assert snap["text"]["status"] == 404
        return
    assert snap["job"]["body"]["state"] == "succeeded", snap["job"]
    assert all(snap[k]["status"] == 200 for k in ("quality", "text", "document_structure", "loss_report"))
    text = snap["text"]["body"]["content"]
    for key in ("text", "document_structure", "loss_report"):
        raw = snap[key]["body"]["content"].encode("utf-8")
        metadata = snap[key]["body"]["metadata"]
        assert metadata["byte_length"] == len(raw) and metadata["sha256"] == hashlib.sha256(raw).hexdigest()
    if record.get("wave") == "A":
        assert record["expected_text"] in text, text
    else:
        assert "Golden" in text and "42" in text
    anchors = json.loads(snap["document_structure"]["body"]["content"])
    assert anchors and all(0 <= x["char_start"] < x["char_end"] <= len(text) for x in anchors)
    loss = json.loads(snap["loss_report"]["body"]["content"])
    if record.get("wave") == "A":
        assert loss.get("engine") and loss.get("engine_version")
        assert loss.get("loss_note") and "losses" in loss
        if record["format"] == "png":
            params = loss["params"]
            assert params["input_transport"] == "stdin"
            assert params["input_sha256"] == record["input"]["sha256"]
            assert params["input_bytes"] == record["input"]["bytes"]
            regions = params["regions"]
            assert regions and all(region["bbox"]["w"] > 0 and region["bbox"]["h"] > 0 for region in regions)
            assert "OCR GOLDEN ANCHOR" in " ".join(region["text"] for region in regions)
            record["ocr_boxes_verified"] = len(regions)
        record["scope"] = "HEADER_PROBE_ONLY_NO_ASR" if record["format"] in {"wav", "mp4"} else "CONTENT_STRUCTURE_ANCHORS_CORE_RESTART"
        return
    facts = loss["params"]["format"]
    assert facts["format"] == record["format"] and facts["parsed"] is True, facts
    assert facts.get("locations"), "no native format location facts"
    assert any("Golden" in str(location.get("value")) for location in facts["locations"])
    if record["format"] in {"json", "yaml", "toml"}:
        assert any(location["path"] == "/lesson/title" and location["value"] == "Golden"
                   for location in facts["locations"])
    if record["format"] in {"csv", "tsv"}:
        assert any(location["row"] == 2 and location["column"] == 2 and location["value"] == "42"
                   for location in facts["locations"])
    if record["format"] == "jsonl":
        assert any(location["record"] == 2 and location["path"] == "/value" and location["value"] == 7
                   for location in facts["locations"])
    if record["format"] == "xml":
        assert any(location["path"] == "/lesson[1]/value[1]" and location["value"] == "42"
                   for location in facts["locations"])
    if record["format"] == "eml":
        assert facts["headers"]["Message-ID"] == "<q12@example.invalid>"
        assert facts["attachments"][0]["sha256"] == hashlib.sha256(b"known attachment bytes").hexdigest()
        assert facts["attachments"][0]["name"] == "evidence.bin"
        assert any("attachments" in note for note in loss["losses"])
    if record["format"] == "epub":
        assert facts["toc"][0] == {"href": "chapter.xhtml", "title": "Golden"}
        assert facts["locations"][0]["chapter"] == 1
        assert facts["assets"] and all(x["sha256"] for x in facts["assets"])
    assert loss.get("loss_note") and "losses" in loss
    record["native_locations"] = facts["locations"]


def archive_members(client, base, token, source_id, payload):
    """Run the jobs production already queued, then verify their own CAS/output."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        expected = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    status, members = client.call(base, "GET", f"/api/v1/sources/{source_id}/members", token)
    assert status == 200 and members["member_count"] == len(expected), members
    results = []
    for member in members["members"]:
        raw = expected[member["member"]]
        assert hashlib.sha256(raw).hexdigest() == member["sha256"]
        status, original = client.call(base, "GET", f"/api/v1/sources/{member['source_id']}/original", token)
        assert status == 200 and base64.b64decode(original["content_base64"]) == raw
        job = member["job_id"]
        assert job, "readable golden member must have a production-enqueued job"
        status, queued = client.call(base, "GET", f"/api/v1/jobs/{job}", token)
        assert status == 200 and queued["state"] == "queued", queued
        status, executed = client.call(base, "POST", f"/api/v1/jobs/{job}/executions", token,
            {"deadline_ms": 30000}, extra_headers={"idempotency-key": job})
        assert status == 202, executed
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            _, state = client.call(base, "GET", f"/api/v1/jobs/{job}", token)
            if state.get("state") in ("succeeded", "failed", "rejected", "cancelled"):
                break
            time.sleep(.1)
        snapshot = office.capture(client, base, token, job)
        child = {"snapshot": snapshot, "wave": "A", "expected_text": raw.decode("utf-8"), "format": "txt"}
        check(child)
        assert snapshot["text"]["body"]["content"] == raw.decode("utf-8")
        results.append({"job_id": job, "source_id": member["source_id"], "sha256": member["sha256"], "snapshot": snapshot})
    status, members = client.call(base, "GET", f"/api/v1/sources/{source_id}/members", token)
    assert status == 200 and members["readable_count"] == len(expected)
    return {"members": members, "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--wave", choices=("A", "B"), default="B")
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    work = REPO / ".project-local/task-runtime/aaos01-light" / uuid.uuid4().hex
    work.mkdir(parents=True)
    launcher = office.load("q12_launcher", REPO / "scripts/release/backend_launcher.py")
    client = office.load("q12_client", REPO / "shared/core_client.py")
    receipt = {"ok": False, "task": "Q06" if args.wave == "A" else "Q12", "wave": args.wave,
               "sample_class": "PROJECT_AUTHORED_FIXTURES_REAL_CORE_EXECUTION",
               "evidence_scope": "CORE_WORKER_API_AND_FILE_READBACK_NOT_INSTALLED_UI",
               "limitations": ["Native Obsidian application not launched",
                                "EPUB source chapter/paragraph facts asserted against the fixture; Core native locator remains unverified",
                                "Audio/video use media.probe only; no decoding, ASR or time-range content claim"],
               "candidate_manifest": office.identity(candidate / "backend-runtime-manifest.json"),
               "worker_text": office.identity(candidate / "workers/document/worker_text.py"),
               "results": [], "export_scope": "Per-format Rust document files for wave B; native format receipts preserved as unknown nodes"}
    receipt["core"] = office.identity(candidate / "core/archeaxis-api.exe")
    receipt["worker_profile_identity"] = office.identity(candidate / "worker-profile.json")
    receipt["lockfile"] = office.identity(REPO / "uv.lock")
    dev = office.load("light_dev", REPO / "scripts/runtime/dev.py")
    dirty, patch_sha = dev.worktree_identity(REPO)
    receipt["source"] = {"commit": dev.git(REPO, "rev-parse", "HEAD"), "dirty": dirty, "patch_sha256": patch_sha}
    child = None
    try:
        child, base, token, worker = office.start(candidate, work, launcher)
        receipt["worker_profile"] = worker
        selected = ({key: (REPO / "tests/fixtures/golden" / entry[0]).read_bytes()
                     for key, entry in A_SAMPLES.items()} if args.wave == "A" else samples())
        for label, payload in selected.items():
            extension = label.removeprefix("corrupt_")
            record = {"format": extension, "wave": args.wave, "corrupt": label.startswith("corrupt_")}
            kind = A_SAMPLES[label][1] if args.wave == "A" else "text"
            if args.wave == "A":
                record["expected_text"] = A_SAMPLES[label][2]
            receipt["results"].append(record)
            try:
                path = work / f"{label}.{extension}"
                path.write_bytes(payload)
                record["input"] = office.identity(path)
                status, imported = client.call(base, "POST", "/api/v1/imports", token,
                    client.import_request(path.name, payload))
                record["import"] = {"status": status, "body": imported}
                assert status == 202
                assert imported["sha256"] == record["input"]["sha256"]
                job = "light-" + uuid.uuid4().hex
                record["job_id"] = job
                status, queued = client.call(base, "POST", "/api/v1/jobs", token,
                    {"job_id": job, "kind": kind, "input_ref": imported["source_id"]})
                assert status == 202, queued
                status, executed = client.call(base, "POST", f"/api/v1/jobs/{job}/executions", token,
                    {"deadline_ms": 30000}, extra_headers={"idempotency-key": job})
                assert status == 202, executed
                deadline = time.monotonic() + 35
                while time.monotonic() < deadline:
                    _, body = client.call(base, "GET", f"/api/v1/jobs/{job}", token)
                    if body.get("state") in ("succeeded", "failed", "rejected", "cancelled"):
                        break
                    time.sleep(.1)
                record["snapshot"] = office.capture(client, base, token, job)
                check(record)
                if args.wave == "A" and extension == "zip":
                    record["archive_expansion"] = archive_members(client, base, token, imported["source_id"], payload)
                if args.wave == "B" and not record["corrupt"]:
                    projected = record["snapshot"]["text"]["body"]["content"]
                    loss = json.loads(record["snapshot"]["loss_report"]["body"]["content"])
                    needle = b"Golden body 42" if extension == "eml" else b"Golden"
                    if extension == "epub":
                        anchor_body = {"revision": imported["sha256"],
                                       "position": json.dumps({"type": "epub", "chapter": 1, "paragraph": 1,
                                                               "path": loss["params"]["format"]["locations"][0]["path"]})}
                    else:
                        offset = payload.index(needle)
                        anchor_body = {"revision": imported["sha256"],
                                       "position": json.dumps({"type": "text", "start": offset, "end": offset + len(needle)}),
                                       "checksum": hashlib.sha256(needle).hexdigest()}
                    status, anchor = client.call(base, "POST", f"/api/v1/sources/{imported['source_id']}/anchors", token, anchor_body)
                    assert status == 201, anchor
                    assert anchor["location_status"] == ("unverified" if extension == "epub" else "located")
                    record["evidence_anchor"] = anchor
                    editor = {"type": "doc", "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": projected}]},
                        {"type": "formatReceipt", "attrs": {"job_id": job, "loss_receipt": loss}}]}
                    status, document = client.call(base, "POST", "/api/v1/documents", token,
                        {"source_id": imported["source_id"], "source_revision": imported["sha256"],
                         "title": extension + " sample", "editor_json": editor})
                    assert status == 201, document
                    record["document_id"] = document["document_id"]
                    status, exported = client.call(base, "GET", f"/api/v1/documents/{document['document_id']}/export?format=markdown", token)
                    assert status == 200, exported
                    directory = work / "export" / label
                    directory.mkdir(parents=True)
                    assert {file["path"] for file in exported["files"]} == {"document.md", "manifest.json"}
                    for file in exported["files"]:
                        (directory / file["path"]).write_text(file["content"], encoding="utf-8", newline="\n")
                    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
                    assert manifest["document"]["source_revision"] == imported["sha256"]
                    assert manifest["anchors"][0]["anchor_id"] == anchor["anchor_id"]
                    assert manifest["document"]["editor_json"]["content"][1]["attrs"]["loss_receipt"] == loss
                    assert projected in (directory / "document.md").read_text(encoding="utf-8")
                    assert manifest["loss"]
                    record["export"] = exported
                    record["export_file_readback"] = True
                record["ok"] = True
            except Exception as error:
                record["ok"] = False
                record["error"] = f"{type(error).__name__}: {error}"
        launcher.stop(child)
        child = None
        child, base, token, _ = office.start(candidate, work, launcher)
        for record in receipt["results"]:
            if "snapshot" in record:
                record["restart_equal"] = office.capture(client, base, token, record["job_id"]) == record["snapshot"]
                record["ok"] = record["ok"] and record["restart_equal"]
                status, original = client.call(base, "GET", f"/api/v1/sources/{record['import']['body']['source_id']}/original", token)
                record["cas_restart_equal"] = status == 200 and hashlib.sha256(base64.b64decode(original["content_base64"])).hexdigest() == record["input"]["sha256"]
                record["ok"] = record["ok"] and record["cas_restart_equal"]
                if "archive_expansion" in record:
                    expansion = record["archive_expansion"]
                    status, members = client.call(base, "GET", f"/api/v1/sources/{record['import']['body']['source_id']}/members", token)
                    assert status == 200 and members == expansion["members"], "container relations changed after restart"
                    for member in expansion["results"]:
                        assert office.capture(client, base, token, member["job_id"]) == member["snapshot"], "member outputs changed after restart"
                        status, original = client.call(base, "GET", f"/api/v1/sources/{member['source_id']}/original", token)
                        assert status == 200 and hashlib.sha256(base64.b64decode(original["content_base64"])).hexdigest() == member["sha256"], "member CAS changed after restart"
                    expansion["restart_equal"] = True
                if "export" in record:
                    status, exported = client.call(base, "GET", f"/api/v1/documents/{record['document_id']}/export?format=markdown", token)
                    record["export_restart_equal"] = status == 200 and exported == record["export"]
                    record["ok"] = record["ok"] and record["export_restart_equal"]
        receipt["ok"] = all(x["ok"] for x in receipt["results"])
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        if child is not None:
            launcher.stop(child)
        receipt["verified_content_extensions"] = [record["format"] for record in receipt["results"]
            if record.get("ok") and not record.get("corrupt")
            and record.get("scope") != "HEADER_PROBE_ONLY_NO_ASR"]
        receipt["verified_content_extension_count"] = len(receipt["verified_content_extensions"])
        receipt["metadata_probe_extensions"] = [record["format"] for record in receipt["results"]
            if record.get("ok") and record.get("scope") == "HEADER_PROBE_ONLY_NO_ASR"]
        receipt["verified_negative_sample_count"] = sum(bool(record.get("ok") and record.get("corrupt")) for record in receipt["results"])
        output = work / "receipt.json"
        output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": receipt["ok"], "receipt": str(output),
                          "results": [{k: x.get(k) for k in ("format", "ok", "error")} for x in receipt["results"]]}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
