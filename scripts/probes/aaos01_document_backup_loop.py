"""Real candidate document autosave, independent backup restore and continued editing.

Authored evidence only; this does not substitute human review or installed UI usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import uuid
from pathlib import Path

from aaos01_office_runtime_loop import REPO, identity, load, start


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    work = REPO / ".project-local/task-runtime/aaos01-document-backup" / uuid.uuid4().hex
    work.mkdir(parents=True)
    original, restored = work / "original", work / "independent-restored"
    original.mkdir()
    restored.mkdir()
    launcher = load("aaos_document_launcher", REPO / "scripts/release/backend_launcher.py")
    client = load("aaos_document_client", REPO / "shared/core_client.py")
    receipt = {
        "ok": False,
        "evidence_level": "REAL_CANDIDATE_CORE_AUTHORED_MATERIAL",
        "candidate": str(candidate),
        "core": identity(candidate / "core/archeaxis-api.exe"),
        "results": [],
        "limitations": ["Not installed UI/IME qualification", "No human review acceptance"],
    }
    child = None
    try:
        child, base, token, worker = start(candidate, original, launcher)

        def call(method, path, body=None, expected=200):
            status, result = client.call(base, method, path, token, body)
            assert status == expected, (method, path, status, result)
            return result

        raw = "独立恢复后仍可继续编辑。AAOS document backup evidence.\n".encode()
        import base64

        source = call(
            "POST", "/api/v1/imports", client.import_request("backup-evidence.txt", raw), 202
        )
        editor = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"block_id": "evidence-block"},
                    "content": [{"type": "text", "text": "中文保存 evidence"}],
                },
                {
                    "type": "unknownEvidence",
                    "attrs": {"block_id": "preserved-block", "opaque": {"x": 1}},
                },
            ],
        }
        document = call(
            "POST",
            "/api/v1/documents",
            {
                "source_id": source["source_id"],
                "source_revision": hashlib.sha256(raw).hexdigest(),
                "title": "恢复证据",
                "editor_json": editor,
            },
            201,
        )
        doc_id = document["document_id"]
        prefix = "/api/v1/documents/" + doc_id
        editor["content"][0]["content"][0]["text"] = "第二版中文保存 evidence"
        updated = call(
            "PUT",
            prefix + "/draft",
            {"expected_version": document["version"], "editor_json": editor},
        )
        call(
            "PUT",
            prefix + "/draft",
            {"expected_version": document["version"], "editor_json": editor},
            409,
        )
        assert updated["blocks"][0]["block_id"] == "evidence-block"
        assert updated["blocks"][1]["codec_status"] == "preserved_unknown"
        before = call("GET", prefix)
        original_bytes = call("GET", f"/api/v1/sources/{source['source_id']}/original")
        assert base64.b64decode(original_bytes["content_base64"]) == raw
        # Backup inside the live writer's Store; a second CLI writer is intentionally forbidden.
        backup_metadata = call("POST", "/api/v1/workspace/backups", {}, 201)
        assert child.poll() is None, "live backup must not restart the writer"
        backup = original / "backups" / backup_metadata["filename"]
        core = candidate / "core/archeaxis-api.exe"
        receipt["backup"] = backup_metadata
        assert identity(backup)["sha256"] == backup_metadata["sha256"]
        launcher.stop(child)
        child = None
        operation = subprocess.run(
            [str(core), "--maintenance-restore", str(restored / "workspace.sqlite"), str(backup)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
        )
        receipt["restore_command"] = {
            "exit": operation.returncode,
            "stdout": operation.stdout,
            "stderr": operation.stderr,
        }
        assert operation.returncode == 0, receipt["restore_command"]
        receipt["restore"] = json.loads(operation.stdout)
        assert receipt["restore"]["ok"] and receipt["restore"]["verified"]
        child, base, token, _ = start(candidate, restored, launcher)
        assert call("GET", prefix) == before
        assert call("GET", f"/api/v1/sources/{source['source_id']}/original") == original_bytes
        older = call("GET", prefix + f"/versions/{document['version']}")
        assert older["editor_json"] == document["editor_json"]
        editor["content"][0]["content"][0]["text"] = "独立副本继续保存"
        continued = call(
            "PUT", prefix + "/draft", {"expected_version": before["version"], "editor_json": editor}
        )
        assert continued["version"] == before["version"] + 1
        receipt["document"] = {"id": doc_id, "before": before, "after_independent_edit": continued}
        launcher.stop(child)
        child = None
        child, base, token, _ = start(candidate, restored, launcher)
        assert call("GET", prefix) == continued
        receipt["backup_file"] = identity(backup)
        receipt["results"] = [
            "CAS original byte/hash preserved",
            "unknown node and stable block IDs preserved",
            "stale write409",
            "consistent live backup",
            "independent restore matches complete document/version/original",
            "continued editing and second restart",
        ]
        receipt["ok"] = True
    except BaseException as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        if child is not None:
            launcher.stop(child)
        (work / "receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {"ok": receipt["ok"], "receipt": str(work / "receipt.json")}, ensure_ascii=False
            )
        )


if __name__ == "__main__":
    main()
