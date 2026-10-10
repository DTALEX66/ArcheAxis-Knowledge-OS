"""Real Rust document export and file readback for a limited Q10 profile.

Does not qualify Obsidian's native application: export files are independently
read from disk, while that application acceptance remains explicit NOT_EXECUTED.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import uuid
from pathlib import Path

import aaos01_office_runtime_loop as office

REPO = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    work = REPO / ".project-local/task-runtime/aaos01-exchange" / uuid.uuid4().hex
    work.mkdir(parents=True)
    launcher = office.load("exchange_launcher", REPO / "scripts/release/backend_launcher.py")
    client = office.load("exchange_client", REPO / "shared/core_client.py")
    receipt = {
        "ok": False,
        "task": "Q10",
        "scope": "RUST_API_EXPORT_AND_FILE_READBACK",
        "external_application": {
            "state": "NOT_EXECUTED",
            "reason": "Native Obsidian application not launched",
        },
        "candidate_manifest": office.identity(candidate / "backend-runtime-manifest.json"),
        "formats": [],
    }
    receipt["core"] = office.identity(candidate / "core/archeaxis-api.exe")
    dev = office.load("exchange_dev", REPO / "scripts/runtime/dev.py")
    dirty, patch_sha = dev.worktree_identity(REPO)
    receipt["source"] = {
        "commit": dev.git(REPO, "rev-parse", "HEAD"),
        "dirty": dirty,
        "patch_sha256": patch_sha,
    }
    child = None
    try:
        child, base, token, _ = office.start(candidate, work, launcher)
        payload = "# 星环证据\nGolden source 42\n".encode()
        status, imported = client.call(
            base, "POST", "/api/v1/imports", token, client.import_request("source.md", payload)
        )
        assert status == 202 and imported["sha256"] == hashlib.sha256(payload).hexdigest()
        receipt["import"] = imported
        start = payload.index(b"Golden")
        excerpt = b"Golden source 42"
        status, anchor = client.call(
            base,
            "POST",
            f"/api/v1/sources/{imported['source_id']}/anchors",
            token,
            {
                "revision": imported["sha256"],
                "position": json.dumps(
                    {"type": "text", "start": start, "end": start + len(excerpt)}
                ),
                "checksum": hashlib.sha256(excerpt).hexdigest(),
            },
        )
        assert status == 201 and anchor["location_status"] == "located", anchor
        receipt["anchor"] = anchor
        editor = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "星环 Golden source 42"}],
                },
                {
                    "type": "futureFigure",
                    "attrs": {"retained": "unknown node payload"},
                    "content": [{"type": "text", "text": "Unknown node evidence"}],
                },
            ],
        }
        status, document = client.call(
            base,
            "POST",
            "/api/v1/documents",
            token,
            {
                "source_id": imported["source_id"],
                "source_revision": imported["sha256"],
                "title": "星环 Exchange",
                "editor_json": editor,
            },
        )
        assert status == 201, document
        receipt["document"] = document
        doc_id = document["document_id"]
        for format_name in ("markdown", "obsidian"):
            status, exported = client.call(
                base, "GET", f"/api/v1/documents/{doc_id}/export?format={format_name}", token
            )
            assert status == 200, exported
            assert {x["path"] for x in exported["files"]} == {"document.md", "manifest.json"}
            destination = work / "export" / format_name
            destination.mkdir(parents=True)
            for file in exported["files"]:
                (destination / file["path"]).write_text(
                    file["content"], encoding="utf-8", newline="\n"
                )
            manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
            markdown = (destination / "document.md").read_text(encoding="utf-8")
            assert manifest["document"] == document
            assert manifest["document"]["source_revision"] == imported["sha256"]
            assert (
                manifest["document"]["editor_json"]["content"][1]["attrs"]["retained"]
                == "unknown node payload"
            )
            assert manifest["anchors"][0]["anchor_id"] == anchor["anchor_id"]
            assert manifest["anchors"][0]["source_revision"] == imported["sha256"]
            assert manifest["loss"] and "structured" in manifest["loss"][0]["message"]
            assert (
                manifest["projection_sha256"]
                == hashlib.sha256(document["text_projection"].encode()).hexdigest()
            )
            assert document["text_projection"] in markdown and anchor["anchor_id"] in markdown
            assert "[Immutable source](archeaxis://" not in markdown
            assert "[Evidence anchor](archeaxis://" not in markdown
            records = [
                json.loads(line[4:]) for line in markdown.splitlines() if line.startswith("    {")
            ]
            assert records == [
                {"source_id": imported["source_id"], "source_revision": imported["sha256"]},
                *manifest["anchors"],
            ]
            assert any(
                item["code"] == "external_navigation_unavailable" for item in manifest["loss"]
            )
            if format_name == "obsidian":
                assert markdown.startswith("---\n") and "archeaxis_source_revision:" in markdown
            receipt["formats"].append(
                {
                    "format": format_name,
                    "ok": True,
                    "export": exported,
                    "files": [
                        office.identity(destination / name)
                        for name in ("document.md", "manifest.json")
                    ],
                }
            )
        status, refused = client.call(
            base, "GET", f"/api/v1/documents/{doc_id}/export?format=../../outside", token
        )
        assert status == 400, refused
        receipt["unsafe_profile_refused"] = True
        status, original = client.call(
            base, "GET", f"/api/v1/sources/{imported['source_id']}/original", token
        )
        assert status == 200 and base64.b64decode(original["content_base64"]) == payload
        receipt["cas_original_equal"] = True
        launcher.stop(child)
        child = None
        child, base, token, _ = office.start(candidate, work, launcher)
        for record in receipt["formats"]:
            status, readback = client.call(
                base, "GET", f"/api/v1/documents/{doc_id}/export?format={record['format']}", token
            )
            assert status == 200 and readback == record["export"]
            record["restart_equal"] = True
        receipt["ok"] = True
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        if child is not None:
            launcher.stop(child)
        path = work / "receipt.json"
        path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            json.dumps({"ok": receipt["ok"], "receipt": str(path), "error": receipt.get("error")})
        )
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
