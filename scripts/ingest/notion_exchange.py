"""Read a Notion Markdown & CSV export into Core and return selected edits to a new ZIP."""

from __future__ import annotations

import argparse
import csv
import io
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

from scripts.ingest.obsidian_vault import DOCUMENTS, _markdown, digest, markdown_bytes, original_bytes
from shared import core_client

NOTION_NAME = re.compile(r"^(?P<title>.+) (?P<id>[0-9a-f]{32})(?P<all>_all)?$", re.I)
ARCHIVE_BYTES = 64 * 1024 * 1024
MARKDOWN = MarkdownIt("commonmark")


class ProjectionLimit(ValueError):
    """A native member is preserved but cannot be represented as this Core object."""


def members(archive):
    entries = archive.infolist()
    if len(entries) > 5000 or sum(entry.file_size for entry in entries) > ARCHIVE_BYTES:
        raise ValueError("this export exceeds the single ZIP reader budget (5000 members, 64 MiB expanded)")
    names = [entry.filename for entry in entries if not entry.is_dir()]
    if len(names) != len(set(names)):
        raise ValueError("repeated ZIP member paths cannot identify a unique page")
    return [name for name in names if not any(
        part in {"", ".", "..", "__MACOSX"} or part.startswith(".") for part in name.split("/")
    ) and "\\" not in name and ":" not in name]


def title(name):
    stem = PurePosixPath(name).stem
    match = NOTION_NAME.fullmatch(stem)
    return (match["title"] if match else stem)[:120]


def store_source(call, name, raw):
    stored = call("POST", "/api/v1/imports", core_client.import_request(PurePosixPath(name).name, raw))
    if stored["sha256"] != digest(raw):
        raise ValueError(f"Core returned different source bytes for {name}")
    return {k: stored[k] for k in ("source_id", "sha256")}


def paragraph(key, text):
    return {"type": "paragraph", "attrs": {"block_id": key},
            "content": [{"type": "text", "text": text}] if text else []}


def save(call, archive_source, paths, source, role, content, attrs=None):
    identity = {"archive": archive_source, "paths": paths, "role": role}
    key = digest(json.dumps([archive_source["sha256"], paths, role], ensure_ascii=False).encode())
    editor = {"type": "doc", "attrs": {"notion": identity, **(attrs or {})}, "content": content}
    if len(json.dumps(editor, ensure_ascii=False, separators=(",", ":")).encode()) > 1024 * 1024:
        raise ProjectionLimit("original member retained; editor representation exceeds 1 MiB")
    return call("POST", DOCUMENTS, {"title": title(paths[0]), "source_id": source["source_id"],
                "source_revision": source["sha256"], "create_request_id": "notion-" + key, "editor_json": editor})


def page_relations(name, markdown, sources):
    links, losses = [], []

    def bind(path, label, embed=False):
        if len(links) >= 256 or len(label.encode()) > 1024:
            losses.append({"target": path, "reason": "Core relation count or label limit reached"})
            return
        item = {"id": f"link-{len(links) + 1}", "kind": "related", "label": label,
                "target": {"kind": "source", **sources[path]}}
        if embed:
            item["presentation"] = "embed"
        links.append(item)

    parent = posixpath.dirname(name)
    if NOTION_NAME.fullmatch(posixpath.basename(parent)):
        for suffix in (".md", "_all.csv", ".csv"):
            if parent + suffix in sources:
                bind(parent + suffix, "Containing Notion page or database")
                break
        # Database row exports put properties immediately below the title. File properties
        # can be bare relative paths and row relations use "Title (path.md)" without brackets.
        lines = iter(markdown.splitlines())
        if next(lines, "").startswith("# "):
            line = next((line for line in lines if line.strip()), "")
            while line:
                field, sep, value = line.partition(": ")
                if not sep:
                    break
                path = posixpath.normpath(posixpath.join(parent, unquote(value)))
                if path in sources:
                    bind(path, field)
                else:
                    for match in re.finditer(r"(?:^|, )(.+?) \(([^()\r\n]+\.(?:md|csv))\)(?=, |$)", value, re.I):
                        target = posixpath.normpath(posixpath.join(parent, unquote(match[2])))
                        if target in sources:
                            bind(target, field + ": " + match[1])
                        else:
                            losses.append({"target": match[2], "reason": "row property target absent from export"})
                line = next(lines, "")
    for token in MARKDOWN.parse(markdown):
        for inline in token.children or []:
            if inline.type not in {"link_open", "image"}:
                continue
            image = inline.type == "image"
            target = inline.attrGet("src" if image else "href")
            parts = urlsplit(target)
            path = posixpath.normpath(posixpath.join(parent, unquote(parts.path))) if parts.path else name
            if parts.scheme or parts.netloc or parts.query or parts.path.startswith("/"):
                losses.append({"target": target, "reason": "non-local reference retained in Markdown"})
            elif path not in sources:
                losses.append({"target": target, "reason": "no corresponding file in this export"})
            else:
                bind(path, inline.content or target, image)
                if parts.fragment:
                    losses.append({"target": target, "reason": "linked file resolved; fragment retained in Markdown"})
    return {"schema": "archeaxis.relations/v1", "relations": links}, losses


def read_table(raw):
    try:
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True))
    except (UnicodeError, csv.Error) as exc:
        raise ProjectionLimit(f"not a readable UTF-8 CSV: {exc}") from exc
    if not rows or not 1 <= len(rows[0]) <= 64 or len(rows) - 1 > 500:
        raise ProjectionLimit("table exceeds Core's 64-column / 500-row collection or has no headers")
    headers = rows[0]
    if any(not name.strip() or len(name.encode()) > 512 for name in headers):
        raise ProjectionLimit("CSV column name is empty or exceeds Core's name size")
    if any(len(row) != len(headers) or any(len(cell.encode()) > 16384 for cell in row) for row in rows[1:]):
        raise ProjectionLimit("CSV has a row with a different width or a cell above Core's text limit")
    return headers, rows[1:]


def table_groups(sources):
    groups = {}
    for path, source in sources.items():
        name = PurePosixPath(path)
        match = NOTION_NAME.fullmatch(name.stem)
        if name.suffix.lower() == ".csv" and match:
            # A full table and its view can share the same UUID while containing different rows.
            key = (name.parent, match["title"], match["id"].lower(), source["sha256"])
            groups.setdefault(key, []).append(path)
    return [sorted(paths) for paths in groups.values()]


def save_table(call, package, paths, source, raw):
    headers, rows = read_table(raw)
    props = [{"property_id": f"col-{i}", "name": heading, "kind": "text"} for i, heading in enumerate(headers, 1)]
    records, blocks = [], []
    for i, cells in enumerate(rows, 1):
        key = f"row-{i:06}"
        blocks.append(paragraph(key, json.dumps(cells, ensure_ascii=False)))
        records.append({"record_id": key, "values": dict(zip((p["property_id"] for p in props), cells))})
    # An exported CSV has no reliable row-page IDs. Pin each occurrence, including identical rows.
    content = blocks or [paragraph("headers", json.dumps(headers, ensure_ascii=False))]
    row_doc = save(call, package, paths, source, "row-sources", content)
    for record in records:
        record["reference"] = {"kind": "document", "document_id": row_doc["document_id"],
                               "version": 1, "block_id": record["record_id"]}
    definition = {"schema": "archeaxis.collection/v1", "properties": props, "records": records,
                  "views": [{"view_id": "table", "name": "Table", "kind": "table"}]}
    doc = save(call, package, paths, source, "table", [], {"archeaxis_collection": definition})
    return doc["document_id"]


def import_export(call, file):
    with file.open("rb") as stream:
        raw = stream.read(ARCHIVE_BYTES + 1)
    if len(raw) > ARCHIVE_BYTES:
        raise ValueError("the single ZIP reader supports up to 64 MiB")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = members(archive)
        package = store_source(call, file.name, raw)
        sources, pages, tables, losses = {}, {}, {}, {}
        for name in names:
            data = archive.read(name)
            if data:
                sources[name] = store_source(call, name, data)
            else:
                losses[name] = "empty member retained in the original ZIP"
        for name, source in sources.items():
            if PurePosixPath(name).suffix.lower() != ".md":
                continue
            try:
                body = archive.read(name).decode("utf-8-sig")
            except UnicodeDecodeError:
                losses[name] = "non-UTF-8 page retained as an original source"
                continue
            rel, missing = page_relations(name, body, sources)
            if missing:
                losses[name] = missing
            try:
                doc = save(call, package, [name], source, "page", [paragraph("markdown", body)],
                           {"archeaxis_markup": "markdown", "archeaxis_relations": rel})
            except ProjectionLimit as exc:
                losses[name] = str(exc)
                continue
            pages[name] = doc["document_id"]
        for paths in table_groups(sources):
            try:
                doc_id = save_table(call, package, paths, sources[paths[0]], archive.read(paths[0]))
            except ProjectionLimit as exc:
                losses.update(dict.fromkeys(paths, str(exc)))
                continue
            tables.update(dict.fromkeys(paths, doc_id))
    return {"schema": "archeaxis.notion-exchange/v1", "archive": package, "sources": sources,
            "pages": pages, "tables": tables, "losses": losses,
            "archive_only": [n for n in archive.namelist() if not n.endswith("/") and n not in sources]}


def csv_bytes(raw, initial, current):
    """Write text cells while retaining the identity of the native columns and row occurrences."""
    if initial == current:
        return raw
    if initial["properties"] != current["properties"]:
        raise ValueError("selected CSV writeback supports the original text columns")
    keys = [p["property_id"] for p in initial["properties"]]
    before = [(r["record_id"], r["reference"]) for r in initial["records"]]
    if [(r["record_id"], r["reference"]) for r in current["records"]] != before:
        raise ValueError("selected CSV writeback supports the original ordered rows")
    values = [[record["values"].get(key) for key in keys] for record in current["records"]]
    if any(not isinstance(cell, str) for row in values for cell in row):
        raise ValueError("native CSV cells require text (an empty cell is the empty string)")
    header, old_rows = read_table(raw)
    if old_rows == values:
        return raw
    original = raw.decode("utf-8-sig")
    header_stream = io.StringIO(original, newline="")
    next(csv.reader(header_stream))
    end_of_header = original[:header_stream.tell()]
    separator = "\r\n" if end_of_header.endswith("\r\n") else "\r" if end_of_header.endswith("\r") else "\n"
    stream = io.StringIO(newline="")
    # csv.writer must quote both CR and LF even in exports that used LF record separators.
    writer = csv.writer(stream, lineterminator="\r\n")
    def line(row):
        stream.seek(0)
        stream.truncate()
        writer.writerow(row)
        return stream.getvalue()[:-2]
    result = separator.join(line(row) for row in [header, *values])
    if original.endswith(("\r", "\n")):
        result += separator
    return result.encode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8")


def export_selected(call, ids, destination):
    package = None
    changes, versions = {}, []
    for doc_id in dict.fromkeys(ids):
        route = DOCUMENTS + "/" + doc_id
        first, doc = call("GET", route + "/versions/1"), call("GET", route)
        info = first["editor_json"].get("attrs", {}).get("notion", {})
        if info.get("role") not in {"table", "page"} or (package and info["archive"] != package):
            raise ValueError("select pages and tables from one Notion export")
        if doc["title"] != first["title"]:
            raise ValueError("ZIP writeback keeps the original paths; edit the page heading in the Markdown body")
        if package is None:
            package = info["archive"]
            raw = original_bytes(call, package["source_id"], package["sha256"])
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for name in info["paths"]:
                old = archive.read(name)
                if digest(old) != first["source_revision"] or doc["source_id"] != first["source_id"]:
                    raise ValueError("selected source revision does not match the archived member")
                if info["role"] == "page":
                    new = markdown_bytes(_markdown(doc["editor_json"]), old)
                else:
                    new = csv_bytes(old, first["editor_json"]["attrs"]["archeaxis_collection"],
                                    doc["editor_json"]["attrs"]["archeaxis_collection"])
                if new != old:
                    changes[name] = new
        versions.append({"document_id": doc_id, "version": doc["version"], "content_sha256": doc["content_sha256"]})
    if not package:
        raise ValueError("select at least one imported page or table")
    if changes:
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(output, "w") as target:
            target.comment = source.comment
            for entry in source.infolist():
                data = changes[entry.filename] if entry.filename in changes else source.read(entry)
                target.writestr(entry, data)
        raw = output.getvalue()
    with destination.open("xb") as stream:
        stream.write(raw)
    return {"archive": package, "sha256": digest(raw), "changed_members": sorted(changes), "documents": versions,
            "scope": "Selected Markdown bodies and original CSV text cells. Core views and graph metadata stay in the workspace."}


def main(argv=None, *, session=None):
    parser = argparse.ArgumentParser(description=__doc__)
    token = core_client.configure_cli_connection(parser, session)
    actions = parser.add_subparsers(dest="action", required=True)
    imp = actions.add_parser("import")
    imp.add_argument("zip", type=Path)
    exp = actions.add_parser("export")
    exp.add_argument("--document", action="append", required=True)
    exp.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.core:
        parser.error("pass --core or set ARCHEAXIS_CORE_BASE")

    def call(method, path, body=None):
        status, value = core_client.call(args.core, method, path, token, body)
        if status not in (200, 201, 202):
            raise ValueError(f"{method} {path} returned {status}: {str(value)[:240]}")
        return value

    try:
        result = import_export(call, args.zip) if args.action == "import" else export_selected(call, args.document, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
