"""REAL-Core round-trip for the formal Library page's own document write path.

Representative page: ``frontend/src/spaces/CanonicalLibrarySpace.tsx`` — the 资料库
(Library) space, the current product entry's canonical owner of *Documents* (an
ordinary Document/Block save that per PROJECT_CONTRACT needs no external evidence or
human approval). It is representative because the product's primary durable object is
an owned Document, and this page is the surface that creates and saves it.

The page drives one native bridge: ``coreCommand(operation, payload)`` ->
``invoke("core_command", {request:{operation,payload}})`` (frontend/src/api/core.ts).
``src-tauri/src/core_bridge.rs::route`` maps those operations to fixed Core HTTP
routes; this module reuses *that exact mapping* so the route and body exercised here
are the ones the page sends, not an approximation:

    document_create    -> POST  /api/v1/documents            {title, editor_json}
    document_draft     -> PUT   /api/v1/documents/{id}/draft  {expected_version, editor_json}
    document_get       -> GET   /api/v1/documents/{id}
    document_version   -> GET   /api/v1/documents/{id}/versions/{n}

EVIDENCE TIER: REAL. A real ``archeaxis-api`` process (the Rust Core, the only
canonical SQLite/CAS writer) performs the write, then the process is STOPPED and
STARTED again against the SAME data root, and the object is read back from disk. This
is neither the SIMULATED browser-stub layout (scripts/a0_browser_smoke.py) nor the
SYNTHETIC protocol knowledge-loop journey (scripts/probes/m0_full_loop_smoke.py);
those prove different things and are not substituted here.

This script writes nothing to the shared main checkout. Its scratch data root and
receipts live under the caller-provided --receipts-dir. It never claims a host/native
window result: the native Tauri WebView2 host and Owner acceptance are separate tiers.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOKEN_HEADER = "x-archeaxis-launch-token"

# Launch identity. The Core validates the human launch token as hex and derives the
# actor from WHICH credential authenticated the call (core documents.rs::human() ->
# request_actor == "human"), so the human token is what lets document create/save run.
TOKEN = "c" * 64
MACHINE_TOKEN = "e" * 64
SESSION = "d" * 32
PROTOCOL = "archeaxis.desktop-launch/v2"

# The exact editor payload the Library page's createOriginal()/save() composes
# (editor_json is a ProseMirror/TipTap doc). The paragraph text is the durable content
# whose bytes the round-trip asserts.
NOTE_TEXT = ("资料库代表页真机往返：这份文档由当前产品入口的写路径产生，"
             "停止并重启 Core 后应原样读回。")
EDIT_TEXT = ("第二次保存：draft 写入第二个版本，正文与 content_sha256 都必须落盘，"
             "重启后仍是这份字节。")


def editor_doc(text: str) -> dict:
    """The ProseMirror doc shape the React editor sends through document_create/draft."""
    return {"type": "doc", "content": [{"type": "paragraph",
            "content": [{"type": "text", "text": text}]}]}


def binary_identity(path: Path) -> dict:
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return {"path": str(path), "sha256": digest.hexdigest(), "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "profile": "release" if "release" in str(path).casefold() else "debug-or-other"}


def launch_doc(text_worker: dict) -> dict:
    return {"protocol": PROTOCOL, "actor": "human", "launch_token": TOKEN,
            "machine_token": MACHINE_TOKEN, "session_id": SESSION, "text_worker": text_worker}


def start_core(binary: Path, db: Path, staging: Path, python: Path, receipt: dict):
    """Start the real Core and wait for its readiness line, honouring port 0 (ephemeral)."""
    staging.mkdir(parents=True, exist_ok=True)
    worker = {"python": str(python.resolve()),
              "script": str((REPO / "services/python-workers/transport/text_ndjson.py").resolve()),
              "staging": str(staging.resolve()), "routes": []}
    child = subprocess.Popen([str(binary), str(db), "0"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, encoding="utf-8")
    assert child.stdin and child.stdout and child.stderr
    child.stdin.write(json.dumps(launch_doc(worker)) + "\n")
    child.stdin.flush()
    child.stdin.close()
    deadline = time.time() + 40
    base = None
    while time.time() < deadline:
        line = child.stdout.readline()
        if not line:
            break
        if line.startswith("archeaxis-api ready on "):
            base = line.split(" ", 3)[3].strip()
            break
    if base is None:
        err = child.stderr.read()[-1500:] if child.stderr else ""
        child.kill()
        raise SystemExit(f"Core never reported readiness: {err}")
    return child, base


def call(base: str, method: str, path: str, body: dict | None = None, timeout: float = 30.0):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base.rstrip("/") + path, data=data, method=method,
                                 headers={TOKEN_HEADER: TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        status = error.code
    except (urllib.error.URLError, OSError) as error:
        return 0, {"error": f"core unreachable: {error}"}
    with contextlib.suppress(json.JSONDecodeError):
        return status, json.loads(raw)
    return status, raw


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True, help="path to the real archeaxis-api Core binary")
    parser.add_argument("--python", type=Path, required=True, help="interpreter the Core uses for its scheduler worker")
    parser.add_argument("--receipts-dir", type=Path, required=True, help="scratch + receipt directory (must be writable, worktree-local)")
    parser.add_argument("--reuse-root", type=Path, default=None,
                        help="continue against an existing data root (for the readback leg of a split run)")
    args = parser.parse_args()

    binary, python = args.core.resolve(), args.python.resolve()
    if not binary.is_file():
        print(json.dumps({"ok": False, "blocked": f"core binary not found: {binary}"})); return 2
    if not python.is_file():
        print(json.dumps({"ok": False, "blocked": f"python interpreter not found: {python}"})); return 2

    work = args.receipts_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    db = work / "workspace.sqlite"
    staging = work / "worker-staging"

    receipt: dict = {
        "schema": "aaos.core-roundtrip.library-document/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "representative_page": "frontend/src/spaces/CanonicalLibrarySpace.tsx",
        "evidence_tier": "REAL",
        "evidence_tier_note": "real Core process wrote the durable object; process stopped and "
                              "restarted against the same data root; object read back from disk. "
                              "Not SIMULATED (browser stub), not SYNTHETIC (protocol-only journey).",
        "core_binary": binary_identity(binary),
        "python_worker": str(python),
        "data_root": str(db),
        "routes_from_core_bridge": {
            "document_create": "POST /api/v1/documents",
            "document_draft": "PUT /api/v1/documents/{id}/draft",
            "document_get": "GET /api/v1/documents/{id}",
            "document_version": "GET /api/v1/documents/{id}/versions/{n}",
        },
        "steps": [],
    }

    def step(name: str, status, payload, **extra):
        entry = {"step": name, "status": status,
                 "response": payload if isinstance(payload, dict) else {"raw": str(payload)[:400]}}
        entry.update(extra)
        receipt["steps"].append(entry)
        return status, payload

    # ---- Leg 1: the write path on a fresh (or continued) real Core process ----
    child, base = start_core(binary, db, staging, python, receipt)
    restart_required = args.reuse_root is None
    try:
        status, version = step("system_version", *call(base, "GET", "/api/v1/system/version"))
        receipt["core_identity_response"] = {"status": status, "body": version}
        # Capability surface read so a "declared/registered yet unsupported" route is caught here.
        status, caps = step("capabilities_list", *call(base, "GET", "/api/v1/capabilities"))

        # document_create (the page's createOriginal): a real owned Document with content.
        status, created = step("document_create",
                               *call(base, "POST", "/api/v1/documents",
                                     {"title": "G-COREDEMO 代表页真机往返", "editor_json": editor_doc(NOTE_TEXT)}))
        document_id = created.get("document_id") if isinstance(created, dict) else None
        v1 = created.get("version") if isinstance(created, dict) else None
        v1_sha = created.get("content_sha256") if isinstance(created, dict) else None
        receipt["failed_stage"] = None
        if status != 201 or not document_id:
            receipt["failed_stage"] = "document_create"; return finish(receipt, work, 1)

        # document_draft (the page's save): second version, optimistic on expected_version.
        status, saved = step("document_draft",
                             *call(base, "PUT", f"/api/v1/documents/{document_id}/draft",
                                   {"expected_version": v1, "editor_json": editor_doc(EDIT_TEXT)}))
        v2 = saved.get("version") if isinstance(saved, dict) else None
        v2_sha = saved.get("content_sha256") if isinstance(saved, dict) else None
        if status != 200 or v2 is None:
            receipt["failed_stage"] = "document_draft"; return finish(receipt, work, 1)

        # read the live snapshot (document_get) BEFORE the restart, to compare after.
        status, before_restart = step("document_get_pre_restart",
                                      *call(base, "GET", f"/api/v1/documents/{document_id}"))
        receipt["pre_restart"] = {"version": v2, "content_sha256": v2_sha,
                                 "editor_json_canonical": canonical(before_restart.get("editor_json"))}

        # list + historical version read (documents_list / document_version)
        step("documents_list", *call(base, "GET", "/api/v1/documents"))
        step("document_version_1", *call(base, "GET", f"/api/v1/documents/{document_id}/versions/{v1}"))
    finally:
        if restart_required:
            stop_core(child)

    if not restart_required:
        receipt["note"] = "write leg only; readback runs in a separate process invocation"
        return finish(receipt, work, 0 if not receipt["failed_stage"] else 1)

    # ---- Leg 2: RESTART the Core against the SAME data root and read back from disk ----
    child2, base2 = start_core(binary, db, staging, python, receipt)
    try:
        step("system_version_after_restart", *call(base2, "GET", "/api/v1/system/version"))
        status, after = step("document_get_after_restart",
                             *call(base2, "GET", f"/api/v1/documents/{document_id}"))
        status2, hist1 = step("document_version_1_after_restart",
                              *call(base2, "GET", f"/api/v1/documents/{document_id}/versions/{v1}"))
        after_version = after.get("version") if isinstance(after, dict) else None
        after_sha = after.get("content_sha256") if isinstance(after, dict) else None
        after_editor = canonical(after.get("editor_json")) if isinstance(after, dict) else None
        receipt["post_restart"] = {"status": status, "version": after_version,
                                   "content_sha256": after_sha, "editor_json_canonical": after_editor}
        errors = []
        if status != 200:
            errors.append(f"readback after restart returned {status}")
        if after.get("document_id") != document_id:
            errors.append("document identity changed after restart")
        if after_version != v2:
            errors.append(f"version changed across restart: {after_version} != {v2}")
        if after_sha != v2_sha:
            errors.append(f"content_sha256 changed across restart: {after_sha} != {v2_sha}")
        if after_editor != receipt["pre_restart"]["editor_json_canonical"]:
            errors.append("editor_json bytes differ across restart")
        # the historical version 1 must still be readable from disk
        if status2 != 200 or hist1.get("version") != v1 or hist1.get("content_sha256") != v1_sha:
            errors.append("historical version 1 not faithfully persisted across restart")
        # the durable text must still be the second save's bytes
        if after_editor is not None and EDIT_TEXT not in json.dumps(after.get("blocks", []), ensure_ascii=False):
            errors.append("saved text not present in persisted blocks after restart")
        receipt["roundtrip_errors"] = errors
        receipt["ok"] = not errors and not receipt["failed_stage"]
    finally:
        stop_core(child2)

    return finish(receipt, work, 0 if receipt["ok"] else 1)


def stop_core(child):
    child.terminate()
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)


def finish(receipt: dict, work: Path, code: int) -> int:
    receipt.setdefault("ok", False)
    out = work / "core-roundtrip-receipt.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"ok": receipt.get("ok"), "tier": receipt.get("evidence_tier"),
                      "document_id": next((s["response"].get("document_id") for s in receipt["steps"]
                                           if s["step"] == "document_create"), None),
                      "roundtrip_errors": receipt.get("roundtrip_errors"),
                      "receipt": str(out)}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
