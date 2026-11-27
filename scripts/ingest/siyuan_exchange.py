"""Edit plain native blocks of a saved SiYuan document and export a new .sy copy."""

from __future__ import annotations

import argparse
import json
import ntpath
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path, PureWindowsPath
from urllib.parse import quote, unquote

from scripts.ingest.obsidian_vault import DOCUMENTS, CoreError, batch_members, digest, original_bytes
from shared import core_client

ID = re.compile(r"[0-9]{14}-[a-z0-9]{7}")
CONTAINERS = {"NodeDocument", "NodeSuperBlock", "NodeList", "NodeListItem", "NodeBlockquote",
              "NodeCallout", "NodeTabs", "NodeTabItem"}


def unique_object(pairs):
    obj = dict(pairs)
    if len(pairs) != len(obj):
        raise ValueError("duplicate JSON key in the SiYuan original")
    return obj


def native_blocks(raw):
    tree = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object)
    if (not isinstance(tree, dict) or tree.get("Type") != "NodeDocument"
            or tree.get("Spec") not in ("2", "3") or not ID.fullmatch(str(tree.get("ID")))):
        raise ValueError("select a SiYuan Spec 2 or 3 document")
    leaves = {}
    seen = set()
    todo = [tree]
    while todo:
        node = todo.pop()
        if not isinstance(node, dict):
            raise ValueError("invalid SiYuan child node")
        kind = node.get("Type")
        children = node.get("Children", [])
        if not isinstance(children, list):
            raise ValueError("invalid SiYuan child list")
        ident = node.get("ID")
        if ident is not None:
            props = node.get("Properties", {})
            if (not isinstance(props, dict) or not isinstance(ident, str)
                    or ident in seen or props.get("id", ident) != ident):
                raise ValueError("inconsistent or duplicate native block identity")
            seen.add(ident)
        if kind in CONTAINERS:
            todo.extend(reversed(children))
        elif kind in ("NodeHeading", "NodeParagraph") and ID.fullmatch(str(ident)) and len(children) == 1:
            leaf = children[0]
            if (isinstance(leaf, dict) and leaf.get("Type") == "NodeText" and not leaf.get("Children")
                    and isinstance(leaf.get("Data"), str)):
                leaves[ident] = leaf
    return tree, leaves


def string_fields(value):
    """Yield string tokens in source order, including object keys."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, None
            if isinstance(child, str):
                yield child, (id(value), key)
            else:
                yield from string_fields(child)
    elif isinstance(value, list):
        for item in value:
            yield from string_fields(item)
    elif isinstance(value, str):
        yield value, None


def affected_blocks(tree, edits):
    """Collect edited nodes, their block ancestors and enclosing heading sections."""
    affected = {}

    def visit(node, ancestors):
        if node.get("ID") in edits:
            for item in (*ancestors, node):
                affected[item["ID"]] = item
        if node.get("Type") not in CONTAINERS:
            return
        headings = []
        for child in node.get("Children", []):
            if child.get("Type") == "NodeHeading":
                level = child.get("HeadingLevel")
                if type(level) is not int or not 1 <= level <= 6:
                    raise ValueError("invalid native heading level")
                while headings and headings[-1]["HeadingLevel"] >= level:
                    headings.pop()
                visit(child, (*ancestors, node, *headings))
                headings.append(child)
            else:
                visit(child, (*ancestors, node, *headings))

    visit(tree, ())
    return affected.values()


def timestamp_changes(tree, edits):
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    changes = {}
    for node in affected_blocks(tree, edits):
        props = node.get("Properties", {})
        previous = props.get("updated")
        if not isinstance(previous, str) or not re.fullmatch(r"[0-9]{14}", previous):
            raise ValueError(f"native block {node['ID']} lacks a supported updated timestamp")
        changes[id(props), "updated"] = max(stamp, previous, node["ID"][:14])
    return changes


def render(raw, tree, leaves, edits):
    if not edits:
        return raw
    # Change only the supported string tokens, preserving numeric spellings,
    # whitespace and unknown metadata. New SiYuan writes use UTF-8 without a BOM.
    replacements = {(id(leaves[key]), "Data"): text for key, text in edits.items()}
    replacements.update(timestamp_changes(tree, edits))
    source = raw.decode("utf-8-sig")
    cursor = copied = 0
    parts = []
    decoder = json.JSONDecoder()
    for expected, leaf in string_fields(tree):
        start = source.index('"', cursor)
        actual, cursor = decoder.raw_decode(source, start)
        if actual != expected:
            raise ValueError("could not locate the native JSON string")
        if leaf in replacements:
            parts.extend((source[copied:start], json.dumps(replacements.pop(leaf), ensure_ascii=False)))
            copied = cursor
    if replacements:
        raise ValueError("could not locate a selected native text node")
    parts.append(source[copied:])
    return "".join(parts).encode("utf-8")


def save_conversion(call, job_id):
    job_path = "/api/v1/jobs/" + quote(job_id, safe="")
    job = call("GET", job_path)
    if job["state"] != "succeeded":
        raise ValueError("select a completed SiYuan text conversion")
    source = job["input_ref"]
    transform = call("GET", "/api/v1/sources/" + quote(source, safe="") + "/jobs/" + quote(job_id, safe="") + "/transform")
    output = call("GET", job_path + "/outputs/loss_report")
    if digest(output["content"].encode()) != output["metadata"]["sha256"] or transform["source_id"] != source:
        raise ValueError("incomplete conversion receipt")
    facts = json.loads(output["content"])["params"]["format"]
    if facts.get("format") != "siyuan" or facts.get("parsed") is not True:
        raise ValueError("select a completed SiYuan text conversion")
    revision = transform["raw_sha256"]
    tree, _ = native_blocks(original_bytes(call, source, revision))
    if tree["ID"] != facts["document_id"] or tree["Spec"] != facts["spec"]:
        raise ValueError("conversion belongs to a different native document")
    text = transform["content"]
    blocks = []
    for fact in facts["blocks"]:
        if "char_start" not in fact:
            continue
        start, stop = fact["char_start"], fact["char_end"]
        if not 0 <= start < stop <= len(text):
            raise ValueError("incomplete converted text for a native block")
        attrs = {"block_id": fact["id"]}
        kind = "paragraph"
        if fact["node_type"] == "NodeHeading":
            kind, attrs["level"] = "heading", fact["heading_level"]
        blocks.append({"type": kind, "attrs": attrs, "content": [{"type": "text", "text": text[start:stop]}]})
    doc = call("POST", DOCUMENTS, {"create_request_id": "siyuan-" + revision,
               "source_id": source, "source_revision": revision, "title": tree["Properties"]["title"],
               "editor_json": {"type": "doc", "content": blocks}})
    return {"document_id": doc["document_id"], "version": doc["version"], "source_id": source}


def mapped_blocks(first, current, leaves):
    baseline = first["editor_json"]["content"]
    nodes = current["editor_json"]["content"]
    if len(baseline) != len(nodes):
        raise ValueError("added or removed document blocks cannot be written to the native copy")
    mapped = {}
    for before, after in zip(baseline, nodes, strict=True):
        key = before.get("attrs", {}).get("block_id")
        leaf = leaves.get(key)
        if (leaf is None or before.get("content") != [{"type": "text", "text": leaf["Data"]}]
                or before.get("type") not in ("heading", "paragraph")):
            if before != after:
                raise ValueError("a changed block cannot be represented as a native plain-text edit")
            continue
        content = after.get("content", [])
        if (len(content) != 1 or not isinstance(content[0], dict) or set(content[0]) != {"type", "text"}
                or content[0]["type"] != "text" or not isinstance(content[0]["text"], str)
                or {**after, "content": before["content"]} != before or key in mapped):
            raise ValueError("edited block structure or identity differs from its original projection")
        mapped[key] = content[0]
    return mapped


def publish_copy(output, data):
    if output.suffix.lower() != ".sy":
        raise ValueError("choose a new .sy output file")
    with tempfile.TemporaryDirectory(prefix=".aaos-siyuan-", dir=output.parent) as folder:
        temp = Path(folder) / "copy.sy"
        temp.write_bytes(data)
        if os.name == "nt":
            temp.rename(output)  # Windows rename fails when the destination exists.
        else:
            os.link(temp, output)


def member_parts(name):
    parts = name.split("/")
    reserved = getattr(ntpath, "isreserved", lambda s: PureWindowsPath(s).is_reserved())
    if any(not part or part.endswith((".", " ")) or reserved(part)
           or re.search(r'[\x00-\x1f<>:"|?*\\]', part) for part in parts):
        raise ValueError(f"unsafe batch member path: {name}")
    return parts


def export_folder(call, args, doc, native_id, data):
    if os.path.lexists(args.output):
        raise FileExistsError(f"choose a new output directory: {args.output}")
    route, workspace, members = batch_members(call, args.batch)
    notes = [m for m in members if m["source_id"] == doc["source_id"]
             and m["source_revision"] == doc["source_revision"] and m["relative_path"].endswith(".sy")]
    if len(notes) != 1:
        raise ValueError("the batch must contain exactly one matching SiYuan source revision")
    note = notes[0]
    note_parts = member_parts(note["relative_path"])
    if note_parts[-1] != native_id + ".sy":
        raise ValueError("the batch filename differs from the native document ID")
    job = note["job_id"]
    if not job:
        raise ValueError("the selected batch note requires a completed SiYuan conversion")
    report = call("GET", "/api/v1/jobs/" + quote(job, safe="") + "/outputs/loss_report")
    loss_sha = digest(report["content"].encode())
    facts = json.loads(report["content"])["params"]["format"]
    if (loss_sha != report["metadata"]["sha256"] or facts["format"] != "siyuan"
            or facts["parsed"] is not True or facts["document_id"] != native_id):
        raise ValueError("batch conversion differs from the native note")
    omitted = facts["omitted_subtrees"]
    # Read the root even for a note without links so Core verifies the conversion and source binding.
    by_block = {native_id: []}
    for link in facts["attachment_paths"]:
        by_block.setdefault(link["source_block_id"], []).append(link["relative_path"])
    by_ordinal = {m["ordinal"]: m for m in members}
    assets = {}
    for block, paths in by_block.items():
        projection = call("GET", f"{route}/members/{note['ordinal']}/siyuan-blocks/{quote(block, safe='')}/assets")
        if (projection["native_source_block"] != {"source_id": doc["source_id"], "sha256": doc["source_revision"], "block_id": block}
                or projection["conversion"]["loss_sha256"] != loss_sha or projection["conversion"]["job_id"] != job
                or [a["relative_path"] for a in projection["assets"]] != paths):
            raise ValueError("batch attachment projection differs from its conversion")
        for asset in projection["assets"]:
            path = asset["relative_path"]
            if asset["status"] != "resolved_reference":
                raise ValueError(f"unresolved attachment in block {block}: {path} ({asset['reason']})")
            target = by_ordinal[asset["target_ordinal"]]
            name = target["relative_path"]
            if (member_parts(name)[0] != "assets" or unquote(path, errors="strict") != name
                    or asset["target"] != {"kind": "source", "source_id": target["source_id"], "sha256": target["source_revision"]}
                    or (name in assets and assets[name] != target)):
                raise ValueError(f"attachment identity conflict for {path}")
            assets[name] = target

    with tempfile.TemporaryDirectory(prefix=".aaos-siyuan-", dir=args.output.parent) as temp:
        folder = Path(temp) / "notebook"
        target = folder.joinpath(*note_parts)
        target.parent.mkdir(parents=True)
        target.write_bytes(data)
        for name, member in assets.items():
            raw = original_bytes(call, member["source_id"], member["source_revision"])
            if len(raw) != member["byte_length"]:
                raise ValueError(f"attachment length differs from its manifest: {name}")
            target = folder.joinpath(*member_parts(name))
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
        if os.name == "nt":
            folder.rename(args.output)
        else:
            # POSIX rename can replace an existing empty directory. Reserve the new name exclusively.
            args.output.mkdir()
            try:
                folder.rename(args.output)
            except OSError:
                args.output.rmdir()
                raise
    return {"workspace_id": workspace, "batch_id": args.batch, "note_path": note["relative_path"],
            "assets": [{"path": name, "sha256": m["source_revision"], "bytes": m["byte_length"]}
                       for name, m in assets.items()], "omitted_subtrees": omitted}


def exchange(call, args):
    if args.action == "save":
        return save_conversion(call, args.job_id)
    route = DOCUMENTS + "/" + quote(args.document, safe="")
    first = call("GET", route + "/versions/1")
    doc = call("GET", route)
    if (not first["source_id"] or first["source_id"] != doc["source_id"]
            or first["source_revision"] != doc["source_revision"]):
        raise ValueError("document requires a fixed SiYuan source revision")
    raw = original_bytes(call, doc["source_id"], doc["source_revision"])
    tree, leaves = native_blocks(raw)
    mapped = mapped_blocks(first, doc, leaves)
    result = {"document_id": doc["document_id"], "source_revision": doc["source_revision"], "version": doc["version"]}
    if args.action == "blocks":
        return {**result, "blocks": [{"block_id": key, "text": val["text"]} for key, val in mapped.items()]}
    if args.action == "block":
        node = mapped.get(args.block_id)
        if node is None:
            raise ValueError("select a native block listed by the blocks command")
        if args.text is not None and args.text != node["text"]:
            if not args.text.strip() or any(ch in args.text for ch in "\r\n\x00"):
                raise ValueError("provide one nonempty line of plain text")
            timestamp_changes(tree, {args.block_id})
            node["text"] = args.text
            saved = call("PUT", route + "/draft", {"expected_version": doc["version"], "editor_json": doc["editor_json"]})
            result["version"] = saved["version"]
        return {**result, "block_id": args.block_id, "text": node["text"]}
    if args.action == "export" and args.output.name != tree["ID"] + ".sy":
        raise ValueError(f"choose a new directory with the native filename {tree['ID']}.sy")
    edits = {key: val["text"] for key, val in mapped.items() if val["text"] != leaves[key]["Data"]}
    data = render(raw, tree, leaves, edits)
    if args.action == "export-folder":
        exported = export_folder(call, args, doc, tree["ID"], data)
        return {**result, **exported, "output": str(args.output), "sha256": digest(data), "edited_blocks": list(edits)}
    publish_copy(args.output, data)
    return {**result, "output": str(args.output), "sha256": digest(data), "edited_blocks": list(edits),
            "scope": "Native text only. Asset paths stay in the note. Attachment files and AAOS metadata are not exported."}


def main(argv=None, *, session=None):
    cli = argparse.ArgumentParser(description=__doc__)
    token = core_client.configure_cli_connection(cli, session)
    commands = cli.add_subparsers(dest="action", required=True)
    commands.add_parser("save", help="save the projection of an existing .sy text conversion").add_argument("job_id")
    blocks = commands.add_parser("blocks", help="list mapped, editable native blocks")
    block = commands.add_parser("block", help="read a native block or update its plain text")
    export = commands.add_parser("export", help="write a native copy to a new file")
    folder = commands.add_parser("export-folder", help="write the note and its recorded assets under a new folder")
    folder.add_argument("--batch", required=True, help="folder import batch containing this note and its assets")
    for sub in (blocks, block, export, folder):
        sub.add_argument("--document", required=True)
    block.add_argument("block_id")
    block.add_argument("--text")
    export.add_argument("--output", type=Path, required=True)
    folder.add_argument("--output", type=Path, required=True)
    args = cli.parse_args(argv)
    if not args.core:
        cli.error("pass --core or set ARCHEAXIS_CORE_BASE")

    def call(method, path, body=None):
        status, result = core_client.call(args.core, method, path, token, body)
        if status not in (200, 201, 202):
            raise CoreError(method, path, status, result)
        return result

    try:
        print(json.dumps(exchange(call, args), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, RecursionError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
