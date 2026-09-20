"""Verify a project-local Green candidate without launching it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

REQUIRED = (
    "启动绿色候选.vbs",
    "desktop/ArcheAxis.Desktop.exe",
    "desktop/hostfxr.dll",
    "desktop/hostpolicy.dll",
    "desktop/ArcheAxis.Desktop.runtimeconfig.json",
    "core/archeaxis-api.exe",
)
WORKER_REQUIRED = ("worker-profile.json", "workers/transport/text_ndjson.py")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path(candidate: Path, relative: object) -> Path | None:
    """Resolve a manifest path only when it is a normalized relative path."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        return None
    parsed = PurePosixPath(relative)
    if parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        return None
    return candidate.joinpath(*parsed.parts)


def _validate_manifest_files(candidate: Path, files: object, problems: list[str]) -> dict:
    """Validate every manifest entry without assuming required files are present."""
    if not isinstance(files, dict):
        problems.append("candidate files manifest is missing or invalid")
        return {}
    for relative, entry in files.items():
        path = _manifest_path(candidate, relative)
        if path is None:
            problems.append(f"unsafe candidate manifest path: {relative!r}")
            continue
        if not isinstance(entry, dict):
            problems.append(f"invalid candidate manifest entry: {relative}")
            continue
        if path.is_symlink() or not path.is_file():
            problems.append(f"manifest file missing from candidate: {relative}")
            continue
        expected_bytes = entry.get("bytes")
        if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes < 0:
            problems.append(f"invalid byte count in candidate manifest: {relative}")
        elif path.stat().st_size != expected_bytes:
            problems.append(f"byte count mismatch: {relative}")
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or not _SHA256_RE.fullmatch(expected_hash):
            problems.append(f"invalid sha256 in candidate manifest: {relative}")
        elif _sha256(path) != expected_hash:
            problems.append(f"hash mismatch: {relative}")
    return files


def _reject_unmanifested_files(candidate: Path, files: dict, problems: list[str]) -> None:
    """Reject files present in the candidate tree but absent from its manifest.

    The manifest is the candidate's completeness receipt.  Accepting an extra file
    would let an unrecorded payload survive verification and then enter a release
    archive without a hash or byte-count check.
    """
    recorded = set(files)
    for path in candidate.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(candidate).as_posix()
        if relative == "candidate-manifest.json":
            continue
        if relative not in recorded:
            problems.append(f"unmanifested file in candidate: {relative}")


def verify(
    candidate: Path,
    *,
    require_runtime: bool = False,
    require_workers: bool = False,
    require_provenance: bool = False,
    expected_commit: str | None = None,
    expected_tree: str | None = None,
) -> dict:
    candidate = candidate.resolve()
    manifest_path = candidate / "candidate-manifest.json"
    problems: list[str] = []
    if not candidate.is_dir():
        return {"ok": False, "problems": ["candidate directory is missing"]}
    if not manifest_path.is_file():
        return {"ok": False, "problems": ["candidate-manifest.json is missing"]}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "problems": [f"manifest unreadable: {exc}"]}
    if manifest.get("schema") != "archeaxis.green-candidate/v1":
        problems.append("unexpected candidate schema")
    provenance = manifest.get("provenance")
    if require_provenance:
        if not isinstance(provenance, dict):
            problems.append("candidate provenance is missing or invalid")
        else:
            for field in ("source_commit", "source_tree"):
                value = provenance.get(field)
                if not isinstance(value, str) or not value.strip():
                    problems.append(f"candidate provenance {field} is missing or blank")
    if expected_commit is not None or expected_tree is not None:
        if not isinstance(provenance, dict):
            if not require_provenance:
                problems.append("candidate provenance is missing")
        else:
            if expected_commit is not None and provenance.get("source_commit") != expected_commit:
                problems.append("candidate source commit mismatch")
            if expected_tree is not None and provenance.get("source_tree") != expected_tree:
                problems.append("candidate source tree mismatch")
    files = _validate_manifest_files(candidate, manifest.get("files"), problems)
    _reject_unmanifested_files(candidate, files, problems)
    for relative in REQUIRED:
        path = candidate / relative
        entry = files.get(relative)
        if not path.is_file() or not isinstance(entry, dict):
            problems.append(f"required file missing from candidate: {relative}")
            continue
        if _sha256(path) != entry.get("sha256"):
            problems.append(f"hash mismatch: {relative}")
    runtime_included = any(name.startswith("runtime/") for name in files)
    if require_runtime and not runtime_included:
        problems.append("runtime directory is required for a complete Green candidate")
    workers_included = any(name.startswith("workers/") for name in files)
    if require_workers:
        for relative in WORKER_REQUIRED:
            path = candidate / relative
            entry = files.get(relative)
            if not path.is_file() or not isinstance(entry, dict):
                problems.append(f"required worker file missing from candidate: {relative}")
                continue
            if _sha256(path) != entry.get("sha256"):
                problems.append(f"hash mismatch: {relative}")
    return {
        "ok": not problems,
        "scope": "desktop-core-runtime-workers" if workers_included else ("desktop-core-runtime" if runtime_included else "desktop-core-only"),
        "runtime_included": runtime_included,
        "workers_included": workers_included,
        "version": manifest.get("version"),
        "files": len(files),
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--require-runtime", action="store_true")
    parser.add_argument("--require-workers", action="store_true")
    parser.add_argument(
        "--require-provenance",
        action="store_true",
        help="fail unless source_commit and source_tree are present and non-blank",
    )
    parser.add_argument("--expected-commit")
    parser.add_argument("--expected-tree")
    args = parser.parse_args()
    result = verify(
        args.candidate,
        require_runtime=args.require_runtime,
        require_workers=args.require_workers,
        require_provenance=args.require_provenance,
        expected_commit=args.expected_commit,
        expected_tree=args.expected_tree,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
