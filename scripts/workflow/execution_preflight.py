"""Read-only execution preflight for a Git project.

Reports the interpreter, optional module imports, Git identities, and broken
relative Markdown links without opening private runtime directories.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PRIVATE_NAMES = {".git", ".codex", ".zcode", ".hermes", ".dsh", ".openhuman"}
LINK_RE = re.compile(r"!?(?:\[[^]]*\])\(([^)\s]+)(?:\s+[^)]*)?\)")


def _git(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=True, encoding="utf-8", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _markdown_files(root: Path) -> list[Path]:
    names = _git(root, "ls-files", "--", "*.md") or ""
    return [root / line for line in names.splitlines() if line and not any(
        part.casefold() in PRIVATE_NAMES for part in Path(line).parts)]


def run(root: Path, modules: list[str]) -> dict:
    root = root.resolve()
    links: list[dict] = []
    expected_missing: list[dict] = []
    for document in _markdown_files(root):
        if not document.is_file():
            continue
        for match in LINK_RE.finditer(document.read_text(encoding="utf-8")):
            target = match.group(1).split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                item = {"document": document.relative_to(root).as_posix(),
                        "target": target, "status": "missing"}
                # Synthetic vaults intentionally contain references to
                # unsupported/placeholder assets; report them without making
                # the repository-wide preflight fail.
                if ("tests" in document.parts and "fixtures" in document.parts) or (
                    "knowledge_base" in document.parts and "obsidian_vault" in document.parts
                ):
                    expected_missing.append({**item, "status": "expected_fixture_missing"})
                else:
                    links.append(item)
    imports = [{"module": name, "available": importlib.util.find_spec(name) is not None}
               for name in modules]
    return {
        "schema": "archeaxis.execution-preflight/v1",
        "root": str(root),
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "git": {"branch": _git(root, "branch", "--show-current"),
                "head": _git(root, "rev-parse", "HEAD"),
                "user_name": _git(root, "config", "user.name"),
                "user_email": _git(root, "config", "user.email")},
        "modules": imports,
        "markdown_links": {"checked": len(_markdown_files(root)),
                           "broken": links, "broken_count": len(links),
                           "expected_missing": expected_missing,
                           "expected_missing_count": len(expected_missing)},
        "private_state_opened": False,
        "passed": not links and all(item["available"] for item in imports),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--module", action="append", default=[], help="module to probe")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run(args.root, args.module)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
