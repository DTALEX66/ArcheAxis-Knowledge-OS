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
import os
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path


def cmd_serve(port: int = 8000) -> None:
    """Start Core through the single lease-aware runtime entry point."""
    from app.runtime_entrypoint import run_core

    os.environ["COGNITIVE_PORT"] = str(port)
    run_core(Namespace())


def cmd_pipeline(source: str, input_data: str) -> None:
    """Run the effectful pipeline under the target database runtime lease."""
    from shared import backup, storage
    from shared.pipeline import run_pipeline

    with backup.runtime_lease(storage.DB_PATH):
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



def cmd_migrate(args: list[str]) -> None:
    """Run the non-interactive migration operator against an explicit database."""
    parser = ArgumentParser(prog="cognitive-os migrate")
    parser.add_argument("action", choices=("status", "apply", "rollback"))
    parser.add_argument("--owner")
    parser.add_argument("--db", required=True)
    parser.add_argument("--backup-dir", required=True)
    options = parser.parse_args(args)

    from shared import backup
    from shared.migration_runner import MigrationOperator

    operator = MigrationOperator(db_path=options.db, backup_dir=options.backup_dir)
    if options.action == "status":
        result = operator.status()
    else:
        if not options.owner:
            parser.error("--owner is required for apply and rollback")
        function = operator.apply if options.action == "apply" else operator.rollback
        with backup.runtime_lease(Path(options.db)):
            result = function(options.owner)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))


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
    if command == "migrate":
        cmd_migrate(sys.argv[2:])
        return
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
