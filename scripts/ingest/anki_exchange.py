"""Save Anki notes as Core documents and export selected, edited fields for Anki text import."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from urllib.parse import quote

from shared import core_client


def save_notes(call, job_id: str) -> dict:
    transform, loss = core_client.archive_job_result(call, job_id, "anki-package")
    graph = loss["params"]["structure"]["anki"]
    saved = []
    for note in graph["notes"]:
        fields = note["fields"]
        catalog = graph["note_types"].get(str(note["note_type_id"]), {})
        editor = {"type": "doc", "attrs": {"anki_guid": note["guid"], "anki_note_type": note["note_type"],
                  "anki_field_names": catalog.get("fields", {}), "anki_source_tags": note["tags"]},
                  "content": [{"type": "paragraph", "attrs": {"block_id": f"anki-field-{i}"},
                               "content": [{"type": "text", "text": field}] if field else []}
                              for i, field in enumerate(fields)]}
        doc = call("POST", "/api/v1/documents", {
            "create_request_id": f"anki-{transform['raw_sha256']}-{note['note_id']}",
            "source_id": transform["source_id"], "source_revision": transform["raw_sha256"],
            "title": (fields[0].strip() if fields else "")[:120] or note["note_type"], "editor_json": editor})
        saved.append({"guid": note["guid"], "document_id": doc["document_id"], "version": doc["version"]})
    return {"source_id": transform["source_id"], "documents": saved}


def _field_text(node):
    if node.get("type") != "paragraph":
        raise ValueError("Anki fields require source paragraphs with literal field HTML")
    pieces = []
    for child in node.get("content", []):
        if child.get("marks") or child.get("type") not in {"text", "hardBreak"}:
            raise ValueError("use literal Anki field HTML or line breaks for text export")
        pieces.append("\n" if child["type"] == "hardBreak" else child["text"])
    return "".join(pieces)


def export_fields(call, job_id: str, document_ids: list[str], output: Path) -> dict:
    """Update native notes by GUID, including when the first field itself changes."""
    transform, loss = core_client.archive_job_result(call, job_id, "anki-package")
    notes = {n["guid"]: n for n in loss["params"]["structure"]["anki"]["notes"]}
    rows = []
    revisions = {}
    for document_id in document_ids:
        doc = call("GET", "/api/v1/documents/" + quote(document_id, safe=""))
        editor = doc["editor_json"]
        guid = editor.get("attrs", {}).get("anki_guid")
        note = notes.get(guid)
        if (not note or guid in revisions or doc["source_id"] != transform["source_id"]
                or doc["source_revision"] != transform["raw_sha256"]):
            raise ValueError("select each Anki source note once from this archive job")
        original = call("GET", f"/api/v1/documents/{quote(document_id, safe='')}/versions/1")
        if original["editor_json"].get("attrs", {}).get("anki_guid") != guid:
            raise ValueError("Anki note identity changed from the saved document")
        nodes = editor.get("content", [])
        field_ids = [f"anki-field-{i}" for i in range(len(note["fields"]))]
        by_field = {node.get("attrs", {}).get("block_id"): node for node in nodes}
        if len(nodes) != len(field_ids) or set(by_field) != set(field_ids):
            raise ValueError("the document no longer has one block per native Anki field")
        # Anki may rename an incoming native type (for example Basic to Basic+)
        # when another type already has its display name. The source ID survives.
        rows.append([guid, str(note["note_type_id"]), *[_field_text(by_field[key]) for key in field_ids]])
        revisions[guid] = {"document_id": document_id, "version": doc["version"]}
    if not rows:
        raise ValueError("select at least one document")
    stream = io.StringIO(newline="")
    stream.write("#separator:Tab\n#html:true\n#guid column:1\n#notetype column:2\n")
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_ALL)
    width = max(map(len, rows))
    for row in rows:
        writer.writerow(row + [""] * (width - len(row)))
    payload = stream.getvalue().encode("utf-8")
    with output.open("xb") as handle:
        handle.write(payload)
    return {"file": str(output), "sha256": hashlib.sha256(payload).hexdigest(), "documents": revisions,
            "source_revision": transform["raw_sha256"],
            "scope": "UTF-8 field update for an existing Anki collection with matching note types, GUIDs and media"}


def main(argv=None, *, session=None):
    parser = argparse.ArgumentParser(description=__doc__)
    token = core_client.configure_cli_connection(parser, session)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("save-notes").add_argument("job_id")
    export = commands.add_parser("export-fields")
    export.add_argument("job_id")
    export.add_argument("--document", required=True, action="append")
    export.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.core:
        parser.error("pass --core or set ARCHEAXIS_CORE_BASE")

    def call(method, path, body=None):
        code, value = core_client.call(args.core, method, path, token, body)
        if code not in (200, 201, 202):
            raise ValueError(f"{method} {path} returned {code}: {str(value)[:240]}")
        return value

    try:
        result = (save_notes(call, args.job_id) if args.action == "save-notes"
                  else export_fields(call, args.job_id, args.document, args.output))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
