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
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "DIRECTORY_AUTHORITY.yaml"
LEGACY_MANIFEST = ROOT / "LEGACY_MANIFEST.yaml"
RECORD = ROOT / "docs/authority/taskpack-0910-r3/R15-PATH-DISPOSITION.json"

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


def load_rules(root: Path = ROOT) -> list[dict]:
    authority = yaml.safe_load((root / "DIRECTORY_AUTHORITY.yaml").read_text(encoding="utf-8"))
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


def _commit_exists(root: Path, sha: str) -> bool:
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

    stated = record.get("measured") or {}
    # The record is a measurement at the commit it names, and its totals are verified *there*
    # (see at_commit below). The unowned set, by contrast, is enforced against the working
    # tree: those paths have no write lane, so a change to them must not happen unrecorded.
    if not stated.get("measured_at_commit"):
        failures.append("record measured.measured_at_commit is missing: a measurement must name the commit it was taken at")
    elif not _commit_exists(root, str(stated["measured_at_commit"])):
        failures.append(f"record measured_at_commit {stated['measured_at_commit']!r} is not a commit in this repository")
    if stated.get("owned") is not None and stated.get("unowned_count") is not None and stated.get("tracked_paths") is not None:
        if stated["owned"] + stated["unowned_count"] != stated["tracked_paths"]:
            failures.append(
                f"record is internally inconsistent: owned {stated['owned']} + unowned {stated['unowned_count']} "
                f"!= tracked_paths {stated['tracked_paths']}"
            )

    # Re-derive the published totals at the recorded commit, so the numbers in the record's
    # own finding are claims a later reader can check rather than numbers nobody re-measures.
    at_commit = None
    if stated.get("measured_at_commit") and _commit_exists(root, str(stated["measured_at_commit"])):
        at_commit = measure(root, paths=tracked_paths_at(root, str(stated["measured_at_commit"])))
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

    stated_unowned = sorted(record.get("unowned_paths") or [])
    if stated_unowned != measured["unowned"]:
        added = sorted(set(measured["unowned"]) - set(stated_unowned))
        removed = sorted(set(stated_unowned) - set(measured["unowned"]))
        if added:
            failures.append(f"{len(added)} path(s) are unowned but not recorded, e.g. {', '.join(added[:5])}")
        if removed:
            failures.append(f"{len(removed)} recorded path(s) are no longer unowned, e.g. {', '.join(removed[:5])}")
    if stated.get("unowned_count") != len(measured["unowned"]):
        failures.append(
            f"record unowned_count is {stated.get('unowned_count')} but {len(measured['unowned'])} paths are unowned"
        )
    by_root = {}
    for path in measured["unowned"]:
        top = path.split("/")[0] if "/" in path else "(root)"
        by_root[top] = by_root.get(top, 0) + 1
    if record.get("unowned_by_root") != dict(sorted(by_root.items())):
        failures.append(f"record unowned_by_root is {record.get('unowned_by_root')} but the tree shows {dict(sorted(by_root.items()))}")

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
            f"{detail['top_level_entries']} top-level entries classified, "
            f"{detail['legacy_manifest_entries']} legacy assets inventoried across {detail['legacy_roots_recorded']} legacy roots"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
