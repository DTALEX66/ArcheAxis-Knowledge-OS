"""Materialise Joplin notes and write edited Markdown bodies and tag relationships to a JEX.

Use with a completed Core archive job. Run python -m scripts.ingest.joplin_exchange --help.
All document reads and writes use the regular Core HTTP API.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tarfile
import time
import unicodedata
from urllib.parse import quote

from shared import core_client
from scripts.ingest.directory_batch import iter_files


def import_raw(call, directory: Path) -> dict:
    """Wrap the selected RAW item files for the same Core conversion used for .jex inputs."""
    files, omitted = iter_files(directory)
    package = io.BytesIO()
    item_count = 0
    member_count = 0
    # The existing non-media worker transport admits a 16 MiB input, including TAR framing.
    limit = 16 * 1024 * 1024
    with tarfile.open(fileobj=package, mode="w") as target:
        for path in files:
            name = path.relative_to(directory).as_posix()
            is_item = bool(re.fullmatch(r"[0-9a-f]{32}\.md", name))
            if not is_item and not re.fullmatch(r"resources/[0-9a-f]{32}(?:\.[^/]+)?", name):
                omitted.append(name)
                continue
            info = tarfile.TarInfo(name)
            with path.open("rb") as stream:
                info.size = os.fstat(stream.fileno()).st_size
                if package.tell() + info.size > limit or member_count >= 5000:
                    raise ValueError("RAW exchange exceeds the Core archive input limits")
                target.addfile(info, stream)
            item_count += int(is_item)
            member_count += 1
    payload = package.getvalue()
    if not item_count or len(payload) > limit:
        raise ValueError("select a Joplin RAW export within the 16 MiB archive route limit")
    source = call("POST", "/api/v1/imports", core_client.import_request(directory.name + ".jex", payload))
    if _digest(payload) != source["sha256"]:
        raise ValueError("stored RAW exchange package differs from the input")
    job_id = "joplin-raw-" + source["sha256"]
    job_path = "/api/v1/jobs/" + job_id
    job = call("POST", "/api/v1/jobs", {"job_id": job_id, "kind": "archive", "input_ref": source["source_id"]})
    if job["state"] == "queued":
        call("POST", job_path + "/executions", {"deadline_ms": 120000}, headers={"idempotency-key": job_id})
    deadline = time.monotonic() + 125
    while job["state"] not in {"succeeded", "failed", "cancelled"}:
        if time.monotonic() >= deadline:
            raise ValueError(f"job {job_id} is still pending; its state is available in Core")
        time.sleep(0.25)
        job = call("GET", job_path)
    if job["state"] != "succeeded":
        raise ValueError(f"RAW import job {job_id} {job['state']}: {job.get('error')}")
    return {**save_notes(call, job_id), "job_id": job_id, "source_format": "joplin-raw",
            "package_sha256": source["sha256"], "packaged_files": member_count, "excluded_paths": omitted}


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_job(call, job_id: str):
    return core_client.archive_job_result(call, job_id, "joplin-jex")


def _paragraph(value: str, block_id: str) -> dict:
    content = [{"type": "text", "text": value}] if value else []
    return {"type": "paragraph", "attrs": {"block_id": block_id}, "content": content}


def _note_properties(note: dict, tag_names: dict) -> dict:
    fields = {f"joplin_{key}": note[key] for key in (
        "id", "parent_id", "notebook_path", "created_time", "updated_time", "user_created_time", "user_updated_time"
    ) if key in note}
    fields["tags"] = [tag_names[key] for key in note["tag_ids"]]
    return fields


def _note_editor(note: dict, tag_names: dict, body: str) -> dict:
    fields = _note_properties(note, tag_names)
    header = "---\n" + "".join(f"{key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in fields.items()) + "---"
    return {"type": "doc", "attrs": {"archeaxis_markup": "markdown", "joplin_item_id": note["id"]},
            "content": [_paragraph(header, "joplin-metadata"), _paragraph(body, "joplin-body")]}


def save_notes(call, job_id: str) -> dict:
    transform, loss = read_job(call, job_id)
    graph = loss["params"]["structure"]["joplin"]
    tags = {tag["id"]: tag["title"] for tag in graph["tags"]}
    result = []
    for note in graph["notes"]:
        body = transform["content"][note["body_start"]:note["body_end"]]
        request = {"create_request_id": f"jex-{transform['raw_sha256']}-{note['id']}", "title": note["title"],
                   "source_id": transform["source_id"], "source_revision": transform["raw_sha256"],
                   "editor_json": _note_editor(note, tags, body)}
        saved = call("POST", "/api/v1/documents", request)
        result.append({"joplin_id": note["id"], "document_id": saved["document_id"],
                       "initial_version": saved["version"], "metadata_issues": saved["metadata_issues"]})
    return {"source_id": transform["source_id"], "documents": result, "import_losses": loss["losses"]}


def _source_paragraph(node: dict) -> str:
    if node["type"] != "paragraph" or set(node.get("attrs", {})) - {"block_id"}:
        raise ValueError("JEX writeback requires Markdown source paragraphs")
    fragments = []
    for child in node.get("content", []):
        if child["type"] not in {"text", "hardBreak"} or child.get("marks"):
            raise ValueError("JEX writeback requires Markdown source text or line breaks")
        fragments.append("\n" if child["type"] == "hardBreak" else child["text"])
    return "".join(fragments)


def _editable_note(snapshot: dict, note: dict, tag_names: dict) -> tuple[str, list[str]]:
    editor = snapshot["editor_json"]
    nodes = editor["content"]
    original = _note_editor(note, tag_names, "")
    if (editor.get("attrs") != original["attrs"] or not nodes
            or nodes[0].get("attrs") != original["content"][0]["attrs"]):
        raise ValueError("select a source-bound Joplin note with its metadata block")
    fields = _note_properties(note, tag_names)
    labels = fields.pop("tags")
    if nodes[0] != original["content"][0]:
        lines = _source_paragraph(nodes[0]).replace("\r\n", "\n").split("\n")
        if (lines[0] != "---" or lines[-1] not in {"---", "..."}
                or any(line in {"---", "..."} for line in lines[1:-1])):
            raise ValueError("the Joplin metadata paragraph must contain a single frontmatter block")
        properties = dict(snapshot["properties"])
        labels = properties.pop("tags", [])
        if properties != fields:
            raise ValueError("only native tag relationships and Markdown bodies support JEX writeback")
        if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
            raise ValueError("Joplin tags must be a list of titles")
    return "\n\n".join(_source_paragraph(node) for node in nodes[1:]), labels


def _tag_key(title: str) -> str:
    # Joplin Tag.loadByTitle uses SQLite NOCASE. Preserve non-ASCII case distinctions.
    return unicodedata.normalize("NFC", title.strip()).translate(_ASCII_LOWER)


_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def _tag_member(item_id: str, kind: int, stamp: str, title: str = "", **relation: str) -> bytes:
    fields = {"id": item_id, **relation, "created_time": stamp, "updated_time": stamp,
              "user_created_time": stamp, "user_updated_time": stamp, "type_": kind}
    # Joplin scans backward from EOF until the first blank line. A trailing
    # newline would hide every property, including the required type_ field.
    return ((title + "\n\n" if title else "") + "\n".join(f"{k}: {v}" for k, v in fields.items())).encode()


def _tag_changes(graph: dict, selections: dict, archive: tarfile.TarFile, revision: str, stamp: str):
    names = {tag["id"]: tag["title"] for tag in graph["tags"]}
    by_key = {}
    for item_id, title in names.items():
        by_key.setdefault(_tag_key(title), []).append(item_id)
    reserved = {match.group(1) for path in archive.getnames()
                if (match := re.fullmatch(r"(?:\./)?(?:resources/)?([0-9a-f]{32})(?:\.[^/]*)?", path))}
    additions = {}
    removals = set()

    def allocate(*identity: str) -> str:
        # Stable across repeated exports and shared by all selected notes.
        for serial in range(len(reserved) + 1):
            encoded = json.dumps([revision, *identity, serial], ensure_ascii=False).encode()
            candidate = _digest(encoded)[:32]
            if candidate not in reserved:
                reserved.add(candidate)
                return candidate
        raise ValueError("could not allocate a Joplin item ID")

    for note_id, (previous, titles) in selections.items():
        wanted = set()
        for title in titles:
            title = unicodedata.normalize("NFC", title.strip())
            if not title or any(unicodedata.category(c) == "Cc" or c in "\u2028\u2029" for c in title):
                raise ValueError("a Joplin tag requires a non-empty single-line title")
            key = _tag_key(title)
            candidates = by_key.get(key, [])
            # Retain native IDs already attached to this note, including a pre-existing
            # duplicate title. Never guess which unrelated duplicate to attach.
            attached = [item for item in candidates if item in previous]
            exact = [item for item in attached if names[item] == title]
            if exact:
                wanted.update(exact)
                continue
            matches = attached or [item for item in candidates if names[item] == title] or candidates
            if len(matches) > 1:
                raise ValueError(f"ambiguous native Joplin tag title: {title}")
            if matches:
                tag_id = matches[0]
            else:
                tag_id = allocate("tag", key)
                additions[tag_id + ".md"] = _tag_member(tag_id, 5, stamp, title=title)
                names[tag_id] = title
                by_key.setdefault(key, []).append(tag_id)
            wanted.add(tag_id)
        for tag_id in sorted(wanted - previous):
            edge_id = allocate("note-tag", note_id, tag_id)
            additions[edge_id + ".md"] = _tag_member(edge_id, 6, stamp, note_id=note_id, tag_id=tag_id)
        removed_ids = previous - wanted
        removals.update(edge["member"] for edge in graph["note_tags"]
                        if edge.get("note_id") == note_id and edge.get("tag_id") in removed_ids)
    return additions, removals


def _replace_body(raw: bytes, title: str, body: str, timestamp: str) -> bytes:
    newline = "\r\n" if b"\r\n" in raw else "\n"
    original = raw.decode("utf-8-sig").replace("\r\n", "\n")
    lines = original.rstrip("\n").split("\n")
    start = len(lines)
    while start and lines[start - 1].strip():
        start -= 1
    props = lines[start:]
    # All unknown native keys, in their original order, survive a body edit.
    timestamps = {"updated_time", "user_updated_time"}
    for index, line in enumerate(props):
        key = line.partition(":")[0].strip()
        if key in timestamps:
            props[index] = f"{key}: {timestamp}"
            timestamps.remove(key)
    props.extend(f"{key}: {timestamp}" for key in sorted(timestamps))
    body = body.replace("\r\n", "\n")
    text = title + "\n\n" + (body + "\n\n" if body else "") + "\n".join(props)
    text += original[len(original.rstrip("\n")):]
    return (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + text.replace("\n", newline).encode()


def export_notes(call, job_id: str, document_ids: list[str], destination: Path) -> dict:
    transform, loss = read_job(call, job_id)
    graph = loss["params"]["structure"]["joplin"]
    notes = {note["id"]: note for note in graph["notes"]}
    tags = {tag["id"]: tag["title"] for tag in graph["tags"]}
    original = call("GET", f"/api/v1/sources/{quote(transform['source_id'], safe='')}/original")
    raw = base64.b64decode(original["content_base64"], validate=True)
    if _digest(raw) != transform["raw_sha256"]:
        raise ValueError("incomplete original JEX")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    changes = {}
    tag_selections = {}
    versions = {}
    for document_id in document_ids:
        doc = call("GET", "/api/v1/documents/" + quote(document_id, safe=""))
        note = notes.get(doc["editor_json"].get("attrs", {}).get("joplin_item_id"))
        if (not note or doc["source_id"] != transform["source_id"] or doc["source_revision"] != transform["raw_sha256"]
                or doc["title"] != note["title"] or note["id"] in versions):
            raise ValueError("select one source-bound document per original Joplin note")
        original_body = transform["content"][note["body_start"]:note["body_end"]]
        body, labels = _editable_note(doc, note, tags)
        if sorted(labels) != sorted(tags[key] for key in note["tag_ids"]):
            tag_selections[note["id"]] = (set(note["tag_ids"]), labels)
        versions[note["id"]] = {"document_id": document_id, "version": doc["version"], "content_sha256": doc["content_sha256"]}
        if body != original_body:
            if note.get("markup_language", "1") != "1":
                raise ValueError("changed native HTML notes require an HTML writeback path")
            changes[note["member"]] = (note["title"], body)
    additions, removals = {}, set()
    if tag_selections:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            additions, removals = _tag_changes(graph, tag_selections, archive, transform["raw_sha256"], timestamp)
    if changes or additions or removals:
        output = io.BytesIO()
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as source, tarfile.open(fileobj=output, mode="w") as target:
            for info in source:
                if info.name in removals:
                    continue
                if info.isdir():
                    target.addfile(info)
                    continue
                with source.extractfile(info) as stream:
                    data = stream.read()
                if info.name in changes:
                    title, body = changes[info.name]
                    data = _replace_body(data, title, body, timestamp)
                    info.size = len(data)
                    info.pax_headers.pop("size", None)
                target.addfile(info, io.BytesIO(data))
            for name, data in additions.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                target.addfile(info, io.BytesIO(data))
        raw = output.getvalue()
    # All selections are checked and the complete result assembled before opening the new destination.
    with destination.open("xb") as handle:
        handle.write(raw)
    return {"file": str(destination), "sha256": _digest(raw), "documents": versions,
            "changed_members": list(changes) + sorted(additions) + sorted(removals),
            "added_members": sorted(additions), "removed_members": sorted(removals),
            "changed_note_timestamp": timestamp if changes else None, "source_revision": transform["raw_sha256"]}


def main(argv=None, *, session=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    token = core_client.configure_cli_connection(parser, session)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("import-raw").add_argument("folder", type=Path)
    commands.add_parser("save-notes").add_argument("job_id")
    export = commands.add_parser("export")
    export.add_argument("job_id")
    export.add_argument("--document", action="append", required=True)
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.core:
        parser.error("pass --core or set ARCHEAXIS_CORE_BASE")

    def call(method, path, body=None, *, headers=None):
        code, value = core_client.call(args.core, method, path, token, body, extra_headers=headers)
        if code not in (200, 201, 202):
            raise ValueError(f"{method} {path} returned {code}: {str(value)[:240]}")
        return value

    try:
        if args.action == "import-raw":
            result = import_raw(call, args.folder)
        elif args.action == "save-notes":
            result = save_notes(call, args.job_id)
        else:
            result = export_notes(call, args.job_id, args.document, args.output)
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
