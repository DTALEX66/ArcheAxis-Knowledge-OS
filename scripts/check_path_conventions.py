#!/usr/bin/env python3
"""Repository path convention and old-asset disposition check (R15 / X13).

`DIRECTORY_AUTHORITY.yaml` declares ownership for the repository with its own
matching semantics: gitwildmatch patterns, `precedence: [deny, exact-path,
highest-literal-segment-count, longest-literal-prefix]` and `ambiguous_match:
reject`. Nothing until now evaluated that declaration against the tracked tree, so
"every tracked file is classified" was an intention rather than a measurement.

This checker measures it and then refuses to let the measurement drift:

  * it re-implements the declared precedence over the real `git ls-files` output
    and computes how many tracked paths are owned, unowned, ambiguous or
    deny-commit-but-tracked;
  * `denied_but_tracked == 0` and `ambiguous == 0` are invariants: any occurrence
    fails, whatever the record says;
  * unowned paths are allowed to exist but may not exist *unrecorded*: the set the
    record lists must equal the set measured, so a new unowned path fails the check
    until somebody classifies it or records it;
  * ownership class `rebuildable-cache` is enforced on disk as well as in the index: a
    declared shared install may exist as a real copy in at most one clean-and-merged
    worktree, because ten copies of one lock file is how the last round grew 2 GB;
  * every top-level entry of the tracked tree must be matched by exactly one
    disposition rule in the record, with an existing `owner_doc`, so no directory
    is unowned in silence;
  * for the legacy roots `DIRECTORY_AUTHORITY.yaml` names, the record's
    `migration_status` must come from the agreed vocabulary and its
    `manifest_entries` / `not_semantically_reviewed` counts must equal what
    `LEGACY_MANIFEST.yaml` actually says, so an inventory count cannot go stale.

What it does not do: it does not edit `DIRECTORY_AUTHORITY.yaml` (a protected
governance file) and it does not claim the repository is fully classified. It
reports the coverage that exists so the owner can close it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "DIRECTORY_AUTHORITY.yaml"
LEGACY_MANIFEST = ROOT / "LEGACY_MANIFEST.yaml"
RECORD = ROOT / "docs/current/R5-PATH-DISPOSITION.json"

DISPOSITIONS = (
    "active",
    "maintenance_only",  # DIRECTORY_AUTHORITY.yaml's own write_mode term for legacy lanes
    "legacy_reference",
    "frozen",
    "migration_pending",
    "custody",
)
MIGRATION_STATUSES = (
    "absorbed",
    "inventoried_not_semantically_reviewed",
    "maintenance_only",
    "deferred",
    "not_applicable",
)
LEGACY_MANIFEST_STATUSES = {
    "INVENTORIED_NOT_SEMANTICALLY_REVIEWED": "inventoried_not_semantically_reviewed",
    "ABSORBED": "absorbed",
    "MAINTENANCE_ONLY": "maintenance_only",
    "DEFERRED": "deferred",
}


def pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """gitwildmatch (the subset DIRECTORY_AUTHORITY.yaml uses) as a regex."""
    parts = pattern.split("/")
    pieces = []
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        if part == "**":
            pieces.append(".*" if last else "(?:[^/]+/)*")
            continue
        body = "".join(
            "[^/]*" if char == "*" else "[^/]" if char == "?" else re.escape(char) for char in part
        )
        pieces.append(body + ("" if last else "/"))
    return re.compile("^" + "".join(pieces) + "$")


def _literal_segments(pattern: str) -> int:
    return sum(1 for part in pattern.split("/") if part and not any(char in part for char in "*?"))


def _literal_prefix(pattern: str) -> int:
    prefix = ""
    for char in pattern:
        if char in "*?":
            break
        prefix += char
    return len(prefix)


def load_rules(root: Path = ROOT, *, commit: str | None = None) -> list[dict]:
    if commit is None:
        source = (root / "DIRECTORY_AUTHORITY.yaml").read_text(encoding="utf-8")
    else:
        if not re.fullmatch(r"[0-9a-fA-F]{7,40}", commit):
            raise ValueError("historical authority requires a commit SHA")
        source = subprocess.check_output(
            ["git", "show", f"{commit}:DIRECTORY_AUTHORITY.yaml"],
            cwd=str(root), text=True, encoding="utf-8",
        )
    authority = yaml.safe_load(source)
    rules = []
    for rule in authority.get("authorities", []):
        pattern = rule["path"]
        wildcard = any(char in pattern for char in "*?")
        rules.append(
            {
                "pattern": pattern,
                "regex": pattern_to_regex(pattern),
                "exact": not wildcard,
                "deny": rule.get("write_mode") == "deny-commit",
                "segments": _literal_segments(pattern),
                "prefix": _literal_prefix(pattern),
                "owner": rule.get("owner"),
                "lanes": rule.get("execution_lanes") or ([rule["execution_lane"]] if rule.get("execution_lane") else []),
            }
        )
    return rules


def tracked_paths(root: Path = ROOT) -> list[str]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=str(root), capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", "replace") or "git ls-files failed")
    return [item for item in result.stdout.decode("utf-8", "replace").split("\x00") if item]


def tracked_paths_at(root: Path, commit: str) -> list[str]:
    """The paths tracked at a commit, so a record's totals can be re-derived later.

    A record measures the tree at the commit it names. The tree keeps growing, so comparing
    its totals to the working tree would mark every added owned file as a stale record; the
    totals are therefore re-derived at that commit and verified there.
    """
    result = subprocess.run(["git", "ls-tree", "-r", "--name-only", "-z", commit], cwd=str(root), capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", "replace") or "git ls-tree failed")
    return [item for item in result.stdout.decode("utf-8", "replace").split("\x00") if item]


def select_owner(path: str, rules: list[dict]) -> tuple[str, dict | None, list[dict]]:
    """Apply the declared precedence. Returns (verdict, rule, ties)."""
    matches = [rule for rule in rules if rule["regex"].match(path)]
    denied = [rule for rule in matches if rule["deny"]]
    if denied:
        return "denied", denied[0], denied
    exact = [rule for rule in matches if rule["exact"]]
    if len(exact) > 1:
        return "ambiguous", None, exact
    if len(exact) == 1:
        return "owned", exact[0], []
    if not matches:
        return "unowned", None, []
    best = max((rule["segments"], rule["prefix"]) for rule in matches)
    top = [rule for rule in matches if (rule["segments"], rule["prefix"]) == best]
    if len(top) > 1:
        return "ambiguous", None, top
    return "owned", top[0], []


def measure(root: Path = ROOT, paths: list[str] | None = None, rules: list[dict] | None = None) -> dict:
    rules = load_rules(root) if rules is None else rules
    paths = tracked_paths(root) if paths is None else paths
    owned, unowned, ambiguous, denied = 0, [], [], []
    for path in paths:
        verdict, rule, ties = select_owner(path, rules)
        if verdict == "owned":
            owned += 1
        elif verdict == "unowned":
            unowned.append(path)
        elif verdict == "ambiguous":
            ambiguous.append({"path": path, "patterns": [item["pattern"] for item in ties]})
        else:
            denied.append({"path": path, "patterns": [item["pattern"] for item in ties]})
    total = len(paths)
    return {
        "tracked_paths": total,
        "owned": owned,
        "unowned": sorted(unowned),
        "ambiguous": ambiguous,
        "denied_but_tracked": denied,
        "coverage_percent": round(100.0 * owned / total, 2) if total else 0.0,
    }


def legacy_manifest_counts(root: Path = ROOT) -> tuple[dict[str, int], dict[str, int], int]:
    """Per-top-level counts of inventoried assets and of those not yet reviewed."""
    text = (root / "LEGACY_MANIFEST.yaml").read_text(encoding="utf-8")
    entries: dict[str, int] = {}
    unreviewed: dict[str, int] = {}
    total = 0
    for block in text.split("- asset_id: ")[1:]:
        path_match = re.search(r"^  path: (.+)$", block, re.MULTILINE)
        if not path_match:
            continue
        raw = path_match.group(1).strip().strip('"')
        top = raw.split("/")[0] if "/" in raw else "(root)"
        status_match = re.search(r"^  review_status: (\S+)$", block, re.MULTILINE)
        entries[top] = entries.get(top, 0) + 1
        total += 1
        if status_match and status_match.group(1) == "INVENTORIED_NOT_SEMANTICALLY_REVIEWED":
            unreviewed[top] = unreviewed.get(top, 0) + 1
    return entries, unreviewed, total


REPARSE_POINT_ATTRIBUTE = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT


def _is_link(path: Path) -> bool:
    """True for a symlink or a Windows junction -- the compliant form of a shared install."""
    try:
        stat_result = path.lstat()
    except OSError:
        return False
    return bool(getattr(stat_result, "st_file_attributes", 0) & REPARSE_POINT_ATTRIBUTE)


def shared_resource_rules(root: Path = ROOT) -> tuple[str, list[dict]]:
    """The declared development root and the installs that must not be copied."""
    authority = yaml.safe_load((root / "DIRECTORY_AUTHORITY.yaml").read_text(encoding="utf-8"))
    block = authority.get("shared_resource_install_rules") or {}
    rules = [item for item in block.get("shared_install_paths") or [] if item.get("relative_path")]
    return str(block.get("development_root") or ""), rules


def worktree_list(root: Path = ROOT) -> list[dict]:
    """Registered worktrees from `git worktree list --porcelain`."""
    result = subprocess.run(
        ["git", "-C", str(root), "worktree", "list", "--porcelain"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git worktree list failed")
    entries: list[dict] = []
    current: dict = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            if current:
                entries.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current["path"] = value.strip()
        elif key == "HEAD":
            current["head"] = value.strip()
        elif key == "branch":
            current["branch"] = value.strip()
    if current:
        entries.append(current)
    return [entry for entry in entries if entry.get("path")]


def _lock_digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copied_shared_resources(root: Path = ROOT) -> list[dict]:
    """Worktrees holding a copied shared install instead of reaching it through a link.

    Ownership class `rebuildable-cache` permits exactly one real copy of a given dependency
    lock across the worktree set; every other worktree links to it. A worktree is exempt only
    when reconfiguring it could disturb work that exists nowhere else: it has uncommitted
    changes, or its HEAD is not an ancestor of the checked-out baseline. So the gate is quiet
    on a dirty tree and loud on a clean one, which is the opposite of a name-pattern sweep.
    """
    baseline = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    if baseline.returncode != 0:
        return []
    development_root, rules = shared_resource_rules(root)
    if not development_root or not rules:
        return []
    marker = f"/{development_root.strip('/')}/"
    scoped = [w for w in worktree_list(root) if marker in w["path"].replace("\\", "/")]
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for rule in rules:
        relative = rule["relative_path"]
        lock_relative = rule.get("lock_file")
        identity_relative = rule.get("installed_tree_identity")
        for worktree in scoped:
            base = Path(worktree["path"])
            install = base / relative
            if not install.exists() or _is_link(install):
                continue
            lock_sha = _lock_digest(base / lock_relative) if lock_relative else None
            if lock_sha is None:
                continue
            # two copies are the same shared install only when the declared lock and the
            # install's own recorded identity agree; a missing identity is its own group
            identity_sha = (_lock_digest(base / identity_relative) if identity_relative
                            else "no-declared-identity") or "absent-installed-tree-identity"
            porcelain = subprocess.run(["git", "-C", str(base), "status", "--porcelain"],
                                       capture_output=True, text=True, encoding="utf-8",
                                       errors="replace")
            clean = porcelain.returncode == 0 and porcelain.stdout.strip() == ""
            merged = subprocess.run(
                ["git", "-C", str(root), "merge-base", "--is-ancestor",
                 worktree.get("head", ""), baseline.stdout.strip()],
                capture_output=True, text=True, encoding="utf-8", errors="replace").returncode == 0
            if not (clean and merged):
                continue
            groups.setdefault((relative, lock_sha, identity_sha), []).append(
                {"worktree": str(base).replace("\\", "/"),
                 "install": str(install).replace("\\", "/"),
                 "clean": clean, "head_is_ancestor_of_baseline": merged})
    return [
        {
            "relative_path": relative,
            "lock_sha256": lock_sha,
            "installed_tree_identity_sha256": identity_sha,
            "copy_count": len(members),
            "copies": sorted(members, key=lambda item: item["install"]),
        }
        for (relative, lock_sha, identity_sha), members in sorted(groups.items())
        if len(members) > 1
    ]


def _commit_exists(root: Path, sha: str) -> bool:
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", sha):
        return False
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=str(root), capture_output=True
    )
    return result.returncode == 0


def check(root: Path = ROOT, record_path: Path = RECORD) -> tuple[list[str], dict]:
    failures: list[str] = []
    try:
        source = record_path if record_path.is_absolute() else root / record_path
        record = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{record_path}: cannot read the record: {error}"], {}

    measured = measure(root)

    # invariants first: these hold whatever the record claims
    if measured["denied_but_tracked"]:
        failures.append(
            f"{len(measured['denied_but_tracked'])} tracked path(s) match a deny-commit authority rule: "
            + ", ".join(item["path"] for item in measured["denied_but_tracked"][:5])
        )
    if measured["ambiguous"]:
        failures.append(
            f"{len(measured['ambiguous'])} tracked path(s) match authority rules ambiguously: "
            + ", ".join(item["path"] for item in measured["ambiguous"][:5])
        )

    # ownership class `rebuildable-cache`: a shared install is copied at most once, so the
    # next round of worktrees cannot re-sprawl the same dependency tree onto disk.
    duplicated = copied_shared_resources(root)
    for group in duplicated:
        failures.append(
            f"copied shared resource: {group['copy_count']} real copies of "
            f"'{group['relative_path']}' for lock {group['lock_sha256'][:12]} "
            f"(installed-tree identity {group['installed_tree_identity_sha256'][:12] if len(group['installed_tree_identity_sha256']) > 12 else group['installed_tree_identity_sha256']}) "
            f"exist across clean-and-merged worktrees; keep one and link the rest with "
            f"`cmd /c mklink /J` (unmount only with `cmd /c rmdir`): "
            + ", ".join(item["install"] for item in group["copies"])
        )

    stated = record.get("measured") or {}
    # The record is a measurement at the commit it names, and its totals are verified *there*
    # (see at_commit below). The unowned set, by contrast, is enforced against the working
    # tree: those paths have no write lane, so a change to them must not happen unrecorded.
    if not stated.get("measured_at_commit"):
        failures.append("record measured.measured_at_commit is missing: a measurement must name the commit it was taken at")
    elif not _commit_exists(root, str(stated["measured_at_commit"])):
        failures.append(f"record measured_at_commit {stated['measured_at_commit']!r} is not a commit in this repository (a SHA is required)")
    if (
        all(stated.get(key) is not None for key in ("owned", "unowned_count", "tracked_paths"))
        and stated["owned"] + stated["unowned_count"] != stated["tracked_paths"]
    ):
        failures.append(
            f"record is internally inconsistent: owned {stated['owned']} + unowned {stated['unowned_count']} "
            f"!= tracked_paths {stated['tracked_paths']}"
        )

    # Re-derive the published totals at the recorded commit, so the numbers in the record's
    # own finding are claims a later reader can check rather than numbers nobody re-measures.
    at_commit = None
    if stated.get("measured_at_commit") and _commit_exists(root, str(stated["measured_at_commit"])):
        commit = str(stated["measured_at_commit"])
        at_commit = measure(root, paths=tracked_paths_at(root, commit), rules=load_rules(root, commit=commit))
        for key in ("tracked_paths", "owned"):
            if stated.get(key) != at_commit[key]:
                failures.append(
                    f"record {key} is {stated.get(key)} but the tree at {str(stated['measured_at_commit'])[:7]} holds {at_commit[key]}"
                )
        if len(at_commit["unowned"]) != stated.get("unowned_count"):
            failures.append(
                f"record unowned_count is {stated.get('unowned_count')} but "
                f"{len(at_commit['unowned'])} paths were unowned at {str(stated['measured_at_commit'])[:7]}"
            )
        if stated.get("coverage_percent") is not None and abs(float(stated["coverage_percent"]) - at_commit["coverage_percent"]) > 0.01:
            failures.append(
                f"record coverage_percent is {stated['coverage_percent']} but the tree at "
                f"{str(stated['measured_at_commit'])[:7]} gives {at_commit['coverage_percent']}"
            )

    # A live reconciliation may close old gaps without rewriting the historical
    # measurement. Old records without this section retain their original rules.
    current = record.get("current_ownership", record)
    stated_unowned = sorted(current.get("unowned_paths") or [])
    if stated_unowned != measured["unowned"]:
        added = sorted(set(measured["unowned"]) - set(stated_unowned))
        removed = sorted(set(stated_unowned) - set(measured["unowned"]))
        if added:
            failures.append(f"{len(added)} path(s) are unowned but not recorded, e.g. {', '.join(added[:5])}")
        if removed:
            failures.append(f"{len(removed)} recorded path(s) are no longer unowned, e.g. {', '.join(removed[:5])}")
    current_count = current.get("unowned_count") if "current_ownership" in record else stated.get("unowned_count")
    if current_count != len(measured["unowned"]):
        failures.append(
            f"record unowned_count is {current_count} but {len(measured['unowned'])} paths are unowned"
        )
    by_root = {}
    for path in measured["unowned"]:
        top = path.split("/")[0] if "/" in path else "(root)"
        by_root[top] = by_root.get(top, 0) + 1
    if current.get("unowned_by_root") != dict(sorted(by_root.items())):
        failures.append(f"record unowned_by_root is {current.get('unowned_by_root')} but the tree shows {dict(sorted(by_root.items()))}")

    # disposition coverage: every top-level entry classified exactly once
    rules = record.get("top_level_disposition") or []
    if not rules:
        failures.append("the record has no top_level_disposition rules")
    covered: list[str] = []
    for entry in sorted({path.split("/")[0] if "/" in path else path for path in tracked_paths(root)}):
        hits = [rule for rule in rules if entry in (rule.get("paths") or [])]
        if len(hits) != 1:
            failures.append(f"top-level entry {entry!r} is matched by {len(hits)} disposition rules, expected exactly one")
            continue
        rule = hits[0]
        covered.append(entry)
        if rule.get("disposition") not in DISPOSITIONS:
            failures.append(f"{entry}: disposition {rule.get('disposition')!r} is not one of {DISPOSITIONS}")
        if not rule.get("class"):
            failures.append(f"{entry}: no class recorded")
        owner_doc = rule.get("owner_doc") or ""
        if not (root / owner_doc).exists():
            failures.append(f"{entry}: owner_doc {owner_doc!r} does not exist")
        if not rule.get("note"):
            failures.append(f"{entry}: no note explaining the disposition")

    # legacy roots: vocabulary plus inventory counts that cannot go stale
    entries, unreviewed, total_assets = legacy_manifest_counts(root)
    authority = yaml.safe_load((root / "DIRECTORY_AUTHORITY.yaml").read_text(encoding="utf-8"))
    declared_legacy = [
        str(pattern).rstrip("/*")
        for pattern in authority.get("legacy_roots", {}).get("enforced_authority_rules", [])
    ]
    declared_legacy = [item for item in declared_legacy if item]
    recorded_legacy = {item.get("root"): item for item in record.get("legacy_roots") or []}
    for legacy in declared_legacy:
        entry = recorded_legacy.get(legacy)
        if entry is None:
            failures.append(f"legacy root {legacy!r} is declared in DIRECTORY_AUTHORITY.yaml but missing from the record")
            continue
        if entry.get("migration_status") not in MIGRATION_STATUSES:
            failures.append(
                f"{legacy}: migration_status {entry.get('migration_status')!r} is not one of {MIGRATION_STATUSES}"
            )
        expected_entries = entries.get(legacy, 0)
        expected_unreviewed = unreviewed.get(legacy, 0)
        if entry.get("manifest_entries") != expected_entries:
            failures.append(f"{legacy}: manifest_entries is {entry.get('manifest_entries')} but LEGACY_MANIFEST.yaml has {expected_entries}")
        if entry.get("not_semantically_reviewed") != expected_unreviewed:
            failures.append(
                f"{legacy}: not_semantically_reviewed is {entry.get('not_semantically_reviewed')} but the manifest shows {expected_unreviewed}"
            )
    recorded_total = record.get("legacy_manifest_total_entries")
    if recorded_total != total_assets:
        failures.append(f"legacy_manifest_total_entries is {recorded_total} but the manifest holds {total_assets} entries")

    detail = {
        "tracked_paths": measured["tracked_paths"],
        "owned": measured["owned"],
        "unowned": len(measured["unowned"]),
        "coverage_percent": measured["coverage_percent"],
        "denied_but_tracked": len(measured["denied_but_tracked"]),
        "ambiguous": len(measured["ambiguous"]),
        "copied_shared_resource_groups": len(duplicated),
        "top_level_entries": len(covered),
        "legacy_manifest_entries": total_assets,
        "legacy_roots_recorded": len(recorded_legacy),
    }
    if at_commit is not None:
        detail["measured_at_commit"] = stated.get("measured_at_commit")
        detail["drift_since_measurement"] = {
            "tracked_paths": measured["tracked_paths"] - at_commit["tracked_paths"],
            "owned": measured["owned"] - at_commit["owned"],
            "unowned": len(measured["unowned"]) - len(at_commit["unowned"]),
            "note": "the record is a measurement at its own commit; this is how the working tree has moved since",
        }
    return failures, detail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--record", type=Path, default=RECORD)
    parser.add_argument("--measure", action="store_true", help="print the measurement only (no record needed)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.measure:
        print(json.dumps(measure(ROOT), ensure_ascii=False, indent=2))
        return 0

    failures, detail = check(ROOT, args.record)
    if args.json:
        print(json.dumps({"passed": not failures, "failures": failures, **detail}, ensure_ascii=False, indent=2))
    elif failures:
        print("path convention check failed:")
        for item in failures:
            print(f"  - {item}")
    else:
        print(
            "path convention check passed: "
            f"{detail['owned']}/{detail['tracked_paths']} tracked paths owned "
            f"({detail['coverage_percent']}%), {detail['unowned']} unowned and all recorded, "
            f"{detail['denied_but_tracked']} deny-commit paths tracked, {detail['ambiguous']} ambiguous, "
            f"{detail['copied_shared_resource_groups']} duplicated shared install group(s), "
            f"{detail['top_level_entries']} top-level entries classified, "
            f"{detail['legacy_manifest_entries']} legacy assets inventoried across {detail['legacy_roots_recorded']} legacy roots"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
