"""Call the workspace handshake for real, against a temporary database.

This is the probe for the one exchange the product shell gates everything on
(frontend/src/api/client.ts). It deliberately does not stub anything: it drives the sanctioned
migration entrypoint, starts the real application, and asks the real endpoint, then checks the
answer against the conditions the shell applies.

Everything it touches lives under a temporary directory. It never opens the worktree database,
never touches the official library or installation, and asserts nothing about them.

As a probe it signs no product qualification: it verifies one exchange, on one machine, at one
commit. Its value is that a manual observation is now repeatable.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HANDSHAKE_PATH = "/api/v1/system/handshake"

# The conditions frontend/src/api/client.ts applies to the handshake.
PINNED_PRODUCT_ID = "archeaxis-workspace"
PINNED_API_CONTRACT = "1.x"
REQUIRED_NON_EMPTY = ("product_name", "backend_version", "source_commit", "runtime_mode", "workspace_id")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def check_handshake(body: object) -> list[str]:
    """Return the violations of the shell contract, empty when the document is acceptable."""
    problems: list[str] = []
    if not isinstance(body, dict):
        return ["handshake is not an object"]
    if body.get("product_id") != PINNED_PRODUCT_ID:
        problems.append(f"product_id is {body.get('product_id')!r}")
    if body.get("api_contract") != PINNED_API_CONTRACT:
        problems.append(f"api_contract is {body.get('api_contract')!r}")
    for field in REQUIRED_NON_EMPTY:
        value = body.get(field)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{field} is not a non-empty string")
    version = body.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        problems.append(f"schema_version is {version!r}")
    capabilities = body.get("capabilities")
    if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
        problems.append("capabilities is not a list of strings")
    if body.get("migration_state") != "ready":
        problems.append(f"migration_state is {body.get('migration_state')!r}")
    return problems


def run(keep: bool) -> dict:
    # Project-owned development output belongs under the ignored .project-local root, not the
    # system temporary directory, which the project treats as ambiguous ownership.
    runs = REPO / ".project-local" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="handshake-probe-", dir=str(runs)))
    database = work / "archeaxis.sqlite"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    env["PYTHONIOENCODING"] = "utf-8"
    env["ARCHEAXIS_DB_PATH"] = str(database)
    env["ARCHEAXIS_DATA_DIR"] = str(work)

    receipt: dict = {"scope": "handshake_contract_probe", "work": str(work), "steps": []}

    migration = subprocess.run(
        [sys.executable, "-m", "app.runtime_entrypoint", "migrate"],
        cwd=str(REPO), env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=600,
    )
    receipt["steps"].append({"step": "migrate", "exit": migration.returncode})
    receipt["database_created"] = database.is_file()
    if migration.returncode != 0:
        receipt["ok"] = False
        receipt["failed_step"] = "migrate"
        receipt["stderr_tail"] = (migration.stderr or "")[-400:]
        return receipt

    port = free_port()
    app = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        cwd=str(REPO), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    body = None
    try:
        deadline = time.time() + 120
        while time.time() < deadline:
            if app.poll() is not None:
                break
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}{HANDSHAKE_PATH}", timeout=5
                ) as response:
                    receipt["steps"].append({"step": "handshake", "status": response.status})
                    body = json.loads(response.read().decode("utf-8"))
                    break
            except urllib.error.HTTPError as error:
                receipt["steps"].append({"step": "handshake", "status": error.code})
                break
            except Exception:
                time.sleep(1.0)
    finally:
        app.kill()
        try:
            output, _ = app.communicate(timeout=20)
        except Exception:
            output = ""
        if not keep:
            shutil.rmtree(work, ignore_errors=True)

    if body is None:
        receipt["ok"] = False
        receipt["failed_step"] = "handshake"
        receipt["app_exit"] = app.returncode
        receipt["app_output_tail"] = (output or "")[-400:]
        return receipt

    problems = check_handshake(body)
    receipt["handshake"] = body
    receipt["contract_violations"] = problems
    receipt["ok"] = not problems
    if problems:
        receipt["failed_step"] = "contract"
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep", action="store_true", help="keep the temporary directory")
    parser.add_argument("--json-out", type=Path, help="also write the receipt here")
    options = parser.parse_args()

    receipt = run(keep=options.keep)
    text = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True)
    if options.json_out:
        options.json_out.parent.mkdir(parents=True, exist_ok=True)
        options.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
