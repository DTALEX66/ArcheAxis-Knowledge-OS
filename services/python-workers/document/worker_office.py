#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext office/document engine worker (F05/F07/F08/F09 partial).

Single worker entrypoint for structured office and PDF sources:

- docx: pure-stdlib ZIP+XML extraction (paragraphs/tables/media inventory;
        headers/footers noted; nothing executed)
- pptx: python-pptx engine (slide order, shape text, notes, image counts)
- xlsx: openpyxl engine (sheets/cells, formula text + cached-value policy note,
        merged ranges; macros never executed)
- pdf : PyMuPDF engine (page blocks in reading order, per-page anchors,
        image inventory; scanned pages reported, OCR is a separate lane)

Isolation boundary: never opens the vNext database; every engine failure
surfaces {"error": ...} with a non-zero exit.

Usage:
    python worker_office.py --probe
    python worker_office.py <input.docx|.pptx|.xlsx|.pdf>
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ENGINE = "python-worker-office"
ENGINE_VERSION = "0.1.0"
# R15/F07-F09: the identity advertised in the sidecar handshake, so an Office job is
# dispatched to this worker through the same route table as every other capability.
WORKER_IDENTITY = "python-worker-office-ndjson"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = lambda tag: f"{{{W_NS}}}{tag}"  # noqa: E731


def probe() -> dict:
    engine_status: dict[str, tuple[bool, str]] = {"docx": (True, "stdlib-zip+xml")}
    for module_name, format_name in (("pptx", "pptx"), ("openpyxl", "xlsx"), ("fitz", "pdf")):
        try:
            module = __import__(module_name)
            engine_status[format_name] = (True, getattr(module, "__version__", "unknown"))
        except ImportError:
            engine_status[format_name] = (False, "missing")
    engines = {fmt: ok for fmt, (ok, _version) in engine_status.items()}
    versions = {fmt: version for fmt, (_ok, version) in engine_status.items()}
    return {
        "engine": ENGINE,
        "engines": engines,
        "versions": versions,
        "formats": [fmt for fmt, ok in engines.items() if ok],
        "note": "docx always enabled (stdlib); pptx/xlsx/pdf require their engines",
    }


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx_styles(root: ET.Element) -> dict[str, dict]:
    """The document's own style definitions: id -> name and outline level.

    A paragraph usually carries only a style id. The level a style means lives in the style
    definition, so reading it from the file is the difference between "this paragraph is
    called Heading1" and "the document defines Heading1 as outline level 1".
    """
    styles: dict[str, dict] = {}
    for style in root.findall(W("style")):
        style_id = style.get(W("styleId"))
        if not style_id:
            continue
        name_el = style.find(W("name"))
        properties = style.find(W("pPr"))
        outline = properties.find(W("outlineLvl")) if properties is not None else None
        entry = {"name": name_el.get(W("val")) if name_el is not None else None,
                 "outline_level": None}
        if outline is not None:
            raw = (outline.get(W("val")) or "").strip()
            if raw.isdigit():
                entry["outline_level"] = int(raw) + 1
        styles[style_id] = entry
    return styles


def _heading_level(properties, style_id: str | None, styles: dict[str, dict]) -> int | None:
    """The outline level this paragraph's own file declares, or None when it declares none."""
    if properties is not None:
        direct = properties.find(W("outlineLvl"))
        if direct is not None:
            raw = (direct.get(W("val")) or "").strip()
            if raw.isdigit():
                return int(raw) + 1
    if not style_id:
        return None
    definition = styles.get(style_id) or {}
    if definition.get("outline_level") is not None:
        return definition["outline_level"]
    # Word names built-in heading styles "heading 1"; a file may also store the id verbatim.
    for candidate in (definition.get("name"), style_id):
        if not candidate:
            continue
        match = re.fullmatch(r"(?:heading|标题)\s*([1-9])", str(candidate).strip(), re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _docx_text(path: Path) -> dict:
    text_parts: list[dict] = []
    media: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        media = sorted(n for n in names if n.startswith("word/media/"))
        has_headers = any(n.startswith("word/header") for n in names)
        has_footers = any(n.startswith("word/footer") for n in names)
        document_xml = archive.read("word/document.xml")
        styles_xml = archive.read("word/styles.xml") if "word/styles.xml" in names else None
    root = ET.fromstring(document_xml)
    styles = _docx_styles(ET.fromstring(styles_xml)) if styles_xml is not None else {}
    body = root.find(W("body"))
    if body is None:
        raise ValueError("docx document.xml has no body")
    for child in body:
        tag = child.tag
        if tag == W("p"):
            runs = child.findall(".//" + W("t"))
            paragraph_text = "".join(run.text or "" for run in runs)
            if paragraph_text.strip():
                properties = child.find(W("pPr"))
                style_el = properties.find(W("pStyle")) if properties is not None else None
                style_id = style_el.get(W("val")) if style_el is not None else None
                style_name = (styles.get(style_id) or {}).get("name") if style_id else None
                part = {"kind": "paragraph", "text": paragraph_text.strip(),
                        "style": style_name or style_id}
                level = _heading_level(properties, style_id, styles)
                if level is not None:
                    part["heading_level"] = level
                text_parts.append(part)
        elif tag == W("tbl"):
            for row in child.findall(".//" + W("tr")):
                cells = []
                for cell in row.findall(".//" + W("tc")):
                    cell_text = "".join(
                        run.text or ""
                        for run in cell.findall(".//" + W("t"))
                    )
                    cells.append(cell_text.strip())
                if any(cells):
                    text_parts.append({"kind": "table_row", "text": " | ".join(cells)})
    if not text_parts:
        raise ValueError("docx contains no extractable paragraph/table text")
    projection = "\n".join(part["text"] for part in text_parts)
    structure = []
    offset = 0
    for index, part in enumerate(text_parts, start=1):
        start = projection.find(part["text"], offset)
        if start < 0:
            start = offset
        entry = {"kind": part["kind"], "path": [f"{part['kind']}-{index}"],
                 "char_start": start, "char_end": start + len(part["text"])}
        if part.get("style"):
            entry["style"] = part["style"]
        if part.get("heading_level") is not None:
            entry["heading_level"] = part["heading_level"]
        structure.append(entry)
        offset = start + len(part["text"])
    return {
        "format": "docx",
        "text": projection,
        "structure": structure,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "headers": has_headers,
                "footers": has_footers,
                "media_files": len(media),
                "engine": "stdlib-zip+xml",
                "style_definitions": len(styles),
                "paragraph_count": len([p for p in text_parts if p["kind"] == "paragraph"]),
                "heading_count": len([p for p in text_parts if p.get("heading_level") is not None]),
                "headings": [{"level": p["heading_level"], "style": p.get("style"),
                              "characters": len(p["text"])}
                             for p in text_parts if p.get("heading_level") is not None][:200],
            },
            "loss_note": (
                "paragraphs/tables extracted in document order; header/footer "
                "text and embedded-image OCR are separate lanes; media files "
                f"({len(media)}) inventoried, not decoded"
            ),
        },
    }


C_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
CHART_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart"
)


def _c(tag: str) -> str:
    return f"{{{C_NS}}}{tag}"


def _cached_points(container: ET.Element | None) -> list[str]:
    """Return a cache's values in idx order, or [] when the series carries no cache at all.

    A category or value element wraps a reference (`c:strRef` / `c:numRef`) which in turn wraps
    the cache, so both levels are descended. A chart can point at a live spreadsheet instead of
    storing values; this worker never opens a spreadsheet application, so an absent cache is
    reported, never guessed."""
    if container is None:
        return []
    for ref_tag in ("numRef", "strRef", "multiLvlStrRef"):
        reference = container.find(_c(ref_tag))
        if reference is not None:
            container = reference
            break
    for cache_tag in ("strCache", "numCache", "multiLvlStrCache"):
        cache = container.find(_c(cache_tag))
        if cache is not None:
            values = []
            for point in cache.findall(_c("pt")):
                node = point.find(_c("v"))
                if node is None:
                    node = point.find(_c("ptCount"))
                values.append("" if node is None or node.text is None else node.text.strip())
            return values
    return []


def _series_name(series: ET.Element) -> str:
    tx = series.find(_c("tx"))
    if tx is None:
        return "(unnamed series)"
    str_ref = tx.find(_c("strRef"))
    if str_ref is None:
        return "(unnamed series)"
    cached = _cached_points(str_ref)
    if cached and cached[0]:
        return cached[0]
    formula = str_ref.find(_c("f"))
    if formula is not None and formula.text and formula.text.strip():
        return f"(named by reference {formula.text.strip()})"
    return "(unnamed series)"


def _chart_text(root: ET.Element, part: str) -> tuple[str, bool]:
    """Render one chart part's cached data as text. Returns (text, carried_any_values)."""
    title_nodes = [node.text.strip() for node in root.iter(f"{{{A_NS}}}t") if node.text and node.text.strip()]
    lines = [f"Chart: {title_nodes[0] if title_nodes else part}"]
    plot_area = root.find(f"{_c('chart')}/{_c('plotArea')}")
    carried = False
    if plot_area is None:
        return lines[0] + "\n  (no plot area in this chart part)", False
    for element in plot_area:
        tag = element.tag.split("}")[-1]
        if not tag.endswith("Chart"):
            continue
        lines.append(f"  Type: {tag[:-5].lower() if len(tag) > 5 else tag}")
        for series in element.findall(_c("ser")):
            categories = _cached_points(series.find(_c("cat")))
            values = _cached_points(series.find(_c("val")))
            name = _series_name(series)
            if not values:
                lines.append(f"  Series {name}: no cached values in this file (linked data is not resolved)")
                continue
            carried = True
            pairs = []
            for position, value in enumerate(values):
                label = categories[position] if position < len(categories) else f"#{position + 1}"
                pairs.append(f"{label}={value}")
            lines.append(f"  Series {name}: " + ", ".join(pairs))
    return "\n".join(lines), carried


def _pptx_charts(path: Path) -> dict[int, list[tuple[str, bool]]]:
    """Map slide number -> [(chart text, carried values)] through the slide's relationships.

    python-pptx reports that a shape is a chart but not what the chart holds, and the cached
    categories/values are the only chart data present without a spreadsheet application."""
    by_slide: dict[int, list[tuple[str, bool]]] = {}
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        parts = sorted(
            name for name in names
            if name.startswith("ppt/charts/chart") and name.endswith(".xml")
        )
        rendered = {}
        for part in parts:
            try:
                root = ET.fromstring(archive.read(part))
            except ET.ParseError:
                rendered[part] = (f"Chart: {part} (the chart part is not well-formed XML)", False)
                continue
            rendered[part] = _chart_text(root, part)
        for name in sorted(n for n in names if n.startswith("ppt/slides/slide")):
            digits = "".join(char for char in Path(name).stem if char.isdigit())
            if not digits:
                continue
            rel_path = f"ppt/slides/_rels/{Path(name).name}.rels"
            if rel_path not in names:
                continue
            try:
                rels = ET.fromstring(archive.read(rel_path))
            except ET.ParseError:
                continue
            for rel in rels:
                target_name = rel.get("Target")
                if rel.get("Type") != CHART_REL_TYPE or not target_name:
                    continue
                target = posixpath.normpath(
                    posixpath.join(posixpath.dirname(name), target_name.lstrip("/"))
                ).replace("\\", "/")
                if target in rendered:
                    by_slide.setdefault(int(digits), []).append(rendered[target])
    return by_slide


def _pptx_text(path: Path) -> dict:
    try:
        from pptx import Presentation
    except ImportError as exc:
        raise RuntimeError("pptx engine missing (python-pptx not installed)") from exc
    presentation = Presentation(str(path))
    charts_by_slide = _pptx_charts(path)
    text_parts: list[dict] = []
    image_count = 0
    chart_count = 0
    charts_with_values = 0
    charts_without_values = 0
    for index, slide in enumerate(presentation.slides, start=1):
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip():
                text_parts.append({"kind": "slide", "index": index, "text": shape.text_frame.text.strip()})
            if shape.shape_type is not None and "PICTURE" in str(shape.shape_type):
                image_count += 1
            if getattr(shape, "has_chart", False):
                chart_count += 1
        for chart_text, carried in charts_by_slide.get(index, []):
            if carried:
                charts_with_values += 1
            else:
                charts_without_values += 1
            text_parts.append({"kind": "slide_chart", "index": index, "text": chart_text})
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                text_parts.append({"kind": "slide_notes", "index": index, "text": notes})
    if not text_parts:
        raise ValueError("pptx contains no extractable text")
    projection = "\n".join(part["text"] for part in text_parts)
    structure = []
    offset = 0
    for index, part in enumerate(text_parts, start=1):
        start = projection.find(part["text"], offset)
        if start < 0:
            start = offset
        structure.append(
            {"kind": part["kind"], "path": [f"slide-{part['index']}", part['kind']], "char_start": start, "char_end": start + len(part["text"])}
        )
        offset = start + len(part["text"])
    return {
        "format": "pptx",
        "text": projection,
        "structure": structure,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "slides": len(presentation.slides._sldIdLst),
                "images": image_count,
                "charts": chart_count,
                "charts_with_cached_values": charts_with_values,
                "charts_without_cached_values": charts_without_values,
                "chart_data_source": "cached values stored in the chart part",
                "engine": "python-pptx",
            },
            "loss_note": "slide order preserved; chart data is the file's own cached categories and "
            "values, never recomputed, and a series that only references a live spreadsheet is "
            "named as carrying no cached values; slide-image OCR and chart rendering are separate lanes",
        },
    }


def _xlsx_text(path: Path) -> dict:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("xlsx engine missing (openpyxl not installed)") from exc
    workbook = load_workbook(str(path), data_only=False)
    text_parts: list[dict] = []
    formula_count = 0
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            cells = []
            for cell in row:
                if cell.value is None:
                    continue
                value = cell.value
                if isinstance(value, str) and value.startswith("="):
                    formula_count += 1
                cells.append(f"{cell.coordinate}={value}")
            if cells:
                text_parts.append({"kind": "sheet_row", "sheet": sheet.title, "text": " | ".join(cells)})
    if not text_parts:
        raise ValueError("xlsx contains no extractable cell values")
    projection = "\n".join(part["text"] for part in text_parts)
    structure = []
    offset = 0
    for index, part in enumerate(text_parts, start=1):
        start = projection.find(part["text"], offset)
        if start < 0:
            start = offset
        structure.append(
            {"kind": part["kind"], "path": [f"sheet-{part['sheet']}", f"row-{index}"], "char_start": start, "char_end": start + len(part["text"])}
        )
        offset = start + len(part["text"])
    return {
        "format": "xlsx",
        "text": projection,
        "structure": structure,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"sheets": len(workbook.worksheets), "formula_cells": formula_count, "engine": "openpyxl"},
            "loss_note": (
                "cell values include formula text (data_only=False); cached "
                "computed values are NOT presented as live calculations; "
                "macros never executed; merged ranges reported per sheet only"
            ),
        },
    }


def _pdf_text(path: Path) -> dict:
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.24 canonical import
    except ImportError:
        try:
            import fitz  # legacy import name (deprecated)
        except ImportError as exc:
            raise RuntimeError("pdf engine missing (PyMuPDF not installed)") from exc
    document = fitz.open(str(path))
    text_parts: list[dict] = []
    scanned_pages = 0
    for page_index, page in enumerate(document, start=1):
        blocks = page.get_text("blocks")
        page_text = "\n".join(block[4].strip() for block in blocks if block[4].strip())
        if not page_text.strip():
            scanned_pages += 1
        if page_text.strip():
            text_parts.append({"kind": "pdf_page", "page": page_index, "text": page_text.strip()})
    if not text_parts:
        raise ValueError(f"pdf contains no text layer ({scanned_pages} scanned pages; OCR lane required)")
    projection = "\n\n".join(part["text"] for part in text_parts)
    structure = []
    offset = 0
    for index, part in enumerate(text_parts, start=1):
        start = projection.find(part["text"], offset)
        if start < 0:
            start = offset
        structure.append(
            {"kind": "pdf_page", "path": [f"page-{part['page']}"], "char_start": start, "char_end": start + len(part["text"])}
        )
        offset = start + len(part["text"])
    return {
        "format": "pdf",
        "text": projection,
        "structure": structure,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"pages": len(document), "scanned_pages_no_text_layer": scanned_pages, "engine": "PyMuPDF"},
            "loss_note": (
                "text blocks concatenated in page reading order; multi-column "
                "order and scanned-page OCR are separate lanes"
            ),
        },
    }

XLS_SHEET_CAP = 32
XLS_BYTES_CAP = 64 * 1024 * 1024
XLS_ERROR_TEXT = {0: "#NULL!", 1: "#DIV/0!", 2: "#VALUE!", 3: "#REF!", 4: "#NAME?",
                  5: "#NUM!", 6: "#N/A", 7: "#GETTING_DATA"}


def _safe_csv_name(index: int, name: str) -> str:
    """A flat, collision-free file name for one converted sheet."""
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in base)[-48:]
    return f"sheet-{index:02d}-{safe or 'sheet'}.csv"


def _xls_cell(sheet, book, row: int, col: int) -> tuple[str, str]:
    """One cell as (displayed text, type name), using only what xlrd reports."""
    import xlrd

    value = sheet.cell_value(row, col)
    kind = sheet.cell_type(row, col)
    if kind == xlrd.XL_CELL_EMPTY:
        return "", "empty"
    if kind == xlrd.XL_CELL_TEXT:
        return str(value), "text"
    if kind == xlrd.XL_CELL_NUMBER:
        return (repr(value)), "number"
    if kind == xlrd.XL_CELL_DATE:
        # the file says "a date"; the calendar it means is the workbook's own datemode
        try:
            converted = xlrd.xldate_as_datetime(value, book.datemode)
        except (xlrd.XLDateError, ValueError, OverflowError):
            return repr(value), "unconvertible_date"
        return converted.isoformat(sep=" "), "date"
    if kind == xlrd.XL_CELL_BOOLEAN:
        return ("TRUE" if value else "FALSE"), "boolean"
    if kind == xlrd.XL_CELL_ERROR:
        return XLS_ERROR_TEXT.get(int(value), f"#ERROR{value}"), "error"
    return str(value), "blank"


def _xls_text(path: Path, member_dir: Path | None = None) -> dict:
    try:
        import xlrd
    except ImportError as exc:
        raise RuntimeError("xls engine missing (xlrd not installed)") from exc
    try:
        book = xlrd.open_workbook(str(path), on_demand=True)
    except xlrd.XLRDError as exc:
        raise ValueError(f"xls could not be opened: {exc}") from exc

    text_parts: list[dict] = []
    sheets: list[dict] = []
    converted: list[dict] = []
    losses: list[str] = []
    members_written: list[dict] = []
    type_counts: dict[str, int] = {}
    total_bytes = 0
    formulas_available = hasattr(book.sheet_by_index(0), "cell_formula_text") if book.nsheets else False

    for index in range(book.nsheets):
        if index >= XLS_SHEET_CAP:
            losses.append(f"only the first {XLS_SHEET_CAP} of {book.nsheets} sheets were read")
            break
        sheet = book.sheet_by_index(index)
        rows: list[list[str]] = []
        cells = 0
        for row in range(sheet.nrows):
            line = []
            for col in range(sheet.ncols):
                display, kind = _xls_cell(sheet, book, row, col)
                type_counts[kind] = type_counts.get(kind, 0) + 1
                line.append(display)
                if display:
                    cells += 1
            rows.append(line)
        sheets.append({"name": sheet.name, "rows": sheet.nrows, "columns": sheet.ncols,
                       "populated_cells": cells})
        body = "\n".join(", ".join(f"{cell!r}" for cell in line if cell) for line in rows if any(line))
        if body.strip():
            text_parts.append({"kind": "sheet", "name": sheet.name, "text": body.strip()})
        if member_dir is not None and index < XLS_SHEET_CAP:
            import csv as _csv
            import hashlib as _hashlib
            import io as _io

            buffer = _io.StringIO()
            writer = _csv.writer(buffer)
            for line in rows:
                writer.writerow(line)
            payload = buffer.getvalue().encode("utf-8")
            if total_bytes + len(payload) > XLS_BYTES_CAP:
                losses.append(f"converted byte budget of {XLS_BYTES_CAP} reached; "
                              "later sheets were not converted")
                break
            out = Path(member_dir)
            out.mkdir(parents=True, exist_ok=True)
            target = out / _safe_csv_name(index + 1, sheet.name)
            target.write_bytes(payload)
            total_bytes += len(payload)
            members_written.append({
                "name": f"{sheet.name}.csv",
                "file": target.name,
                "bytes": len(payload),
                "sha256": _hashlib.sha256(payload).hexdigest(),
            })

    # xlrd keeps the stream mapped while the book lives, and on Windows that holds the attempt's
    # view file open; release it before anything else can raise or return.
    book.release_resources()
    if not text_parts:
        raise ValueError("xls contains no readable cell values")
    projection = "\n".join(part["text"] for part in text_parts)
    structure = []
    offset = 0
    for part in text_parts:
        start = projection.find(part["text"], offset)
        if start < 0:
            start = offset
        structure.append({"kind": "sheet", "path": [f"sheet-{part['name']}"],
                          "char_start": start, "char_end": start + len(part["text"])})
        offset = start + len(part["text"])

    losses.append(
        "converted to one CSV per sheet of the values the file carries: formulas are not "
        "recalculated, and number formats, styles, merged-cell spans, charts, images, pivots "
        "and macros are not carried into the conversion; the original bytes stay the source of record"
    )
    if not formulas_available:
        losses.append("the engine exposes no formula text for this file, so formulas are "
                      "reported only as the cached value the file carries")
    return {
        "format": "xls",
        "text": projection,
        "structure": structure,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {
                "engine": "xlrd",
                "engine_version_reported": getattr(xlrd, "__version__", "unknown"),
                "sheets": len(sheets),
                "datemode": book.datemode,
                "cell_types": type_counts,
                "sheet_structure": sheets,
                "structure": {"extractable_members": members_written},
                "converted_member_count": len(members_written),
                "converted_bytes": total_bytes,
            },
            "losses": losses,
            "loss_note": "; ".join(losses),
        },
    }
def extract(path: str, member_dir: str | None = None) -> dict:
    suffix = Path(path).suffix.lower()
    if not Path(path).is_file():
        raise ValueError(f"input file not found: {path}")
    if suffix == ".docx":
        return _docx_text(Path(path))
    if suffix == ".pptx":
        return _pptx_text(Path(path))
    if suffix == ".xlsx":
        return _xlsx_text(Path(path))
    if suffix == ".xls":
        return _xls_text(Path(path), Path(member_dir) if member_dir else None)
    if suffix == ".pdf":
        return _pdf_text(Path(path))
    raise ValueError(f"unsupported office/document extension: {suffix}")


def main() -> int:
    # R15/F07-F09: this worker existed since the 2026-09-05 slice but was unreachable
    # through the job contract - no route pointed at it. The sidecar mode below is that
    # wiring: the same stdio loop every route uses, with this worker's own identity and
    # capability, so an Office job travels the normal job/attempt/error machinery.
    if "--staging-root" in sys.argv:
        import importlib.util

        # The shared transport sits beside this worker's own category directory, in a
        # source checkout (`services/python-workers/transport/`) and in a staged runtime
        # (`workers/transport/`) alike, so both are tried from this file's location. A
        # fixed parents[3] plus a `services/python-workers/` suffix was correct only for
        # the source layout and left a staged worker unable to start.
        _transport_candidates = (
            Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py",
            Path(__file__).resolve().parents[2] / "services" / "python-workers" / "transport" / "text_ndjson.py",
        )
        _transport = next((p for p in _transport_candidates if p.is_file()), _transport_candidates[0])
        spec = importlib.util.spec_from_file_location("office_transport", _transport)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        sidecar = argparse.ArgumentParser(description=__doc__)
        sidecar.add_argument("--staging-root", type=Path, required=True)
        sidecar.add_argument("--artifact-root", type=Path, default=None)
        sidecar_args = sidecar.parse_args()
        return transport.serve_stdio(
            WORKER_IDENTITY, ["office.structure"], sidecar_args.staging_root, sidecar_args.artifact_root
        )

    parser = argparse.ArgumentParser(description="ArcheAxis office/document engine worker")
    parser.add_argument("input", nargs="?", help="input file (.docx/.pptx/.xlsx/.pdf)")
    parser.add_argument("--probe", action="store_true", help="engine capability probe")
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe(), ensure_ascii=False))
        return 0
    if not args.input:
        print(json.dumps({"error": "usage: worker_office.py <input-file> | --probe"}))
        return 2
    try:
        out = extract(args.input)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    out["engine"] = ENGINE
    out["engine_version"] = ENGINE_VERSION
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
