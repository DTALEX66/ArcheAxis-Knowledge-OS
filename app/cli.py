#!/usr/bin/env python3
"""Cognitive-Loop-OS CLI — unified command-line entry point.

Usage:
    python -m app.cli serve              # Start server
    python -m app.cli pipeline <input>   # Run pipeline
    python -m app.cli backup             # Backup database
    python -m app.cli health             # Health check
    python -m app.cli stats              # Show stats
"""

from __future__ import annotations

import json
import sys


def cmd_serve(port: int = 8000) -> None:
    """Start the Cognitive-Loop-OS server."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        proxy_headers=False,
    )


def cmd_pipeline(source: str, input_data: str) -> None:
    """Run the pipeline on input."""
    from shared.pipeline import run_pipeline

    result = run_pipeline(source=source, input_data=input_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_backup() -> None:
    """Create a database backup."""
    from shared.backup import auto_backup

    result = auto_backup()
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_health() -> None:
    """Check system health."""
    from app.tools.registry import list_tools
    from shared.storage import count as _c

    stats = {
        "documents": _c("kb_documents"),
        "cards": _c("kb_cards"),
        "reviews": _c("kb_reviews"),
        "mku": _c("machine_knowledge_units"),
        "tools": len(list_tools()),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))



def cmd_stats() -> None:
    """Show live runtime stats without hardcoded route/test counters."""
    import pkgutil

    import shared
    from app.main import _http_route_counts
    from shared.config import config
    from shared.storage import count as _c

    print(f"Cognitive-Loop-OS v{config.get('app.version', 'unknown')}")
    print("=" * 40)
    tables = [
        "kb_documents",
        "kb_cards",
        "kb_reviews",
        "kb_mistakes",
        "machine_knowledge_units",
        "kb_taskpacks",
        "kb_context_packs",
        "daily_notes",
        "graph_entities",
        "graph_relations",
        "canvases",
        "canvas_nodes",
        "kb_evidence",
        "kb_links",
    ]
    for table in tables:
        try:
            n = _c(table)
            print(f"  {table:30s}: {n:>6d}")
        except Exception:
            pass
    print("=" * 40)
    routes = _http_route_counts()
    print(f"  {'HTTP operations':30s}: {routes['total']:>6d}")
    print(f"  {'Knowledge operations':30s}: {routes['kb']:>6d}")
    shared_modules = sum(1 for module in pkgutil.iter_modules(shared.__path__) if not module.ispkg)
    print(f"  {'Shared modules':30s}: {shared_modules:>6d}")
    print("  Tests: source checkout only; see README quality gates")


COMMANDS = {
    "serve": cmd_serve,
    "pipeline": cmd_pipeline,
    "backup": cmd_backup,
    "health": cmd_health,
    "stats": cmd_stats,
}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: cognitive-os <command> [args]")
        print(f"Commands: {', '.join(COMMANDS)}")
        raise SystemExit(1)

    command = sys.argv[1]
    if command not in COMMANDS:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(COMMANDS)}")
        raise SystemExit(1)

    function = COMMANDS[command]
    args = sys.argv[2:]
    if command == "serve":
        function(int(args[0]) if args else 8000)
    elif command == "pipeline" and len(args) >= 2:
        function(args[0], args[1])
    elif command == "pipeline" and len(args) == 1:
        function("text", args[0])
    else:
        function()


if __name__ == "__main__":
    main()
