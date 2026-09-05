#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext web worker: static HTML snapshot extraction (F02 partial).

Reads a saved HTML snapshot file and deterministically extracts title,
main text, links and paragraph anchors using only the standard library
(html.parser). Network fetching and dynamic rendering are Core-side
concerns (F02/F03 full slices); this worker consumes a local snapshot and
never executes scripts. Page-noise separation (ads/boilerplate) and
trafilatura-grade extraction are later slices.

Usage:
    python worker_html.py <snapshot.html>
Output: {"engine","engine_version","text","title","links","structure","loss_receipt"}
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ENGINE = "python-worker-html"
ENGINE_VERSION = "0.1.0"

_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
_BLOCK_TAGS = {
    "p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5",
    "h6", "blockquote", "pre", "table", "tr", "br", "ul", "ol",
}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.links: list[dict] = []
        self.blocks: list[dict] = []
        self._skip_depth = 0
        self._text_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag == "a" and self._skip_depth == 0 and attr_map.get("href"):
            self.links.append({"href": attr_map["href"], "text": ""})
        if tag == "title" and self._skip_depth == 0:
            self._in_title = True
        if tag in _BLOCK_TAGS and self._skip_depth == 0:
            self._flush_block()

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in _BLOCK_TAGS and self._skip_depth == 0:
            self._flush_block()

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title:
            self.title += data
            return
        self._text_parts.append(data)
        if self.links and not self.links[-1]["text"]:
            self.links[-1]["text"] = data.strip()[:200]

    def _flush_block(self) -> None:
        raw = "".join(self._text_parts)
        text = re.sub(r"[ \t]+", " ", raw).strip()
        if text:
            self.blocks.append(text)
        self._text_parts = []


def extract(path: str) -> dict:
    raw = Path(path).read_bytes()
    try:
        html_text = raw.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        html_text = raw.decode("utf-8", errors="replace")
        encoding = "utf-8-replace"
    parser = _Extractor()
    parser.feed(html_text)
    parser.close()

    blocks = parser.blocks
    projection = "\n\n".join(blocks)
    anchors: list[dict] = []
    offset = 0
    for index, block in enumerate(blocks, start=1):
        start = projection.find(block, offset)
        if start < 0:
            start = offset
        anchors.append(
            {"kind": "block", "path": [f"block-{index}"], "char_start": start, "char_end": start + len(block)}
        )
        offset = start + len(block)

    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": projection,
        "title": parser.title.strip(),
        "links": parser.links,
        "structure": anchors,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"encoding": encoding, "skip_tags": sorted(_SKIP_TAGS)},
            "loss_note": (
                "scripts/styles never executed; layout/ads separation and "
                "trafilatura-grade extraction are later slices; link list "
                "kept with href and visible text"
            ),
        },
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_html.py <snapshot.html>"}))
        return 2
    try:
        out = extract(sys.argv[1])
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
