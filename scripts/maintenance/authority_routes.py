"""Resolve public document identity and fail on live authority routing drift.

Does not inspect private/global software state or turn source material into grants.
The document-authority CI entry invokes check_routes; --resolve is for readers.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import stat
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = "docs/current/AAOS-AUTHORITY-ROUTES.json"
PRIVATE = {".git", ".codex", ".claude", ".hermes", ".ssh", "memory", "memories",
           "session", "sessions", "credentials", "cookies", "browser-data"}
LINK = re.compile(r"\]\(([^)]+)\)")


def public_path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or name.startswith("/"):
        raise ValueError("outside or non-repository path")
    parts = PurePosixPath(name).parts
    if ".." in parts or any(p.casefold() in PRIVATE or p.casefold().startswith(".env") for p in parts):
        raise ValueError("private or traversal path")
    for i in range(1, len(parts) + 1):
        candidate = root.joinpath(*parts[:i])
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("reparse path")
    return root.joinpath(*parts)


def resolve(name: str, data: dict, root: Path = ROOT) -> dict:
    public_path(root, name)
    for alias in data["aliases"]:
        if name == alias["old_path"]:
            return {"path": name, "role": "RETIRED_LOCATOR", "canonical_path": alias["canonical_path"]}
    for entry in data["entries"]:
        if name == entry["path"]:
            return entry.copy()
    for rule in data["rules"]:
        if fnmatch.fnmatchcase(name, rule["pattern"]):
            return {"path": name, "role": rule["role"]}
    return {"path": name, "role": "UNCLASSIFIED_REFERENCE"}


def check_routes(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    try:
        data = json.loads(public_path(root, REGISTRY).read_text(encoding="utf-8"))
        if data["schema"] != "archeaxis.authority-routes/v1":
            raise ValueError("invalid schema")
        paths = [entry["path"] for entry in data["entries"]]
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate exact routes")
        for required in ("README.md", "AUTHORITY.md", "AGENTS.md", data["active_pointer"]):
            if required not in paths:
                problems.append("required public entry not classified: " + required)
        for entry in data["entries"]:
            path = public_path(root, entry["path"])
            if not path.is_file():
                problems.append("missing exact route: " + entry["path"])
        for alias in data["aliases"]:
            public_path(root, alias["old_path"])
            if not public_path(root, alias["canonical_path"]).is_file():
                problems.append("missing alias destination: " + alias["canonical_path"])
        pointer = json.loads(public_path(root, data["active_pointer"]).read_text(encoding="utf-8"))
        if pointer.get("authority_routes") != REGISTRY:
            problems.append("active pointer does not route through this registry")
        control = pointer.get("execution_control", {})
        if control.get("state") == "PAUSED_BY_OWNER":
            if control.get("automatic_continuation") is not False:
                problems.append("product automatic continuation is not disabled while paused")
        elif control.get("state") == "RUNNING_BY_OWNER":
            revision = control.get("owner_resume_record")
            if not isinstance(revision, str) or not revision.startswith("docs/current/"):
                problems.append("product resume lacks a new Owner-selected routing revision")
            else:
                decision = json.loads(public_path(root, revision).read_text(encoding="utf-8"))
                if (
                    decision.get("schema") != "archeaxis.owner-execution-resume/v1"
                    or decision.get("resumes_product_execution") is not True
                    or not decision.get("owner_instruction")
                    or decision.get("active_taskpack") != pointer.get("active_taskpack")
                    or decision.get("active_progress") != pointer.get("active_progress")
                ):
                    problems.append("product resume revision does not match the selected scope")
        else:
            problems.append("product pause changed without a new Owner-selected routing revision")
        for frozen in pointer.get("frozen_source_inputs", []):
            if frozen.get("state") != "FROZEN_BY_OWNER" or frozen.get("execution") != "NOT_EXECUTED":
                problems.append("frozen input promoted to execution")
            for field in ("index", "manifest"):
                name = frozen[field]
                if not public_path(root, name).is_file() or resolve(name, data, root)["role"] != "FROZEN_SOURCE_INPUT":
                    problems.append("frozen input routing missing: " + name)
        # Actual historical failures: a dated current/handoff path must not become an active router.
        for name in ("HERMES_HANDOFF.md", "docs/current/AAOS01-AGENT-HANDOFF-20261006.txt",
                     "docs/current/AAOS-CLOUD-AUDIT-HANDOFF-20260926.md"):
            if resolve(name, data, root)["role"] in {"ACTIVE_ROUTER", "LIVE_NAVIGATION", "SCOPED_PROGRESS"}:
                problems.append("historical path promoted to live authority: " + name)
        for entry in data["entries"]:
            if entry["role"] != "LIVE_NAVIGATION":
                continue
            name = entry["path"]
            path = public_path(root, name)
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8-sig")
            if "AAOS-AUTHORITY-ROUTES.json" not in text and name not in {"frontend/README.md", "src-tauri/README.md", "crates/README.md"}:
                problems.append("live entry lacks document identity route: " + name)
            for token in LINK.findall(text):
                target = unquote(token.strip("<> ").split("#", 1)[0])
                if not target or target.startswith(("https://", "http://", "mailto:", "app://")):
                    continue
                # Existing machine locators are not probed or treated as cloud paths.
                if ":" in target or target.startswith("/") or "<" in target:
                    continue
                joined = PurePosixPath(name).parent / target
                parts: list[str] = []
                for part in joined.parts:
                    if part == "..":
                        if not parts:
                            raise ValueError("live link escapes repository")
                        parts.pop()
                    elif part != ".":
                        parts.append(part)
                reference = public_path(root, "/".join(parts))
                if not reference.exists():
                    problems.append(f"{name}: unresolved live link: {target}")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        problems.append(f"{REGISTRY}: {error}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolve", metavar="REPOSITORY_PATH")
    args = parser.parse_args()
    if args.resolve:
        data = json.loads(public_path(ROOT, REGISTRY).read_text(encoding="utf-8"))
        try:
            print(json.dumps(resolve(args.resolve, data), ensure_ascii=False))
            return 0
        except ValueError as error:
            print(str(error))
            return 1
    errors = check_routes()
    for error in errors:
        print(error)
    if not errors:
        print("authority routes: PASS (public navigation only; runtime/CI qualification not established)")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
