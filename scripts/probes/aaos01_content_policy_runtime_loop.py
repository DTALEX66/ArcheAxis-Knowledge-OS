"""Schema11 policy through independent candidate Core processes, never direct SQL.

Authored text fixtures, actual Core/Python execution; no installed UI, human
assessment or paid cloud call is qualified. Machine/human claims use distinct
launch credentials, retained only in memory.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
import subprocess
import time
import uuid
from pathlib import Path

import aaos01_office_runtime_loop as office

REPO = Path(__file__).resolve().parents[2]


def start(candidate, work, launcher):
    profile = launcher.load_profile(candidate)
    human, machine = secrets.token_hex(32), secrets.token_hex(32)
    staging = work / "worker-staging"
    staging.mkdir(exist_ok=True)
    launch = {
        "launch_token": human,
        "machine_token": machine,
        "session_id": secrets.token_hex(16),
        "actor": "human",
        "protocol": launcher.LAUNCH_PROTOCOL,
        "text_worker": {
            "python": str(profile["python"]),
            "script": str(profile["script"]),
            "staging": str(staging),
            "routes": [
                {"capability": row["capability"], "script": str(row["script"])}
                for row in profile["routes"]
            ],
        },
    }
    child = subprocess.Popen(
        [str(candidate / "core/archeaxis-api.exe"), str(work / "workspace.sqlite"), "0"],
        cwd=candidate,
        env=launcher.build_environment(candidate),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        child.stdin.write(json.dumps(launch) + "\n")
        child.stdin.close()
        return child, launcher.wait_for_readiness(child, 0, 30), human, machine
    except BaseException:
        launcher.stop(child)
        raise


def editor(text):
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {"block_id": "stable-policy-block"},
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    work = REPO / ".project-local/task-runtime/aaos01-content-policy" / uuid.uuid4().hex
    work.mkdir(parents=True)
    launcher = office.load("policy_launcher", REPO / "scripts/release/backend_launcher.py")
    client = office.load("policy_client", REPO / "shared/core_client.py")
    dev = office.load("policy_dev", REPO / "scripts/runtime/dev.py")
    receipt = {
        "ok": False,
        "scope": "REAL_INDEPENDENT_CORE_SCHEMA11",
        "limits": [
            "Authored text fixture",
            "Manual assessment fixture is not actual human review",
            "Cloud worker not configured; no network/paid execution",
            "No installed desktop/UI qualification",
        ],
        "calls": [],
        "processes": [],
    }
    child = None
    try:
        dirty, patch = dev.worktree_identity(REPO)
        receipt["source"] = {
            "commit": dev.git(REPO, "rev-parse", "HEAD"),
            "dirty": dirty,
            "patch_sha256": patch,
        }
        receipt["candidate_manifest"] = office.identity(candidate / "backend-runtime-manifest.json")
        receipt["core"] = office.identity(candidate / "core/archeaxis-api.exe")
        child, base, human, machine = start(candidate, work, launcher)
        receipt["processes"].append({"phase": "initial", "pid": child.pid})

        def call(method, path, body=None, expected=200, actor="human", headers=None):
            status, result = client.call(
                base,
                method,
                path,
                human if actor == "human" else machine,
                body,
                extra_headers=headers,
            )
            receipt["calls"].append(
                {"method": method, "path": path, "actor": actor, "status": status, "result": result}
            )
            assert status == expected, {
                "path": path,
                "expected": expected,
                "status": status,
                "result": result,
            }
            return result

        version = call("GET", "/api/v1/system/version")
        receipt["system"] = version
        workspace_info = call("GET", "/api/v1/workspaces/info")
        assert workspace_info["schema_version"] == 11, workspace_info
        receipt["workspace_info"] = workspace_info
        original = call(
            "POST",
            "/api/v1/documents",
            {
                "title": "OriginalPolicyNote",
                "editor_json": editor("OriginalUnverifiedNeedle 创作没有外部来源仍入库"),
            },
            201,
        )
        assert original["source_id"] is None and original["source_revision"] is None
        oid = original["document_id"]
        ochecks = f"/api/v1/documents/{oid}/checks"
        assert call("GET", ochecks)["checks"] == []
        assert any(
            row["document_id"] == oid
            for row in call("GET", client.search_path("OriginalUnverifiedNeedle"))["documents"]
        )
        call(
            "POST",
            "/api/v1/documents",
            {"title": "machine", "editor_json": editor("machine")},
            403,
            "machine",
        )
        call(
            "POST",
            "/api/v1/documents",
            {"source_id": "missing", "title": "half", "editor_json": editor("half")},
            400,
        )
        pending = call(
            "POST",
            ochecks,
            {"version": 1, "dimension": "professional_basis", "provider_mode": "cloud"},
            201,
            "machine",
        )
        assert pending["status"] == "pending" and pending["reason"] == "worker_not_configured"
        assert (
            pending["execution_state"] == "not_executed" and pending["execution_verified"] is False
        )
        for fake in ("passed", "supported", "failed"):
            call(
                "POST",
                ochecks,
                {
                    "version": 1,
                    "dimension": "professional_basis",
                    "provider_mode": "cloud",
                    "status": fake,
                },
                400,
            )
        call(
            "POST",
            ochecks,
            {
                "version": 1,
                "dimension": "professional_basis",
                "provider_mode": "cloud",
                "execution_verified": True,
            },
            422,
        )
        manual = {
            "version": 1,
            "dimension": "professional_basis",
            "provider_mode": "manual",
            "status": "uncertain",
            "position": {"block_id": "stable-policy-block"},
            "basis": "Fixture reports uncertainty without asserting support",
        }
        call("POST", ochecks, manual, 403, "machine")
        report = call("POST", ochecks, manual, 201)
        assert (
            report["execution_state"] == "reported_manual" and report["execution_verified"] is False
        )
        old_checks = call("GET", ochecks)
        basis = {
            "reference_version": 1,
            "check_id": report["check_id"],
            "position": manual["position"],
            "rationale": "Revision preserves prior uncertain report, without approval",
        }
        updated = call(
            "PUT",
            f"/api/v1/documents/{oid}/draft",
            {
                "expected_version": 1,
                "editor_json": editor("UpdatedUnverifiedNeedle 新版保持未核验"),
                "revision_basis": basis,
            },
        )
        assert updated["revision_basis"] == basis
        assert call("GET", ochecks)["checks"] == []
        historical = call("GET", ochecks + "?version=1")
        assert historical["historical"] is True and historical["checks"] == old_checks["checks"]
        assert any(
            row["document_id"] == oid and row["version"] == 2
            for row in call("GET", client.search_path("UpdatedUnverifiedNeedle"))["documents"]
        )
        payload = b"Known original recognition statement 42\n"
        imported = call(
            "POST", "/api/v1/imports", client.import_request("policy-original.txt", payload), 202
        )
        assert imported["sha256"] == hashlib.sha256(payload).hexdigest()
        job = "policy-" + uuid.uuid4().hex
        call(
            "POST",
            "/api/v1/jobs",
            {"job_id": job, "kind": "text", "input_ref": imported["source_id"]},
            202,
        )
        call(
            "POST",
            f"/api/v1/jobs/{job}/executions",
            {"deadline_ms": 30000},
            202,
            headers={"idempotency-key": job},
        )
        deadline = time.monotonic() + 40
        while True:
            state = call("GET", f"/api/v1/jobs/{job}")
            if state["state"] in ("succeeded", "failed", "rejected", "cancelled"):
                break
            assert time.monotonic() < deadline, "real worker deadline expired"
            time.sleep(0.1)
        assert state["state"] == "succeeded", state
        output = call("GET", f"/api/v1/jobs/{job}/outputs/text")
        assert output["content"].encode() == payload
        digest = hashlib.sha256(output["content"].encode()).hexdigest()
        sourced = call(
            "POST",
            "/api/v1/documents",
            {
                "source_id": imported["source_id"],
                "source_revision": imported["sha256"],
                "title": "UnreviewedRecognizedNote",
                "editor_json": editor(output["content"]),
            },
            201,
        )
        sid = sourced["document_id"]
        schecks = f"/api/v1/documents/{sid}/checks"
        assert call("GET", schecks)["checks"] == [], (
            "Processing success must not infer verification or approval"
        )
        assert any(
            row["document_id"] == sid
            for row in call("GET", client.search_path("Known original recognition"))["documents"]
        )
        fidelity = {
            "version": 1,
            "dimension": "recognition_fidelity",
            "provider_mode": "manual",
            "status": "mismatch",
            "recognition_job_id": job,
            "recognition_result_sha256": digest,
            "source_id": imported["source_id"],
            "source_revision": imported["sha256"],
            "position": {"type": "text", "start": 0, "end": len(payload)},
            "basis": "Synthetic issue report attached to actual job and original range, not a real human assessment",
        }
        call("POST", schecks, {**fidelity, "recognition_result_sha256": "f" * 64}, 400)
        call(
            "POST",
            schecks,
            {**fidelity, "position": {"type": "text", "start": 0, "end": 999999}},
            400,
        )
        located = call("POST", schecks, fidelity, 201)
        assert (
            located["recognition_result_sha256"] == digest
            and located["content_sha256"] == sourced["content_sha256"]
        )
        source_checks = call("GET", schecks)
        receipt["assertions"] = {
            "original_without_source": True,
            "unreviewed_searchable": True,
            "processing_not_verification": True,
            "cloud_not_executed": True,
            "machine_manual_refused": True,
            "version_bound_revision_basis": True,
            "actual_job_sha_and_original_position": True,
        }
        backup = call("POST", "/api/v1/workspace/backups", {}, 201)
        assert backup["verified"] is True
        artifact = work / "backups" / backup["filename"]
        receipt["backup"] = {"receipt": backup, "artifact": office.identity(artifact)}
        launcher.stop(child)
        child = None
        child, base, human, machine = start(candidate, work, launcher)
        receipt["processes"].append({"phase": "restart", "pid": child.pid})
        assert call("GET", f"/api/v1/documents/{oid}") == updated
        assert call("GET", ochecks + "?version=1") == historical
        assert call("GET", schecks) == source_checks
        launcher.stop(child)
        child = None
        independent = work / "independent-restore"
        independent.mkdir()
        restored = subprocess.run(
            [
                str(candidate / "core/archeaxis-api.exe"),
                "--maintenance-restore",
                str(independent / "workspace.sqlite"),
                str(artifact),
            ],
            cwd=candidate,
            env=launcher.build_environment(candidate),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=45,
        )
        assert len(restored.stdout) < 65536 and len(restored.stderr) < 65536
        result = json.loads(restored.stdout)
        receipt["restore"] = {
            "exit": restored.returncode,
            "result": result,
            "stderr": restored.stderr,
        }
        assert (
            restored.returncode == 0
            and result["ok"] is True
            and result["verified"] is True
            and result["action"] == "restore"
        )
        child, base, human, machine = start(candidate, independent, launcher)
        receipt["processes"].append({"phase": "independent-restored", "pid": child.pid})
        assert call("GET", f"/api/v1/documents/{oid}") == updated
        assert call("GET", ochecks + "?version=1") == historical
        assert call("GET", f"/api/v1/documents/{sid}") == sourced
        assert call("GET", schecks) == source_checks
        original_bytes = call("GET", f"/api/v1/sources/{imported['source_id']}/original")
        assert base64.b64decode(original_bytes["content_base64"]) == payload
        receipt["assertions"].update(
            {"restart_equal": True, "independent_restore_docs_blocks_checks_cas_equal": True}
        )
        launcher.stop(child)
        child = None
        receipt["ok"] = True
    except Exception as error:
        receipt["ok"] = False
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        if child is not None:
            try:
                launcher.stop(child)
            except Exception as error:
                receipt["ok"] = False
                receipt["cleanup_error"] = f"{type(error).__name__}: {error}"
        path = work / "receipt.json"
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {"ok": receipt["ok"], "receipt": str(path), "error": receipt.get("error")},
                ensure_ascii=False,
            )
        )
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
