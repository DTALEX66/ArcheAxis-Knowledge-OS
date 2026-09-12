"""R11: the machine capability surface, reached through a real MCP client.

This is the piece R11 still owed: not a hand-written JSON-RPC caller, but the official MCP SDK
client talking to a server this repository ships. The order of the run is the boundary itself:

1. a Core launched by a **human** claim seeds the workspace with one import and one accepted
   fact, because a machine principal may not accept and seeding as a machine would be faking it;
2. a Core launched by a **machine** claim serves the tools - the launch claim is the identity,
   and a client cannot change it with a header;
3. the MCP client starts ``scripts/mcp/archeaxis_mcp_server.py`` over stdio, lists the tools,
   searches, records a machine task receipt, reads it back, and tries a human review action.

The token is passed to the server through the environment only. It is never printed, never an
argument, and never part of the receipt.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SERVER = REPO / "scripts" / "mcp" / "archeaxis_mcp_server.py"

TOKEN = "c" * 64
HUMAN_SESSION = "a" * 32
MACHINE_SESSION = "b" * 32

DOCUMENT_NAME = "holdout/mcp-source.md"
DOCUMENT_BODY = (
    "The MCP surface probe records that the radio array at the desert site measured "
    "41.5 decibels. The observation was filed by the operator. "
)
QUERY = "radio array desert site"
TASK_ID = "mcp-surface-probe-1"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _load("core_client_mcp_probe", REPO / "shared" / "core_client.py")


def allocate_database() -> Path:
    """Use dev.py's worktree/run boundary and never reuse a probe database."""
    runtime = _load("runtime_mcp_probe", REPO / "scripts/runtime/dev.py")
    directory = runtime.artifact_directory(REPO, "r11-mcp")
    return directory / "mcp.sqlite"


def launch_core(binary: Path, db: Path, actor: str, session: str):
    """Start a real Core and read its readiness line. The launch claim is the identity."""
    child = subprocess.Popen(
        [str(binary), str(db), "0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        cwd=str(REPO),
    )
    claim = {"launch_token": TOKEN, "session_id": session}
    if actor == "machine":
        claim["actor"] = "machine"
    child.stdin.write(json.dumps(claim) + "\n")
    child.stdin.flush()
    child.stdin.close()  # the Core reads its claim to EOF, then reports readiness
    deadline = time.time() + 20
    while time.time() < deadline:
        line = child.stdout.readline()
        if "127.0.0.1:" in line:
            port = line.split("127.0.0.1:", 1)[1].split()[0].strip()
            return child, f"http://127.0.0.1:{port}"
    child.kill()
    child.wait()
    return None, ""


def seed(base: str, receipt: dict) -> bool:
    """One import and one accepted fact, done by the human claim and by nothing else."""
    status, imported = core.call(base, "POST", "/api/v1/imports", TOKEN, core.import_request(DOCUMENT_NAME, DOCUMENT_BODY.encode("utf-8")))
    receipt["seed_import"] = {"status": status}
    if status not in (200, 201, 202):
        receipt["seed_import"]["body"] = str(imported)[:200]
        return False
    status, created = core.call(
        base,
        "POST",
        "/api/v1/knowledge-items",
        TOKEN,
        {"knowledge_type": "OBSERVATION", "body": DOCUMENT_BODY, "status": "accepted", "created_by": "human"},
    )
    receipt["seed_fact"] = {"status": status, "knowledge_id": (created or {}).get("knowledge_id") if isinstance(created, dict) else None}
    return status in (200, 201)


def _text_of(result) -> str:
    parts = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


async def drive(base: str, receipt: dict) -> int:
    """Run the real MCP client against this repository's server."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    environment = dict(os.environ)
    environment["ARCHEAXIS_CORE_BASE"] = base
    environment["ARCHEAXIS_CORE_TOKEN"] = TOKEN
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        env=environment,
        cwd=str(REPO),
    )

    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        listing = await session.list_tools()
        names = [tool.name for tool in listing.tools]
        receipt["tools_exposed"] = names
        receipt["exposes_a_human_review_tool"] = any(
            hint in name.lower() for name in names for hint in ("accept", "reject", "review", "modify", "deprecat")
        )

        found = await session.call_tool("archeaxis_search", {"query": QUERY})
        body = _text_of(found)
        receipt["search"] = {
            "is_error": bool(getattr(found, "isError", False)),
            "core_status": _json_field(body, "status"),
            "document_returned": DOCUMENT_BODY.startswith(_first_head(body)),
        }

        written = await session.call_tool(
            "archeaxis_record_task",
            {
                "task_id": TASK_ID,
                "conditions": "answer one closed-form question from the workspace corpus",
                "model_version": "deepseek-flash (harness session)",
                "tool_version": "archeaxis.mcp/v1",
                "method_version": "one retrieval then one recorded outcome",
                "scope": f"read-only search plus one receipt write, query {QUERY!r}",
                "outcome": "succeeded",
            },
        )
        receipt["record_task"] = {
            "is_error": bool(getattr(written, "isError", False)),
            "core_status": _json_field(_text_of(written), "status"),
        }

        read_back = await session.call_tool("archeaxis_task_receipt", {"task_id": TASK_ID})
        text = _text_of(read_back)
        receipt["read_receipt"] = {
            "is_error": bool(getattr(read_back, "isError", False)),
            "outcome": _json_field(text, "outcome", nested=True),
            "note": _json_field(text, "note", nested=True),
        }

        refused = await session.call_tool("archeaxis_accept", {"knowledge_id": "k_probe"})
        receipt["human_action_through_mcp"] = {
            "is_error": bool(getattr(refused, "isError", False)),
            "reason": _text_of(refused)[:160],
        }

        unmeasured = await session.call_tool(
            "archeaxis_record_task",
            {
                "task_id": f"{TASK_ID}-unmeasured",
                "conditions": "retest on an unseen example",
                "model_version": "deepseek-flash (harness session)",
                "scope": "not run in this probe",
                "outcome": "unmeasured",
                "retest_of": TASK_ID,
            },
        )
        receipt["unmeasured_receipt"] = {
            "is_error": bool(getattr(unmeasured, "isError", False)),
            "core_status": _json_field(_text_of(unmeasured), "status"),
        }

    return 0


def _json_field(text: str, key: str, nested: bool = False):
    """Read one field from the server's JSON text, without trusting its shape."""
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        payload = json.loads(text)
        if nested and isinstance(payload.get("result"), dict):
            return payload["result"].get(key)
        return payload.get(key)
    return None


def _first_head(text: str) -> str:
    """The first head in a search payload, so the document can be identified by prefix."""
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        payload = json.loads(text)
        items = ((payload.get("result") or {}).get("items")) or []
        if items:
            return str(items[0].get("head") or "")
    return ""


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")

    receipt: dict = {"protocol": "mcp over stdio", "token_printed": False}
    if importlib.util.find_spec("mcp") is None:
        receipt.update({"ok": False, "blocked": "the MCP SDK is not installed, so no real client can run"})
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 3

    import importlib.metadata as metadata

    receipt["mcp_sdk_version"] = metadata.version("mcp")

    binary = REPO / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
    if not binary.is_file():
        receipt.update({"ok": False, "blocked": "core binary not built", "path": str(binary)})
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 2

    db = allocate_database()

    human_core, base = launch_core(binary, db, "human", HUMAN_SESSION)
    if human_core is None:
        receipt.update({"ok": False, "reason": "the human Core never reported readiness"})
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 4
    try:
        if not seed(base, receipt):
            receipt.update({"ok": False, "reason": "seeding the workspace as a human failed"})
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            return 5
    finally:
        human_core.kill()
        human_core.wait()

    machine_core, machine_base = launch_core(binary, db, "machine", MACHINE_SESSION)
    if machine_core is None:
        receipt.update({"ok": False, "reason": "the machine Core never reported readiness"})
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 4
    try:
        code = asyncio.run(drive(machine_base, receipt))
    except Exception as error:  # surfaced as a named failure, never as a silent pass
        receipt.update({"ok": False, "reason": f"the MCP client run failed: {type(error).__name__}: {error}"})
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 6
    finally:
        machine_core.kill()
        machine_core.wait()

    receipt["ok"] = bool(
        code == 0
        and receipt.get("tools_exposed")
        and not receipt.get("exposes_a_human_review_tool")
        and receipt.get("search", {}).get("document_returned")
        and receipt.get("record_task", {}).get("core_status") == 201
        and receipt.get("read_receipt", {}).get("outcome") == "succeeded"
        and receipt.get("human_action_through_mcp", {}).get("is_error")
        and receipt.get("unmeasured_receipt", {}).get("core_status") == 201
    )
    receipt["verdict"] = (
        "MEASURED: a real MCP client reached the Core through this repository's server; this probe "
        "signs no PASS for capability quality and never trains or claims a weight"
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["ok"] else 7


if __name__ == "__main__":
    raise SystemExit(main())
