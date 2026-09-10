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
import importlib.util
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


def extract(path: str) -> dict:
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
    for page_index, page in enumerate(pages, start=1):
        page_text = _page_text(page)
        if not page_text.strip():
            empty_pages.append(page_index)
        blocks.append((page_index, page_text))
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
    # Coverage is measured in the same unit as the anchors (lines) and supplied
    # together with covered/total, which the Core validates as a set.
    covered = len(anchors)
    total = len(lines)
    loss_receipt = {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "params": {
            "pages": len(pages),
            "cap_anchors": MAX_ANCHORS,
            "coverage_unit": "line anchors",
            "pages_without_text": empty_pages,
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
        args = parser.parse_args()
        return transport.serve_stdio(WORKER_IDENTITY, ["pdf.extract"], args.staging_root)

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
