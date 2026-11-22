"""Exchange a local Logseq Markdown/Org file graph through the human Core session."""

from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote, unquote, urlsplit

from scripts.ingest.directory_batch import iter_files
from scripts.ingest.logseq_outline import block_text, native_uuid, page_name, split_outline, write_outline
from scripts.ingest.obsidian_vault import DOCUMENTS, CoreError, digest, original_bytes
from shared import core_client

GRAPH = "archeaxis.logseq-file-graph/v1"
EDITOR_LIMIT = 1024 * 1024
FORMATS = {".md": "Markdown", ".markdown": "Markdown", ".org": "Org"}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@contextmanager
def parser_session(node, module):
    driver = Path(__file__).with_name("logseq_parser.cjs")
    if not node:
        # In a staged full backend the existing course provider already supplies Node.
        location = driver.resolve().parents[2]
        bundled = location.parent.parent / "workers/openmaic/node.exe"
        node = str(bundled) if location.name == "exchange" and bundled.is_file() else "node"
    command = [node, str(driver)] + ([str(module)] if module else [])
    env = {k: v for k, v in os.environ.items() if k.upper() not in {"ARCHEAXIS_CORE_TOKEN", "NODE_OPTIONS"}}
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env) as proc:
        try:
            def reply():
                line = proc.stdout.readline()
                if not line:
                    raise OSError("the Logseq parser exited before returning a result")
                message = json.loads(line)
                if "error" in message:
                    raise ValueError(message["error"])
                return message

            if not reply().get("ready"):
                raise ValueError("the Logseq parser did not start")

            def parse(data, fmt):
                proc.stdin.write(encoded({"format": fmt, "text": data.decode("utf-8-sig")}) + b"\n")
                proc.stdin.flush()
                return split_outline(data, reply()["ast"], fmt)

            yield parse
        finally:
            proc.stdin.close()


def document_path(ident):
    return DOCUMENTS + "/" + quote(ident, safe="")


def store(call, name, data):
    sha = digest(data)
    if not data:
        return {"source_id": None, "sha256": sha}
    result = call("POST", "/api/v1/imports", core_client.import_request(name, data))
    if result["sha256"] != sha:
        raise ValueError(f"Core returned a different source revision for {name}")
    return {"source_id": result["source_id"], "sha256": sha}


def member_format(name):
    path = PurePosixPath(name)
    return FORMATS.get(path.suffix.lower()) if path.parts[0] in {"pages", "journals"} else None


def graph_member(name):
    path = PurePosixPath(name)
    if (name != path.as_posix() or path.is_absolute() or len(path.parts) < 2 or ".." in path.parts
            or any(":" in part or "\\" in part or part.endswith((" ", ".")) for part in path.parts)):
        return False
    return path.parts[0] in {"pages", "journals", "assets", "whiteboards", "draws"} or name == "logseq/config.edn"


def page_aliases(name, props):
    yield page_name(PurePosixPath(name))
    if props.get("title", "").strip():
        yield props["title"].strip()
    for value in re.findall(r"\[\[([^\]]+)\]\]|([^,\[\]]+)", props.get("alias", "") or props.get("aliases", "")):
        alias = (value[0] or value[1]).strip()
        if alias:
            yield alias


def relation_target(name, kind, target, pages, ids, members):
    if kind == "Block_ref":
        found = ids.get(native_uuid(target), [])
        if len(found) == 1:
            path, block_id = found[0]
            return {"kind": "document", "document_id": members[path]["document_id"], "version": 1, "block_id": block_id}, None
    elif kind == "Page_ref":
        found = pages.get(target.strip().casefold(), set())
        if len(found) == 1:
            path = next(iter(found))
            return {"kind": "document", "document_id": members[path]["document_id"], "version": 1}, None
    else:
        url = urlsplit(target)
        if url.scheme or url.netloc or url.path.startswith("/"):
            return None, "external"
        path = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(url.path)))
        found = [path] if path in members else []
        if found and members[path]["source_id"] and not url.fragment and not url.query:
            return {"kind": "source", "source_id": members[path]["source_id"], "sha256": members[path]["sha256"]}, None
        if found:
            return None, "file retained; empty content or fragment has no fixed source target"
    return None, "ambiguous target" if len(found) > 1 else "target absent from the selected file graph"


def bind(call, name, links, pages, ids, members, losses):
    relations = []
    for kind, target, label, embed in links:
        ref, reason = relation_target(name, kind, target, pages, ids, members)
        if reason == "external":
            continue
        if ref and (len(relations) >= 256 or len(label.encode()) > 1024):
            ref, reason = None, "Core relation count or label limit reached"
        if not ref:
            losses.append({"path": name, "kind": kind, "target": target, "reason": reason})
            continue
        row = {"id": f"logseq-{len(relations) + 1}", "kind": "related", "label": label, "target": ref}
        if embed:
            row["presentation"] = "embed"
        relations.append(row)
    if not relations:
        return 0
    route = document_path(members[name]["document_id"])
    bundle = {"schema": "archeaxis.relations/v1", "relations": relations}
    current = call("GET", route)
    if current["version"] == 1:
        editor = current["editor_json"]
        editor["attrs"]["archeaxis_relations"] = bundle
        if len(encoded(editor)) > EDITOR_LIMIT:
            losses.append({"path": name, "reason": "page saved; resolved relations exceed the Core editor limit"})
            return 0
        try:
            call("PUT", route + "/draft", {"expected_version": 1, "editor_json": editor})
            return len(relations)
        except CoreError as exc:
            if exc.status != 409:
                raise
    # A replay after an ordinary edit keeps the imported relation snapshot and all later edits.
    first_update = call("GET", route + "/versions/2")
    if first_update["editor_json"].get("attrs", {}).get("archeaxis_relations") == bundle:
        return len(relations)
    losses.append({"path": name, "reason": "the page was edited before its initial links could be saved"})
    return 0


def import_graph(call, root, parse):
    root = root.resolve(strict=True)
    files, excluded = iter_files(root)
    if not any((root / subdir).is_dir() for subdir in ("pages", "journals")):
        raise ValueError("select the Logseq file graph folder containing pages or journals")
    members, page_links, losses = {}, {}, []
    pages, ids = defaultdict(set), defaultdict(list)
    for path in files:
        name = path.relative_to(root).as_posix()
        if not graph_member(name) or path.stat().st_size > 64 * 1024 * 1024:
            excluded.append(name)
            continue
        members[name] = store(call, path.name, path.read_bytes())
    if not members:
        raise ValueError("no Logseq graph members were selected")
    identity = digest(encoded(sorted((name, row["sha256"]) for name, row in members.items())))
    for name, member in sorted(members.items()):
        fmt = member_format(name)
        if not fmt:
            continue
        raw = (root / name).read_bytes()
        if digest(raw) != member["sha256"]:
            raise ValueError(f"{name} changed during import; restart with the desired file snapshot")
        if len(raw) > EDITOR_LIMIT or not raw:
            losses.append({"path": name, "reason": "empty page or page above the editor size limit; original retained"})
            continue
        try:
            blocks, links, props = parse(raw, fmt)
        except ValueError as exc:
            losses.append({"path": name, "reason": "source retained; " + str(exc)})
            continue
        meta = {"graph": identity, "path": name, "format": fmt, "properties": props}
        editor = {"type": "doc", "attrs": {"logseq": meta}, "content": blocks}
        if len(encoded(editor)) > EDITOR_LIMIT or len(blocks) > 5000:
            losses.append({"path": name, "reason": "outline exceeds the Core document limit; original retained"})
            continue
        names = list(page_aliases(name, props))
        doc = call("POST", DOCUMENTS, {"create_request_id": "logseq-" + digest(encoded([identity, name])),
                   "title": (props.get("title") or names[0])[:230], "source_id": member["source_id"],
                   "source_revision": member["sha256"], "editor_json": editor})
        member["document_id"] = doc["document_id"]
        member["native_ids"] = []
        for alias in names:
            pages[alias.casefold()].add(name)
        for block in blocks:
            attrs = block["attrs"]
            if attrs["native_id"]:
                member["native_ids"].append(attrs["native_id"])
                ids[attrs["native_id"]].append((name, attrs["block_id"]))
        page_links[name] = links
    bound = sum(bind(call, name, links, pages, ids, members, losses) for name, links in page_links.items())
    manifest = {"schema": GRAPH, "graph": identity, "members": dict(sorted(members.items()))}
    graph = store(call, root.name + ".logseq-graph.json", encoded(manifest))
    return {"schema": GRAPH, "graph_id": graph["source_id"], "manifest_sha256": graph["sha256"],
            "files": len(members), "documents": {n: m["document_id"] for n, m in members.items() if "document_id" in m},
            "native_ids": len(ids), "bound_links": bound, "excluded": sorted(excluded), "losses": losses}


def load_graph(call, ident):
    record = call("GET", "/api/v1/sources/" + quote(ident, safe="") + "/original")
    data = base64.b64decode(record["content_base64"], validate=True)
    graph = json.loads(data)
    if digest(data) != record["sha256"] or graph.get("schema") != GRAPH:
        raise ValueError("select a saved Logseq file graph ID")
    members = graph["members"]
    if any(not graph_member(name) for name in members) or (
            digest(encoded(sorted((n, m["sha256"]) for n, m in members.items()))) != graph["graph"]):
        raise ValueError("the graph index does not match its original member identities")
    return graph


def page_snapshot(call, graph, name):
    member = graph["members"][name]
    route = document_path(member["document_id"])
    original = call("GET", route + "/versions/1")
    meta = original["editor_json"]["attrs"]["logseq"]
    if (original["source_id"] != member["source_id"] or original["source_revision"] != member["sha256"]
            or meta["graph"] != graph["graph"] or meta["path"] != name):
        raise ValueError(f"page belongs to a different Logseq source or graph: {name}")
    return original, call("GET", route)


def select_block(call, graph, ident, text=None):
    uuid = native_uuid(ident)
    found = [name for name, m in graph["members"].items() for value in m.get("native_ids", []) if value == uuid]
    if not uuid or len(found) != 1:
        raise ValueError("the native block UUID is missing or ambiguous in this graph")
    name = found[0]
    original, doc = page_snapshot(call, graph, name)
    block = next((b for b in doc["editor_json"]["content"] if b.get("attrs", {}).get("block_id") == uuid), None)
    if not block:
        raise ValueError("the current document no longer contains this block")
    body = block_text(block)
    if text is not None:
        if not text.strip() or "\n" in text or "\r" in text:
            raise ValueError("provide one nonempty line for the block text")
        first = re.split(r"[\r\n]", body, maxsplit=1)[0]
        if first != text:
            body = text + body[len(first):]
            block["content"] = [{"type": "text", "text": body}]
            doc = call("PUT", document_path(doc["document_id"]) + "/draft",
                       {"expected_version": doc["version"], "editor_json": doc["editor_json"]})
    return {"path": name, "block_id": uuid, "document_id": doc["document_id"], "version": doc["version"],
            "source_version": original["source_revision"], "text": body}


def export_graph(call, graph, destination, parser):
    if destination.exists():
        raise ValueError("choose a new directory for the exported graph")
    saved = {}
    with ExitStack() as stack:
        temp = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".aaos-logseq-", dir=destination.parent)))
        folder = temp / "graph"
        folder.mkdir()
        parse = None
        for name, m in graph["members"].items():
            data = original_bytes(call, m["source_id"], m["sha256"]) if m["source_id"] else b""
            if digest(data) != m["sha256"]:
                raise ValueError(f"the retained source differs from {name}")
            if "document_id" in m:
                orig, latest = page_snapshot(call, graph, name)
                before = orig["editor_json"]["content"]
                rendered = write_outline(data, before, latest["editor_json"]["content"])
                if rendered != data:
                    if parse is None:
                        parse = stack.enter_context(parser())
                    after, _, _ = parse(rendered, member_format(name))
                    def structure(blocks):
                        return [(b["attrs"]["block_id"], b["attrs"]["level"], b["attrs"]["parent"]) for b in blocks]
                    if structure(after) != structure(before):
                        raise ValueError(f"the edit changes the native outline or block identities in {name}")
                data = rendered
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
            saved[name] = digest(data)
        folder.rename(destination)
    return {"schema": GRAPH, "output": str(destination), "files": saved}


def main(argv=None, *, session=None):
    cli = argparse.ArgumentParser(description=__doc__)
    token = core_client.configure_cli_connection(cli, session)
    commands = cli.add_subparsers(dest="action", required=True)
    imp = commands.add_parser("import")
    imp.add_argument("folder", type=Path)
    exp = commands.add_parser("export")
    exp.add_argument("--graph", required=True)
    exp.add_argument("--output", type=Path, required=True)
    for sub in (imp, exp):
        sub.add_argument("--node", help="local Node executable")
        sub.add_argument("--mldoc", default=os.environ.get("ARCHEAXIS_LOGSEQ_MLDOC"),
                         help="local mldoc 1.5.7 index.js")
    block = commands.add_parser("block", help="read a native block or change its first line")
    block.add_argument("--graph", required=True)
    block.add_argument("uuid")
    block.add_argument("--text")
    args = cli.parse_args(argv)
    if not args.core:
        cli.error("pass --core or set ARCHEAXIS_CORE_BASE")

    def call(method, path, body=None):
        status, result = core_client.call(args.core, method, path, token, body)
        if status not in (200, 201, 202):
            raise CoreError(method, path, status, result)
        return result

    try:
        if args.action == "import":
            with parser_session(args.node, args.mldoc) as parse:
                result = import_graph(call, args.folder, parse)
        else:
            graph = load_graph(call, args.graph)
            result = (select_block(call, graph, args.uuid, args.text) if args.action == "block" else
                      export_graph(call, graph, args.output, lambda: parser_session(args.node, args.mldoc)))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
