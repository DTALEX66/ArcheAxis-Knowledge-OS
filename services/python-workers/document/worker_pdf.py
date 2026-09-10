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
import json
import sys
from pathlib import Path

ENGINE = "pymupdf-native-pdf"
ENGINE_VERSION = "pymupdf"

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
    parts: list[str] = []
    anchors: list[dict] = []
    empty_pages: list[int] = []
    offset = 0
    for page_index, page in enumerate(pages, start=1):
        text = _page_text(page)
        if not text.strip():
            empty_pages.append(page_index)
        # Page separator keeps page boundaries visible in the projected text.
        prefix = "" if page_index == 1 else "\n"
        if prefix:
            parts.append(prefix)
            offset += len(prefix)
        page_start = offset
        for line_index, line in enumerate(text.splitlines(keepends=True), start=1):
            if len(anchors) >= MAX_ANCHORS:
                break
            anchors.append(
                {
                    "kind": "line",
                    "path": [f"page-{page_index}", f"line-{line_index}"],
                    "char_start": offset,
                    "char_end": offset + len(line),
                }
            )
            offset += len(line)
        parts.append(text)
        # Recompute the offset from the final buffer so page/line offsets stay
        # exact even when the anchor cap truncated this page.
        offset = page_start + len(text)
    text = "".join(parts)
    losses: list[str] = []
    if empty_pages:
        losses.append(
            "pages with no extractable text: "
            + ", ".join(str(p) for p in empty_pages)
            + " (likely scanned; route to the OCR worker)"
        )
    if len(anchors) >= MAX_ANCHORS:
        losses.append(f"page/line anchors capped at {MAX_ANCHORS}")
    covered = len(pages) - len(empty_pages)
    total = len(pages)
    loss_receipt = {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "params": {"pages": total, "cap_anchors": MAX_ANCHORS, "coverage_unit": "pages with text"},
        "losses": losses,
        "covered": covered,
        "total": total,
        "loss_note": "; ".join(losses)
        if losses
        else "no transform applied",
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
    with contextlib.suppress(AttributeError, OSError):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_pdf.py <input-file>"}))
        return 2
    try:
        print(json.dumps(extract(sys.argv[1]), ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001 - explicit failure, never silent
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}", "engine": ENGINE}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
