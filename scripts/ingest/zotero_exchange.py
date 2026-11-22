"""Import public Zotero references or bibliography files and export saved AAOS document revisions."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlsplit

from app.adapters.anki_zotero import parse_zotero_json
from scripts.ingest.zotero_public import PublicGroup
from shared import core_client

FORMATS = ("csljson", "ris", "bibtex", "biblatex")
BIB_SUFFIXES = {".bib": "biblatex", ".bibtex": "bibtex", ".biblatex": "biblatex"}


def encoded(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class LocalTranslator:
    """Use Zotero's translation-server import/export endpoints on the user's own machine."""

    def __init__(self, base: str):
        url = urlsplit(base)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "::1", "localhost"}
                or url.username or url.password or url.path not in {"", "/"} or url.query or url.fragment):
            raise ValueError("the Zotero translation server must be a local HTTP origin")
        self.host, self.port = url.hostname, url.port or 80

    def _post(self, path, payload, media):
        connection = http.client.HTTPConnection(self.host, self.port, timeout=45)
        try:
            connection.request("POST", path, body=payload, headers={"Content-Type": media})
            response = connection.getresponse()
            body = response.read()
            if response.status != 200:
                raise ValueError(f"local Zotero {path} returned HTTP {response.status}: {body[:220].decode(errors='replace')}")
            return body, response.headers.get("Zotero-Translator-ID")
        except OSError as exc:
            raise ValueError(f"cannot reach the local Zotero translation server at {self.host}:{self.port}") from exc
        finally:
            connection.close()

    def import_items(self, payload):
        raw, translator_id = self._post("/import", payload, "text/plain; charset=utf-8")
        return json.loads(raw), translator_id

    def export_items(self, items, fmt):
        if fmt not in FORMATS:
            raise ValueError("unsupported bibliography export format")
        return self._post("/export?format=" + fmt, encoded(items), "application/json")[0]


def preserve(call, name, raw):
    source = call("POST", "/api/v1/imports", core_client.import_request(name, raw))
    if source["sha256"] != digest(raw):
        raise ValueError("the stored source digest differs from the supplied bibliography")
    return source


def convert_source(call, source):
    job_id = "bibliography-" + source["source_id"]
    route = "/api/v1/jobs/" + job_id
    job = call("POST", "/api/v1/jobs", {"job_id": job_id, "kind": "text", "input_ref": source["source_id"]})
    if job["state"] == "queued":
        call("POST", route + "/executions", {"deadline_ms": 120000}, headers={"idempotency-key": job_id})
    deadline = time.monotonic() + 125
    while job["state"] not in {"succeeded", "failed", "cancelled"}:
        if time.monotonic() >= deadline:
            raise ValueError(f"bibliography conversion is still pending: {job_id}")
        time.sleep(0.2)
        job = call("GET", route)
    if job["state"] != "succeeded":
        raise ValueError(f"bibliography conversion {job_id} is {job['state']}: {job.get('error')}")
    return job_id


def paragraph(key, value):
    return {"type": "paragraph", "attrs": {"block_id": key},
            "content": [{"type": "text", "text": value}] if value else []}


def _save_reference(call, source, job, index, csl, native, context):
    if not isinstance(csl, dict) or not csl.get("type") or not isinstance(csl.get("title"), str):
        raise ValueError(f"record {index + 1} has no CSL type or text title")
    csl = dict(csl)
    if not csl.get("id"):
        csl["id"] = f"aaos-{source['sha256'][:16]}-{index + 1}"
    identity = digest(encoded([source["sha256"], index, context]))
    binding = {"index": index, "job_id": job, "csl": csl, "native": native, **context}
    editor = {"type": "doc", "attrs": {"bibliography": binding}, "content": [
        paragraph("bibliography-title", csl["title"]), paragraph("bibliography-abstract", csl.get("abstract", ""))]}
    doc = call("POST", "/api/v1/documents", {"title": csl["title"][:120] or str(csl["id"]),
               "create_request_id": "bibliography-" + identity, "source_id": source["source_id"],
               "source_revision": source["sha256"], "editor_json": editor})
    return {"document_id": doc["document_id"], "document_version": doc["version"], "citation_id": csl["id"],
            "source_id": source["source_id"], "source_sha256": source["sha256"], "job_id": job}


def import_public(call, group: PublicGroup, keys, collection=None):
    records, pages, collections = group.capture(keys, collection, lambda name, raw: preserve(call, name, raw))
    saved, excluded = [], []
    for entry in records:
        row, origin = entry["record"], entry["origin"]
        if entry.get("excluded"):
            excluded.append({"key": row["key"], "version": row["version"], "source_id": origin["source_id"],
                             "reason": entry["excluded"]})
            continue
        if row["library"]["type"] != "group" or row["library"]["id"] != group.group:
            raise ValueError("unexpected library identity in Zotero object")
        summaries = parse_zotero_json([row])
        if not summaries or not isinstance(row.get("csljson"), dict):
            raise ValueError(f"Zotero item {row['key']} is not a bibliographic reference")
        context = {"format": "zotero-web-v3", "group": group.group, "key": row["key"], "version": row["version"],
                   "source_url": row["links"]["self"]["href"], "creator_names": summaries[0]["creators"],
                   "collections": entry["collections"], "children": entry["children"]}
        doc = _save_reference(call, origin, convert_source(call, origin), 0, row["csljson"], row["data"], context)
        saved.append({**doc, "key": row["key"], "version": row["version"],
                      "trashed_at_source": bool(row["data"].get("deleted")), "children": len(entry["children"])})
    return {"group": group.group, "pages": pages, "collections": collections, "documents": saved, "excluded": excluded,
            "attachment_scope": "Records and parent relationships; file contents must be separately supplied."}


def _native_citekey(item):
    if item.get("citationKey"):
        return item["citationKey"]
    for line in item.get("extra", "").splitlines():
        if line.lower().startswith("citation key:"):
            return line.partition(":")[2].strip()
    return None


def read_bib_file(executable, raw, source_format):
    try:
        result = subprocess.run([executable, "--from", source_format, "--to", "csljson"],
                                input=raw, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("local bibliography conversion needs a working Pandoc executable; pass --pandoc") from exc
    if result.returncode or not result.stdout.strip():
        detail = result.stderr.decode("utf-8", errors="replace").strip()[:240]
        raise ValueError(f"Pandoc could not read {source_format}: {detail}")
    return json.loads(result.stdout)


def import_file(call, path: Path, translator, pandoc="pandoc"):
    raw = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix not in {".json", ".csljson", ".ris", ".bib", ".bibtex", ".biblatex"}:
        raise ValueError("select a CSL JSON, RIS, BibTeX or BibLaTeX file")
    source = preserve(call, path.name, raw)
    job = convert_source(call, source)
    if suffix in BIB_SUFFIXES:
        reader = BIB_SUFFIXES[suffix]
        items = read_bib_file(pandoc, raw, reader)
        if any(not item.get("id") for item in items):
            raise ValueError("a BibTeX entry has no reusable citation key")
        item_pairs = [({**item, "citation-key": item["id"]}, None) for item in items]
        context = {"format": reader, "reader": "pandoc"}
    elif suffix in {".json", ".csljson"}:
        parsed = json.loads(raw)
        items = parsed if isinstance(parsed, list) else [parsed]
        item_pairs = [(record, None) for record in items]
        context = {"format": "csljson"}
    else:
        native_items, reader = translator.import_items(raw)
        item_pairs = []
        for native in native_items:
            if native.get("itemType") in {"note", "attachment", "annotation"}:
                continue
            # File translation assigns temporary Zotero library keys. The file's citation
            # key, when present, is the reusable identity for an exchange document.
            saved_native = {k: v for k, v in native.items() if k not in {"key", "version", "dateAdded", "dateModified"}}
            csl, = json.loads(translator.export_items([saved_native], "csljson"))
            csl["id"] = _native_citekey(saved_native) or csl.get("citation-key")
            item_pairs.append((csl, saved_native))
        context = {"format": suffix[1:], "reader": reader}
    if not item_pairs:
        raise ValueError("the file contains no bibliographic reference")
    docs = [_save_reference(call, source, job, i, csl, native, context)
            for i, (csl, native) in enumerate(item_pairs)]
    return {"documents": docs, "source_id": source["source_id"], "source_sha256": source["sha256"], "job_id": job}


def _block_text(node):
    if node.get("type") != "paragraph":
        raise ValueError("bibliography title and abstract require text paragraphs")
    parts = []
    for child in node.get("content", []):
        if child.get("marks") or child.get("type") not in {"text", "hardBreak"}:
            raise ValueError("keep rich source markup as literal text in bibliography field blocks")
        parts.append("\n" if child["type"] == "hardBreak" else child["text"])
    return "".join(parts)


def export_documents(call, document_ids, output, fmt, translator):
    if not document_ids or fmt not in FORMATS:
        raise ValueError("select reference documents and a supported format")
    records, native_items, versions, identifiers = [], [], [], set()
    for doc_id in document_ids:
        route = "/api/v1/documents/" + quote(doc_id, safe="")
        doc = call("GET", route)
        original = call("GET", route + "/versions/1")
        binding = original["editor_json"].get("attrs", {}).get("bibliography")
        if not binding or doc["source_id"] != original["source_id"] or doc["source_revision"] != original["source_revision"]:
            raise ValueError("select a saved bibliography document with its original source binding")
        nodes = doc["editor_json"].get("content", [])
        fields = {n.get("attrs", {}).get("block_id"): _block_text(n) for n in nodes}
        if set(fields) != {"bibliography-title", "bibliography-abstract"} or len(nodes) != 2:
            raise ValueError("a bibliography document must retain its title and abstract blocks")
        csl = dict(binding["csl"])
        if fmt in {"bibtex", "biblatex"}:
            csl["id"] = csl.get("citation-key") or csl["id"]
        if csl["id"] in identifiers:
            raise ValueError(f"two selected documents share citation ID {csl['id']}")
        identifiers.add(csl["id"])
        csl["title"] = fields["bibliography-title"]
        abstract = fields["bibliography-abstract"]
        if "abstract" in csl or abstract:
            csl["abstract"] = abstract
        records.append(csl)
        if fmt != "csljson":
            item = binding.get("native")
            if item is None:
                translated, _ = translator.import_items(encoded([csl]))
                item = next(v for v in translated if v.get("itemType") not in {"note", "annotation", "attachment"})
                if not item.get("tags") and isinstance(csl.get("keyword"), str):
                    item["tags"] = [{"tag": tag.strip()} for tag in csl["keyword"].split(",") if tag.strip()]
            item = {**item, "title": csl["title"], "abstractNote": abstract}
            if fmt in {"bibtex", "biblatex"}:
                item["citationKey"] = str(csl["id"])
            native_items.append(item)
        versions.append({"document_id": doc_id, "version": doc["version"], "source_id": doc["source_id"],
                         "source_sha256": doc["source_revision"], "citation_id": csl["id"]})
    if fmt == "csljson":
        data = (json.dumps(records, indent=2, ensure_ascii=False) + "\n").encode()
    else:
        data = translator.export_items(native_items, fmt)
    with output.open("xb") as stream:
        stream.write(data)
    return {"path": str(output), "format": fmt, "sha256": digest(data), "documents": versions,
            "scope": "Bibliography exchange. Collection membership, attachment files and Zotero library revisions remain in the source."}


def main(argv=None, *, session=None):
    parser = argparse.ArgumentParser(description=__doc__)
    token = core_client.configure_cli_connection(parser, session)
    parser.add_argument("--translator", default="http://127.0.0.1:1969",
                        help="local Zotero translation-server for RIS input and RIS or Bib(La)TeX output")
    parser.add_argument("--pandoc", default=os.environ.get("ARCHEAXIS_PANDOC") or "pandoc",
                        help="local Pandoc executable for BibTeX or BibLaTeX")
    actions = parser.add_subparsers(dest="action", required=True)
    public = actions.add_parser("import-public")
    public.add_argument("--group", required=True, type=int)
    select = public.add_mutually_exclusive_group(required=True)
    select.add_argument("--item", action="append")
    select.add_argument("--collection")
    public.add_argument("--page-size", default=50, type=int)
    actions.add_parser("import-file").add_argument("path", type=Path)
    export = actions.add_parser("export")
    export.add_argument("--document", required=True, action="append")
    export.add_argument("--format", choices=FORMATS, required=True)
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.core:
        parser.error("pass --core or set ARCHEAXIS_CORE_BASE")

    def call(method, path, body=None, *, headers=None):
        status, value = core_client.call(args.core, method, path, token, body, extra_headers=headers)
        if status not in {200, 201, 202}:
            raise ValueError(f"{method} {path} returned {status}: {str(value)[:240]}")
        return value

    try:
        if args.action == "import-public":
            result = import_public(call, PublicGroup(args.group, args.page_size), args.item, args.collection)
        elif args.action == "import-file":
            result = import_file(call, args.path, LocalTranslator(args.translator), args.pandoc)
        else:
            result = export_documents(call, args.document, args.output, args.format, LocalTranslator(args.translator))
    except (ValueError, OSError, http.client.HTTPException) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
