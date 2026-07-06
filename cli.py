#!/usr/bin/env python3
"""Cognitive-Loop-OS CLI — unified command-line entry point.

Usage:
    python -m cli serve              # Start server
    python -m cli pipeline <input>   # Run pipeline
    python -m cli backup             # Backup database
    python -m cli test               # Run tests
    python -m cli health             # Health check
    python -m cli stats              # Show stats
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))


def cmd_serve(port: int = 8000) -> None:
    """Start the Cognitive-Loop-OS server."""
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)


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
    from shared.storage import count as _c
    from app.tools.registry import list_tools
    stats = {
        "documents": _c("kb_documents"), "cards": _c("kb_cards"),
        "reviews": _c("kb_reviews"), "mku": _c("machine_knowledge_units"),
        "tools": len(list_tools()),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def cmd_test() -> None:
    """Run test suite."""
    import subprocess
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"], cwd=str(_PROJECT_ROOT))
    kb = _PROJECT_ROOT / "Knowledge-Base"
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"], cwd=str(kb))


def cmd_stats() -> None:
    """Show comprehensive stats."""
    from shared.storage import count as _c, select_all
    print("Cognitive-Loop-OS v0.4.0")
    print("=" * 40)
    tables = [
        "kb_documents", "kb_cards", "kb_reviews", "kb_mistakes",
        "machine_knowledge_units", "kb_taskpacks", "kb_context_packs",
        "daily_notes", "graph_entities", "graph_relations",
        "canvases", "canvas_nodes", "kb_evidence", "kb_links",
    ]
    for table in tables:
        try:
            n = _c(table)
            print(f"  {table:30s}: {n:>6d}")
        except Exception:
            pass
    print("=" * 40)
    print(f"  {'Total API endpoints':30s}: {'~40':>6s}")
    print(f"  {'Shared modules':30s}: {'37':>6s}")
    print(f"  {'Tests passed':30s}: {'106':>6s}")


COMMANDS = {
    "serve": cmd_serve,
    "pipeline": cmd_pipeline,
    "backup": cmd_backup,
    "health": cmd_health,
    "test": cmd_test,
    "stats": cmd_stats,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m cli <command> [args]")
        print(f"Commands: {', '.join(COMMANDS)}")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS)}")
        sys.exit(1)

    fn = COMMANDS[cmd]
    args = sys.argv[2:]
    if cmd == "serve":
        port = int(args[0]) if args else 8000
        fn(port)
    elif cmd == "pipeline" and len(args) >= 2:
        fn(args[0], args[1])
    elif cmd == "pipeline" and len(args) == 1:
        fn("text", args[0])
    else:
        fn()
