"""R15/F15: put a folder into the workspace, one file at a time, resumably.

The archive route reads one container; nothing read a *directory*. This driver walks a folder,
imports each file as its own source through the Core's own HTTP API, enqueues the job the file's
kind calls for, and appends one JSONL line per attempt.

Three rules it will not bend:

* **the latest attempt per path decides.** A later failure is never hidden by an earlier
  success, and a later success does not hide a failure that is still the latest word on a file
  whose content has changed;
* **the driver never guesses a kind.** A file whose extension it has no kind for is imported and
  recorded as carrying no job, with the reason, rather than being silently skipped or handed to a
  route that would refuse it;
* **the Core stays the authority.** A refusal is recorded in the Core's own words.

Nothing here holds a database handle: every step is one HTTP call, and the Core remains the only
writer.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

SCHEMA = "archeaxis.directory-batch/v1"
MANIFEST_SCHEMA = "archeaxis.directory-batch-entry/v1"

# The kind each extension calls for. Kinds are the Core's route kinds; a test checks every
# extension here against the Core's own media-type table so this cannot invent one.
KIND_BY_EXTENSION = {
    "txt": "text", "log": "text", "text": "text", "rs": "text", "py": "text", "ts": "text",
    "tsx": "text", "js": "text", "jsx": "text", "c": "text", "h": "text", "cpp": "text",
    "hpp": "text", "go": "text", "java": "text", "cs": "text", "rb": "text", "sh": "text",
    "ps1": "text", "bat": "text", "toml": "text", "yaml": "text", "yml": "text", "ini": "text",
    "cfg": "text", "sql": "text", "md": "text", "markdown": "text", "csv": "text",
    "tsv": "text", "json": "text", "xml": "text",
    "pdf": "pdf",
    "zip": "archive",
    "png": "image", "jpg": "image", "jpeg": "image", "webp": "image", "bmp": "image",
    "tif": "image", "tiff": "image",
    "wav": "media", "mp4": "media", "m4v": "media", "mov": "media",
    "docx": "office", "pptx": "office", "xlsx": "office",
    "canvas": "canvas",
    "srt": "subtitles", "vtt": "subtitles",
    "html": "html", "htm": "html", "xhtml": "html",
}

# Directories that are never part of a user's document folder. Skipped, and counted, so the
# omission is visible in the receipt rather than silent.
EXCLUDED_DIRS = frozenset(
    {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", ".project-local",
     ".hermes", ".cache", "dist", "build", "target"}
)

STATUSES = ("enqueued", "already_enqueued", "imported_no_job", "refused", "failed", "skipped_unchanged")
# What counts as "nothing more to do with this content". `imported_no_job` belongs here: the
# reason is the extension, which will not change between runs, so retrying would import the same
# file again and again and pile up duplicate sources. A refusal or a failure is retried, because
# either can be transient or fixable.
RESUMABLE_STATUSES = frozenset({"enqueued", "already_enqueued", "imported_no_job"})


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path, *, limit: int | None = None) -> tuple[list[Path], list[str]]:
    """The files of a folder, and the paths that were left out, both explicit."""
    if not root.is_dir():
        raise ValueError(f"not a folder: {root}")
    files: list[Path] = []
    skipped: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
        if any(part in EXCLUDED_DIRS or (part.startswith(".") and part not in {".", ".."}) for part in parts[:-1]):
            skipped.append(f"{relative} (excluded directory)")
            continue
        if path.is_dir():
            continue
        if path.name.startswith("."):
            skipped.append(f"{relative} (hidden file)")
            continue
        if not path.is_file():
            skipped.append(f"{relative} (not a regular file)")
            continue
        files.append(path)
    if limit is not None:
        for path in files[limit:]:
            skipped.append(f"{path.relative_to(root).as_posix()} (over the limit of {limit})")
        files = files[:limit]
    return files, skipped


def latest_by_path(records: list[dict]) -> dict[str, dict]:
    """The latest attempt per source path: the record that speaks for a file now."""
    latest: dict[str, dict] = {}
    for record in records:
        path = str(record.get("path") or "")
        if path:
            latest[path] = record
    return latest


def latest_decidable_by_path(records: list[dict]) -> dict[str, dict]:
    """The latest attempt that actually *did* something, per source path.

    A `skipped_unchanged` record says nothing was done, so it can never be the last word on
    whether work is needed: without this filter a third run re-processes the whole folder,
    because the second run's skip overwrote the "job already enqueued for this content" fact.
    Measured against a real Core, and the reason this function exists.
    """
    return latest_by_path([record for record in records if record.get("status") != "skipped_unchanged"])


def decide(latest: dict | None, digest: str) -> tuple[bool, str]:
    """Whether to process a file again, and why. Only the latest attempt is consulted."""
    if latest is None:
        return True, "no earlier attempt"
    if str(latest.get("sha256") or "") != digest:
        return True, "the content changed since the last attempt"
    status = str(latest.get("status") or "")
    if status in RESUMABLE_STATUSES:
        return False, f"unchanged and the last attempt was {status}"
    return True, f"unchanged but the last attempt was {status or 'unrecorded'}"


def read_manifest(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def append_records(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def run_batch(
    root: Path,
    *,
    core_call: Callable[[str, str, dict | None], tuple[int, object]],
    manifest_path: Path,
    resume: bool = True,
    limit: int | None = None,
    dry_run: bool = False,
    job_prefix: str = "batch",
    now: str | None = None,
) -> dict:
    """Walk a folder and put it into the workspace. Returns the receipt, and writes the JSONL."""
    files, skipped = iter_files(root, limit=limit)
    previous = latest_decidable_by_path(read_manifest(manifest_path)) if resume else {}
    stamp = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries: list[dict] = []
    counts = dict.fromkeys(STATUSES, 0)

    for path in files:
        relative = path.relative_to(root).as_posix()
        digest = sha256_of(path)
        should_run, why = decide(previous.get(relative), digest) if resume else (True, "resume is off")
        entry = {
            "schema": MANIFEST_SCHEMA,
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": digest,
            "kind": KIND_BY_EXTENSION.get(path.suffix.lower().lstrip(".")),
            "at": stamp,
        }
        if not should_run:
            entry.update({"status": "skipped_unchanged", "detail": why})
            counts["skipped_unchanged"] += 1
            entries.append(entry)
            continue
        if dry_run:
            entry.update({"status": "skipped_unchanged", "detail": f"dry run: would import ({why})"})
            counts["skipped_unchanged"] += 1
            entries.append(entry)
            continue

        status, body = core_call("POST", "/api/v1/imports", {
            "name": relative,
            "content_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
        })
        if status not in (200, 201, 202) or not isinstance(body, dict) or not body.get("source_id"):
            entry.update({"status": "refused", "detail": f"the Core refused the import with status {status}: {body}"})
            counts["refused"] += 1
            entries.append(entry)
            continue
        entry["source_id"] = body["source_id"]

        if entry["kind"] is None:
            entry.update({
                "status": "imported_no_job",
                "detail": (
                    f"no kind is mapped for {path.suffix or 'a file with no extension'}, so no job was "
                    "enqueued: the driver will not hand a file to a route that would refuse it"
                ),
            })
            counts["imported_no_job"] += 1
            entries.append(entry)
            continue

        job_id = f"{job_prefix}-{digest[:12]}"
        status, body = core_call("POST", "/api/v1/jobs", {"job_id": job_id, "kind": entry["kind"], "input_ref": entry["source_id"]})
        entry["job_id"] = job_id
        if status in (200, 201, 202):
            entry.update({"status": "enqueued", "detail": f"{entry['kind']} job accepted"})
            counts["enqueued"] += 1
        elif status == 409:
            entry.update({"status": "already_enqueued", "detail": f"the Core already holds job {job_id} for this content"})
            counts["already_enqueued"] += 1
        else:
            entry.update({"status": "failed", "detail": f"the Core refused the {entry['kind']} job with status {status}: {body}"})
            counts["failed"] += 1
        entries.append(entry)

    if entries and not dry_run:
        append_records(manifest_path, entries)

    return {
        "schema": SCHEMA,
        "root": str(root),
        "manifest": str(manifest_path),
        "dry_run": dry_run,
        "resume": resume,
        "files_seen": len(files),
        "excluded_paths": skipped,
        "excluded_count": len(skipped),
        "counts": counts,
        "entries": entries,
        "note": (
            "one JSONL line per attempt; the latest attempt per path decides what happens next, so a "
            "later failure is never hidden by an earlier success"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="import a folder into the Core, resumably")
    parser.add_argument("--root", type=Path, required=True, help="the folder to walk")
    parser.add_argument("--core", default=None, help="Core base URL (default ARCHEAXIS_CORE_BASE)")
    parser.add_argument("--token-env", default="ARCHEAXIS_CORE_TOKEN", help="environment variable holding the launch token")
    parser.add_argument("--manifest", type=Path, default=None, help="JSONL manifest (default under .project-local/runs)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true", help="ignore earlier attempts")
    parser.add_argument("--dry-run", action="store_true", help="report what would happen, write nothing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    base = (args.core or os.environ.get("ARCHEAXIS_CORE_BASE") or "").strip()
    if not base:
        print("no Core base URL: pass --core or set ARCHEAXIS_CORE_BASE", file=sys.stderr)
        return 2
    if not args.root.is_dir():
        print(f"not a folder: {args.root}", file=sys.stderr)
        return 3

    import importlib.util

    repo = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("core_client_for_batch", repo / "shared" / "core_client.py")
    if spec is None or spec.loader is None:
        print("shared/core_client.py is missing", file=sys.stderr)
        return 4
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    token = os.environ.get(args.token_env) or None
    manifest = args.manifest or (repo / ".project-local" / "runs" / "directory-batch" / f"{args.root.name}.jsonl")

    receipt = run_batch(
        args.root,
        core_call=lambda method, path, body: core.call(base, method, path, token, body),
        manifest_path=manifest,
        resume=not args.no_resume,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        counts = receipt["counts"]
        print(
            f"walked {receipt['files_seen']} file(s) in {receipt['root']}: "
            + ", ".join(f"{name} {count}" for name, count in counts.items() if count)
            + f"; {receipt['excluded_count']} path(s) excluded; manifest {receipt['manifest']}"
        )
    return 0 if counts_ok(receipt["counts"]) else 5


def counts_ok(counts: dict) -> bool:
    """A batch with refused or failed files is not a success, however many succeeded."""
    return not counts.get("refused") and not counts.get("failed")


if __name__ == "__main__":
    raise SystemExit(main())
