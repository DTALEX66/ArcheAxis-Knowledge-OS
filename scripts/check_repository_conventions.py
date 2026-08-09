"""Repository naming and text-encoding convention checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

import yaml

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from shared.naming import NamingRegistry, NamingRegistryError  # noqa: E402

_BINARY_SUFFIXES = {
    ".7z",
    ".avi",
    ".db",
    ".dll",
    ".doc",
    ".docx",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".pyc",
    ".sqlite",
    ".tar",
    ".wav",
    ".webm",
    ".webp",
    ".xls",
    ".xlsx",
    ".zip",
}
_RESERVED_WINDOWS_NAMES = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
_ZERO_WIDTH = {"\u200b", "\u200c", "\u200d", "\u2060"}
_WINDOWS_EOL_SUFFIXES = {".bat", ".cmd", ".ps1"}
_FROZEN_DOCUMENT_HASHES = {
    "docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md": (
        "ef3066231d8251562c6b9fb361e9a0a0424c100c6c27b6ec4de8ebba7b585155"
    ),
    "docs/taskpacks/MANDATORY_WEB_KNOWLEDGE_INGESTION_ADDENDUM_v1_2026-08-09.md": (
        "971e0ee9ba32f6b30c8d8435dbb4d5c46574f0dbba96210ce00076055afedb19"
    ),
    "docs/taskpacks/MANDATORY_CAPABILITY_FIRST_KNOWLEDGE_LIFECYCLE_ADDENDUM_v1_2026-08-09.md": (
        "2bfd1192b3119121fd921c59721890d751adbdcb9383fa4d9b15ce714a4ed288"
    ),
}


@dataclass(frozen=True, order=True)
class ConventionIssue:
    code: str
    path: str
    detail: str


def _is_declared_binary(path: str, content: bytes) -> bool:
    return PurePosixPath(path).suffix.casefold() in _BINARY_SUFFIXES or b"\0" in content


def normalize_text_bytes(path: str, content: bytes) -> bytes:
    """Normalize a UTF-8 text file without changing words or path identity."""
    if _is_declared_binary(path, content):
        return content
    text = content.decode("utf-8-sig")
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    normalized = "\n".join(line.rstrip(" \t") for line in text.split("\n"))
    if normalized and not normalized.endswith("\n"):
        normalized += "\n"
    if PurePosixPath(path).suffix.casefold() in _WINDOWS_EOL_SUFFIXES:
        normalized = normalized.replace("\n", "\r\n")
    return normalized.encode("utf-8")


def scan_text_bytes(path: str, content: bytes) -> list[ConventionIssue]:
    """Return deterministic text-contract violations for one repository path."""
    if _is_declared_binary(path, content):
        return []
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [ConventionIssue("invalid-utf8", path, str(exc))]

    issues: list[ConventionIssue] = []
    if content.startswith(b"\xef\xbb\xbf"):
        issues.append(ConventionIssue("unexpected-bom", path, "UTF-8 BOM is prohibited"))
    windows_eol = PurePosixPath(path).suffix.casefold() in _WINDOWS_EOL_SUFFIXES
    invalid_carriage_return = (
        b"\r" in content.replace(b"\r\n", b"") if windows_eol else b"\r" in content
    )
    if invalid_carriage_return:
        issues.append(
            ConventionIssue(
                "crlf",
                path,
                "only Windows command files may use CRLF; lone CR is prohibited",
            )
        )
    if unicodedata.normalize("NFC", text) != text:
        issues.append(ConventionIssue("non-nfc-text", path, "text must be Unicode NFC"))
    body = text[1:] if text.startswith("\ufeff") else text
    if any(character in body for character in _ZERO_WIDTH) or "\ufeff" in body:
        issues.append(
            ConventionIssue(
                "zero-width-character",
                path,
                "prohibited invisible Unicode character",
            )
        )
    if content and not content.endswith(b"\n"):
        issues.append(
            ConventionIssue("missing-final-newline", path, "text must end with LF")
        )
    if any(line.rstrip(" \t") != line for line in text.splitlines()):
        issues.append(
            ConventionIssue("trailing-whitespace", path, "line ends with space or tab")
        )
    return sorted(issues)


def scan_naming_registry_bytes(path: str, content: bytes) -> list[ConventionIssue]:
    """Validate the naming registry schema and alias ownership."""
    try:
        payload = yaml.safe_load(content.decode("utf-8-sig"))
        if not isinstance(payload, dict):
            raise NamingRegistryError("naming registry root must be a mapping")
        NamingRegistry.from_mapping(payload)
    except (UnicodeDecodeError, yaml.YAMLError, NamingRegistryError) as exc:
        return [ConventionIssue("invalid-naming-registry", path, str(exc))]
    return []


def scan_frozen_document_bytes(path: str, content: bytes) -> list[ConventionIssue]:
    """Reject accidental edits to owner-approved frozen comparison baselines."""
    expected = _FROZEN_DOCUMENT_HASHES.get(path)
    if expected is None:
        return []
    actual = hashlib.sha256(content).hexdigest()
    if actual == expected:
        return []
    return [
        ConventionIssue(
            "frozen-document-modified",
            path,
            f"expected sha256 {expected}, got {actual}",
        )
    ]


def scan_path_set(paths: list[str]) -> list[ConventionIssue]:
    """Return cross-platform path and collision violations."""
    issues: list[ConventionIssue] = []
    folded: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        normalized = unicodedata.normalize("NFC", path)
        if normalized != path:
            issues.append(ConventionIssue("non-nfc-path", path, f"use {normalized!r}"))
        folded[normalized.casefold()].append(path)
        for part in PurePosixPath(path).parts:
            base = part.rstrip(" .").split(".", 1)[0].casefold()
            if base in _RESERVED_WINDOWS_NAMES:
                issues.append(
                    ConventionIssue(
                        "windows-reserved-name",
                        path,
                        f"reserved Windows path component: {part!r}",
                    )
                )
            if part.endswith((" ", ".")) or re.search(r'[<>:"|?*]', part):
                issues.append(
                    ConventionIssue(
                        "windows-invalid-name",
                        path,
                        f"cross-platform-invalid path component: {part!r}",
                    )
                )
    for variants in folded.values():
        if len(variants) > 1:
            joined = ", ".join(sorted(variants))
            issues.append(
                ConventionIssue(
                    "case-path-collision",
                    sorted(variants)[0],
                    f"case-insensitive collision: {joined}",
                )
            )
    return sorted(issues)


def _read_git_blobs(root: Path, object_ids: list[str]) -> list[bytes]:
    """Read Git blobs in one process instead of spawning ``git show`` per file."""
    if not object_ids:
        return []
    result = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=root,
        input="".join(f"{object_id}\n" for object_id in object_ids).encode("ascii"),
        capture_output=True,
        check=True,
    )
    output = result.stdout
    cursor = 0
    contents: list[bytes] = []
    for expected_object_id in object_ids:
        header_end = output.find(b"\n", cursor)
        if header_end < 0:
            raise RuntimeError("truncated git cat-file batch header")
        header = output[cursor:header_end].decode("ascii").split()
        if len(header) != 3 or header[1] != "blob":
            raise RuntimeError(f"expected Git blob {expected_object_id}, got: {' '.join(header)}")
        size = int(header[2])
        content_start = header_end + 1
        content_end = content_start + size
        if content_end >= len(output) or output[content_end : content_end + 1] != b"\n":
            raise RuntimeError(f"truncated git cat-file batch body for {expected_object_id}")
        contents.append(output[content_start:content_end])
        cursor = content_end + 1
    return contents


def _git_blob_entries(root: Path, source: str) -> list[tuple[str, str]]:
    if source == "head":
        command = ["git", "ls-tree", "-r", "-z", "HEAD"]
        raw_entries = subprocess.run(command, cwd=root, capture_output=True, check=True).stdout
        entries: list[tuple[str, str]] = []
        for record in raw_entries.split(b"\0")[:-1]:
            metadata, raw_path = record.split(b"\t", 1)
            _, object_type, object_id = metadata.decode("ascii").split()
            if object_type == "blob":
                entries.append((raw_path.decode("utf-8"), object_id))
        return entries

    raw_entries = subprocess.run(
        ["git", "ls-files", "-s", "-z"], cwd=root, capture_output=True, check=True
    ).stdout
    entries = []
    for record in raw_entries.split(b"\0")[:-1]:
        metadata, raw_path = record.split(b"\t", 1)
        _, object_id, stage = metadata.decode("ascii").split()
        if stage != "0":
            raise RuntimeError(f"index contains an unmerged path: {raw_path.decode('utf-8')}")
        entries.append((raw_path.decode("utf-8"), object_id))
    return entries


def scan_git_repository(root: Path, *, source: str = "worktree") -> list[ConventionIssue]:
    """Scan tracked paths from the worktree, index, or HEAD without mixing sources."""
    if source not in {"worktree", "index", "head"}:
        raise ValueError(f"unsupported Git source: {source!r}")

    blob_contents: dict[str, bytes] = {}
    if source == "worktree":
        raw_paths = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
        ).stdout
        paths = raw_paths.decode("utf-8").split("\0")[:-1]
    else:
        entries = _git_blob_entries(root, source)
        paths = [path for path, _ in entries]
        contents = _read_git_blobs(root, [object_id for _, object_id in entries])
        blob_contents = dict(zip(paths, contents, strict=True))

    issues = scan_path_set(paths)
    for path in paths:
        if source == "worktree":
            candidate = root / Path(*PurePosixPath(path).parts)
            if not candidate.is_file():
                issues.append(
                    ConventionIssue(
                        "missing-worktree-file",
                        path,
                        "tracked path is absent from the worktree",
                    )
                )
                continue
            content = candidate.read_bytes()
        else:
            content = blob_contents[path]
        issues.extend(scan_text_bytes(path, content))
        issues.extend(scan_frozen_document_bytes(path, content))
        if path == "config/naming-registry.yaml":
            issues.extend(scan_naming_registry_bytes(path, content))
    return sorted(issues)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument(
        "--source",
        choices=("worktree", "index", "head"),
        default="worktree",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    issues = scan_git_repository(args.root.resolve(), source=args.source)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "source": args.source,
                    "issue_count": len(issues),
                    "issues": [asdict(issue) for issue in issues],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif issues:
        for issue in issues:
            print(f"{issue.path}: {issue.code}: {issue.detail}")
        print(f"repository convention check failed: {len(issues)} issue(s)")
    else:
        print(f"repository convention check passed ({args.source})")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
