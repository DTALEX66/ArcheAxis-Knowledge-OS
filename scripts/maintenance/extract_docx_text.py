"""Extract readable text (paragraphs, headings and tables) from a .docx into Markdown-ish text.

A maintenance tool, not part of the product: a blueprint input arrives as a .docx and its full text
— including the source appendix — has to be readable in a diffable form. Run it as
`python -B scripts/maintenance/extract_docx_text.py <input.docx> <output.txt>`; it writes UTF-8 text
with headings as Markdown and table rows as pipe rows, and it never modifies the input.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def paragraph_text(node: ET.Element) -> str:
    return "".join(t.text or "" for t in node.iter(f"{W}t"))


def style_of(node: ET.Element) -> str:
    properties = node.find(f"{W}pPr")
    if properties is None:
        return ""
    style = properties.find(f"{W}pStyle")
    return style.get(f"{W}val", "") if style is not None else ""


def render(document: ET.Element) -> list[str]:
    lines: list[str] = []
    body = document.find(f"{W}body")
    if body is None:
        return lines
    for node in body:
        if node.tag == f"{W}p":
            text = paragraph_text(node).strip()
            style = style_of(node).lower()
            if not text:
                lines.append("")
                continue
            if style.startswith("heading") or style.startswith("标题"):
                depth = "".join(ch for ch in style if ch.isdigit()) or "1"
                lines.append(f"{'#' * min(int(depth), 6)} {text}")
            else:
                lines.append(text)
        elif node.tag == f"{W}tbl":
            for row in node.iter(f"{W}tr"):
                cells = [paragraph_text(cell).strip().replace("|", "\\|") for cell in row.iter(f"{W}tc")]
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")
    return lines


def main() -> int:
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    with zipfile.ZipFile(source) as archive:
        names = [n for n in archive.namelist() if n.endswith(".xml")]
        document = ET.fromstring(archive.read("word/document.xml"))
        lines = render(document)
        # Footnotes/endnotes and headers carry the source appendix in some exports.
        for extra in ("word/footnotes.xml", "word/endnotes.xml"):
            if extra in archive.namelist():
                notes = ET.fromstring(archive.read(extra))
                rendered = [line for line in render(notes) if line.strip()]
                if rendered:
                    lines.append("")
                    lines.append(f"## [{extra}]")
                    lines.extend(rendered)
    text = "\n".join(lines)
    target.write_text(text, encoding="utf-8")
    print(f"parts: {len(names)}  paragraphs/lines: {len(lines)}  chars: {len(text)}  -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
