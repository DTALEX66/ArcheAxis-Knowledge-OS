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
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OPAQUE_NAMES = frozenset({
    ".git", ".codex", ".dsh", ".zcode", ".hermes", ".openhuman", ".claude",
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


def metadata_path(path):
    """Native long-path spelling inside an already validated project tree.

    This does not resolve links, change ACLs, or permit caller-supplied UNC roots.
    Each queued directory is still checked without following reparse points.
    """
    value = os.fspath(path)
    if os.name == "nt" and len(value) >= 248:
        return "\\\\?\\" + os.path.abspath(value)
    return value


def volume_observation(root):
    """Volume metadata only, called after the project root has been validated."""
    result = {"observed_at": datetime.now(timezone.utc).isoformat()}
    try:
        usage = shutil.disk_usage(root)
        result.update(status="measured", total_bytes=usage.total,
                      used_bytes=usage.used, free_bytes=usage.free)
    except OSError as exc:
        result.update(status="unavailable", error_kind=type(exc).__name__,
                      total_bytes=None, used_bytes=None, free_bytes=None)
    return result


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
        before_volume = volume_observation(root)
        opaque = OPAQUE_NAMES | {name.casefold() for name in exclude_names}
        report["opaque_names"] = sorted(opaque)
        pending = [(root, "(root)")]
        while pending:
            directory, group = pending.pop()
            try:
                # Recheck queued directories before opening; never resolve targets.
                if is_reparse(os.stat(metadata_path(directory), follow_symlinks=False)):
                    group_for(group)["skipped_reparse"] += 1
                    report["reparse_points"].append({"path": directory.relative_to(root).as_posix(), "bytes": None})
                    continue
                with os.scandir(metadata_path(directory)) as entries:
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
                            info = entry.stat(follow_symlinks=False)
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

        after_volume = volume_observation(root)
        free_delta = None
        if before_volume["status"] == after_volume["status"] == "measured":
            free_delta = after_volume["free_bytes"] - before_volume["free_bytes"]
        report["volume_space"] = {
            "before": before_volume, "after": after_volume,
            "observed_free_delta_bytes": free_delta,
            "attributed_reclaimed_bytes": None,
            "scope": "volume containing validated project root; not project allocated size",
            "limitations": "concurrent writers, recycle bin and other volume users affect free space; no cleanup attribution",
        }

    report["groups"] = [groups[name] for name in sorted(groups)]
    report["totals"] = {key: sum(group[key] for group in report["groups"]) for key in COUNTERS}
    for group in report["groups"]:
        if not any(group[key] for key in ("errors", "skipped_reparse", "excluded")):
            group["total_bytes"] = group["bytes"]
    report["ended_at"] = datetime.now(timezone.utc).isoformat()
    return report


def capacity_diagnostics(current, baseline=None, budgets=None):
    """Compare observed metadata only; never infer a complete repository size."""
    budgets = budgets or {}
    for name, limit in budgets.items():
        if not name or any(c in name for c in "/\\:") or type(limit) is not int or limit < 0:
            raise ValueError("budget requires a top-level group and nonnegative integer bytes")
    comparison = "NO_BASELINE"
    previous = {}
    if baseline is not None:
        if not isinstance(baseline, dict) or any(
            baseline.get(key) != current.get(key)
            for key in ("schema", "root", "unit", "opaque_names")
        ):
            raise ValueError("baseline scope differs from current project inventory")
        if not isinstance(baseline.get("groups"), list) or not isinstance(baseline.get("totals"), dict):
            raise ValueError("baseline inventory groups/totals are missing")
        for row in baseline["groups"]:
            if not isinstance(row, dict) or not isinstance(row.get("path"), str) or type(row.get("bytes")) is not int or row["bytes"] < 0:
                raise ValueError("invalid baseline group")
            if row["path"] in previous:
                raise ValueError("duplicate baseline group")
            previous[row["path"]] = row
        comparison = "COMPARABLE_OBSERVED_SCOPE"
        for field in ("exclusions", "reparse_points"):
            if sorted(x["path"] for x in baseline.get(field, [])) != sorted(x["path"] for x in current[field]):
                comparison = "INCOMPLETE_OR_CHANGED_OBSERVATIONS"
        if baseline["totals"].get("errors", 0) or current["totals"]["errors"]:
            comparison = "INCOMPLETE_OR_CHANGED_OBSERVATIONS"
    present = {row["path"]: row for row in current["groups"]}
    producers = {
        "target": "legacy cargo output; current .cargo/config.toml redirects new builds",
        ".project-local": "scripts/runtime/dev.py and declared project build/test/packaging callers",
        ".venv": "project Python environment; preserve required dependencies",
    }
    rows = []
    for name in sorted(set(present) | set(previous) | set(budgets)):
        now, before = present.get(name), previous.get(name)
        limit = budgets.get(name)
        status = "UNCONFIGURED"
        if limit is not None:
            status = "UNKNOWN"
            if now is not None and now["bytes"] > limit:
                status = "EXCEEDED"
            elif now is not None and now.get("total_bytes") is not None:
                status = "WITHIN_LIMIT"
        rows.append({
            "path": name, "observed_bytes": now["bytes"] if now else None,
            "baseline_observed_bytes": before["bytes"] if before else None,
            "delta_bytes": now["bytes"] - before["bytes"] if now is not None and before is not None else None,
            "budget_bytes": limit, "budget_status": status,
            "producer": producers.get(name, "unverified; inspect ownership before action"),
        })
    return {
        "comparison_status": comparison, "groups": rows,
        "exceeded_groups": [r["path"] for r in rows if r["budget_status"] == "EXCEEDED"],
        "unknown_budget_groups": [r["path"] for r in rows if r["budget_status"] == "UNKNOWN"],
        "action": "diagnostics_only_no_deletion",
        "limitations": "logical observed bytes, not allocated space or reclaimed bytes; snapshots are non-atomic",
    }


def load_baseline(path, root):
    """Read a selected project-local metadata snapshot without following links."""
    path = Path(os.path.abspath(path))
    root = Path(os.path.abspath(root))
    try:
        relative = path.relative_to(root / ".project-local")
    except ValueError as exc:
        raise ValueError("baseline must be inside this project's .project-local") from exc
    if (
        any(part.casefold() in OPAQUE_NAMES or part.casefold().startswith(".env") for part in relative.parts)
        or relative.parts[:1] == ("agents",)
    ):
        raise ValueError("baseline cannot read private state")
    for part in (*reversed(path.parents), path):
        if is_reparse(os.stat(metadata_path(part), follow_symlinks=False)):
            raise ValueError("baseline path must not contain links or reparse points")
    return json.loads(Path(metadata_path(path)).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="exact Git project root")
    parser.add_argument("--exclude-name", action="append", default=[],
                        help="additional opaque private directory name (case-insensitive)")
    parser.add_argument("--baseline", type=Path, help="existing inventory JSON inside project .project-local")
    parser.add_argument("--budget", action="append", default=[], metavar="GROUP=BYTES",
                        help="explicit top-level logical-byte budget; exit 2 if exceeded, "
                             "3 if unmeasurable; no default limit or automatic deletion")
    args = parser.parse_args()
    budgets = {}
    try:
        for item in args.budget:
            name, value = item.rsplit("=", 1)
            if name in budgets:
                raise ValueError("duplicate budget group")
            budgets[name] = int(value)
        # Validate before any potentially expensive inventory work.
        capacity_diagnostics({"groups": []}, budgets=budgets)
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    report = inventory_project(args.root, exclude_names=args.exclude_name)
    report["command"] = [sys.executable, *sys.argv]
    if not report["errors"]:
        try:
            baseline = load_baseline(args.baseline, args.root) if args.baseline else None
            report["capacity"] = capacity_diagnostics(report, baseline, budgets)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
            return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["errors"]:
        return 1
    if report["capacity"]["exceeded_groups"]:
        return 2
    return 3 if report["capacity"]["unknown_budget_groups"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
