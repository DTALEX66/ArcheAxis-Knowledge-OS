"""Verify a candidate bundle, and optionally run it.

    python -X utf8 scripts/release/verify_candidate.py --candidate DIR [--run]

Without ``--run`` this re-hashes every recorded file against ``CANDIDATE.json``, refuses a
file the manifest does not record, and checks that the source commit it names is a commit in
this repository.

With ``--run`` it also starts the bundled binary with a fresh launch claim, reads the loopback
port it reports, and stops that exact process - so "it verifies" means "it ran here", not "the
hashes look right".

Exit codes: 0 verified, 2 no candidate, 3 the bundle does not match its manifest, 4 the run
failed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import queue
import re
import secrets
import subprocess
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load_candidate_module():
    spec = importlib.util.spec_from_file_location("archeaxis_candidate", Path(__file__).with_name("candidate.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate.py is missing beside this script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate = _load_candidate_module()
_dev_spec = importlib.util.spec_from_file_location("verify_dev", REPO / "scripts/runtime/dev.py")
assert _dev_spec and _dev_spec.loader
dev = importlib.util.module_from_spec(_dev_spec)
_dev_spec.loader.exec_module(dev)


def known_commits() -> set[str]:
    result = subprocess.run(["git", "rev-list", "--all"], cwd=str(REPO), capture_output=True, text=True)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def run_binary(root: Path, manifest: dict, receipt: dict, *, timeout: float = 20) -> int:
    """Start the bundled binary, wait for its port, then stop that exact process.

    The database goes to a temporary directory, never into the bundle: a verification that
    writes a file into the directory it is verifying would make the *next* verification fail
    with an unrecorded stowaway.
    """
    binary_name = next((item["path"] for item in manifest["files"] if item["path"].endswith(".exe")), "")
    if not binary_name:
        receipt["run"] = {"ok": False, "reason": "the manifest records no executable"}
        return 4
    binary = candidate.safe_bundle_path(root, binary_name)
    run_dir = dev.artifact_directory(REPO, "candidate-verify")
    database = run_dir / "verify.sqlite"
    receipt['run'] = {'binary': binary_name, 'database': str(database),
                      'ready_port': None, 'stopped': False, 'token_printed': False}
    child = subprocess.Popen(
        [str(binary), str(database), "0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        cwd=str(root),
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        start_new_session=sys.platform != 'win32',
    )
    ready = queue.Queue(maxsize=1)

    def read_ready():
        try:
            while line := child.stdout.readline(4096):
                match = re.search(r'127\.0\.0\.1:(\d{1,5})(?:\s|$)', line)
                if match and 0 < int(match[1]) <= 65535:
                    ready.put(match[1])
                    return
        finally:
            if ready.empty():
                ready.put(None)

    reader = threading.Thread(target=read_ready, daemon=True)
    reader.start()
    try:
        child.stdin.write(json.dumps({"launch_token": secrets.token_hex(32), "session_id": secrets.token_hex(16)}) + "\n")
        child.stdin.flush()
        child.stdin.close()  # the Core reads its claim to EOF, then reports readiness
        try:
            port = ready.get(timeout=timeout)
        except queue.Empty:
            port = None
        receipt['run'].update(ready_port=port, database_created=database.is_file())
        if not port or not database.is_file():
            receipt["run"]["reason"] = "candidate did not report readiness and create its database"
            return 4
        return 0
    except OSError:
        receipt['run']['reason'] = 'candidate launch communication failed'
        return 4
    finally:
        dev.stop_owned_process(child)
        reader.join(timeout=2)
        if reader.is_alive():
            receipt['run']['reason'] = 'candidate stdout remains open after process cleanup'
            raise RuntimeError('candidate stdout reader did not stop')
        child.stdout.close()
        if not child.stdin.closed:
            child.stdin.close()
        receipt["run"]["stopped"] = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="verify a candidate bundle")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--run", action="store_true", help="also start the binary and stop it")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        root = candidate.safe_bundle_path(args.candidate)
        manifest_path = candidate.safe_bundle_path(root, candidate.MANIFEST_NAME)
    except (OSError, ValueError):
        print("unsafe candidate path", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"no candidate directory at {root}", file=sys.stderr)
        return 2
    if not manifest_path.is_file():
        print(f"{manifest_path} is missing: a bundle without a manifest cannot be verified", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("candidate manifest cannot be read as JSON", file=sys.stderr)
        return 3
    if not isinstance(manifest, dict):
        print("candidate manifest must be an object", file=sys.stderr)
        return 3

    problems = candidate.verify_manifest(root, manifest, known_commits=known_commits())
    receipt: dict = {
        "candidate": str(root),
        "schema": manifest.get("schema"),
        "source_commit": manifest.get("source_commit"),
        "build_kind": manifest.get("build_kind"),
        "files": len(manifest.get("files") or []),
        "problems": problems,
    }
    code = 3 if problems else 0
    if args.run and not problems:
        code = run_binary(root, manifest, receipt)
    elif args.run:
        receipt["run"] = {"ok": False, "reason": "not run: the bundle does not match its manifest"}

    receipt["ok"] = code == 0
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    elif problems:
        print(f"candidate verification failed with {len(problems)} problem(s):")
        for item in problems:
            print(f"  - {item}")
    else:
        run_note = ""
        if args.run:
            run_note = f", ran and stopped on port {receipt['run'].get('ready_port')}"
        print(
            f"candidate verified: {receipt['files']} file(s) re-hashed against "
            f"{candidate.MANIFEST_NAME}, source commit {str(receipt['source_commit'])[:12]}, "
            f"build {receipt['build_kind']}{run_note}"
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
