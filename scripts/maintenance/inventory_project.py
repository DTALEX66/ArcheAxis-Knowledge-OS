"""Read-only, metadata-only Git project inventory. Never a deletion plan.

Only successfully observed regular-file logical sizes are summed. Hard-linked
paths each contribute their logical size; this is not allocated disk space.
Private/mixed directories are opaque and their sizes remain unknown. Supply
--exclude-name for additional private runtime directory names in a project.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OPAQUE_NAMES = frozenset({
    ".git", ".codex", ".dsh", ".hermes", ".openhuman", ".claude",
    ".agents", ".agent", ".cursor", ".continue", ".aider", ".gemini",
    ".opencode", ".openhands", ".cline", ".roo", ".kilocode",
    ".windsurf", ".copilot", ".ssh", ".aws", ".azure", ".gnupg",
    "agent-private", "private-agent-state", "sessions", "memories",
    "keychain", "credentials", "auth", "browser-data",
    ".npmrc", ".pypirc", ".netrc",
})
COUNTERS = ("bytes", "files", "errors", "skipped_reparse", "excluded")


def is_reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def inventory_project(root, *, exclude_names=()):
    """Inspect an exact project root without opening inventoried file content."""
    report = {
        "schema": "archeaxis.metadata-inventory/v1",
        "mode": "read_only_dry_run",
        "root": str(root),
        "unit": "logical_bytes",
        "scope": "successfully observed regular files only; excluded sizes unknown",
        "repository_total_bytes": None,
        "snapshot": "non-atomic metadata observations; concurrent changes may affect results",
        "status": "partial",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "allocated_space": "not_measured",
        "file_identity": "not_collected; hard-linked paths counted independently",
        "groups": [], "totals": dict.fromkeys(COUNTERS, 0),
        "errors": [], "exclusions": [], "reparse_points": [],
    }
    groups = {}

    def group_for(name):
        if name not in groups:
            groups[name] = {
                "path": name, **dict.fromkeys(COUNTERS, 0),
                "total_bytes": None,
                "cleanup": {"status": "pending", "deletion_authorized": False,
                            "ownership": "unverified", "rebuild": "unverified",
                            "reference": "unverified", "hash": "not_read"},
            }
        return groups[name]

    def error(path, group, exc):
        group_for(group)["errors"] += 1
        report["errors"].append({"path": str(path), "kind": type(exc).__name__, "message": str(exc)})

    try:
        # Reject the drive before any filesystem access, including on POSIX hosts.
        root_text = os.fspath(root).replace("\\", "/")
        if root_text.casefold().startswith(("e:", "//")):
            raise ValueError("protected drive or UNC root is not permitted")
        root = Path(os.path.abspath(root))
        for ancestor in (*reversed(root.parents), root):
            if is_reparse(ancestor.lstat()):
                raise ValueError("root and ancestors must not be links or reparse points")
        if not stat.S_ISDIR(root.lstat().st_mode):
            raise ValueError("root must be the exact Git project root directory")
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True, encoding="utf-8", check=False)
        if result.returncode or os.path.normcase(os.path.abspath(result.stdout.strip())) != os.path.normcase(str(root)):
            raise ValueError("root must be the exact Git project root")
        report["root"] = str(root)
    except (OSError, ValueError) as exc:
        error(".", "(root)", exc)
        report["status"] = "error"
    else:
        opaque = OPAQUE_NAMES | {name.casefold() for name in exclude_names}
        report["opaque_names"] = sorted(opaque)
        pending = [(root, "(root)")]
        while pending:
            directory, group = pending.pop()
            try:
                # Recheck queued directories before opening; never resolve targets.
                if is_reparse(directory.lstat()):
                    group_for(group)["skipped_reparse"] += 1
                    report["reparse_points"].append({"path": directory.relative_to(root).as_posix(), "bytes": None})
                    continue
                with os.scandir(directory) as entries:
                    for entry in entries:
                        path = directory / entry.name
                        relative = path.relative_to(root).as_posix()
                        entry_group = entry.name if directory == root else group
                        if (entry.name.casefold() in opaque or entry.name.casefold().startswith(".env")
                                or relative.casefold() == ".project-local/agents"):
                            group_for(entry_group)["excluded"] += 1
                            report["exclusions"].append({
                                "path": relative, "bytes": None, "status": "not_measured",
                                "reason": "opaque private, Git, or mixed-ownership boundary; retain",
                            })
                            continue
                        try:
                            info = path.lstat()
                            if is_reparse(info):
                                group_for(entry_group)["skipped_reparse"] += 1
                                report["reparse_points"].append({"path": relative, "bytes": None})
                            elif stat.S_ISDIR(info.st_mode):
                                group_for(entry_group)
                                pending.append((path, entry_group))
                            elif stat.S_ISREG(info.st_mode):
                                measured_group = group_for("(root)" if directory == root else group)
                                measured_group["bytes"] += info.st_size
                                measured_group["files"] += 1
                            else:
                                group_for(entry_group)["excluded"] += 1
                                report["exclusions"].append({"path": relative, "bytes": None,
                                                             "status": "not_measured", "reason": "non-regular file"})
                        except OSError as exc:
                            error(relative, entry_group, exc)
            except OSError as exc:
                error(directory.relative_to(root).as_posix(), group, exc)

    report["groups"] = [groups[name] for name in sorted(groups)]
    report["totals"] = {key: sum(group[key] for group in report["groups"]) for key in COUNTERS}
    for group in report["groups"]:
        if not any(group[key] for key in ("errors", "skipped_reparse", "excluded")):
            group["total_bytes"] = group["bytes"]
    report["ended_at"] = datetime.now(timezone.utc).isoformat()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="exact Git project root")
    parser.add_argument("--exclude-name", action="append", default=[],
                        help="additional opaque private directory name (case-insensitive)")
    args = parser.parse_args()
    report = inventory_project(args.root, exclude_names=args.exclude_name)
    report["command"] = [sys.executable, *sys.argv]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
