"""Native PDF text worker (R08).

One job contract, native extraction first: this worker returns the same response
shape as ``worker_text.py`` - ``{engine, engine_version, text, structure,
loss_receipt}`` - so PDF, Markdown/text and (later) OCR routes feed the same
ingestion path.

Anchors: every line anchor carries its page and line in ``path``
(``["page-3", "line-12"]``) and character offsets into the concatenated ``text``,
so a consumer can navigate from knowledge back to the page and region it came
from.

Degradation is explicit and never silent:
- an unreadable/corrupt PDF raises (the caller must record a failure, not an
  empty success);
- a PDF whose pages expose no text (typically a scan or a screenshot) returns the
  empty text it really has, with a loss note saying OCR is required - the caller
  routes it to the OCR worker instead of pretending extraction succeeded.

Nothing here reports a model confidence as recognition accuracy: the receipt
records engine, version, counts and losses only.

Usage: ``python worker_pdf.py <input-file>``
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path

ENGINE = "pymupdf-native-pdf"
ENGINE_VERSION = "pymupdf"
# R08: identity advertised in the sidecar handshake for this route.
WORKER_IDENTITY = "python-worker-pdf-ndjson"

# Cap the number of page-separated lines converted into anchors, mirroring the
# text worker's 5000-line cap so both routes bound work identically.
MAX_ANCHORS = 5000
# R15/F05: structural facts are reported, not unlimited. Each cap carries its own
# "capped" fact so a reader is never misled by a truncated list.
PARAGRAPH_CAP = 300
TABLE_CAP = 100
# R15/F06: a page with no text is rendered so the OCR route has a real image to read.
# Rendering is bounded and declared; the Core decides whether to enqueue anything.
OCR_PAGE_CAP = 20
OCR_DPI = 150

# R15/F05: the reading-order model. A page is read as one vertical gutter with text on
# both sides, then column by column and top to bottom - and only when that model changes
# nothing about which lines the page holds. These bound what counts as a gutter.
COLUMN_MIN_GUTTER = 6.0
COLUMN_GUTTER_FRACTION = 0.02
COLUMN_EDGE_MARGIN = 0.15
READING_ORDER_MODEL = "one vertical gutter, then column by column, top to bottom"


def _render_ocr_candidates(
    pages_without_text: list[int], document, out_dir: Path | None
) -> tuple[list[dict], list[str]]:
    """Render the pages that need OCR and declare them, or explain why not.

    The worker cannot enqueue anything (it holds no database handle), so it does the
    half it owns: it renders those pages to PNG in the transfer area and reports each
    file with its digest and size. A render failure is reported per page rather than
    skipped, and nothing is written when no output directory was supplied.
    """
    candidates: list[dict] = []
    problems: list[str] = []
    if out_dir is None or not pages_without_text:
        return candidates, problems
    out_dir.mkdir(parents=True, exist_ok=True)
    for page_index in pages_without_text[:OCR_PAGE_CAP]:
        name = f"page-{page_index}.png"
        target = out_dir / name
        try:
            pixmap = document[page_index - 1].get_pixmap(dpi=OCR_DPI)
            target.write_bytes(pixmap.tobytes("png"))
            raw = target.read_bytes()
            candidates.append(
                {
                    "page": page_index,
                    "file": name,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "media_type": "image/png",
                }
            )
        except Exception as exc:  # noqa: BLE001 - a page that cannot be rendered is a fact
            problems.append(f"page {page_index}: {type(exc).__name__}: {exc}")
    if len(pages_without_text) > OCR_PAGE_CAP:
        problems.append(
            f"only the first {OCR_PAGE_CAP} of {len(pages_without_text)} text-less pages were rendered"
        )
    return candidates, problems


def _capture(callable_, sink: list[str]):
    """Run an engine call with stdout diverted.

    The sidecar protocol is one JSON envelope per stdout line, so ANY stray output
    from the engine corrupts the stream (PyMuPDF's table finder prints a layout hint
    on first use). The text is captured rather than discarded and reported as a fact,
    so the protocol stays clean and nothing is silently dropped.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = callable_()
    text = buffer.getvalue().strip()
    if text:
        sink.append(text)
    return result


def _page_facts(page, engine_messages: list[str]) -> dict:
    """Structure one page really exposes: text blocks, image references, tables.

    A block-level fact is a measurement by the engine, not a claim about meaning:
    blocks are not paragraphs in a linguistic sense and a detected table is a
    detection. Detection failures are reported as facts instead of being swallowed.
    """
    facts: dict = {"chars": 0, "text_blocks": 0, "image_references": 0, "tables": []}
    blocks: list = []
    getter = getattr(page, "get_text", None)
    if getter is not None:
        with contextlib.suppress(Exception):
            blocks = [
                block
                for block in _capture(lambda: getter("blocks"), engine_messages)
                if isinstance(block, (list, tuple)) and len(block) >= 7
            ]
    facts["text_blocks"] = sum(1 for block in blocks if block[6] == 0)
    facts["image_blocks"] = sum(1 for block in blocks if block[6] == 1)
    with contextlib.suppress(Exception):
        facts["image_references"] = len(_capture(lambda: page.get_images(full=True), engine_messages) or [])
    finder = getattr(page, "find_tables", None)
    if callable(finder):
        try:
            found = _capture(finder, engine_messages)
            facts["tables"] = [
                {"rows": int(getattr(table, "row_count", 0)), "cols": int(getattr(table, "col_count", 0))}
                for table in (getattr(found, "tables", []) or [])
            ]
        except Exception as exc:  # noqa: BLE001 - a detector failure is a fact, not a crash
            facts["table_detection_error"] = f"{type(exc).__name__}: {exc}"
    return facts


def _open_document(raw: bytes):
    """Open a PDF in memory with the available native engine."""
    module = None
    for name in ("pymupdf", "fitz"):
        try:
            module = __import__(name)
            break
        except ImportError:
            continue
    if module is None:  # pragma: no cover - engine availability
        raise RuntimeError("no native PDF engine available (pymupdf/pdfminer)")
    try:
        # `pymupdf.open` accepts a stream + filetype, same as the legacy alias.
        return module.open(stream=raw, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"unreadable PDF: {type(exc).__name__}") from exc


def _page_text(page) -> str:
    getter = getattr(page, "get_text", None)
    if getter is None:
        raise ValueError("PDF engine cannot extract text")
    return getter() or ""


def _text_lines(page, engine_messages: list[str]) -> list[tuple[float, float, float, float, str]]:
    """The engine's text lines with their boxes, in the order the engine returns them.

    Lines rather than blocks, because the engine merges vertically adjacent runs into one
    block: measured on an 800x600 page with six runs inserted as left, right, left, right, the
    engine returns **three** blocks, each spanning both columns, while the lines inside them
    carry the real per-column boxes. Ordering by block therefore cannot see the columns at all.
    """
    getter = getattr(page, "get_text", None)
    if getter is None:
        return []
    lines: list[tuple[float, float, float, float, str]] = []
    with contextlib.suppress(Exception):
        payload = _capture(lambda: getter("dict"), engine_messages) or {}
        for block in payload.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                body = "".join(span.get("text", "") for span in line.get("spans", []))
                bbox = line.get("bbox") or ()
                if len(bbox) < 4 or not body.strip():
                    continue
                lines.append((float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]), body))
    return lines


def _two_column_gutter(lines: list[tuple[float, float, float, float, str]]) -> tuple[float, float] | None:
    """A vertical band that no text line crosses and that has text on both sides.

    Candidate bands are the gaps between line edges, so a line that spans a candidate (a
    full-width heading) cannot be assigned to either side and that candidate is rejected. The
    widest accepted band wins, because a real column gutter is wide and an incidental gap
    between indented lines is not.
    """
    edges = sorted({round(line[0], 2) for line in lines} | {round(line[2], 2) for line in lines})
    width = max(line[2] for line in lines)
    best: tuple[float, float, float] | None = None
    for left_edge, right_edge in zip(edges, edges[1:]):
        band = right_edge - left_edge
        if band < max(COLUMN_MIN_GUTTER, COLUMN_GUTTER_FRACTION * width):
            continue
        if left_edge < COLUMN_EDGE_MARGIN * width or right_edge > (1 - COLUMN_EDGE_MARGIN) * width:
            continue
        left = [line for line in lines if line[2] <= left_edge + 0.01]
        right = [line for line in lines if line[0] >= right_edge - 0.01]
        if len(left) < 2 or len(right) < 2 or len(left) + len(right) != len(lines):
            continue
        if best is None or band > best[2]:
            best = (left_edge, right_edge, band)
    return None if best is None else (best[0], best[1])


def _line_key(line: tuple[float, float, float, float, str]) -> tuple[float, float]:
    return (round(line[1], 1), round(line[0], 1))


def _line_text(line: tuple[float, float, float, float, str]) -> str:
    body = line[4]
    return body if body.endswith("\n") else body + "\n"


def _lines_of(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _ordered_page_text(page, engine_text: str, engine_messages: list[str]) -> tuple[str, dict]:
    """The page text in a reading order the page's own geometry supports.

    The engine returns lines in its own order, which on a two-column page interleaves the
    columns. When the geometry shows one unambiguous gutter with text on both sides, the lines
    are ordered column by column and then top to bottom. **The model may only reorder**: it is
    refused whenever the result would change which lines the page holds, and it is not applied
    at all when the engine text carries blank separator lines, because a line-level
    reconstruction would not carry those. A single-column page is returned untouched, so this
    costs nothing where there is no layout to model.
    """
    facts: dict = {"model": READING_ORDER_MODEL, "applied": False, "columns": 1, "gutter": None}
    lines = _text_lines(page, engine_messages)
    if len(lines) < 4:
        facts["reason"] = "fewer than four text lines, so no layout is inferred"
        return engine_text, facts
    if any(not line.strip() for line in engine_text.splitlines()):
        facts["reason"] = "the engine text carries blank separator lines, which a line-level reconstruction would not preserve"
        return engine_text, facts
    gutter = _two_column_gutter(lines)
    if gutter is None:
        facts["reason"] = "no vertical band that no text line crosses with text on both sides"
        return engine_text, facts
    left = [line for line in lines if line[2] <= gutter[0] + 0.01]
    right = [line for line in lines if line[0] >= gutter[1] - 0.01]
    ordered = sorted(left, key=_line_key) + sorted(right, key=_line_key)
    candidate = "".join(_line_text(line) for line in ordered)
    # The comparison is over the lines as a set, not in order: reordering is the whole point of
    # the model, so what it may never do is change which lines the page holds.
    if sorted(_lines_of(candidate)) != sorted(_lines_of(engine_text)):
        facts["reason"] = "the reconstruction would change the lines the page holds, so the engine order is kept"
        facts["reconstruction_refused"] = True
        return engine_text, facts
    facts.update(
        {
            "applied": True,
            "columns": 2,
            "gutter": [round(gutter[0], 2), round(gutter[1], 2)],
            "lines_carried": len(ordered),
            "reason": "one unambiguous gutter with text on both sides, and the same lines in both orders",
        }
    )
    return candidate, facts


def extract(path: str, ocr_dir: Path | None = None) -> dict:
    raw = Path(path).read_bytes()
    document = _open_document(raw)
    pages = list(document)
    if not pages:
        # Some engines accept arbitrary bytes as a zero-page document. That is not
        # a usable PDF, and reporting it as a successful empty extraction would be
        # exactly the silent success this worker must avoid.
        raise ValueError("PDF exposes no pages")
    # Build the projected text as page blocks, then derive the anchors from the
    # FINISHED text with the same line semantics as the text route. Deriving
    # anchors while appending (the earlier version) drifts as soon as a page
    # separator joins two page lines: offsets and line counts no longer match the
    # projected text, which the Core correctly rejects as an inconsistent receipt.
    blocks: list[tuple[int, str]] = []
    empty_pages: list[int] = []
    ordered_pages: list[int] = []
    refused_order_pages: list[int] = []
    per_page: list[dict] = []
    paragraphs: list[dict] = []
    tables: list[dict] = []
    image_references = 0
    table_errors: list[str] = []
    engine_messages: list[str] = []
    for page_index, page in enumerate(pages, start=1):
        engine_text = _page_text(page)
        # R15/F05: the projected text is what the anchors are derived from, so the reading
        # order is decided here, once, and reported below with its reason.
        page_text, reading_order = _ordered_page_text(page, engine_text, engine_messages)
        if reading_order.get("applied"):
            ordered_pages.append(page_index)
        elif reading_order.get("reconstruction_refused"):
            refused_order_pages.append(page_index)
        if not page_text.strip():
            empty_pages.append(page_index)
        blocks.append((page_index, page_text))
        facts = _page_facts(page, engine_messages)
        facts["chars"] = len(page_text)
        per_page.append(
            {
                "page": page_index,
                **{key: value for key, value in facts.items() if key != "tables"},
                "reading_order": reading_order,
            }
        )
        image_references += facts["image_references"]
        if facts.get("table_detection_error"):
            table_errors.append(f"page {page_index}: {facts['table_detection_error']}")
        for table in facts["tables"]:
            if len(tables) < TABLE_CAP:
                tables.append({"page": page_index, **table})
        page_blocks: list = []
        getter = getattr(page, "get_text", None)
        if getter is not None:
            with contextlib.suppress(Exception):
                page_blocks = [
                    block
                    for block in _capture(lambda: getter("blocks"), engine_messages)
                    if isinstance(block, (list, tuple)) and len(block) >= 7 and block[6] == 0
                ]
        for block_no, block in enumerate(page_blocks, start=1):
            if len(paragraphs) >= PARAGRAPH_CAP:
                break
            body = str(block[4]).strip()
            paragraphs.append(
                {
                    "page": page_index,
                    "block": block_no,
                    "bbox": [round(float(value), 2) for value in block[:4]],
                    "chars": len(body),
                    "first_line": body.splitlines()[0] if body else "",
                }
            )
    text = "\n".join(block for _, block in blocks)

    page_ranges: list[tuple[int, int, int]] = []
    cursor = 0
    for page_index, block in blocks:
        page_ranges.append((page_index, cursor, cursor + len(block)))
        cursor += len(block) + 1  # the joining separator

    anchors: list[dict] = []
    lines = text.splitlines(keepends=True)
    offset = 0
    per_page_line: dict[int, int] = {}
    for line in lines:
        if len(anchors) >= MAX_ANCHORS:
            break
        page_index = next(
            (page for page, start, end in page_ranges if start <= offset <= end),
            page_ranges[0][0] if page_ranges else 1,
        )
        per_page_line[page_index] = per_page_line.get(page_index, 0) + 1
        anchors.append(
            {
                "kind": "line",
                "path": [f"page-{page_index}", f"line-{per_page_line[page_index]}"],
                "char_start": offset,
                "char_end": offset + len(line),
            }
        )
        offset += len(line)

    losses: list[str] = []
    if empty_pages:
        losses.append(
            "pages with no extractable text: "
            + ", ".join(str(p) for p in empty_pages)
            + " (likely scanned; route to the OCR worker)"
        )
    if len(anchors) >= MAX_ANCHORS:
        losses.append(f"page/line anchors capped at {MAX_ANCHORS}")
    if len(paragraphs) >= PARAGRAPH_CAP:
        losses.append(f"page text blocks listed only for the first {PARAGRAPH_CAP} blocks")
    if len(tables) >= TABLE_CAP:
        losses.append(f"detected tables listed only for the first {TABLE_CAP} tables")
    if table_errors:
        losses.append("table detection failed on: " + "; ".join(table_errors))
    if refused_order_pages:
        # Worth a loss line of its own: the page did look like two columns, and the model
        # refused its own reconstruction because it would have changed the lines held.
        losses.append(
            "reading order kept as the engine order on pages "
            + ", ".join(str(p) for p in refused_order_pages)
            + " (the reconstruction would have changed the lines held)"
        )
    if engine_messages:
        losses.append(
            f"{len(engine_messages)} engine message(s) diverted from stdout: {engine_messages[0][:120]}"
        )
    # R15/F06: the half of the OCR chain this worker owns - a real image for every
    # page that has no text, declared with its digest so the Core can verify it before
    # anything is enqueued. The worker never enqueues: it has no database handle.
    candidates, render_problems = _render_ocr_candidates(empty_pages, document, ocr_dir)
    if render_problems:
        losses.append("OCR page rendering: " + "; ".join(render_problems))
    # Coverage is measured in the same unit as the anchors (lines) and supplied
    # together with covered/total, which the Core validates as a set.
    covered = len(anchors)
    total = len(lines)
    table_finder = any(callable(getattr(page, "find_tables", None)) for page in pages)
    loss_receipt = {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "params": {
            "pages": len(pages),
            "cap_anchors": MAX_ANCHORS,
            "coverage_unit": "line anchors",
            "pages_without_text": empty_pages,
            # R15/F05: what the engine exposed beyond the text itself. These are
            # measurements, not an accuracy claim and not a second anchor scheme -
            # navigation stays on the page/line anchors above.
            "structure": {
                "page_facts": per_page,
                "text_block_count": len(paragraphs),
                "text_blocks": paragraphs,
                "text_blocks_capped": len(paragraphs) >= PARAGRAPH_CAP,
                "table_support": table_finder,
                "table_count": len(tables),
                "tables": tables,
                "image_reference_count": image_references,
                "table_detection": (
                    "detected by the engine's own table finder; a detection is a measurement, "
                    "not a guarantee that the region is a table"
                ),
                # R15/F05: the reading order is a decision with a reason, recorded the same
                # way as every other fact here. It never adds or drops a line: when the
                # reconstruction would, the engine order is kept and the page says so.
                "reading_order": {
                    "model": READING_ORDER_MODEL,
                    "applied_to_pages": ordered_pages,
                    "refused_on_pages": refused_order_pages,
                    "note": (
                        "the model may only reorder lines; it is applied when the page shows one "
                        "unambiguous vertical gutter with text on both sides, and the engine order "
                        "is kept otherwise, with the per-page reason recorded above"
                    ),
                },
                "block_meaning": "a text block is an engine block, not a linguistic paragraph",
                "engine_messages": engine_messages[:10],
                "engine_messages_capped": len(engine_messages) > 10,
                "engine_message_policy": (
                    "engine chatter is captured into this receipt instead of being printed, "
                    "because the stdio protocol is one JSON envelope per line"
                ),
                "ocr_candidates": candidates,
                "ocr_candidate_count": len(candidates),
                "ocr_render": {
                    "dpi": OCR_DPI,
                    "format": "image/png",
                    "cap": OCR_PAGE_CAP,
                    "rendered": bool(candidates),
                    "note": (
                        "these files are rendered pages offered to the OCR route; the Core "
                        "verifies each digest and decides whether to enqueue a job, because a "
                        "worker holds no database handle"
                    ),
                },
            },
        },
        "losses": losses,
        "covered": covered,
        "total": total,
        "coverage": (covered / total) if total else 1.0,
        "loss_note": "; ".join(losses)
        if losses
        else (
            "no transform applied"
            if total
            else "no lines to anchor; zero-line coverage defined as 1.0"
        ),
    }
    if total == 0:
        loss_receipt["loss_note"] += "; zero-page PDF has no coverage to claim"
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "structure": anchors,
        "loss_receipt": loss_receipt,
    }


def main() -> int:
    # R08: the same sidecar stdio loop the text worker uses, with this route's
    # own identity and capability, so PDF input reaches the Core through the same
    # job/attempt/error machinery instead of a private CLI path.
    if "--staging-root" in sys.argv:
        import argparse

        repo_root = Path(__file__).resolve().parents[3]
        spec = importlib.util.spec_from_file_location(
            "pdf_transport", repo_root / "services" / "python-workers" / "transport" / "text_ndjson.py"
        )
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--staging-root", type=Path, required=True)
        # R15/F06: where durable transfer files (rendered pages) may be written; the
        # attempt directory itself is temporary, so renders must not live there.
        parser.add_argument("--artifact-root", type=Path, default=None)
        args = parser.parse_args()
        return transport.serve_stdio(WORKER_IDENTITY, ["pdf.extract"], args.staging_root, args.artifact_root)

    with contextlib.suppress(AttributeError, OSError):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_pdf.py <input-file> | --staging-root <dir>"}))
        return 2
    try:
        print(json.dumps(extract(sys.argv[1]), ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001 - explicit failure, never silent
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}", "engine": ENGINE}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
