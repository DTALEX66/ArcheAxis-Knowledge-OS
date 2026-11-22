"""Import, export or synchronize knowledge files with the selected AAOS workspace."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
from pathlib import Path

FORMATS = {
    "anki": "anki_exchange",
    "evernote": "evernote_exchange",
    "git": "git_snapshot",
    "joplin": "joplin_exchange",
    "logseq": "logseq_exchange",
    "notion": "notion_exchange",
    "obsidian": "obsidian_vault",
    "siyuan": "siyuan_exchange",
    "zotero": "zotero_exchange",
}


def client(name):
    return importlib.import_module("scripts.ingest." + FORMATS[name])


def main(argv):
    if argv == ["--check-runtime"]:
        for name in FORMATS:
            client(name)
        importlib.import_module("scripts.ingest.obsidian_sync")
        print(" ".join(FORMATS))
        return 0
    args_parser = argparse.ArgumentParser(prog="start-backend.cmd exchange", description=__doc__)
    args_parser.add_argument("--backend-root", type=Path, help="use the Core and worker profile of this backend directory")
    args_parser.add_argument("--workspace", type=Path, help="the existing or new workspace database file")
    args_parser.add_argument("format", choices=FORMATS)
    args_parser.add_argument("arguments", nargs=argparse.REMAINDER, metavar="ARG")
    args = args_parser.parse_args(argv)
    selected = client(args.format)
    if args.arguments[-1:] in (["--help"], ["-h"]) and "--" not in args.arguments:
        return selected.main(args.arguments, session=("", ""))
    if args.workspace is None:
        args_parser.error("select a workspace database with --workspace")

    # This file is installed as shared/exchange/__main__.py. Its sibling
    # launcher owns the Core process and worker profile in the same release.
    launcher_path = Path(__file__).resolve().parents[2] / "start-backend.py"
    spec = importlib.util.spec_from_file_location("aaos_exchange_launcher", launcher_path)
    if spec is None or spec.loader is None:
        raise ValueError("the backend launcher is missing")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    workspace = args.workspace.absolute()
    try:
        options = {"backend_root": args.backend_root} if args.backend_root is not None else {}
        child, base, _, tokens = launcher.start(workspace.parent, 0, workspace_name=workspace.name, **options)
    except (launcher.LaunchFailure, OSError) as exc:
        print(f"Could not open the workspace: {exc}", file=sys.stderr)
        return 2
    try:
        status = selected.main(args.arguments, session=(base, tokens["human"]))
    except KeyboardInterrupt:
        status = 130
    except SystemExit as exc:
        status = exc.code
    finally:
        closed = launcher.close_session(child, base, tokens)
        print(json.dumps(closed), file=sys.stderr)
    return status or int(closed["shutdown"] != "graceful")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if arguments[:1] == ["exchange"]:
        arguments = arguments[1:]
    try:
        raise SystemExit(main(arguments))
    except (ImportError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
