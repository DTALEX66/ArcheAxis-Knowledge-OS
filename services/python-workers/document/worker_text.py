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
    return {
        "format": "json",
        "parsed": True,
        "top_level": type(payload).__name__,
        "key_count": _count_keys(payload),
        "max_depth": _depth(payload),
        "depth_unit": DEPTH_UNIT,
        "item_count": len(payload) if isinstance(payload, (list, dict)) else 0,
    }


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
