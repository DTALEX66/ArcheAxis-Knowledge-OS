"""R13: the legacy Core-only candidate manifest and its verification rules.

A candidate is a small directory plus a manifest that binds every file in it to a source
commit by sha256. The manifest is deliberately explicit about what is **not** in the bundle -
no installer, no code signing, no Python runtime, no workers.  This module describes the
legacy Core-only candidate schema; the newer Green candidate is assembled and verified by
``assemble_green_candidate.py``/``verify_green_candidate.py`` and has an explicit runtime scope.

This module holds the rules and imports nothing that needs a toolchain, so it can be tested
without building anything.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path

SCHEMA = "archeaxis.candidate/v1"
MANIFEST_NAME = "CANDIDATE.json"


def safe_bundle_path(root: Path, relative: str = "") -> Path:
    if os.fspath(root).replace('\\', '/').casefold().startswith(('e:', 'f:', '//')):
        raise ValueError("unsafe bundle root")
    root = Path(os.path.abspath(root))
    if root.drive.upper() in {"E:", "F:"} or str(root).startswith("\\\\"):
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

_UNTRACKED_BUILD_ROOTS = {
    "apps", "config", "crates", "packages", "scripts", "services", "shared", "tests"
}
_UNTRACKED_BUILD_FILES = {
    "Cargo.toml", "Cargo.lock", "pyproject.toml", "uv.lock", "Directory.Build.props",
    "Directory.Build.targets", "global.json", "NuGet.Config", "nuget.config",
}
_PRIVATE_COMPONENTS = {
    ".codex", ".hermes", ".zcode", "profile", "profiles", "browser-profile",
    "browser_profiles", "web-chain-debug",
}
_PRIVATE_NAME = re.compile(
    r"(?i)^(?:\.env(?:\..*)?|credentials?(?:\..*)?|cookies?|login data|local state|"
    r"id_(?:rsa|ed25519)|.*\.(?:pem|p12|pfx|key))$"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def read_source_snapshot(path: Path, *, project_root: Path) -> dict[str, str | int]:
    """Read and validate a source snapshot receipt captured before compilation."""
    path = Path(os.path.abspath(path))
    allowed = (Path(project_root).resolve() / ".project-local" / "runs").resolve()
    try:
        path.relative_to(allowed)
    except ValueError as exc:
        raise ValueError("source snapshot receipt must stay under project .project-local/runs") from exc
    for ancestor in (*reversed(path.parents), path):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked source snapshot receipt path is not allowed")
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"source snapshot receipt is unreadable: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != "aaos.source-snapshot-receipt/v1":
        raise ValueError("source snapshot receipt has an unsupported schema")
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("algorithm") != "aaos-source-snapshot/v1":
        raise ValueError("source snapshot receipt has no supported snapshot")
    for name in ("sha256", "excluded_paths_sha256"):
        if not isinstance(snapshot.get(name), str) or not _SHA256_RE.fullmatch(snapshot[name]):
            raise ValueError(f"source snapshot receipt has an invalid {name}")
    for name in ("file_count", "untracked_build_input_count", "excluded_path_count"):
        value = snapshot.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"source snapshot receipt has an invalid {name}")
    return snapshot


def working_tree_snapshot(root: Path) -> dict[str, str | int]:
    """Fingerprint Git-tracked source plus untracked build inputs without reading private state.

    Ignored files (including project-local build outputs), docs, browser-profile
    components, and credential-shaped names are excluded from content hashing. Their path
    names contribute to a separate exclusion digest so additions/removals are visible without
    opening their contents. Untracked files outside declared build-input roots are similarly
    path-only exclusions because they cannot enter the supported product build by default.
    """
    root = Path(os.path.abspath(root))
    if root.drive.upper() in {"E:", "F:"} or str(root).startswith("\\\\"):
        raise ValueError("protected source worktree root")

    def git_bytes(*args: str) -> bytes:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, check=False
        )
        if result.returncode:
            raise ValueError(result.stderr.decode("utf-8", "replace").strip() or "git query failed")
        return result.stdout

    top = Path(os.fsdecode(git_bytes("rev-parse", "--show-toplevel").strip())).resolve()
    if top != root.resolve():
        raise ValueError("source snapshot requires the exact Git worktree root")

    tracked = {os.fsdecode(item) for item in git_bytes("ls-files", "--cached", "-z").split(b"\0") if item}
    untracked = {os.fsdecode(item) for item in git_bytes("ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if item}
    entries: list[tuple[str, str, str]] = []
    excluded: list[tuple[str, str]] = []
    for relative in sorted(tracked | untracked, key=lambda value: value.encode("utf-8", "surrogateescape")):
        normalized = relative.replace("\\", "/")
        parts = normalized.split("/")
        folded_parts = {part.casefold() for part in parts}
        name = parts[-1]
        # Governance and execution records are not compiler inputs. Excluding
        # their contents also lets the Candidate receipt be recorded without
        # invalidating the build identity it documents.
        if parts[0].casefold() == "docs":
            continue
        if folded_parts & _PRIVATE_COMPONENTS or _PRIVATE_NAME.fullmatch(name):
            excluded.append((normalized, "private-or-sensitive-path"))
            continue
        if relative in untracked and relative not in tracked:
            top_component = parts[0]
            if top_component not in _UNTRACKED_BUILD_ROOTS and name not in _UNTRACKED_BUILD_FILES:
                excluded.append((normalized, "untracked-outside-build-input-roots"))
                continue

        path = root.joinpath(*parts)
        try:
            info = path.lstat()
        except FileNotFoundError:
            entries.append((normalized, "missing", ""))
            continue
        if stat.S_ISLNK(info.st_mode):
            link_target = os.readlink(path).encode("utf-8", "surrogateescape")
            content_digest = hashlib.sha256(link_target).hexdigest()
            kind = "symlink"
        elif stat.S_ISREG(info.st_mode):
            content_digest = sha256_of(path)
            kind = "file"
        else:
            raise ValueError(f"unsupported non-file source input at {normalized}")
        entries.append((normalized, kind, content_digest))

    digest = hashlib.sha256()
    for relative, kind, content_digest in entries:
        for field in (relative, kind, content_digest):
            raw = field.encode("utf-8", "surrogateescape")
            digest.update(len(raw).to_bytes(8, "big"))
            digest.update(raw)
    excluded_digest = hashlib.sha256()
    for relative, reason in sorted(excluded):
        for field in (relative, reason):
            raw = field.encode("utf-8", "surrogateescape")
            excluded_digest.update(len(raw).to_bytes(8, "big"))
            excluded_digest.update(raw)
    return {
        "algorithm": "aaos-source-snapshot/v1",
        "sha256": digest.hexdigest(),
        "file_count": len(entries),
        "untracked_build_input_count": sum(relative in untracked and relative not in tracked for relative, _, _ in entries),
        "excluded_path_count": len(excluded),
        "excluded_paths_sha256": excluded_digest.hexdigest(),
    }


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
    source_snapshot: dict | None = None,
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
        "source_snapshot": source_snapshot,
        "files": sorted((file_fact(path, root) for path in files), key=lambda item: item["path"]),
        "not_included": NOT_INCLUDED,
        "route_note": ROUTE_NOTE,
        "verification": [
            "python -X utf8 scripts/release/verify_candidate.py --candidate <this directory>",
            "python -X utf8 scripts/release/verify_candidate.py --candidate <this directory> --require-current-source",
            "python -X utf8 scripts/release/verify_candidate.py --candidate <this directory> --run",
        ],
        "hash_meaning": (
            "a digest binds these bytes to this manifest; it is not a signature and it says nothing "
            "about who produced the bundle"
        ),
    }


def verify_manifest(
    root: Path,
    manifest: dict,
    *,
    known_commits: set[str] | None = None,
    expected_source_snapshot: dict | None = None,
    current_source_root: Path | None = None,
) -> list[str]:
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
    recorded_snapshot = manifest.get("source_snapshot")
    if expected_source_snapshot is not None and recorded_snapshot != expected_source_snapshot:
        problems.append("the candidate source snapshot differs from the snapshot captured for this build")
    if current_source_root is not None:
        try:
            current_snapshot = working_tree_snapshot(current_source_root)
        except (OSError, ValueError) as exc:
            problems.append(f"the current source snapshot could not be read: {exc}")
        else:
            if not isinstance(recorded_snapshot, dict):
                problems.append("the candidate has no source snapshot to compare with the current worktree")
            elif recorded_snapshot != current_snapshot:
                problems.append("the current worktree differs from the candidate source snapshot")

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
        "python -X utf8 scripts/launch/core_launch.py --backup     # Rust Core snapshot + raw-object store",
        "python -X utf8 scripts/launch/core_launch.py --restore --from <backup.sqlite>",
        "python -X utf8 scripts/launch/core_launch.py --check      # dependencies and ports",
        "```",
        "",
        "`--stop` refuses to kill a process whose image is not the Core, so a recycled process id",
        "cannot be mistaken for it. Backup and restore database operations run only inside the Rust",
        "Core under its writer lock; the Python launcher records hashes and reports the Core receipt.",
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
