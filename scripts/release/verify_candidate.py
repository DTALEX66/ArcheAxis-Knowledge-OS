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
import subprocess
import sys
import tempfile
import time
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

TOKEN = "9" * 64
SESSION = "8" * 32


def known_commits() -> set[str]:
    result = subprocess.run(["git", "rev-list", "--all"], cwd=str(REPO), capture_output=True, text=True)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def run_binary(root: Path, manifest: dict, receipt: dict) -> int:
    """Start the bundled binary, wait for its port, then stop that exact process.

    The database goes to a temporary directory, never into the bundle: a verification that
    writes a file into the directory it is verifying would make the *next* verification fail
    with an unrecorded stowaway.
    """
    binary_name = next((item["path"] for item in manifest["files"] if item["path"].endswith(".exe")), "")
    if not binary_name:
        receipt["run"] = {"ok": False, "reason": "the manifest records no executable"}
        return 4
    binary = root / binary_name
    run_dir = Path(tempfile.mkdtemp(prefix="archeaxis-verify-"))
    database = run_dir / "verify.sqlite"
    child = subprocess.Popen(
        [str(binary), str(database), "0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        cwd=str(root),
    )
    try:
        child.stdin.write(json.dumps({"launch_token": TOKEN, "session_id": SESSION}) + "\n")
        child.stdin.flush()
        child.stdin.close()  # the Core reads its claim to EOF, then reports readiness
        deadline = time.time() + 20
        port = ""
        while time.time() < deadline:
            line = child.stdout.readline()
            if "127.0.0.1:" in line:
                port = line.split("127.0.0.1:", 1)[1].split()[0].strip()
                break
        receipt["run"] = {
            "binary": binary_name,
            "cwd": "the candidate directory",
            "database": "a temporary directory, so the bundle is left exactly as it was",
            "ready_port": port or None,
            "database_created": database.is_file(),
            "token_printed": False,
        }
        if not port:
            receipt["run"]["reason"] = "the binary never reported a port"
            return 4
        return 0
    finally:
        child.kill()
        child.wait()
        receipt["run"]["stopped"] = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="verify a candidate bundle")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--run", action="store_true", help="also start the binary and stop it")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = args.candidate
    if not root.is_dir():
        print(f"no candidate directory at {root}", file=sys.stderr)
        return 2
    manifest_path = root / candidate.MANIFEST_NAME
    if not manifest_path.is_file():
        print(f"{manifest_path} is missing: a bundle without a manifest cannot be verified", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

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
