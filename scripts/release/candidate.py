"""R13: what a candidate bundle is, and what it takes to verify one.

A candidate is a small directory plus a manifest that binds every file in it to a source
commit by sha256. The manifest is deliberately explicit about what is **not** in the bundle -
no installer, no code signing, no Python runtime, no workers - because a bundle that lets a
reader assume those exist is worse than no bundle.

This module holds the rules and imports nothing that needs a toolchain, so it can be tested
without building anything.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

SCHEMA = "archeaxis.candidate/v1"
MANIFEST_NAME = "CANDIDATE.json"


def safe_bundle_path(root: Path, relative: str = "") -> Path:
    if os.fspath(root).replace('\\', '/').casefold().startswith(('e:', '//')):
        raise ValueError("unsafe bundle root")
    root = Path(os.path.abspath(root))
    if root.drive.upper() == "E:" or str(root).startswith("\\\\"):
        raise ValueError("unsafe bundle root")
    if relative and (not isinstance(relative, str) or any(c in relative for c in "\\:")
                     or any(not part or part.startswith('.') or part.endswith((' ', '.'))
                            for part in relative.split('/'))):
        raise ValueError("unsafe bundle path")
    target = root / relative
    for path in (*reversed(target.parents), target):
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError("unsafe linked bundle path")
    return target

# Stated in the manifest and the README of every bundle, whatever it contains.
NOT_INCLUDED = [
    "no installer (MSI or EXE) and no uninstaller: this is a directory and a zip",
    "no code signing: the files are hashed, not signed, and that is what the manifest can prove",
    "no Python runtime: the Core binary is self-contained, but the worker routes need an interpreter",
    "no workers: services/python-workers/ is not in the bundle, so routes that dispatch to a worker "
    "will report a missing worker rather than quietly producing nothing",
    "no research host and no source corpus: the bundle carries no data",
]

ROUTE_NOTE = (
    "the Core owns the database; a bundle without the workers can still import and serve text, and "
    "every other route fails by name"
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_fact(path: Path, root: Path) -> dict:
    """One recorded file: its path relative to the bundle, its size and its digest."""
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_of(path),
    }


def build_manifest(
    root: Path,
    files: list[Path],
    *,
    commit: str,
    commit_subject: str,
    kind: str,
    built_at: str,
    tree_clean: bool,
    untracked_present: bool,
    python_hint: str,
) -> dict:
    """The manifest for a bundle. `kind` says which build it is, so a debug bundle says so."""
    return {
        "schema": SCHEMA,
        "source_commit": commit,
        "source_commit_subject": commit_subject,
        "built_at": built_at,
        "build_kind": kind,
        "tree_clean_when_built": tree_clean,
        "untracked_paths_present_when_built": untracked_present,
        "python_interpreter_hint": python_hint,
        "files": sorted((file_fact(path, root) for path in files), key=lambda item: item["path"]),
        "not_included": NOT_INCLUDED,
        "route_note": ROUTE_NOTE,
        "verification": [
            "python -X utf8 scripts/release/verify_candidate.py --candidate <this directory>",
            "python -X utf8 scripts/release/verify_candidate.py --candidate <this directory> --run",
        ],
        "hash_meaning": (
            "a digest binds these bytes to this manifest; it is not a signature and it says nothing "
            "about who produced the bundle"
        ),
    }


def verify_manifest(root: Path, manifest: dict, *, known_commits: set[str] | None = None) -> list[str]:
    """Every reason this bundle does not match its own manifest. An empty list is a pass."""
    problems: list[str] = []
    try:
        root = safe_bundle_path(root)
    except (ValueError, OSError):
        return ["unsafe bundle root"]
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    if manifest.get("schema") != SCHEMA:
        problems.append(f"manifest schema is {manifest.get('schema')!r}, expected {SCHEMA!r}")
    commit = str(manifest.get("source_commit") or "").strip()
    if not commit:
        problems.append("the manifest names no source commit, so nothing binds it to a source")
    elif known_commits is not None and commit not in known_commits:
        problems.append(f"the source commit {commit[:12]} is not a commit in this repository")
    if not manifest.get("build_kind"):
        problems.append("the manifest does not say which build this is")
    if not manifest.get("not_included"):
        problems.append("the manifest does not state what the bundle leaves out")

    recorded = manifest.get("files")
    if not isinstance(recorded, list) or not recorded:
        problems.append("the manifest records no files")
        return problems

    seen: set[str] = set()
    for entry in recorded:
        if not isinstance(entry, dict):
            problems.append("manifest file entry must be an object")
            continue
        relative = entry.get("path")
        try:
            if not isinstance(relative, str) or not relative:
                raise ValueError("unsafe empty path")
            target = safe_bundle_path(root, relative)
        except (ValueError, OSError):
            problems.append("unsafe manifest file path")
            continue
        identity = relative.casefold()
        if identity in seen:
            problems.append(f"duplicate manifest file path: {relative}")
            continue
        seen.add(identity)
        if not target.is_file():
            problems.append(f"{relative} is recorded but missing from the bundle")
            continue
        if target.stat().st_size != entry.get("bytes"):
            problems.append(
                f"{relative} is {target.stat().st_size} bytes, the manifest records {entry.get('bytes')}"
            )
        digest = sha256_of(target)
        if digest != entry.get("sha256"):
            problems.append(f"{relative} hashes to {digest[:16]}..., the manifest records {str(entry.get('sha256'))[:16]}...")

    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            relative = (Path(directory) / name).relative_to(root).as_posix()
            try:
                safe_bundle_path(root, relative)
            except (ValueError, OSError):
                dirs.remove(name)
                problems.append("unsafe directory in bundle")
        for name in files:
            relative = (Path(directory) / name).relative_to(root).as_posix()
            try:
                safe_bundle_path(root, relative)
            except (ValueError, OSError):
                problems.append("unsafe file in bundle")
                continue
            if relative.casefold() not in seen and relative != MANIFEST_NAME:
                problems.append(f"{relative} is in the bundle but not recorded in the manifest")
    return problems


def readme_text(manifest: dict) -> str:
    """The one-click instructions, generated from the manifest so they cannot drift from it."""
    binary = next(
        (entry["path"] for entry in manifest["files"] if entry["path"].endswith(".exe")),
        "<binary>",
    )
    commit = str(manifest["source_commit"])[:12]
    lines = [
        f"# ArcheAxis Core candidate ({manifest['build_kind']}, source {commit})",
        "",
        f"Built {manifest['built_at']} from commit `{manifest['source_commit']}`",
        f"({manifest['source_commit_subject']}).",
        "",
        "## Verify before you run it",
        "",
        "```",
        f"python -X utf8 scripts/release/verify_candidate.py --candidate {'.'} ",
        f"python -X utf8 scripts/release/verify_candidate.py --candidate {'.'} --run",
        "```",
        "",
        "The first command re-hashes every file against `CANDIDATE.json`; the second also starts",
        "the binary, waits for it to report a port, and stops it.",
        "",
        "## Start it",
        "",
        "The Core reads a launch claim as one JSON line on stdin and prints its loopback port.",
        "Closing stdin is what tells it to continue:",
        "",
        "```",
        f'echo {{\\"launch_token\\": \\"<64 hex characters>\\", \\"session_id\\": \\"<32 hex characters>\\"}} | {binary} <database.sqlite> 0',
        "```",
        "",
        "## Stop, back up and restore it",
        "",
        "The repository's launcher implements these against a real database and is the supported",
        "path; run it from the repository root, not from this bundle:",
        "",
        "```",
        "python -X utf8 scripts/launch/core_launch.py --stop       # stops only the pid it recorded",
        "python -X utf8 scripts/launch/core_launch.py --backup     # VACUUM INTO, source opened read-only",
        "python -X utf8 scripts/launch/core_launch.py --restore --from <backup.sqlite>",
        "python -X utf8 scripts/launch/core_launch.py --check      # dependencies and ports",
        "```",
        "",
        "`--stop` refuses to kill a process whose image is not the Core, so a recycled process id",
        "cannot be mistaken for it. `--backup` opens the source read-only and records the digest, so",
        "it does not checkpoint the write-ahead log out from under a running Core.",
        "",
        "## What this bundle does not include",
        "",
    ]
    lines += [f"- {item}" for item in manifest["not_included"]]
    lines += [
        "",
        f"Note: {manifest['hash_meaning']}",
        "",
    ]
    return "\n".join(lines)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8", newline="\n")


def write_bundle(root: Path, files: list[Path], **manifest_kwargs) -> dict:
    """Write README.md and CANDIDATE.json for a bundle, and record both.

    The README is generated from the manifest and the manifest then records the README, so the
    order is: a draft manifest writes the README, and the final manifest is built from the files
    plus the README. Nothing in the bundle may be unrecorded, including the files this function
    writes itself.
    """
    draft = build_manifest(root, files, **manifest_kwargs)
    readme = root / "README.md"
    readme.write_text(readme_text(draft), encoding="utf-8", newline="\n")
    final = build_manifest(root, [*files, readme], **manifest_kwargs)
    if readme_text(final) != readme_text(draft):
        raise RuntimeError("the README depends on the file list, so it cannot be recorded by the manifest it is generated from")
    write_json(root / MANIFEST_NAME, final)
    return final
