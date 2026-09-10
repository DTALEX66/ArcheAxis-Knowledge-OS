"""The project-side MCP server: ArcheAxis capabilities over stdio.

An MCP client starts this as a subprocess and speaks JSON-RPC over stdio. Configuration comes
from the environment only, never from arguments:

* ``ARCHEAXIS_CORE_BASE``  - the loopback base URL of a running Core
* ``ARCHEAXIS_CORE_TOKEN`` - the launch token the Core issued to this process's owner

The token is read from the environment, is never printed, never appears in a tool result and
never appears in a process listing. The server holds no database handle: every tool is one HTTP
request to the Core, which remains the only writer.

The tool surface, its schemas and its refusals live in ``shared/mcp_surface.py`` so they can be
tested without the SDK; this file only wires them to the protocol and to HTTP.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    """Load a module by path, the way this repository's probes do.

    The architecture guard refuses new ``sys.path`` mutations, so the two shared modules are
    loaded explicitly rather than by making the repository root importable.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mcp_surface = _load("archeaxis_mcp_surface", REPO / "shared" / "mcp_surface.py")
core_client = _load("archeaxis_core_client", REPO / "shared" / "core_client.py")


class CoreHttpPort:
    """The Core as the surface needs it: four calls, no database handle."""

    def __init__(self, base: str, token: str | None) -> None:
        self._base = base.rstrip("/")
        self._token = token

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None):
        return core_client.call(self._base, method, path, self._token, body)

    def search(self, query: str, active_only: bool):
        return self._call("GET", core_client.search_path(query, active_only))

    def qualification(self, knowledge_id: str):
        return self._call("GET", f"/api/v1/knowledge-items/{quote(knowledge_id, safe='')}/qualification")

    def record_task(self, body: dict[str, Any]):
        return self._call("POST", "/api/v1/machine/tasks", body)

    def task_receipt(self, task_id: str):
        return self._call("GET", f"/api/v1/machine/tasks/{quote(task_id, safe='')}")


def _require_sdk():
    try:
        import mcp.server  # noqa: F401
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import CallToolResult, TextContent, Tool
    except ImportError as error:  # a named failure, never a silent downgrade
        print(
            "the MCP SDK is not installed in this interpreter, so this server cannot speak MCP: "
            f"{error}. Install the mcp dependency group (uv sync --group mcp) rather than "
            "falling back to a different protocol.",
            file=sys.stderr,
        )
        return None
    return Server, stdio_server, Tool, TextContent, CallToolResult


def build_server(port, sdk):
    """Wire the surface to the low-level MCP server. Kept separate so it can be imported."""
    Server, _, Tool, TextContent, CallToolResult = sdk
    server = Server("archeaxis")

    def _result(text: str, *, is_error: bool):
        return CallToolResult(content=[TextContent(type="text", text=text)], isError=is_error)

    @server.list_tools()
    async def list_tools() -> list:
        return [Tool(**spec) for spec in mcp_surface.tool_specs()]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None):
        try:
            outcome = mcp_surface.dispatch(name, arguments, port)
        except mcp_surface.ToolError as refusal:
            # A refusal is an error result, not a successful call with bad news inside it.
            return _result(str(refusal), is_error=True)
        status = outcome.get("status")
        if not isinstance(status, int) or not 200 <= status < 300:
            reason = outcome.get("result")
            return _result(f"the Core refused {name} with status {status}: {reason}", is_error=True)
        return _result(_as_text(outcome), is_error=False)

    return server


def _as_text(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> int:
    import os

    sdk = _require_sdk()
    if sdk is None:
        return 3
    base = os.environ.get("ARCHEAXIS_CORE_BASE", "").strip()
    if not base:
        print("ARCHEAXIS_CORE_BASE is not set: this server has no Core to talk to", file=sys.stderr)
        return 2
    token = os.environ.get("ARCHEAXIS_CORE_TOKEN") or None

    Server, stdio_server, _, _, _ = sdk
    server = build_server(CoreHttpPort(base, token), sdk)

    async def serve() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    import anyio

    anyio.run(serve)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
