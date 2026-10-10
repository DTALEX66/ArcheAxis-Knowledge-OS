"""Core-owned UI journal over actual HTTP, restart and independent restore.

Uses synthetic owned notes, no browser storage, direct SQL or private user data.
This qualifies the journal API, not an installed UI or human learning outcome.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

import aaos01_office_runtime_loop as office
import aaos01_content_policy_runtime_loop as policy

REPO = Path(__file__).resolve().parents[2]
ROUTE = "/api/v1/workspace/ui-state"


def basis(read):
    return {key: read[key] for key in ("workspace_id", "restore_epoch", "state_revision")}


def empty_state():
    return {"drafts": {}, "opened_documents": [], "active_document": None,
            "page_id": None, "pending_original": None}


def assert_snapshot(read, state, previous=None, increment=0):
    assert read["schema"] == "archeaxis.ui-working-state/v1"
    assert read["recovery_requires_confirmation"] is False
    assert read["recovery_candidates"] is None
    assert read["state"] == state, "journal changed opaque content or scene"
    assert set(read["draft_digests"]) == set(state["drafts"])
    assert all(len(value) == 64 and all(c in "0123456789abcdef" for c in value)
               for value in read["draft_digests"].values())
    pending = state.get("pending_original")
    expected = "doc_req_" + hashlib.sha256(pending["create_request_id"].encode()).hexdigest() if pending else None
    assert read["pending_document_id"] == expected
    if previous is not None:
        assert read["workspace_id"] == previous["workspace_id"]
        assert read["restore_epoch"] == previous["restore_epoch"]
        assert read["state_revision"] == previous["state_revision"] + increment


def discard_ack(base, human, client, body):
    wire = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    request = urllib.request.Request(base + ROUTE, data=wire,
                                     headers=client.headers(human), method="PUT")
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.status == 200
        # Deliberate client injection. Never consumes the journal ACK body.
    return {"request_sha256": hashlib.sha256(wire).hexdigest(),
            "fault_injection": "CLIENT_ACK_BODY_CONSUMPTION_ONLY", "ack_body": "DISCARDED_UNREAD"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    candidate = parser.parse_args().candidate.resolve()
    dev = office.load("journal_dev", REPO / "scripts/runtime/dev.py")
    paths = dev.layout(REPO)
    dev.prepare(paths)
    work = paths["run"]
    launcher = office.load("journal_launcher", REPO / "scripts/release/backend_launcher.py")
    client = office.load("journal_client", REPO / "shared/core_client.py")
    receipt = {"ok": False, "materials": "SYNTHETIC_AUTHORED_NOTES",
               "execution": "ACTUAL_CANDIDATE_CORE_HTTP", "qualification": "NOT_EXECUTED",
               "limits": ["No installed UI or physical IME", "No human knowledge or mastery claim",
                          "Lost ACK is deliberate client injection, not actual network failure"],
               "calls": [], "processes": []}
    child = None
    try:
        dirty, patch = dev.worktree_identity(REPO)
        receipt["source"] = {"commit": dev.git(REPO, "rev-parse", "HEAD"), "dirty": dirty,
                             "patch_sha256": patch, "changes": office.source_changes(dev)}
        # The isolated Green candidate carries the same Core/profile in a
        # candidate manifest. Formal backend bundles use their runtime manifest.
        manifest = candidate / "backend-runtime-manifest.json"
        if not manifest.is_file():
            manifest = candidate / "candidate-manifest.json"
        receipt["candidate"] = office.identity(manifest)
        receipt["core"] = office.identity(candidate / "core/archeaxis-api.exe")

        def launch(directory, phase):
            nonlocal child, base, human, machine
            child, base, human, machine = policy.start(candidate, directory, launcher)
            receipt["processes"].append({"phase": phase, "pid": child.pid})

        def stop():
            nonlocal child
            launcher.stop(child)
            receipt["processes"][-1]["stopped"] = child.poll() is not None
            assert receipt["processes"][-1]["stopped"], "owned Core still live"
            child = None

        def call(method, path, body=None, expected=200, actor="human"):
            status, result = client.call(base, method, path, human if actor == "human" else machine, body)
            receipt["calls"].append({"method": method, "path": path, "actor": actor,
                                     "status": status, "result": result})
            assert status == expected, {"path": path, "expected": expected, "status": status, "result": result}
            return result

        base = human = machine = None
        launch(work, "initial")
        initial = call("GET", ROUTE)
        assert_snapshot(initial, empty_state())
        docs = [call("POST", "/api/v1/documents", {"title": f"Journal-owned-{n}",
                "editor_json": policy.editor(f"已保存正文 {n}")}, 201) for n in (1, 2)]
        ids = [doc["document_id"] for doc in docs]
        frozen = {"create_request_id": "journal_original_fixed", "title": "冻结原创请求",
                  "editor_json": policy.editor("冻结正文 中文")}
        state = {"drafts": {identity: {"base_version": 1, "editor_json": {
                    **policy.editor(f"独立未保存中文 {index}"),
                    "future_envelope": {"opaque": [1, None, "未知字段保全"]}}}
                    for index, identity in enumerate(ids)},
                 "opened_documents": ids, "active_document": ids[1], "page_id": "03",
                 "pending_original": frozen}
        request = {**basis(initial), "state": state}
        call("GET", ROUTE, expected=403, actor="machine")
        call("PUT", ROUTE, request, 403, "machine")
        receipt["discarded_journal_ack"] = discard_ack(base, human, client, request)
        saved = call("GET", ROUTE)
        assert_snapshot(saved, state, initial, 1)
        stale = call("PUT", ROUTE, request, 409)
        assert "state" not in stale and "drafts" not in stale, "conflict leaked journal content"
        changed_pending = copy.deepcopy(state)
        changed_pending["pending_original"]["title"] = "different pending body"
        call("PUT", ROUTE, {**basis(saved), "state": changed_pending}, 422)
        call("PUT", ROUTE, {**basis(saved), "workspace_id": "0" * 32, "state": state}, 409)
        assert call("GET", ROUTE) == saved
        for doc in docs:
            assert call("GET", f"/api/v1/documents/{doc['document_id']}") == doc, "journal committed body"
        pending_id = saved["pending_document_id"]
        call("GET", f"/api/v1/documents/{pending_id}", expected=404)
        created = call("POST", "/api/v1/documents", frozen, 201)
        assert created["document_id"] == pending_id and created["version"] == 1
        assert call("POST", "/api/v1/documents", frozen, 201) == created
        assert call("GET", f"/api/v1/documents/{pending_id}/versions/1") == created

        clear = {**basis(saved), "document_id": ids[0], "base_version": 1,
                 "content_sha256": saved["draft_digests"][ids[0]], "saved_version": 2}
        call("POST", ROUTE + "/clear-saved", clear, 409)
        call("POST", ROUTE + "/clear-saved", clear, 403, "machine")
        updated = call("PUT", f"/api/v1/documents/{ids[0]}/draft", {
            "expected_version": 1, "editor_json": state["drafts"][ids[0]]["editor_json"]})
        assert updated["version"] == 2
        assert updated["editor_json"] == state["drafts"][ids[0]]["editor_json"]
        cleared = call("POST", ROUTE + "/clear-saved", clear)
        remaining = copy.deepcopy(state)
        del remaining["drafts"][ids[0]]
        assert_snapshot(cleared, remaining, saved, 1)
        later = copy.deepcopy(state)
        later["drafts"][ids[0]] = {"base_version": 2, "editor_json": policy.editor("保存后的新编辑仍保留")}
        latest = call("PUT", ROUTE, {**basis(cleared), "state": later})
        assert_snapshot(latest, later, cleared, 1)
        call("POST", ROUTE + "/clear-saved", {**clear, **basis(latest)}, 409)
        assert call("GET", ROUTE) == latest
        backup = call("POST", "/api/v1/workspace/backups", {}, 201)
        assert backup["verified"] is True
        artifact = work / "backups" / backup["filename"]
        receipt["backup"] = {"receipt": backup, "artifact": office.identity(artifact)}
        stop()
        launch(work, "restart")
        assert call("GET", ROUTE) == latest
        assert call("GET", f"/api/v1/documents/{ids[0]}") == updated
        assert call("GET", f"/api/v1/documents/{ids[1]}") == docs[1]
        assert call("POST", "/api/v1/documents", frozen, 201) == created
        assert sum(row["document_id"] == pending_id for row in policy.document_listing(call)) == 1
        stop()

        for action in ("preserve", "discard"):
            independent = work / f"independent-{action}"
            independent.mkdir()
            result = subprocess.run([str(candidate / "core/archeaxis-api.exe"), "--maintenance-restore",
                str(independent / "workspace.sqlite"), str(artifact)], cwd=candidate,
                env=launcher.build_environment(candidate), capture_output=True, text=True,
                encoding="utf-8", timeout=45)
            assert len(result.stdout) < 65536 and len(result.stderr) < 65536
            restored = json.loads(result.stdout)
            assert result.returncode == 0 and restored["ok"] is True and restored["verified"] is True
            assert restored["action"] == "restore"
            launch(independent, f"restored-{action}")
            candidates = call("GET", ROUTE)
            assert candidates["workspace_id"] == latest["workspace_id"]
            assert candidates["restore_epoch"] != latest["restore_epoch"]
            assert candidates["state_revision"] == latest["state_revision"]
            assert candidates["state"] == empty_state()
            assert candidates["recovery_requires_confirmation"] is True
            assert candidates["recovery_candidates"] == later
            assert candidates["pending_document_id"] is None and candidates["draft_digests"] == {}
            call("PUT", ROUTE, {**basis(latest), "state": later}, 409)
            recovery = {**basis(candidates), "action": action}
            call("POST", ROUTE + "/recover", recovery, 403, "machine")
            recovered = call("POST", ROUTE + "/recover", recovery)
            expected = later if action == "preserve" else empty_state()
            assert_snapshot(recovered, expected, candidates, 1)
            call("POST", ROUTE + "/recover", recovery, 409)
            assert call("GET", f"/api/v1/documents/{ids[0]}") == updated
            assert call("GET", f"/api/v1/documents/{ids[1]}") == docs[1]
            assert call("GET", f"/api/v1/documents/{pending_id}") == created
            stop()
            launch(independent, f"restored-{action}-restart")
            assert call("GET", ROUTE) == recovered
            stop()
        receipt["qualification"] = "INTEGRATED_CORE_JOURNAL_RESTART_EXPLICIT_RESTORE"
        receipt["ok"] = True
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        if child is not None:
            try:
                stop()
            except Exception as error:
                receipt["ok"] = False
                receipt["cleanup_error"] = f"{type(error).__name__}: {error}"
        receipt["source_consistent"] = dev.worktree_identity(REPO) == (dirty, patch) if "source" in receipt else False
        if not receipt["source_consistent"]:
            receipt["ok"] = False
        output = paths["artifacts"] / "working-state.json"
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": receipt["ok"], "receipt": str(output), "error": receipt.get("error")}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
