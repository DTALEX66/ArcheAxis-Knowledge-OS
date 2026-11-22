"""Save the fixed revision of a git archive ZIP and retrieve its original files through Core."""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

from scripts.ingest.obsidian_sync import install_if_absent
from scripts.ingest.obsidian_vault import digest, original_bytes
from shared import core_client


def read_snapshot(call, job_id, expected_commit=None):
    transform, loss = core_client.archive_job_result(call, job_id, "zip-or-uncompressed-tar-single-level")
    source, revision = transform["source_id"], transform["raw_sha256"]
    raw = original_bytes(call, source, revision)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if not re.fullmatch(rb"(?:[0-9a-f]{40}|[0-9a-f]{64})", archive.comment):
            raise ValueError("select a git archive ZIP produced from a commit or tag")
        commit = archive.comment.decode("ascii")
        if expected_commit is not None and expected_commit.lower() != commit:
            raise ValueError("the ZIP comment differs from the selected commit")
        file_count = sum(not item.is_dir() for item in archive.infolist())

    declared = {(item["name"], item["sha256"]) for item in loss["params"]["structure"]["extractable_members"]}
    family = call("GET", f"/api/v1/sources/{source}/members")
    members = {row["member"]: {"path": row["member"], "source_id": row["source_id"], "sha256": row["sha256"]}
               for row in family["members"] if (row["member"], row["sha256"]) in declared}
    if {(row["path"], row["sha256"]) for row in members.values()} != declared:
        raise ValueError("the archive job's member revisions do not match the stored sources")
    index = {"schema": "archeaxis.git-snapshot/v1", "commit": commit, "commit_basis": "zip_comment",
             "archive_files": file_count, "members": [members[key] for key in sorted(members)]}
    return source, revision, raw, index


def save_snapshot(call, job_id, expected_commit=None):
    source, revision, _, index = read_snapshot(call, job_id, expected_commit)
    lines = [f"Git commit {index['commit']}", *(item["path"] for item in index["members"])]
    editor = {"type": "doc", "attrs": {"archeaxis_git_snapshot": index}, "content": [
        {"type": "paragraph", "attrs": {"block_id": f"git-{i}"},
         "content": [{"type": "text", "text": line}]} for i, line in enumerate(lines)]}
    index_hash = digest(json.dumps(index, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())
    document = call("POST", "/api/v1/documents", {"create_request_id": "git-" + digest((revision + index_hash).encode()),
                    "title": "Git · " + index["commit"][:12], "source_id": source, "source_revision": revision,
                    "editor_json": editor})
    return {"document_id": document["document_id"], "version": document["version"], "source_id": source,
            "source_revision": revision, **index}


def export_original(call, job_id, expected_commit, member, output):
    source, revision, raw, index = read_snapshot(call, job_id, expected_commit)
    if member is not None:
        item = next((item for item in index["members"] if item["path"] == member), None)
        if item is None:
            raise ValueError("this path has no separately retained source in the selected archive job")
        source, revision = item["source_id"], item["sha256"]
        raw = original_bytes(call, source, revision)
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        staged = Path(directory) / "original"
        staged.write_bytes(raw)
        install_if_absent(staged, output)
    return {"commit": index["commit"], "source_id": source, "sha256": revision,
            "member": member, "output": str(output), "bytes": len(raw)}


def main(argv=None, *, session=None):
    parser = argparse.ArgumentParser(description=__doc__)
    token = core_client.configure_cli_connection(parser, session)
    actions = parser.add_subparsers(dest="action", required=True)
    save = actions.add_parser("save", help="save a revision index from a completed archive job")
    export = actions.add_parser("export", help="write the original ZIP or one retained member")
    for command in (save, export):
        command.add_argument("--job", required=True)
        command.add_argument("--commit", help="check the full Git object name before saving or exporting")
    export.add_argument("--member", help="exact repository-relative file path")
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.core:
        parser.error("pass --core or set ARCHEAXIS_CORE_BASE")

    def call(method, path, body=None):
        status, value = core_client.call(args.core, method, path, token, body)
        if status not in (200, 201):
            raise ValueError(f"{method} {path} returned {status}: {str(value)[:240]}")
        return value

    try:
        if args.action == "save":
            result = save_snapshot(call, args.job, args.commit)
        else:
            result = export_original(call, args.job, args.commit, args.member, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
