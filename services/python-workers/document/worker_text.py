#!/usr/bin/env python3
"""ArcheAxis vNext document worker: plain text family (F01).

Formats: TXT / MD / CSV / TSV / JSON / XML (textual sources).

Isolation boundary: this worker NEVER opens the vNext database and never
executes file content. It decodes bytes faithfully (encoding/line endings
preserved and reported), projects text + line anchors, and prints a single
JSON envelope on stdout. Failure contract: non-zero exit + {"error": ...},
never a fake success envelope.

R15/F01: the projection stays canonical (text + line anchors), and the format
facts the route can actually derive - markdown headings and links, CSV row and
column shape, JSON depth and keys, XML root and element count - are reported in
`loss_receipt.params["format"]`. A file that does not parse is still projected as
text, and the fact says so: `parsed: false` with the reason, never silence and
never a fabricated structure.

Usage:
    python worker_text.py <input-file> [media-type]
Output: {"engine","engine_version","text","structure","loss_receipt"}
"""

from __future__ import annotations

import contextlib
import csv
import email
import io
import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

ENGINE = "python-worker-text"
ENGINE_VERSION = "0.1.0"

HEADING_CAP = 200
ROW_CAP = 50_000
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
# a wiki-link is not an embed: `![[x]]` is counted separately, so the link pattern
# must not match inside it (counting both would double-report one occurrence)
WIKI_LINK = re.compile(r"(?<!\!)\[\[([^\]\[]+)\]\]")
MD_LINK = re.compile(r"(?<!\!)\[[^\]\n]*\]\(([^)\n]+)\)")
EMBED = re.compile(r"!\[\[([^\]\[]+)\]\]")
FENCE = re.compile(r"^\s*(```|~~~)", re.MULTILINE)
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
DEPTH_UNIT = "nested containers, the outermost one counts as 1"


def decode_bytes(raw: bytes, source: str = "<bytes>") -> tuple[str, dict]:
    """Deterministic decode: BOM-aware, strict UTF-8, documented fallbacks."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), {"encoding": "utf-8-sig", "loss_note": "UTF-8 BOM stripped"}
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        try:
            return raw.decode("utf-16"), {"encoding": "utf-16", "loss_note": "UTF-16 BOM decoded"}
        except UnicodeDecodeError as exc:
            raise ValueError(f"{source}: invalid UTF-16 content: {exc}") from exc
    try:
        return raw.decode("utf-8"), {"encoding": "utf-8", "loss_note": None}
    except UnicodeDecodeError:
        pass
    # Legacy behaviour tolerated GBK/CP1252 documents; record the fallback.
    for encoding in ("gbk", "cp1252"):
        try:
            return raw.decode(encoding), {
                "encoding": encoding,
                "loss_note": f"non-UTF-8 bytes decoded as {encoding} (undecodable bytes reported, not silently replaced)",
            }
        except UnicodeDecodeError:
            continue
    text = raw.decode("utf-8", errors="replace")
    return text, {"encoding": "utf-8-replace", "loss_note": "undecodable bytes replaced with U+FFFD"}


def line_anchors(text: str, *, cap_lines: int = 5000) -> list[dict]:
    """Per-line character anchors in the projected text."""
    anchors: list[dict] = []
    offset = 0
    for index, line in enumerate(text.splitlines(keepends=True), start=1):
        anchors.append(
            {"kind": "line", "path": [f"line-{index}"], "char_start": offset, "char_end": offset + len(line)}
        )
        offset += len(line)
        if index >= cap_lines:
            break
    return anchors


CUE_TIME = re.compile(r"(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})")
SRT_INDEX = re.compile(r"^\s*\d+\s*$", re.MULTILINE)
CUE_CAP = 5000
CANVAS_DANGLING_CAP = 50


def _subtitle_facts(text: str) -> dict | None:
    """Subtitle cues, when the text really looks like SRT or WebVTT.

    Detection is by pattern and is reported as such: the declared media type for
    these files is text/plain, so a reader must be able to tell a detection from a
    declaration.
    """
    is_vtt = text.lstrip().startswith("WEBVTT")
    cues = CUE_TIME.findall(text)
    if not is_vtt and not cues:
        return None
    if not is_vtt and not SRT_INDEX.search(text):
        return None
    return {
        "format": "webvtt" if is_vtt else "srt",
        "parsed": True,
        "detected_by": "pattern (WEBVTT header or numbered cues with a time arrow), not by media type",
        "cue_count": len(cues[:CUE_CAP]),
        "cues_capped": len(cues) > CUE_CAP,
        "first_cue_start": cues[0][0] if cues else None,
        "last_cue_end": cues[-1][1] if cues else None,
        "note": "cue times are reported as facts; they are not anchors, so navigation stays on line anchors"
        if cues
        else "a WEBVTT document with no cues was found",
    }


def _canvas_facts(payload) -> dict | None:
    """JSON Canvas nodes and edges, when the document has both arrays.

    This is an integrity measurement, not a graph: an edge that names a node which
    does not exist is reported as dangling rather than quietly ignored, and repeated
    node ids are named.
    """
    if not isinstance(payload, dict):
        return None
    nodes, edges = payload.get("nodes"), payload.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return None
    ids = [node.get("id") for node in nodes if isinstance(node, dict)]
    duplicates = sorted({node_id for node_id in ids if node_id is not None and ids.count(node_id) > 1})
    known = {node_id for node_id in ids if node_id is not None}
    dangling = [
        {"edge": edge.get("id"), "missing": side}
        for edge in edges
        if isinstance(edge, dict)
        for side in (edge.get("fromNode"), edge.get("toNode"))
        if side is not None and side not in known
    ]
    kinds: dict[str, int] = {}
    for node in nodes:
        if isinstance(node, dict):
            kind = str(node.get("type", "untyped"))
            kinds[kind] = kinds.get(kind, 0) + 1
    return {
        "format": "json-canvas",
        "parsed": True,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": dict(sorted(kinds.items())),
        "duplicate_node_ids": duplicates,
        "dangling_edges": dangling[:CANVAS_DANGLING_CAP],
        "dangling_edges_capped": len(dangling) > CANVAS_DANGLING_CAP,
        "note": "nodes and edges are counted as they appear; an edge naming a missing node is reported, not ignored",
    }


MAIL_HEADERS = ("from", "to", "cc", "subject", "date", "message-id")
ATTACHMENT_CAP = 50


def _looks_like_mail(text: str) -> bool:
    """RFC 822 shape: a header block separated from the body by a blank line.

    A file that merely starts with `From:` is not a message, so the rule needs the
    blank-line separator AND either a structured header (an address, a message id) or
    at least two recognised headers. Detection is only ever reported as a detection.
    """
    head, separator, _body = text.partition("\n\n")
    if not separator:
        return False
    seen = 0
    structured = False
    for line in head.splitlines():
        name, _, value = line.partition(":")
        key = name.strip().lower()
        if key not in MAIL_HEADERS:
            continue
        seen += 1
        stripped = value.strip()
        if key in ("from", "to", "cc") and "@" in stripped:
            structured = True
        if key == "message-id" and stripped.startswith("<") and stripped.endswith(">"):
            structured = True
        if key == "date" and any(char.isdigit() for char in stripped):
            structured = True
    return structured or seen >= 2


def _mail_facts(text: str) -> dict | None:
    """Structure of a saved mail message, when the text really looks like one.

    Detection is by RFC 822 shape and is reported as such: the declared media type for
    a .eml is text/plain, so a reader must be able to tell a detection from a
    declaration. Attachments are listed by name and size - they are NOT extracted,
    which is stated rather than implied.
    """
    if not _looks_like_mail(text):
        return None
    try:
        message = email.message_from_string(text)
        parts = list(message.walk())
    except Exception as exc:  # noqa: BLE001 - a mail that cannot be parsed is a fact
        return {
            "format": "eml",
            "parsed": False,
            "error": f"{type(exc).__name__}: {exc}",
            "note": "the text is still projected; an unparsable message is reported, not guessed at",
        }
    attachments = []
    for part in parts:
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename or part.get_content_disposition() == "attachment":
            if len(attachments) < ATTACHMENT_CAP:
                attachments.append({"name": filename or "(unnamed)", "bytes": len(payload)})
    bodies = {
        "text_body": any(part.get_content_type() == "text/plain" for part in parts),
        "html_body": any(part.get_content_type() == "text/html" for part in parts),
    }
    headers = {}
    for name in MAIL_HEADERS:
        value = message.get(name)
        if value is not None:
            headers[name] = " ".join(str(value).split())[:200]
    return {
        "format": "eml",
        "parsed": True,
        "detected_by": "RFC 822 header shape, not by media type",
        "headers": headers,
        "header_count": len(headers),
        "part_count": len(parts),
        "attachment_count": len(attachments),
        "attachments": attachments,
        "attachments_capped": len(attachments) >= ATTACHMENT_CAP,
        **bodies,
        "note": (
            "attachments are listed by name and size and are NOT extracted here; the raw message "
            "remains the source of record and its bytes are preserved"
        ),
    }


def _depth(value) -> int:
    """Nested container depth: the outermost container counts as 1, a scalar as 0."""
    if isinstance(value, dict):
        return 1 + max([_depth(item) for item in value.values()] or [0])
    if isinstance(value, list):
        return 1 + max([_depth(item) for item in value] or [0])
    return 0


def _count_keys(value) -> int:
    if isinstance(value, dict):
        return len(value) + sum(_count_keys(item) for item in value.values())
    if isinstance(value, list):
        return sum(_count_keys(item) for item in value)
    return 0


def _markdown_facts(text: str) -> dict:
    lines = text.splitlines()
    headings = []
    in_fence = False
    for index, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if match and len(headings) < HEADING_CAP:
            headings.append({"level": len(match.group(1)), "line": index, "text": match.group(2).strip()})
    facts = {
        "format": "markdown",
        "parsed": True,
        "frontmatter": bool(FRONTMATTER.match(text)),
        "heading_count": len(headings),
        "headings": headings,
        "headings_capped": len(headings) >= HEADING_CAP,
        "wiki_link_count": len(WIKI_LINK.findall(text)),
        "embed_count": len(EMBED.findall(text)),
        "markdown_link_count": len(MD_LINK.findall(text)),
        "code_fence_count": len(FENCE.findall(text)),
        "list_item_count": len(LIST_ITEM.findall(text)),
    }
    if facts["code_fence_count"] % 2:
        facts["note"] = "an odd number of code fences means one is unclosed; headings inside it are not listed"
    return facts


def _delimited_facts(text: str, delimiter: str) -> dict:
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    rows = rows[:ROW_CAP]
    widths = [len(row) for row in rows]
    header = rows[0] if rows else []
    ragged = sum(1 for width in widths[1:] if width != (widths[0] if widths else 0))
    return {
        "format": "tsv" if delimiter == "\t" else "csv",
        "parsed": True,
        "delimiter": delimiter,
        "row_count": len(rows),
        "rows_capped": len(rows) >= ROW_CAP,
        "column_count": max(widths) if widths else 0,
        "header": header[:32],
        "ragged_rows": ragged,
        "note": "row widths are reported as counted; a ragged file is not silently squared off"
        if ragged
        else "every row has the width of the first row",
    }


def _json_facts(text: str) -> dict:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        return {
            "format": "json",
            "parsed": False,
            "error": f"{error.msg} at line {error.lineno} column {error.colno}",
            "note": "the text is still projected; an unparsable document is reported, not guessed at",
        }
    facts = {
        "format": "json",
        "parsed": True,
        "top_level": type(payload).__name__,
        "key_count": _count_keys(payload),
        "max_depth": _depth(payload),
        "depth_unit": DEPTH_UNIT,
        "item_count": len(payload) if isinstance(payload, (list, dict)) else 0,
    }
    canvas = _canvas_facts(payload)
    if canvas is not None:
        facts["canvas"] = canvas
    return facts


def _xml_depth(element) -> int:
    return 1 + max([_xml_depth(child) for child in element] or [0])


def _xml_facts(text: str) -> dict:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        return {
            "format": "xml",
            "parsed": False,
            "error": str(error),
            "note": "the text is still projected; an unparsable document is reported, not guessed at",
        }
    elements = list(root.iter())
    return {
        "format": "xml",
        "parsed": True,
        "root": root.tag,
        "element_count": len(elements),
        "max_depth": _xml_depth(root),
        "depth_unit": DEPTH_UNIT,
        "child_count": len(list(root)),
    }


def format_facts(text: str, media_type: str) -> dict:
    """The facts this route can really derive for the declared media type."""
    media = (media_type or "text/plain").split(";", 1)[0].strip().lower()
    if media == "text/markdown":
        return _markdown_facts(text)
    if media in ("text/csv", "text/tab-separated-values"):
        return _delimited_facts(text, "\t" if media == "text/tab-separated-values" else ",")
    if media == "application/json":
        return _json_facts(text)
    if media in ("application/xml", "text/xml"):
        return _xml_facts(text)
    if media == "text/plain":
        subtitle = _subtitle_facts(text)
        if subtitle is not None:
            return subtitle
        mail = _mail_facts(text)
        if mail is not None:
            return mail
    return {"format": "plain", "parsed": True, "note": "no format-specific structure is claimed for plain text"}


def extract(path: str, media_type: str = "text/plain") -> dict:
    raw = Path(path).read_bytes()
    text, decode_note = decode_bytes(raw, source=path)
    structure = line_anchors(text)
    # Use the same line semantics as anchors (CR/LF/CRLF and Unicode separators).
    # A final separator terminates its line; it does not create an extra anchor.
    total = len(text.splitlines(keepends=True))
    covered = len(structure)
    losses = [decode_note["loss_note"]] if decode_note["loss_note"] else []
    if covered < total:
        losses.append("line anchors capped at 5000")
    facts = format_facts(text, media_type)
    if facts.get("parsed") is False:
        losses.append(f"{facts['format']} structure could not be derived: {facts.get('error', 'parse failed')}")
    loss_receipt = {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "params": {"decode": decode_note["encoding"], "cap_lines": 5000,
                   "coverage_unit": "line anchors", "line_splitting": "str.splitlines(keepends=True)",
                   "media_type": (media_type or "text/plain").split(";", 1)[0].strip().lower(),
                   "format": facts},
        "losses": losses,
        "covered": covered,
        "total": total,
        "coverage": covered / total if total else 1.0,
        "loss_note": "; ".join(losses) if losses else "no transform applied",
    }
    if total == 0:
        loss_receipt["loss_note"] += "; no lines to anchor; zero-line coverage defined as 1.0"
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "structure": structure,
        "loss_receipt": loss_receipt,
    }


def main() -> int:
    with contextlib.suppress(AttributeError, OSError):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) not in (2, 3):
        print(json.dumps({"error": "usage: worker_text.py <input-file> [media-type]"}))
        return 2
    try:
        out = extract(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else "text/plain")
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
