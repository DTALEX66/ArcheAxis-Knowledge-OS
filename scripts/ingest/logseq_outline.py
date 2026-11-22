"""Map mldoc's native Markdown/Org block positions to editable Core paragraphs."""

from __future__ import annotations

import codecs
from collections import Counter
import re
from urllib.parse import unquote
from uuid import UUID


def native_uuid(value):
    try:
        parsed = str(UUID(value))
    except (ValueError, AttributeError):
        return None
    return parsed if parsed == value.lower() else None


def references(tree):
    """Walk parsed inline constructs. Literal strings and code examples are never links."""
    if isinstance(tree, dict):
        for value in tree.values():
            yield from references(value)
    if not isinstance(tree, list):
        return
    if len(tree) == 2 and tree[0] == "Link":
        link = tree[1]
        kind, target = link["url"]
        if kind in ("Page_ref", "Block_ref", "Search") and isinstance(target, str):
            label = link["full_text"]
            yield kind, target, label, label.startswith("![")
        return
    if len(tree) == 2 and tree[0] == "Macro":
        macro = tree[1]
        args = macro.get("arguments", [])
        if macro["name"].lower() == "embed" and len(args) == 1:
            value = args[0].strip()
            if value.startswith("((") and value.endswith("))"):
                yield "Block_ref", value[2:-2], value, True
            elif value.startswith("[[") and value.endswith("]]"):
                yield "Page_ref", value[2:-2], value, True
        return
    for child in tree:
        yield from references(child)


def split_outline(raw, ast, fmt):
    # mldoc positions count UTF-8 bytes, including newlines. A BOM belongs to
    # the file encoding and is removed before parsing and restored on export.
    data = raw.removeprefix(codecs.BOM_UTF8)
    groups = []
    for node, position in ast:
        pos = position["start_pos"]
        if not 0 <= pos <= position["end_pos"] <= len(data):
            raise ValueError("mldoc returned positions outside the original page")
        if node[0] == "Heading":
            if not groups and pos:
                groups.append((0, 0, []))
            if groups and pos <= groups[-1][0]:
                raise ValueError("mldoc returned overlapping outlines")
            groups.append((pos, node[1]["level"], []))
        if not groups:
            groups.append((0, 0, []))
        groups[-1][2].append(node)
    if not groups and data:
        groups.append((0, 0, []))

    records, links, props = [], [], {}
    for i, (pos, level, nodes) in enumerate(groups):
        stop = groups[i + 1][0] if i + 1 < len(groups) else len(data)
        text = data[pos:stop].decode("utf-8")
        prefix = re.match(r"^[ \t]*(?:[-+*][ \t]+)" if fmt == "Markdown" else r"^\*+[ \t]+", text) if level else None
        start = prefix.group() if prefix else ""
        ending = "\r\n" if text.endswith("\r\n") else text[-1:] if text.endswith(("\r", "\n")) else ""
        body = text[len(start):len(text) - len(ending)]
        properties = {key.casefold(): value for node in nodes if node[0] == "Property_Drawer"
                      for key, value, *_ in node[1]}
        if not level:
            props.update(properties)
        ident = native_uuid(properties.get("id", "")) if level else None
        records.append((level, ident, start, ending, body))
        links.extend(references(nodes))

    counts = Counter(ident for _, ident, *_ in records if ident)
    blocks, parents = [], []
    for i, (level, ident, start, ending, body) in enumerate(records):
        key = ident if ident and counts[ident] == 1 else f"logseq-{i}"
        while parents and parents[-1][0] >= level:
            parents.pop()
        attrs = {"block_id": key, "native_id": ident, "level": level, "parent": parents[-1][1] if parents else None,
                 "prefix": start, "ending": ending}
        blocks.append({"type": "paragraph", "attrs": attrs,
                       "content": [{"type": "text", "text": body}] if body else []})
        if level:
            parents.append((level, key))
    return blocks, links, props


def page_name(path):
    return unquote(path.stem).replace("___", "/")


def block_text(block):
    if block.get("type") != "paragraph":
        raise ValueError("Logseq writeback requires outline paragraphs")
    parts = []
    for span in block.get("content", []):
        if span.get("type") == "text" and not span.get("marks"):
            parts.append(span["text"])
        elif span.get("type") == "hardBreak":
            parts.append("\n")
        else:
            raise ValueError("a rich-text span has no lossless Logseq outline mapping")
    return "".join(parts)


def write_outline(raw, initial, edited):
    if initial == edited:
        return raw
    if [b["attrs"]["block_id"] for b in initial] != [b.get("attrs", {}).get("block_id") for b in edited]:
        raise ValueError("writeback requires the original outline blocks in order")
    data = bytearray(codecs.BOM_UTF8 if raw.startswith(codecs.BOM_UTF8) else b"")
    for before, after in zip(initial, edited):
        attrs = before["attrs"]
        body = block_text(after)
        if attrs["ending"] == "\r\n" and "\n" not in block_text(before).replace("\r\n", ""):
            body = body.replace("\r\n", "\n").replace("\n", "\r\n")
        data.extend((attrs["prefix"] + body + attrs["ending"]).encode("utf-8"))
    return bytes(data)
