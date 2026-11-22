"""Import a Vault through Core or write a new Vault from a saved folder batch."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import sys
import tempfile
from itertools import groupby
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from scripts.ingest.directory_batch import iter_files, sha256_of
from shared import core_client

BATCHES = "/api/v1/ingest-batches"
DOCUMENTS = "/api/v1/documents"
PAGE = 200
RELATION_NOTE_BYTES = 256 * 1024
RELATION_MEMBER_BYTES = 2 * 1024 * 1024
RELATION_BATCH_BYTES = 8 * 1024 * 1024


class CoreError(ValueError):
    def __init__(self, method, path, status, value):
        super().__init__(f"{method} {path} returned {status}: {str(value)[:220]}")
        self.status = status


class UnsupportedMarkdownError(ValueError):
    """This editor content has no lossless representation in the Vault exporter."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chunks(items):
    for start in range(0, len(items), PAGE):
        yield items[start:start + PAGE]


def classify(call, names):
    members = {}
    for page in chunks(names):
        result = call("POST", "/api/v1/vault/members", {"members": page})
        members.update((row["member"], row) for row in result["members"])
    return members


def batch_members(call, batch_id):
    route = BATCHES + "/" + quote(batch_id, safe="")
    request = route + f"?limit={PAGE}"
    members = []
    while True:
        page = call("GET", request)
        if not page["complete"]:
            raise ValueError("the Core folder manifest is incomplete")
        members.extend(page["members"])
        if page["next_ordinal"] is None:
            return route, page["workspace_id"], members
        request = route + f"?limit={PAGE}&after_ordinal={page['next_ordinal']}"


def _save_note(call, source, name, text, batch_id):
    editor = {"type": "doc", "attrs": {"obsidian_batch": batch_id, "obsidian_path": name},
              "content": [{"type": "paragraph", "attrs": {"block_id": "vault-markdown"},
                           "content": [{"type": "text", "text": text}] if text else []}]}
    if len(json.dumps(editor, ensure_ascii=False, separators=(",", ":")).encode()) > 1024 * 1024:
        return None  # Core still holds the complete source when it exceeds the editor's limit.
    identity = digest(json.dumps([batch_id, name, source["sha256"]], ensure_ascii=False).encode())
    doc = call("POST", DOCUMENTS, {"create_request_id": "vault-" + identity, "title": PurePosixPath(name).stem[:120],
               "source_id": source["source_id"], "source_revision": source["sha256"], "editor_json": editor})
    # Original link targets pin the original document revision, including on replay after editing.
    return {key: doc[key] for key in ("document_id", "version", "content_sha256")}


def _bind_links(call, route, scope, bindings, notes, sizes):
    results = {}
    omissions = {}
    targets = {entry["ordinal"]: entry for entry in bindings}
    for ordinal, name in notes.items():
        if sizes[ordinal] > RELATION_NOTE_BYTES:
            omissions[name] = "note saved; Core indexes original links in Markdown up to 256 KiB"
            continue
        source = targets[ordinal]
        route_for_note = route + f"/members/{ordinal}/relations"
        document = call("GET", DOCUMENTS + "/" + quote(source["document"]["document_id"], safe=""))
        body = {**scope, "source_id": source["source_id"], "source_revision": source["source_revision"],
                "document_id": document["document_id"], "expected_version": document["version"],
                "content_sha256": document["content_sha256"], "targets": []}
        # Core resolves names and relative paths. Only pass bindings for the files actually linked.
        try:
            result = call("POST", route_for_note, body)
        except ValueError as exc:
            if "original link count exceeds relation budget" not in str(exc):
                raise
            omissions[name] = "Core can bind up to 256 links per note; all Markdown remains in the source"
            continue
        links = result["links"]
        selected = sorted({link["target_ordinal"] for link in result["links"]
                           if link["reason"] == "target_binding_required" and link["target_ordinal"] in targets})
        candidates = []
        total = sizes[ordinal]
        groups = []
        for target in selected:
            if sizes[target] > RELATION_MEMBER_BYTES:
                for link in links:
                    if link["target_ordinal"] == target and link["reason"] == "target_binding_required":
                        link["reason"] = "source_preserved_above_relation_byte_limit"
                continue
            if len(candidates) == PAGE or total + sizes[target] > RELATION_BATCH_BYTES:
                groups.append(candidates)
                candidates, total = [], sizes[ordinal]
            candidates.append(target)
            total += sizes[target]
        if candidates:
            groups.append(candidates)
        for group in groups:
            body["targets"] = [targets[i] for i in group]
            result = call("POST", route_for_note, body)
            body["expected_version"] = result["document"]["version"]
            body["content_sha256"] = result["document"]["content_sha256"]
            for i, link in enumerate(result["links"]):
                if link["target_ordinal"] in group:
                    links[i] = link
        results[name] = links
    return results, omissions


def import_vault(call, root: Path):
    root = root.resolve(strict=True)
    files, skipped = iter_files(root)
    by_name = {path.relative_to(root).as_posix(): path for path in files}
    classified = classify(call, list(by_name))
    inventory = []
    excluded = list(skipped)
    for name, path in sorted(by_name.items()):
        member = classified[name]
        if member["disposition"] not in {"import_as_knowledge", "import_as_source"}:
            excluded.append(f"{name} ({member['disposition']})")
            continue
        size = path.stat().st_size
        if size > 64 * 1024 * 1024:
            excluded.append(f"{name} (above the Core folder import limit)")
            continue
        inventory.append((name, size, sha256_of(path)))
    if not inventory:
        raise ValueError("the folder contains no supported Vault content")
    info = call("GET", BATCHES + "?limit=1")
    scope = {k: info[k] for k in ("workspace_id", "restore_epoch")}
    batch_id = "vault-" + digest(json.dumps([root.name, inventory], ensure_ascii=False).encode())
    route = BATCHES + "/" + batch_id
    rows = [{"ordinal": i, "relative_path": name, "byte_length": size, "disposition": "pending"}
            for i, (name, size, _) in enumerate(inventory)]
    for page in chunks(rows):
        call("POST", BATCHES, {**scope, "batch_id": batch_id, "folder_label": root.name,
                               "expected_members": len(rows), "members": page})
    bindings, notes, documents, source_only = [], {}, {}, []
    for i, (name, _, sha) in enumerate(inventory):
        raw = by_name[name].read_bytes()
        source = call("POST", route + "/imports", {**scope, "ordinal": i, "expected_sha256": sha,
                      "content_base64": base64.b64encode(raw).decode("ascii")})
        if source["sha256"] != sha:
            raise ValueError(f"stored source differs from {name}")
        bound = {"ordinal": i, "source_id": source["source_id"], "source_revision": sha}
        if classified[name]["role"] == "note":
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                source_only.append({"path": name, "reason": "non-UTF-8 note kept in original bytes"})
            else:
                doc = _save_note(call, source, name, text, batch_id)
                if doc is None:
                    source_only.append({"path": name, "reason": "note exceeds the Core document limit"})
                else:
                    bound["document"] = doc
                    documents[name] = doc["document_id"]
                    notes[i] = name
        bindings.append(bound)
    links, omissions = _bind_links(call, route, scope, bindings, notes, [size for _, size, _ in inventory])
    return {"schema": "archeaxis.vault-exchange/v1", **scope, "batch_id": batch_id, "documents": documents,
            "members": len(rows), "excluded": excluded, "source_only": source_only, "original_links": links,
            "link_omissions": omissions}


def _inline_markdown(nodes):
    spans = []
    for marks, group in groupby(nodes, key=lambda node: node.get("marks") or []):
        parts = []
        for node in group:
            if node["type"] == "text":
                parts.append(node["text"])
            elif node["type"] == "hardBreak":
                parts.append("  \n")
            else:
                raise UnsupportedMarkdownError(f"Vault writeback has no Markdown mapping for {node['type']!r}")
        value = "".join(parts)
        if marks:
            if len(marks) != 1 or marks[0].get("type") != "bold" or marks[0].get("attrs"):
                raise UnsupportedMarkdownError("Vault writeback has no lossless mapping for these text marks")
            if value and value[0].isalnum() and value[-1].isalnum() and "*" not in value and "\n" not in value:
                value = "**" + value + "**"
            else:
                # Inline HTML also preserves emphasis on punctuation, where Markdown delimiters can be literal.
                value = "<strong>" + html.escape(value, quote=False) + "</strong>"
        spans.append(value)
    return "".join(spans)


def _markdown(editor):
    paragraphs = []
    for block in editor["content"]:
        kind = block.get("type")
        if kind not in {"paragraph", "heading"}:
            raise UnsupportedMarkdownError(f"Vault writeback has no lossless Markdown mapping for {kind!r}")
        prefix = ""
        if kind == "heading":
            level = block.get("attrs", {}).get("level")
            if type(level) is not int or not 1 <= level <= 6:
                raise UnsupportedMarkdownError("a Vault Markdown heading needs a level from 1 to 6")
            prefix = "#" * level + " "
        paragraphs.append(prefix + _inline_markdown(block.get("content", [])))
    return "\n\n".join(paragraphs)


def original_bytes(call, source_id, sha256):
    original = call("GET", "/api/v1/sources/" + quote(source_id, safe="") + "/original")
    raw = base64.b64decode(original["content_base64"], validate=True)
    if original["sha256"] != sha256 or digest(raw) != sha256:
        raise ValueError("the retrieved file differs from its source revision")
    return raw


def markdown_bytes(text, raw):
    baseline = raw.decode("utf-8-sig")
    if text.removeprefix("\ufeff") == baseline:
        return raw
    text = text.removeprefix("\ufeff")
    if "\r\n" in baseline and "\n" not in baseline.replace("\r\n", ""):
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    return text.encode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8")


def current_markdown(call, doc, original):
    attrs = doc["editor_json"].get("attrs", {})
    source = attrs.get("obsidian_sync_source")
    if source:
        original = original_bytes(call, source["source_id"], source["sha256"])
    return markdown_bytes(_markdown(doc["editor_json"]), original)


def _edited_note(call, id_, member, raw):
    route = DOCUMENTS + "/" + quote(id_, safe="")
    original = call("GET", route + "/versions/1")
    latest = call("GET", route)
    for doc in (original, latest):
        if doc["source_id"] != member["source_id"] or doc["source_revision"] != member["source_revision"]:
            raise ValueError(f"the selected note is bound to another source: {member['relative_path']}")
    # Older folder imports also stored a single literal Markdown paragraph, without Vault attributes.
    initial = _markdown(original["editor_json"])
    baseline = raw.decode("utf-8-sig")
    if initial.removeprefix("\ufeff").replace("\r\n", "\n") != baseline.replace("\r\n", "\n"):
        raise ValueError(f"the selected document was not created from the complete Markdown note: {member['relative_path']}")
    unchanged = _markdown(latest["editor_json"]) == initial and not latest["editor_json"].get("attrs", {}).get("obsidian_sync_source")
    data = raw if unchanged else current_markdown(call, latest, raw)
    return data, {"document_id": id_, "version": latest["version"], "content_sha256": latest["content_sha256"]}


def export_vault(call, batch_id, output: Path, documents, workspace_id=None):
    _, workspace, members = batch_members(call, batch_id)
    if workspace_id is not None and workspace != workspace_id:
        raise ValueError("the Vault import receipt belongs to a different Core workspace")
    names = [member["relative_path"] for member in members]
    classified = classify(call, names)
    for name in documents:
        if name not in classified or classified[name]["role"] != "note":
            raise ValueError(f"the selected Markdown path is absent from this batch: {name}")
    if output.exists():
        raise ValueError("choose a new directory for the exported Vault")
    saved, excluded = [], []
    # Publish the folder only after all selected versions and source bytes have been read and written.
    with tempfile.TemporaryDirectory(prefix=".aaos-vault-", dir=output.parent) as temp:
        folder = Path(temp) / "vault"
        folder.mkdir()
        for member in members:
            name = member["relative_path"]
            role = classified[name]
            if member["disposition"] != "pending" or role["disposition"] not in {"import_as_source", "import_as_knowledge"}:
                if name in documents:
                    raise ValueError(f"the selected note cannot be exported: {name}")
                excluded.append(name)
                continue
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
                raise ValueError(f"invalid Vault member path: {name}")
            if not member["source_id"]:
                raise ValueError(f"folder import is unfinished for {name}")
            raw = original_bytes(call, member["source_id"], member["source_revision"])
            if len(raw) != member["byte_length"]:
                raise ValueError(f"source custody check failed for {name}")
            data, revision = (_edited_note(call, documents[name], member, raw) if name in documents else (raw, None))
            target = folder.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
            saved.append({"path": name, "role": role["role"], "source_sha256": member["source_revision"],
                          "export_sha256": digest(data), "document": revision})
        folder.rename(output)
    return {"schema": "archeaxis.vault-export/v1", "batch_id": batch_id, "workspace_id": workspace,
            "path": str(output), "files": saved, "excluded": excluded}


def _export_selection(call, args):
    workspace, documents, batch = None, {}, args.batch
    if args.receipt:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8-sig"))
        if receipt.get("schema") == "archeaxis.vault-sync/v1":
            from scripts.ingest.obsidian_sync import export_synced

            if args.document:
                raise ValueError("use the synchronized selection in the cursor or select the original batch")
            return export_synced(call, receipt, args.output, after_restore=args.after_restore)
        if receipt.get("schema") != "archeaxis.vault-exchange/v1":
            raise ValueError("select a Vault import receipt or a sync cursor")
        workspace, batch = receipt["workspace_id"], receipt["batch_id"]
        documents.update(receipt["documents"])
    if args.after_restore:
        raise ValueError("--after-restore requires the saved sync cursor for this workspace")
    documents.update(args.document)
    return export_vault(call, batch, args.output, documents, workspace)


def main(argv=None, *, session=None):
    parser = argparse.ArgumentParser(description=__doc__)
    token = core_client.configure_cli_connection(parser, session)
    actions = parser.add_subparsers(dest="action", required=True)
    imp = actions.add_parser("import")
    imp.add_argument("folder", type=Path)
    imp.add_argument("--receipt", dest="save_receipt", type=Path, help="save the note-to-path selection for subsequent export")
    exp = actions.add_parser("export")
    origin = exp.add_mutually_exclusive_group(required=True)
    origin.add_argument("--batch", help="export original members plus edits named by --document")
    origin.add_argument("--receipt", type=Path, help="use the current versions of notes in an import receipt or sync cursor")
    exp.add_argument("--document", nargs=2, metavar=("VAULT_PATH", "DOCUMENT_ID"), action="append", default=[])
    exp.add_argument("--output", type=Path, required=True)
    exp.add_argument("--save-receipt", type=Path, help="save the exported versions for the new Vault's first sync")
    exp.add_argument("--after-restore", action="store_true", help="verify a prior connection against a restored Core backup before exporting")
    sync = actions.add_parser("sync", help="exchange changes since the last local Vault sync")
    sync.add_argument("folder", type=Path)
    sync.add_argument("--receipt", type=Path, help="an import or export receipt, required only for the first sync")
    sync.add_argument("--resolve", nargs=2, action="append", default=[], metavar=("VAULT_PATH", "vault|aaos"),
                      help="choose a side of a reported conflict")
    sync.add_argument("--add-document", nargs=2, action="append", default=[], metavar=("VAULT_PATH", "DOCUMENT_ID"),
                      help="connect a new AAOS note at this path in the Vault")
    args = parser.parse_args(argv)
    if not args.core:
        parser.error("pass --core or set ARCHEAXIS_CORE_BASE")

    def call(method, path, body=None):
        payload = None if body is None else json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        status, value = core_client.call(args.core, method, path, token, payload)
        if status not in {200, 201, 202}:
            raise CoreError(method, path, status, value)
        return value

    try:
        output_receipt = getattr(args, "save_receipt", None)
        if output_receipt and (output_receipt.exists() or not output_receipt.parent.is_dir()):
            raise ValueError("select a new receipt file in an existing directory")
        if output_receipt and args.action == "export" and output_receipt.resolve() == args.output.resolve():
            raise ValueError("save the receipt separately from the exported Vault")
        if args.action == "import":
            result = import_vault(call, args.folder)
        elif args.action == "sync":
            from scripts.ingest.obsidian_sync import sync_vault

            receipt = json.loads(args.receipt.read_text(encoding="utf-8-sig")) if args.receipt else None
            result = sync_vault(call, args.folder, receipt, dict(args.resolve), dict(args.add_document))
        else:
            result = _export_selection(call, args)
        if output_receipt:
            with output_receipt.open("x", encoding="utf8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
    except (OSError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if args.action == "sync" and (result["conflicts"] or result["retry"] or result["issues"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
