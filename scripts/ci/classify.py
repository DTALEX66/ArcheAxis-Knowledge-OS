#!/usr/bin/env python3
"""Deterministic changed-path risk classifier for Cognitive-Loop-OS CI.

Reads the project validation profile and produces a GatePlanV1 JSON artifact.
Classification is fully deterministic: real base/head diff paths are matched
against the versioned ``.worklab/project-validation.v1.yaml`` risk classes and
the required Gate sets are unioned. Unknown paths and CI/security/schema
classes force ``full-qualification``. LLM judgement is never used to decide
required Gates.

This is the OS-local standalone source of truth. WORK-LAB (when present) may
only select Gates registered in ``gate-registry.v1.yaml``; it may never inject
arbitrary shell or override this plan.

Usage:
    python scripts/ci/classify.py \
        --base <base-sha> --head <head-sha> \
        [--paths path1 path2 ... | --diff <file>] \
        [--force-full] [--event pull_request]
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / ".worklab" / "project-validation.v1.yaml"
REGISTRY_PATH = ROOT / ".worklab" / "gate-registry.v1.yaml"
ALWAYS_GATES = {"ci-verdict"}


def resolve_diff_refs(
    event_name: str,
    *,
    push_before: str | None = None,
    push_after: str | None = None,
    pull_base: str | None = None,
    pull_head: str | None = None,
) -> tuple[str, str, bool]:
    """Resolve trusted two-point diff refs for a GitHub event.

    Push events must use the event's before/after SHAs. Pull requests must use
    the base/head SHAs supplied by GitHub so a missing or shallow ref cannot
    silently turn a selective plan into an accidental full run.
    """

    if event_name == "push":
        base = push_before or "origin/main"
        head = push_after or "HEAD"
        trusted = bool(push_before and push_after and set(push_before) != {"0"})
        return base, head, trusted
    if event_name == "pull_request":
        base = pull_base or "origin/main"
        head = pull_head or "HEAD"
        trusted = bool(pull_base and pull_head)
        return base, head, trusted
    return "origin/main", "HEAD", False


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # local import so classifier works in minimal CI envs
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(f"PyYAML required: {exc}") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _path_matches(pattern: str, path: str) -> bool:
    norm = path.replace("\\", "/")
    pat = pattern.replace("\\", "/")
    if fnmatch.fnmatchcase(norm, pat):
        return True
    # support trailing /** matching any descendant
    if pat.endswith("/**"):
        prefix = pat[:-3]
        return norm == prefix.rstrip("/") or norm.startswith(prefix.rstrip("/") + "/")
    # support a leading **/ matching the path with or without a directory prefix
    # (e.g. **/*.md must also match a root-level README.md / AGENTS.md)
    if pat.startswith("**/"):
        remainder = pat[3:]
        return fnmatch.fnmatchcase(norm, remainder)
    return False


def classify_paths(
    paths: list[str],
    profile: dict[str, Any] | None = None,
    force_full: bool = False,
) -> dict[str, Any]:
    if profile is None:
        profile = _load_yaml(PROFILE_PATH)

    classes = profile["risk_classes"]
    matched_classes: list[str] = []
    matched_reasons: list[str] = []
    unknown_paths: list[str] = []
    gates: set[str] = set()

    for path in paths:
        norm = path.replace("\\", "/")
        if not norm or norm.endswith("/"):
            continue
        hit = False
        for cls in classes:
            for pattern in cls["paths"]:
                if _path_matches(str(pattern), norm):
                    if cls["id"] not in matched_classes:
                        matched_classes.append(cls["id"])
                    matched_reasons.append(f"{cls['id']}:{norm}")
                    gates.update(cls["gates"])
                    hit = True
                    break
            if hit:
                break  # first class match for this path; unions still apply
        if not hit:
            unknown_paths.append(norm)
            gates.add("full-qualification")

    if force_full:
        gates.add("full-qualification")
        matched_classes.append("forced-full")
        matched_reasons.append("force_full:CI_FORCE_FULL")

    # full-qualification dominates every other gate
    is_full = "full-qualification" in gates
    if is_full:
        gates = {"full-qualification", "ci-verdict"}

    gates = set(ALWAYS_GATES) | gates
    gates.discard("full-qualification")  # logical profile, not a runnable job
    required = sorted(gates)

    # deterministic digest over the whole decision
    digest_payload = {
        "classes": matched_classes,
        "reasons": matched_reasons,
        "unknown_paths": unknown_paths,
        "required_gates": required,
        "force_full": force_full,
        "full_qualification": is_full,
    }
    digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "schema": "dtalex.verification/gate-plan/v1",
        "matched_classes": matched_classes,
        "reason_codes": matched_reasons,
        "unknown_paths": unknown_paths,
        "required_gates": required,
        "force_full": force_full,
        "full_qualification": is_full,
        "digest": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic CI risk classifier")
    parser.add_argument("--base", help="Base SHA")
    parser.add_argument("--head", help="Head SHA")
    parser.add_argument("--event", default="pull_request", help="Event type")
    parser.add_argument("--force-full", action="store_true", help="Force full-qualification")
    parser.add_argument("--paths", nargs="*", help="Changed paths (absolute or repo-relative)")
    parser.add_argument("--diff", help="File containing changed paths, one per line")
    parser.add_argument("--profile", help="Path to project validation profile (default repo .worklab)")
    parser.add_argument("--output", help="Write GatePlan JSON to this path")
    args = parser.parse_args()

    profile_path = Path(args.profile) if args.profile else PROFILE_PATH
    if not profile_path.is_file():
        print(f"ERROR: profile not found: {profile_path}", file=sys.stderr)
        return 2
    profile = _load_yaml(profile_path)

    paths: list[str] = []
    if args.diff:
        paths = [
            line.strip()
            for line in Path(args.diff).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("::") and not line.startswith("#")
        ]
    elif args.paths:
        paths = list(args.paths)

    if not paths:
        # no diff available -> unknown/full
        plan = classify_paths([], profile=profile, force_full=True)
        plan["fallback_reason"] = "no_diff_available"
    else:
        plan = classify_paths(paths, profile=profile, force_full=args.force_full)

    plan["repository"] = "DTALEX66/archeaxis-workspace"
    plan["event"] = args.event
    plan["base_sha"] = args.base or "unavailable"
    plan["head_sha"] = args.head or "unavailable"
    plan["mode"] = "standalone"

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
