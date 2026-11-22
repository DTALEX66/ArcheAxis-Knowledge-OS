"""Import ENEX notes through Core and return annotated copies of the original notebook."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from html.entities import name2codepoint
from pathlib import Path, PureWindowsPath
from urllib.parse import quote
from xml.etree import ElementTree as ET

from defusedxml import ElementTree as SafeET
from defusedxml import minidom

from scripts.ingest.obsidian_vault import original_bytes
from shared import core_client

DOCUMENTS = "/api/v1/documents"
EXCHANGE = "archeaxis.evernote-exchange/v1"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def store(call, name, raw):
    source = call("POST", "/api/v1/imports", core_client.import_request(name, raw))
    if source["sha256"] != sha(raw):
        raise ValueError("stored bytes differ from the Evernote input")
    return {"source_id": source["source_id"], "sha256": source["sha256"]}


def enml_xml(text):
    # ENML's XHTML named entities are often supplied by the external DTD.
    # Translate those names locally so reading a notebook stays offline.
    def numeric(match):
        name = match[1]
        if name in {"amp", "lt", "gt", "apos", "quot"} or name not in name2codepoint:
            return match[0]
        return f"&#{name2codepoint[name]};"
    return re.sub(r"<!\[CDATA\[.*?\]\]>|<!--.*?-->|&([a-zA-Z][a-zA-Z0-9]*);", numeric, text.strip(), flags=re.S)


def read_resources(call, note):
    resources, losses = [], []
    for index, element in enumerate(note.findall("resource"), 1):
        name = element.findtext("resource-attributes/file-name") or f"resource-{index}"
        mime = element.findtext("mime") or "application/octet-stream"
        data = element.find("data")
        if data is None or data.get("encoding", "base64").lower() != "base64":
            losses.append(f"Resource {index} has no supported base64 data; kept in the ENEX.")
            continue
        try:
            payload = base64.b64decode("".join((data.text or "").split()), validate=True)
        except (binascii.Error, ValueError):
            losses.append(f"Resource {index} has invalid base64 data; kept in the ENEX.")
            continue
        if not payload:
            losses.append(f"Resource {index} is empty; kept in the ENEX.")
            continue
        # Evernote identifies an inline resource by MD5 of the binary. Core
        # independently identifies the stored original by SHA-256.
        md5 = hashlib.md5(payload, usedforsecurity=False).hexdigest()
        leaf = PureWindowsPath(name).name or f"resource-{index}"
        resource = store(call, leaf, payload)
        resources.append({**resource, "index": index, "name": name, "mime": mime, "bytes": len(payload),
                          "en_media_hash": md5, "recognition_in_original": element.find("recognition") is not None})
    return resources, losses


def note_markdown(content, resources, losses, pandoc):
    root = SafeET.fromstring(enml_xml(content))
    if root.tag != "en-note":
        raise ValueError("note content has no en-note root")
    root.tag = "div"
    for element in root.iter():
        if element.tag == "en-media":
            native_hash = element.get("hash", "").lower()
            mime = element.get("type", "").lower()
            matches = [r for r in resources if r["en_media_hash"] == native_hash and r["mime"].lower() == mime]
            if len({r["sha256"] for r in matches}) != 1:
                element.tag, element.attrib = "span", {}
                element.text = f"[Unresolved Evernote attachment: {native_hash}]"
                losses.append(f"Unresolved en-media reference {native_hash} ({mime}).")
                continue
            resource = matches[0]
            alt = element.get("alt") or resource["name"]
            # A source link carries the actual Core identity. The binary is
            # retrievable separately from the editable text projection.
            target = "/api/v1/sources/" + quote(resource["source_id"], safe="") + "/original"
            element.tag, element.attrib, element.text = "a", {"href": target}, alt
        elif element.tag == "en-todo":
            checked = element.get("checked", "").lower() == "true"
            element.tag, element.attrib, element.text = "span", {}, "☑ " if checked else "☐ "
        elif element.tag == "en-crypt":
            element.tag, element.attrib, element.text = "span", {}, "[Encrypted content in original ENEX]"
            losses.append("Encrypted text was preserved only in the original ENEX.")
    result = subprocess.run([str(pandoc), "--sandbox", "--from=html", "--to=gfm-raw_html", "--wrap=none"],
                            input=ET.tostring(root, encoding="utf-8", method="html"),
                            capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise ValueError("Pandoc could not read the ENML projection: " + result.stderr.decode(errors="replace")[:240])
    return result.stdout.decode("utf-8").rstrip("\r\n")


def paragraph(key, value):
    return {"type": "paragraph", "attrs": {"block_id": key},
            "content": [{"type": "text", "text": value}] if value else []}


def import_notes(call, path, pandoc):
    raw = path.read_bytes()
    source = store(call, path.name, raw)
    tree = SafeET.fromstring(raw)
    if tree.tag != "en-export" or not tree.findall("note"):
        raise ValueError("select an ENEX export containing at least one note")
    documents, unconverted = [], []
    for ordinal, note in enumerate(tree.findall("note"), 1):
        title = note.findtext("title") or ""
        content = note.findtext("content") or ""
        tags = [item.text for item in note.findall("tag") if item.text]
        resources, losses = read_resources(call, note)
        try:
            body = note_markdown(content, resources, losses, pandoc)
        except ET.ParseError as error:
            unconverted.append({"note": ordinal, "title": title, "reason": str(error), "resources": resources})
            continue
        metadata = {"note": ordinal, "enml_sha256": sha(content.encode()), "created": note.findtext("created"),
                    "updated": note.findtext("updated"), "tags": tags, "resources": resources, "losses": losses,
                    "attributes": {key: note.findtext("note-attributes/" + key) for key in ("author", "source-url")
                                   if note.find("note-attributes/" + key) is not None}}
        front = "---\ntags: " + json.dumps(tags, ensure_ascii=False) + "\n---"
        editor = {"type": "doc", "attrs": {"archeaxis_markup": "markdown", "evernote": metadata},
                  "content": [paragraph("enex-tags", front), paragraph("enex-body", body)]}
        saved = call("POST", DOCUMENTS, {"title": title[:120] or f"Note {ordinal}",
                     "source_id": source["source_id"], "source_revision": source["sha256"],
                     "create_request_id": f"enex-{source['sha256']}-{ordinal}", "editor_json": editor})
        documents.append({"note": ordinal, "title": title, "document_id": saved["document_id"],
                          "version": saved["version"], "resources": resources, "losses": losses,
                          "metadata_issues": saved["metadata_issues"]})
    return {"schema": EXCHANGE, **source, "exporter": tree.attrib, "documents": documents, "unconverted": unconverted}


def children(element, name):
    return [node for node in element.childNodes if node.nodeType == node.ELEMENT_NODE and node.tagName == name]


def set_text(element, text, *, cdata=False):
    while element.firstChild:
        element.removeChild(element.firstChild)
    doc = element.ownerDocument
    if cdata:
        pieces = text.split("]]>")
        for index, piece in enumerate(pieces):
            element.appendChild(doc.createCDATASection((">" if index else "") + piece
                                                       + ("]]" if index < len(pieces) - 1 else "")))
    else:
        element.appendChild(doc.createTextNode(text))


def append_paragraphs(enml, blocks):
    inner = minidom.parseString(enml_xml(enml))
    additions = []
    for block in blocks:
        if block.get("type") != "paragraph":
            raise ValueError("annotated ENEX export needs appended plain paragraphs")
        line = inner.createElement("div")
        for span in block.get("content", []):
            if span.get("type") == "hardBreak":
                line.appendChild(inner.createElement("br"))
            elif span.get("type") == "text" and not span.get("marks"):
                line.appendChild(inner.createTextNode(span["text"]))
            else:
                raise ValueError("annotated ENEX export needs plain text or line breaks")
        inner.documentElement.appendChild(line)
        additions.append(line.toxml())
    # Retain the original markup spelling, entities and inline styles when
    # appending to a regular closing tag, including a trailing line break.
    end = re.search(r"</en-note\s*>\s*\Z", enml)
    if end:
        return enml[:end.start()] + "".join(additions) + enml[end.start():]
    return inner.toxml()


def edited_tags(block):
    if block.get("type") != "paragraph" or block.get("attrs", {}).get("block_id") != "enex-tags":
        raise ValueError("the ENEX tags block is missing")
    parts = []
    for span in block.get("content", []):
        if span.get("type") == "hardBreak":
            parts.append("\n")
        elif span.get("type") == "text" and not span.get("marks"):
            parts.append(span["text"])
        else:
            raise ValueError("the ENEX tags block requires a plain tag list")
    front = re.fullmatch(r"---\r?\ntags:[ \t]*(.*?)\r?\n---\s*", "".join(parts), re.S)
    if not front:
        raise ValueError("preserve the ENEX tags header and its JSON list")
    tags = json.loads(front[1])
    if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
        raise ValueError("the ENEX tags field must be a list of nonempty names")
    return tags


def replace_tags(note, tags):
    for field in children(note, "tag"):
        note.removeChild(field)
    following = next((n for n in note.childNodes if n.nodeType == n.ELEMENT_NODE
                      and n.tagName not in {"title", "content", "created", "updated", "deleted"}), None)
    for tag in tags:
        field = note.ownerDocument.createElement("tag")
        set_text(field, tag)
        note.insertBefore(field, following)


def export_annotated(call, document_ids, destination):
    originals = []
    for doc_id in dict.fromkeys(document_ids):
        route = DOCUMENTS + "/" + quote(doc_id, safe="")
        initial, current = call("GET", route + "/versions/1"), call("GET", route)
        metadata = initial["editor_json"].get("attrs", {}).get("evernote")
        if not metadata or any(initial[key] != current[key] for key in ("document_id", "source_id", "source_revision")):
            raise ValueError("select notes imported from the same ENEX file")
        originals.append((initial, current, metadata))
    source_keys = {(first["source_id"], first["source_revision"]) for first, _, _ in originals}
    if len(source_keys) != 1:
        raise ValueError("one output file requires notes from one ENEX source")
    source_id, revision = source_keys.pop()
    raw = original_bytes(call, source_id, revision)
    outer = minidom.parseString(raw)
    notes = children(outer.documentElement, "note")
    changed = []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for first, current, metadata in originals:
        ordinal = metadata["note"]
        if type(ordinal) is not int or not 1 <= ordinal <= len(notes):
            raise ValueError("the selected note ordinal is outside the ENEX")
        note = notes[ordinal - 1]
        content = children(note, "content")[0]
        enml = "".join(n.data for n in content.childNodes if n.nodeType in (n.TEXT_NODE, n.CDATA_SECTION_NODE))
        if sha(enml.encode()) != metadata["enml_sha256"]:
            raise ValueError("the selected note differs from the imported ENML")
        editor, baseline = current["editor_json"], first["editor_json"]
        count = len(baseline["content"])
        if (editor.get("attrs") != baseline.get("attrs") or len(editor["content"]) < count
                or editor["content"][1:count] != baseline["content"][1:]):
            raise ValueError("native annotation export preserves the imported rich body; select a version with appended paragraphs")
        tags = edited_tags(editor["content"][0])
        retagged = tags != metadata["tags"]
        appended = editor["content"][count:]
        retitled = current["title"] != first["title"]
        if not appended and not retitled and not retagged:
            continue
        if appended:
            set_text(content, append_paragraphs(enml, appended), cdata=True)
        if retitled:
            set_text(children(note, "title")[0], current["title"])
        if retagged:
            replace_tags(note, tags)
        updated = children(note, "updated")
        if updated:
            set_text(updated[0], timestamp)
        else:
            field = outer.createElement("updated")
            following = next((n for n in note.childNodes if n.nodeType == n.ELEMENT_NODE
                              and n.tagName not in {"title", "content", "created"}), None)
            note.insertBefore(field, following)
            set_text(field, timestamp)
        changed.append({"note": ordinal, "document_id": current["document_id"], "version": current["version"]})
    if changed:
        outer.documentElement.setAttribute("export-date", timestamp)
        outer.documentElement.setAttribute("application", "ArcheAxis Knowledge")
        with (Path(__file__).resolve().parents[2] / "pyproject.toml").open("rb") as project:
            outer.documentElement.setAttribute("version", tomllib.load(project)["project"]["version"])
    payload = outer.toxml(encoding="utf-8") if changed else raw
    with destination.open("xb") as output:
        output.write(payload)
    return {"source_id": source_id, "source_revision": revision, "notes": len(notes), "changed": changed,
            "path": str(destination), "sha256": sha(payload)}


def main(argv=None, *, session=None):
    parser = argparse.ArgumentParser(description=__doc__)
    token = core_client.configure_cli_connection(parser, session)
    actions = parser.add_subparsers(dest="action", required=True)
    ingest = actions.add_parser("import")
    ingest.add_argument("file", type=Path)
    ingest.add_argument("--pandoc", default=os.environ.get("ARCHEAXIS_PANDOC") or "pandoc")
    export = actions.add_parser("export-annotated")
    export.add_argument("--document", action="append", required=True)
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.core:
        parser.error("pass --core or set ARCHEAXIS_CORE_BASE")

    def call(method, path, body=None):
        status, value = core_client.call(args.core, method, path, token, body)
        if status not in (200, 201, 202):
            raise ValueError(f"{method} {path} returned {status}: {str(value)[:240]}")
        return value

    try:
        result = (import_notes(call, args.file, args.pandoc) if args.action == "import"
                  else export_annotated(call, args.document, args.output))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, IndexError, OSError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
