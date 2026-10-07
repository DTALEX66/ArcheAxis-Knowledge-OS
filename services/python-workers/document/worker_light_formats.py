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
    body_text = "\n".join(parts)
    inventoried = "attachments inventoried with byte hashes; independent extraction is not performed"
    if body_text.strip():
        losses = ["mail MIME body decoded; headers retained as facts; display formatting is not preserved"]
        if attachments:
            losses.append(inventoried)
        return body_text, {"format": "eml", "parsed": True, "headers": headers,
                           "has_readable_body": True, "text_body_parts": len(parts),
                           "locations": locations, "attachments": attachments}, losses
    # The body carries no readable text: either no text part exists at all, or every text part
    # is empty. A mail can still be readable here - its headers are the file's own text, and mail
    # headers are a required output - so refusing would throw the headers away with the body.
    header_block = [(key, f"{key}: {value}") for key, value in headers.items() if value.strip()]
    if not parts and not header_block and not attachments:
        raise ValueError("EML has no readable text body, headers or attachments")
    absent = "no text body part exists" if not parts else "every text body part is empty"
    if header_block:
        locations = [
            {"kind": "mail_header", "path": f"/headers/{key.lower()}", "value": line}
            for key, line in header_block
        ]
        text = "\n".join(line for _, line in header_block)
        losses = [f"{absent}; the projected text is the mail's own header block and no body is claimed"]
    else:
        text = ""
        losses = [f"{absent} and no readable headers are present; the projection claims no text"]
    if attachments:
        losses.append(inventoried)
    return text, {"format": "eml", "parsed": True, "headers": headers,
                  "has_readable_body": False, "text_body_parts": len(parts),
                  "locations": locations, "attachments": attachments}, losses


ATTACHMENT_JOB_CAP = 50
ATTACHMENT_BYTES_CAP = 64 * 1024 * 1024


def _safe_attachment_name(index: int, name: str) -> str:
    """A flat, collision-free file name for one attachment.

    An attachment's own name may contain separators, be absolute or try to escape, so the
    written file is named by its index with a sanitised suffix. The true name travels in the
    declaration, never in the path - the same rule the archive worker follows.
    """
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in base)[-64:]
    return f"{index:04d}-{safe or 'attachment'}"


def _long_path(path) -> str:
    """Name an absolute transfer path in a form Windows still creates inside a deep workspace.

    The transport prefixes only the directory it hands over, and Windows answers a create whose
    full path passes the limit with ERROR_FILE_NOT_FOUND, so a part whose own name is a dozen
    characters longer than that directory simply stops existing. Same convention as
    `worker_archive._long_path`; the Core reads these bytes back through the same prefix.
    """
    import sys
    from pathlib import Path as _Path

    text = str(path)
    if sys.platform == "win32" and not text.startswith("\\\\?\\") and _Path(text).is_absolute():
        return "\\\\" + "?\\" + text
    return text


def mail_attachments(raw, member_dir):
    """Write the attachments a mail carries and declare each one by digest.

    The worker holds no database handle, so it writes bytes and reports them; the Core verifies
    each digest and size, imports each attachment as its own source and queues the route the
    attachment's own name selects. A part with no filename is a body part, not an attachment.
    Anything over the count or byte budget is reported as a problem instead of being dropped.
    """
    import hashlib
    from pathlib import Path as _Path

    out = _Path(str(member_dir))
    message = BytesParser(policy=email.policy.default).parsebytes(raw)
    if message.defects:
        raise ValueError("malformed EML MIME structure")
    extracted: list[dict] = []
    problems: list[str] = []
    total = 0
    seen = 0
    for part in message.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        if not filename and part.get_content_disposition() != "attachment":
            continue
        seen += 1
        if len(extracted) >= ATTACHMENT_JOB_CAP:
            problems.append(
                f"only the first {ATTACHMENT_JOB_CAP} of {seen} attachments were extracted"
            )
            break
        try:
            payload = part.get_payload(decode=True)
        except Exception as exc:  # noqa: BLE001 - an undecodable part is a fact, not a crash
            problems.append(
                f"attachment {filename!r} could not be decoded: {type(exc).__name__}: {exc}"
            )
            continue
        if payload is None:
            problems.append(f"attachment {filename!r} carries no decodable payload")
            continue
        if total + len(payload) > ATTACHMENT_BYTES_CAP:
            problems.append(
                f"attachment byte budget of {ATTACHMENT_BYTES_CAP} reached; later attachments were not extracted"
            )
            break
        try:
            _Path(_long_path(out)).mkdir(parents=True, exist_ok=True)
            target = out / _safe_attachment_name(seen, filename or "attachment")
            _Path(_long_path(target)).write_bytes(payload)
        except OSError as exc:
            problems.append(f"attachment {filename!r} could not be written: {exc}")
            continue
        total += len(payload)
        extracted.append({
            "name": filename or f"attachment-{seen}",
            "file": target.name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    return extracted, problems


ODF_MEDIA = {
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.oasis.opendocument.presentation": "odp",
}
# ODF names its elements and attributes by namespace, so both are matched in Clark notation.
ODF_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
}


def _odf(namespace, name):
    return f"{{{ODF_NS[namespace]}}}{name}"


# An ODF cell or row may declare itself repeated, and a template can declare the whole grid
# (16384 columns), so expansion is bounded and a bounded row is reported rather than hidden.
ODF_REPEAT_CAP = 512


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _odf_safe(archive):
    infos = archive.infolist()
    if len(infos) > 128 or sum(item.file_size for item in infos) > MAX_BYTES:
        raise ValueError("ODF entry/expanded-byte budget exceeded")
    names = [item.filename for item in infos]
    if len(set(names)) != len(names):
        raise ValueError("ODF duplicate paths are forbidden")
    for item in infos:
        if (item.filename.startswith(("/", "\\")) or "\\" in item.filename
                or ".." in item.filename.split("/") or item.file_size > 2 * 1024 * 1024
                or item.flag_bits & 1 or (item.external_attr >> 16) & 0o170000 == 0o120000):
            raise ValueError("unsafe ODF member")
    return names


def _odf_text(element):
    return "".join(element.itertext()).strip()


def _odf_repeat(element, namespace, attribute):
    declared = element.get(_odf(namespace, attribute))
    try:
        value = int(declared) if declared else 1
    except ValueError:
        value = 1
    value = max(1, value)
    return min(value, ODF_REPEAT_CAP), value > ODF_REPEAT_CAP


def odf(raw, media):
    """Read an ODF package's own content.xml: headings, paragraphs, cells and pages."""
    name = ODF_MEDIA[media]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = _odf_safe(archive)
        if "mimetype" not in names:
            raise ValueError("ODF mimetype entry missing")
        declared = archive.read("mimetype").decode("ascii", "ignore").strip()
        if declared != media:
            raise ValueError(f"ODF mimetype declares {declared!r}, not {media}")
        if "content.xml" not in names:
            raise ValueError("ODF content.xml missing")
        root, _ = xml(archive.read("content.xml"))
        title = None
        if "meta.xml" in names:
            meta, _ = xml(archive.read("meta.xml"))
            for node in meta.iter(_odf("meta", "title")):
                if node.text and node.text.strip():
                    title = node.text.strip()
                    break
        body = [element for element in root.iter()
                if element.tag in {_odf("text", "h"), _odf("text", "p"), _odf("table", "table"),
                                   _odf("table", "table-row"), _odf("table", "table-cell"),
                                   _odf("draw", "page")}]

    blocks, locations, losses = [], [], []
    capped = False
    sheet = None
    page = None
    row = 0
    column = 0
    for element in body:
        tag = element.tag
        if tag == _odf("table", "table"):
            sheet = element.get(_odf("table", "name")) or f"sheet-{len(locations) + 1}"
            column = 0
        elif tag == _odf("table", "table-row"):
            repeat, hit_cap = _odf_repeat(element, "table", "number-rows-repeated")
            capped = capped or hit_cap
            row += repeat
            column = 0
        elif tag == _odf("table", "table-cell"):
            if sheet is None:
                continue
            value = element.get(_odf("office", "value"))
            text = _odf_text(element)
            display = value if value not in (None, "") else text
            repeat, hit_cap = _odf_repeat(element, "table", "number-columns-repeated")
            capped = capped or hit_cap
            if not display:
                column += repeat
                continue
            column += 1
            locations.append({"kind": "odf_table_cell", "sheet": sheet, "row": row,
                              "column": column, "span": repeat,
                              "value_type": element.get(_odf("office", "value-type")) or "text",
                              "value": display, "path": f"{sheet}/r{row}c{column}"})
            blocks.append(f"{sheet}!R{row}C{column}: {display}")
            column += repeat - 1
        elif tag == _odf("draw", "page"):
            page = element.get(_odf("draw", "name")) or f"page-{len(locations) + 1}"
            blocks.append(f"Page: {page}")
            locations.append({"kind": "odf_page", "path": page, "value": page,
                              "position": len(blocks)})
        elif tag == _odf("text", "h"):
            text = _odf_text(element)
            if not text:
                continue
            level = element.get(_odf("text", "outline-level")) or "1"
            path = "/".join(part for part in (page, sheet, f"heading-{level}") if part)
            blocks.append(text)
            locations.append({"kind": "odf_heading", "path": path, "level": level,
                              "value": text, "position": len(blocks)})
        elif tag == _odf("text", "p"):
            text = _odf_text(element)
            if not text:
                continue
            path = "/".join(part for part in (page, sheet, "paragraph") if part)
            blocks.append(text)
            locations.append({"kind": "odf_paragraph", "path": path, "value": text,
                              "position": len(blocks)})
    if capped:
        losses.append(f"row/column repeat expansion capped at {ODF_REPEAT_CAP}; a template that "
                      "declares a larger grid is reported at the cap, not inflated")
    if not blocks:
        raise ValueError("ODF carries no readable text")
    losses.append("ODF body read from content.xml; styles, fields, embedded objects and "
                  "hyperlink targets are not followed")
    return "\n".join(blocks), {"format": name, "parsed": True, "title": title,
            "location_model": "odf content.xml elements; canonical anchors refer to projected lines",
            "locations": locations[:MAX_LOCATIONS],
            "locations_capped": len(locations) > MAX_LOCATIONS}, losses


def rtf(raw):
    """Strip RTF control words with the declared engine; a missing engine fails the job."""
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError as exc:
        raise RuntimeError("rtf engine missing (striprtf not installed)") from exc
    text = (rtf_to_text(raw.decode("utf-8", "replace")) or "").strip()
    if not text:
        raise ValueError("RTF carries no readable text")
    paragraphs = [item.strip() for item in text.split("\n\n") if item.strip()]
    if len(paragraphs) > MAX_LOCATIONS:
        raise ValueError("light format location budget exceeded")
    locations = [{"kind": "rtf_paragraph", "path": f"/paragraphs/{index}", "value": paragraph,
                  "position": index} for index, paragraph in enumerate(paragraphs, 1)]
    return text, {"format": "rtf", "parsed": True,
            "location_model": "RTF paragraphs after control words are stripped",
            "locations": locations}, [
        "RTF control words stripped by the declared engine; tables, footnotes, styles and "
        "embedded objects are not reconstructed"]


def python_source(raw):
    """Report the symbols a Python file actually declares, using the interpreter's own parser.

    Only what `ast` states is reported: a name, its kind and the line it starts on. A file that
    does not parse is reported as such - the text route still keeps every line as an anchor, so a
    version mismatch or a template file never turns into a fabricated symbol list."""
    text = raw.decode("utf-8-sig", "strict")
    lines = text.splitlines()
    try:
        import ast as _ast

        tree = _ast.parse(text)
    except SyntaxError as exc:
        return text, {"format": "python", "parsed": False,
                     "location_model": "line anchors; symbols need a parseable module",
                     "symbols": [], "parse_error": f"{type(exc).__name__}: {exc}"}, [
            "Python source did not parse, so no symbols are claimed"]
    symbols = []
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.ClassDef, _ast.FunctionDef, _ast.AsyncFunctionDef)):
            kind = "class" if isinstance(node, _ast.ClassDef) else (
                "async_function" if isinstance(node, _ast.AsyncFunctionDef) else "function")
            line = min(max(int(node.lineno), 1), len(lines)) if lines else 1
            symbols.append({"kind": "python_symbol", "symbol_kind": kind, "name": node.name,
                            "line": line, "path": f"/symbols/{node.name}",
                            "value": (lines[line - 1].strip() if lines else node.name)})
        elif isinstance(node, (_ast.Import, _ast.ImportFrom)):
            count = len(node.names)
            if count:
                line = min(max(int(node.lineno), 1), len(lines)) if lines else 1
                symbols.append({"kind": "python_symbol", "symbol_kind": "import",
                                "name": getattr(node, "module", None) or node.names[0].name,
                                "count": count, "line": line, "path": "/symbols/import",
                                "value": (lines[line - 1].strip() if lines else "")})
    if len(symbols) > MAX_LOCATIONS:
        raise ValueError("light format location budget exceeded")
    order = {(typ, name) for typ, name in ((s["symbol_kind"], s["name"]) for s in symbols)}
    return text, {"format": "python", "parsed": True,
                  "location_model": "ast symbols over the source lines; anchors remain line based",
                  "locations": symbols, "symbol_count": len(symbols),
                  "top_level_symbols": len(order)}, [
        "Symbols come from the file's own syntax tree; decorators, docstrings and type hints are "
        "not interpreted, and anchors stay line based"]


def parse(raw, media):
    if media not in {"application/epub+zip", "message/rfc822", "text/csv",
                     "text/tab-separated-values", "application/x-ndjson", "application/yaml",
                     "text/x-yaml", "application/toml", "application/json", "application/xml", "text/xml",
                     "text/x-python", *ODF_MEDIA, "application/rtf"}:
        return None
    if len(raw) > MAX_BYTES:
        raise ValueError("light format input exceeds byte budget")
    if media == "application/epub+zip":
        return epub(raw)
    if media == "message/rfc822":
        return mail(raw)
    if media in ODF_MEDIA:
        return odf(raw, media)
    if media == "application/rtf":
        return rtf(raw)
    if media == "text/x-python":
        return python_source(raw)
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
                  "location_model": "native values; canonical anchors refer to projected text lines",
                  "locations_capped": capped if name in {"csv", "tsv"} else False}, (
        ["native cell locations capped at 2000"] if name in {"csv", "tsv"} and capped else []
    )
