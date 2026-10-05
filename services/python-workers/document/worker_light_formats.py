"""Bounded lightweight structure facts; no database or content execution."""
from __future__ import annotations

import csv
import email.policy
import io
import json
import math
import posixpath
import re
import tomllib
import zipfile
from datetime import date, datetime, time
from email.parser import BytesParser
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

MAX_BYTES = 16 * 1024 * 1024
MAX_LOCATIONS = 2000
MAX_DEPTH = 64


def leaves(value, path="", depth=0, seen=None):
    if depth > MAX_DEPTH:
        raise ValueError("structured input depth exceeds 64")
    seen = set() if seen is None else seen
    if isinstance(value, (dict, list)):
        if id(value) in seen:
            raise ValueError("cyclic structure is not supported")
        seen = seen | {id(value)}
        children = value.items() if isinstance(value, dict) else enumerate(value)
        out = []
        for key, child in children:
            key = str(key).replace("~", "~0").replace("/", "~1")
            out.extend(leaves(child, path + "/" + key, depth + 1, seen))
            if len(out) > MAX_LOCATIONS:
                raise ValueError("structured input exceeds 2000 leaf locations")
        return out
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite structured values are not supported")
    if isinstance(value, (date, datetime, time)):
        return [{"kind": "object_path", "path": path or "/", "value": value.isoformat(),
                 "value_type": type(value).__name__}]
    if not isinstance(value, (str, int, float, bool, type(None))):
        raise ValueError("unsupported structured scalar type")
    return [{"kind": "object_path", "path": path or "/", "value": value}]


def xml(raw):
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", raw, re.I):
        raise ValueError("XML DTD/entity declarations are forbidden")
    root = ET.fromstring(raw)
    result = []

    def visit(node, path, depth):
        if depth > MAX_DEPTH or len(result) >= MAX_LOCATIONS:
            raise ValueError("XML depth/location budget exceeded")
        if node.text and node.text.strip():
            result.append({"kind": "xml_path", "path": path, "value": node.text.strip()})
        for key, value in node.attrib.items():
            result.append({"kind": "xml_path", "path": path + "/@" + key, "value": value})
        counts = {}
        for child in node:
            counts[child.tag] = counts.get(child.tag, 0) + 1
            visit(child, path + f"/{child.tag}[{counts[child.tag]}]", depth + 1)
    visit(root, "/" + root.tag + "[1]", 1)
    return root, result


class BodyText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def epub(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len(infos) > 128 or sum(x.file_size for x in infos) > MAX_BYTES:
            raise ValueError("EPUB entry/expanded-byte budget exceeded")
        names = [x.filename for x in infos]
        if len(set(names)) != len(names):
            raise ValueError("EPUB duplicate paths are forbidden")
        for item in infos:
            if (item.filename.startswith(("/", "\\")) or "\\" in item.filename
                    or ".." in item.filename.split("/") or item.file_size > 2 * 1024 * 1024
                    or item.flag_bits & 1 or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("unsafe EPUB member")
        container, _ = xml(archive.read("META-INF/container.xml"))
        rootfile = next((x.attrib.get("full-path") for x in container.iter()
                         if x.tag.rsplit("}", 1)[-1] == "rootfile"), None)
        if rootfile not in names:
            raise ValueError("EPUB rootfile missing")
        package, _ = xml(archive.read(rootfile))
        manifest = {x.attrib["id"]: x.attrib for x in package.iter()
                    if x.tag.rsplit("}", 1)[-1] == "item" and "id" in x.attrib}
        spine = [x.attrib.get("idref") for x in package.iter()
                 if x.tag.rsplit("}", 1)[-1] == "itemref"]
        parts, locations, chapter_list = [], [], []
        for index, key in enumerate(spine, 1):
            item = manifest.get(key)
            if item is None:
                raise ValueError("EPUB spine item missing")
            href = item.get("href", "")
            if ":" in href or href.startswith("/") or ".." in href.split("/"):
                raise ValueError("EPUB external/traversal chapter is forbidden")
            name = posixpath.join(posixpath.dirname(rootfile), href)
            chapter_raw = archive.read(name)
            xml(chapter_raw)
            reader = BodyText()
            reader.feed(chapter_raw.decode("utf-8"))
            chapter_list.append({"chapter": index, "path": name,
                        "title": reader.parts[0] if reader.parts else "",
                        "derived_from": "spine chapter first text; not a native navigation TOC"})
            for paragraph, text in enumerate(reader.parts, 1):
                parts.append(text)
                locations.append({"kind": "epub_chapter_paragraph", "path": name,
                                  "chapter": index, "paragraph": paragraph, "value": text})
        if not parts:
            raise ValueError("EPUB has no readable spine text")
        toc = []
        for item in manifest.values():
            if "nav" not in item.get("properties", "").split():
                continue
            href = item.get("href", "")
            if ":" in href or ".." in href.split("/") or href.startswith("/"):
                raise ValueError("unsafe EPUB navigation path")
            nav, _ = xml(archive.read(posixpath.join(posixpath.dirname(rootfile), href)))
            toc.extend({"href": node.attrib["href"], "title": "".join(node.itertext()).strip()}
                       for node in nav.iter() if node.tag.rsplit("}", 1)[-1] == "a" and "href" in node.attrib)
        import hashlib
        assets = [{"path": x.filename, "bytes": x.file_size,
                   "sha256": hashlib.sha256(archive.read(x.filename)).hexdigest()} for x in infos
                  if x.filename not in ("mimetype", "META-INF/container.xml", rootfile)]
        return "\n".join(parts), {"format": "epub", "parsed": True,
                "locations": locations, "spine": spine, "toc": toc,
                "chapter_list": chapter_list, "assets": assets}, [
                "EPUB text projected in spine order; chapter list derives from first text; EPUB3 navigation links retained; CSS/layout and binary asset decoding are not rendered" +
                ("; no EPUB3 navigation TOC declared" if not toc else "")]


def mail(raw):
    import hashlib
    message = BytesParser(policy=email.policy.default).parsebytes(raw)
    if message.defects:
        raise ValueError("malformed EML MIME structure")
    headers = {key: str(message.get(key, "")) for key in ("From", "To", "Subject", "Message-ID", "Date")}
    parts, locations, attachments = [], [], []
    for index, part in enumerate(message.walk()):
        if part.is_multipart():
            continue
        payload = part.get_payload(decode=True) or b""
        if part.get_filename() or part.get_content_disposition() == "attachment":
            attachments.append({"part": index, "name": part.get_filename(), "bytes": len(payload),
                                "sha256": hashlib.sha256(payload).hexdigest()})
            continue
        if part.get_content_type() in ("text/plain", "text/html"):
            text = payload.decode(part.get_content_charset() or "utf-8", "strict")
            if part.get_content_type() == "text/html":
                reader = BodyText()
                reader.feed(text)
                text = "\n".join(reader.parts)
            parts.append(text)
            locations.append({"kind": "mail_mime_part", "path": f"/parts/{index}", "value": text})
    if not parts:
        raise ValueError("EML has no readable text body")
    losses = ["mail MIME body decoded; headers retained as facts; display formatting is not preserved"]
    if attachments:
        losses.append("attachments inventoried with byte hashes; independent extraction is not performed")
    return "\n".join(parts), {"format": "eml", "parsed": True, "headers": headers,
            "locations": locations, "attachments": attachments}, losses


def parse(raw, media):
    if media not in {"application/epub+zip", "message/rfc822", "text/csv",
                     "text/tab-separated-values", "application/x-ndjson", "application/yaml",
                     "text/x-yaml", "application/toml", "application/json", "application/xml", "text/xml"}:
        return None
    if len(raw) > MAX_BYTES:
        raise ValueError("light format input exceeds byte budget")
    if media == "application/epub+zip":
        return epub(raw)
    if media == "message/rfc822":
        return mail(raw)
    text = raw.decode("utf-8-sig", "strict")
    if media in ("text/csv", "text/tab-separated-values"):
        rows = list(csv.reader(io.StringIO(text), delimiter="\t" if media.endswith("values") else ","))
        locations = [{"kind": "table_cell", "row": row, "column": col, "value": value}
                     for row, values in enumerate(rows, 1) for col, value in enumerate(values, 1)]
        capped = len(locations) > MAX_LOCATIONS
        locations = locations[:MAX_LOCATIONS]
        name = "tsv" if media.endswith("values") else "csv"
    elif media == "application/x-ndjson":
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) > MAX_LOCATIONS:
            raise ValueError("JSONL record budget exceeded")
        values = [json.loads(line) for line in lines]
        locations = [{**loc, "record": index} for index, value in enumerate(values, 1) for loc in leaves(value)]
        name = "jsonl"
    elif media in ("application/yaml", "text/x-yaml"):
        import yaml
        locations = leaves(yaml.safe_load(text))
        name = "yaml"
    elif media == "application/toml":
        locations = leaves(tomllib.loads(text))
        name = "toml"
    elif media == "application/json":
        locations = leaves(json.loads(text))
        name = "json"
    elif media in ("application/xml", "text/xml"):
        _, locations = xml(raw)
        name = "xml"
    else:
        return None
    if len(locations) > MAX_LOCATIONS:
        raise ValueError("light format location budget exceeded")
    return text, {"format": name, "parsed": True, "locations": locations,
                  "locations_capped": capped if name in {"csv", "tsv"} else False}, [
        "native value locations are structure facts; canonical anchors refer to projected text lines" +
        ("; native cell locations capped at 2000" if name in {"csv", "tsv"} and capped else "")]
