"""Run authored Office fixtures through a complete candidate's real Core/worker.

This is a Core integration probe, not installed desktop/UI qualification. No
database writes bypass Core. Tokens remain in memory and receipts exclude them.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO / ".project-local/task-runtime/aaos01-office"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def identity(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size}


def source_changes(dev):
    """Identify changed public source bytes without collecting diff contents."""
    names = dev.git(REPO, "diff", "HEAD", "--name-only", "--no-renames", "-z")
    untracked = dev.git(REPO, "ls-files", "--others", "--exclude-standard", "-z")
    changes = []
    protected = {".codex", ".agents", ".hermes", ".dsh", ".zcode", ".claude",
                 ".ssh", ".aws", ".azure", ".gnupg", ".npmrc", ".pypirc", ".netrc",
                 "credentials", "keychain", "agent-private", "private-agent-state"}
    for name in sorted(set(filter(None, (names + "\0" + untracked).split("\0")))):
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or any(
            part.casefold() in protected or part.casefold().startswith(".env")
            for part in relative.parts
        ):
            raise ValueError("protected source change cannot enter a public receipt")
        path = dev.safe_path(REPO / relative)
        path.relative_to(REPO.absolute())
        baseline = dev.git(REPO, "ls-tree", "HEAD", "--", name)
        entry = {"path": name, "head_tree_entry": baseline, "exists": path.is_file()}
        if entry["exists"]:
            entry.update({"worktree_blob": dev.git(REPO, "hash-object", "--", name),
                          "bytes": path.stat().st_size})
        changes.append(entry)
    return changes


def start(candidate, work, launcher):
    profile = launcher.load_profile(candidate)
    token = secrets.token_hex(32)
    worker = {"python": str(profile["python"]), "script": str(profile["script"]),
              "staging": str(work / "worker-staging"),
              "routes": [{"capability": r["capability"], "script": str(r["script"])}
                         for r in profile["routes"]]}
    (work / "worker-staging").mkdir(exist_ok=True)
    launch = {"launch_token": token, "machine_token": secrets.token_hex(32),
              "session_id": secrets.token_hex(16), "actor": "human",
              "protocol": launcher.LAUNCH_PROTOCOL, "text_worker": worker}
    child = subprocess.Popen([str(candidate / "core/archeaxis-api.exe"),
                              str(work / "workspace.sqlite"), "0"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, encoding="utf-8",
                             cwd=candidate, env=launcher.build_environment(candidate))
    try:
        child.stdin.write(json.dumps(launch) + "\n")
        child.stdin.close()
        base = launcher.wait_for_readiness(child, 0, 30)
        return child, base, token, worker
    except BaseException:
        launcher.stop(child)
        raise


def capture(client, base, token, job):
    paths = {"job": f"/api/v1/jobs/{job}", "quality": f"/api/v1/jobs/{job}/quality"}
    paths.update({kind: f"/api/v1/jobs/{job}/outputs/{kind}"
                  for kind in ("text", "document_structure", "loss_report")})
    return {key: {"status": status, "body": body}
            for key, path in paths.items()
            for status, body in [client.call(base, "GET", path, token)]}


def validate(record):
    snap = record["snapshot"]
    state = snap["job"]["body"].get("state")
    if record["corrupt"]:
        error = snap["job"]["body"].get("error")
        assert state == "failed" and error, f"corrupt sample state/error: {state}/{error}"
        assert "AAK-WORKER-003" in str(error), f"unexpected failure category: {error}"
        assert snap["text"]["status"] == 404, "failed sample published text"
        return
    assert state == "succeeded", f"sample did not succeed: {snap['job']}"
    for key in ("text", "document_structure", "loss_report", "quality"):
        assert snap[key]["status"] == 200, f"missing {key}: {snap[key]}"
    text = snap["text"]["body"]["content"]
    for key in ("text", "document_structure", "loss_report"):
        output = snap[key]["body"]
        raw = output["content"].encode("utf-8")
        assert output["metadata"]["sha256"] == hashlib.sha256(raw).hexdigest()
        assert output["metadata"]["byte_length"] == len(raw)
    anchors = json.loads(snap["document_structure"]["body"]["content"])
    loss = json.loads(snap["loss_report"]["body"]["content"])
    quality = snap["quality"]["body"]
    assert quality["engine"] == "python-worker-office" and quality["engine_version"]
    assert quality["coverage"] == 1 and quality["loss_count"] > 0
    assert anchors and all(0 <= a["char_start"] < a["char_end"] <= len(text) for a in anchors)
    assert loss["losses"] and loss["loss_note"]
    structure = loss["params"]["worker_structure"]
    if record["format"] == "xlsx":
        assert "A1=Sheet evidence anchor" in text
        assert any(a["path"][0] == "sheet-Evidence" and
                   "A1=Sheet evidence anchor" in text[a["char_start"]:a["char_end"]]
                   for a in structure)
        assert loss["params"]["engine"] == "openpyxl"
    else:
        assert "Slide evidence anchor" in text
        assert any(a["path"][0] == "slide-1" and
                   "Slide evidence anchor" in text[a["char_start"]:a["char_end"]]
                   for a in structure)
        assert loss["params"]["engine"] == "python-pptx"
    assert "This project-authored fixture contains no personal data." in text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--run-id", help="Optional safe data-root ID; default full UUID tests long paths")
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    run_id = args.run_id or uuid.uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
        parser.error("run-id must be 1-64 safe characters")
    work = OUTPUT_ROOT / run_id
    work.mkdir(parents=True, exist_ok=False)
    receipt = {"ok": False, "evidence_level": "REAL_CORE_WORKER_INTEGRATION_AUTHORED_FIXTURES",
               "candidate": str(candidate), "work": str(work), "results": [],
               "limitations": ["No installed Tauri/UI qualification", "Line anchors derive from projection; Office paths are retained worker facts",
                               "No live formula calculation or rendering qualification"]}
    launcher = load("aaos_office_launcher", REPO / "scripts/release/backend_launcher.py")
    client = load("aaos_office_client", REPO / "shared/core_client.py")
    child = None
    try:
        dev = load("aaos_office_dev", REPO / "scripts/runtime/dev.py")
        dirty, patch_sha = dev.worktree_identity(REPO)
        receipt["source"] = {"commit": dev.git(REPO, "rev-parse", "HEAD"),
                             "dirty": dirty, "patch_sha256": patch_sha,
                             "changes": source_changes(dev)}
        profile = launcher.load_profile(candidate)
        receipt["candidate_manifest"] = identity(candidate / "backend-runtime-manifest.json")
        receipt["worker_profile"] = identity(candidate / "worker-profile.json")
        receipt["worker_files"] = [identity(path) for path in
                                   sorted((candidate / "workers").rglob("*.py"))]
        receipt["interpreter"] = identity(profile["python"])
        receipt["core"] = identity(candidate / "core/archeaxis-api.exe")
        receipt["lockfile"] = identity(REPO / "uv.lock")
        # Real import under the candidate interpreter, never find_spec or directory search.
        probe = subprocess.run([str(profile["python"]), "-B", "-I", "-c",
            "import json,sys,openpyxl,pptx; print(json.dumps({'executable':sys.executable,'modules':[{ 'name':m.__name__,'path':m.__file__,'version':m.__version__} for m in (openpyxl,pptx)]}))"],
            capture_output=True, text=True, encoding="utf-8", timeout=60)
        receipt["imports"] = {"exit": probe.returncode, "stdout": probe.stdout, "stderr": probe.stderr}
        assert probe.returncode == 0, "candidate real imports failed"
        child, base, token, worker = start(candidate, work, launcher)
        receipt["launch_worker"] = worker
        receipt["pid"] = child.pid
        for extension in ("xlsx", "pptx"):
            source = REPO / f"tests/fixtures/golden/golden-{extension}-anchor.{extension}"
            for corrupt in (False, True):
                name = f"{'corrupt' if corrupt else 'golden'}-office.{extension}"
                payload = (f"deliberately invalid {extension} container".encode()
                           if corrupt else source.read_bytes())
                sample = work / name
                sample.write_bytes(payload)
                record = {"format": extension, "corrupt": corrupt, "sample": identity(sample)}
                receipt["results"].append(record)
                status, imported = client.call(base, "POST", "/api/v1/imports", token,
                                               client.import_request(name, payload))
                record["import"] = {"status": status, "body": imported}
                assert status == 202 and imported["sha256"] == record["sample"]["sha256"]
                job = "office-" + uuid.uuid4().hex
                record["job_id"] = job
                status, queued = client.call(base, "POST", "/api/v1/jobs", token,
                    {"job_id": job, "kind": "office", "input_ref": imported["source_id"]})
                assert status == 202, queued
                status, executed = client.call(base, "POST", f"/api/v1/jobs/{job}/executions", token,
                    {"deadline_ms": 180000}, extra_headers={"idempotency-key": job})
                record["execution"] = {"status": status, "body": executed}
                assert status == 202, executed
                deadline = time.monotonic() + 190
                while time.monotonic() < deadline:
                    _, current = client.call(base, "GET", f"/api/v1/jobs/{job}", token)
                    if current.get("state") in ("succeeded", "failed", "cancelled", "rejected"):
                        break
                    time.sleep(0.2)
                record["snapshot"] = capture(client, base, token, job)
                validate(record)
                record["validated_before_restart"] = True
        launcher.stop(child)
        child = None
        child, base, token, _ = start(candidate, work, launcher)
        receipt["restart_pid"] = child.pid
        for record in receipt["results"]:
            after = capture(client, base, token, record["job_id"])
            record["restart_snapshot"] = after
            assert after == record["snapshot"], "persisted readback changed after restart"
            record["restart_equal"] = True
        receipt["ok"] = True
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        if child is not None:
            launcher.stop(child)
        output = work / "receipt.json"
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": receipt["ok"], "receipt": str(output), "error": receipt.get("error")}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
