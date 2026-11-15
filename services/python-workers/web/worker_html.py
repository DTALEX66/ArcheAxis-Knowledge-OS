#!/usr/bin/env python3
"""ArcheAxis vNext web worker: static HTML/MHTML snapshot extraction (F02 partial).

Reads a saved HTML snapshot file and deterministically extracts title,
main text, links and paragraph anchors. Explicit article/main pages use the
locked Trafilatura donor; fragments and unavailable/empty/failed extraction
use html.parser with a recorded fallback. Network fetching and dynamic rendering are Core-side
concerns (F02/F03 full slices); this worker consumes a local snapshot and
never executes scripts. Derived text offsets are not original DOM locations.
MHTML selects one bounded MIME HTML root; resources stay inert in the original.

Usage:
    python worker_html.py <snapshot.html|snapshot.mhtml>
Output: {"engine","engine_version","text","title","links","structure","loss_receipt"}
"""

from __future__ import annotations

import base64
import email.policy
import hashlib
import json
import quopri
import re
import sys
from html.parser import HTMLParser
from email.parser import BytesParser
from importlib.metadata import version
from pathlib import Path

ENGINE = "python-worker-html"
ENGINE_VERSION = "0.1.1"
# R15/F02: the identity advertised in the sidecar handshake. This worker existed since an
# earlier slice with no route pointing at it; the sidecar mode below is that wiring.
WORKER_IDENTITY = "python-worker-html-ndjson"

_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
# R15/F02: a marker that makes a file an HTML document rather than bytes with a .html name.
# Deliberately any tag, not a list of block tags: `<b>hi</b>` is a marked-up document, and an
# allow-list refused it as "not an HTML document" (found by the bulk HTML worker test).
_TAG_MARKER = re.compile(r"<\s*(?:!doctype\b|/?\s*[a-zA-Z][a-zA-Z0-9:_-]*)", re.I)
_BLOCK_TAGS = {
    "p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5",
    "h6", "blockquote", "pre", "table", "tr", "br", "ul", "ol",
}
MHTML_MAX_BYTES = 16 * 1024 * 1024
MHTML_MAX_PARTS = 128
MHTML_MAX_DEPTH = 32


def _mhtml_root(raw: bytes) -> tuple[str, str, dict]:
    """Decode one MIME root, never resolve its URLs or materialise resources.

    RFC 2387 sections 3.1/3.2 select a direct root by start/Content-ID or the
    first part. RFC 2557 Content-Location remains an untrusted declaration.
    Python's stdlib email parser owns MIME parsing; no mail route is changed.
    https://docs.python.org/3.12/library/email.parser.html
    https://www.rfc-editor.org/rfc/rfc2387
    https://www.rfc-editor.org/rfc/rfc2557
    """
    if len(raw) > MHTML_MAX_BYTES:
        raise ValueError("MHTML original exceeds 16 MiB")
    message = BytesParser(policy=email.policy.default.clone(raise_on_defect=True)).parsebytes(raw)
    if message.get_content_type() != "multipart/related" or not message.is_multipart():
        raise ValueError("MHTML requires a multipart/related envelope")

    def header(part, name):
        values = part.get_all(name, [])
        if len(values) > 1 or any(getattr(value, "defects", ()) for value in values):
            raise ValueError("MHTML duplicate MIME identity/encoding header")
        value = str(values[0]).strip() if values else None
        if value is not None and (not value or len(value) > 4096 or any(ord(c) < 32 for c in value)):
            raise ValueError("MHTML invalid MIME identity/encoding header")
        return value

    parts, identities, locations = [], set(), set()
    stack = [(message, [], 0)]
    while stack:
        part, path, depth = stack.pop()
        if depth > MHTML_MAX_DEPTH or len(parts) >= MHTML_MAX_PARTS:
            raise ValueError("MHTML MIME part/depth budget exceeded")
        if part.defects:
            raise ValueError("MHTML malformed MIME part")
        metadata = {key: header(part, key) for key in
                    ("Content-Type", "Content-ID", "Content-Location", "Content-Transfer-Encoding")}
        params = part.get_params() or []
        keys = [key.lower() for key, _ in params[1:]]
        if len(keys) != len(set(keys)):
            raise ValueError("MHTML duplicate MIME parameter")
        cid, location = metadata["Content-ID"], metadata["Content-Location"]
        if cid:
            if not re.fullmatch(r"<[^<>\s]+>", cid) or cid in identities:
                raise ValueError("MHTML duplicate or invalid Content-ID")
            identities.add(cid)
        if location:
            if location in locations:
                raise ValueError("MHTML ambiguous Content-Location")
            locations.add(location)
        parts.append((part, path, metadata))
        if part.is_multipart():
            children = list(part.iter_parts())
            stack.extend((child, path + [index], depth + 1)
                         for index, child in reversed(list(enumerate(children, 1))))

    children = list(message.iter_parts())
    if not children:
        raise ValueError("MHTML root part is missing")
    start = message.get_param("start")
    if start is not None:
        if not isinstance(start, str) or not re.fullmatch(r"<[^<>\s]+>", start):
            raise ValueError("MHTML start is not a Content-ID")
        roots = [part for part in children if header(part, "Content-ID") == start]
        if len(roots) != 1:
            raise ValueError("MHTML start root is missing or ambiguous")
        root = roots[0]
    else:
        root = children[0]
    declared_type = message.get_param("type")
    if (root.is_multipart() or root.get_content_type() not in {"text/html", "application/xhtml+xml"}
            or not isinstance(declared_type, str) or declared_type.lower() != root.get_content_type()):
        raise ValueError("MHTML selected root is not the declared HTML type")

    resources, root_bytes, root_info, total = [], None, None, 0
    for part, path, metadata in parts:
        if part.is_multipart():
            continue
        encoding = (metadata["Content-Transfer-Encoding"] or "7bit").lower()
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes) or part.defects:
            raise ValueError("MHTML invalid encoded MIME payload")
        # email accepts some malformed transfers for mail readers. A fixed archive
        # projection must reject those instead of silently repairing its root.
        if encoding in {"base64", "quoted-printable"}:
            wire = part.get_payload(decode=False).encode("ascii", "strict")
            if encoding == "base64":
                payload = base64.b64decode(re.sub(rb"[ \t\r\n]", b"", wire), validate=True)
            else:
                if re.search(rb"=(?![a-fA-F0-9]{2}|\r?\n)", wire):
                    raise ValueError("MHTML invalid quoted-printable payload")
                payload = quopri.decodestring(wire)
        elif encoding == "7bit":
            payload.decode("ascii", "strict")
        elif encoding not in {"8bit", "binary"}:
            raise ValueError("MHTML unsupported transfer encoding")
        total += len(payload)
        if total > MHTML_MAX_BYTES:
            raise ValueError("MHTML decoded resources exceed 16 MiB")
        info = {"path": [f"mime-part-{index}" for index in path],
                "content_id": metadata["Content-ID"], "content_location": metadata["Content-Location"],
                "media_type": part.get_content_type(), "transfer_encoding": encoding,
                "decoded_bytes": len(payload), "decoded_sha256": hashlib.sha256(payload).hexdigest()}
        if part is root:
            root_bytes, root_info = payload, info
        else:
            resources.append(info)
    if root_bytes is None or root_info is None:
        raise ValueError("MHTML root payload missing")
    charset = root.get_content_charset() or "us-ascii"
    html = root_bytes.decode(charset, "strict")
    root_info["charset"] = charset
    return html, charset, {
        "schema": "archeaxis.mhtml-projection/v1", "format": "mhtml", "root": root_info,
        "root_selection": "start-content-id" if start is not None else "first-body-part",
        "part_count": len(parts) - 1, "resource_count": len(resources), "resources": resources,
        "reference_policy": "DECLARATIONS_ONLY; no URL, cid or file resolution and no resource files written",
        "location_model": "MIME root path plus offsets in derived HTML text; not original archive byte offsets or browser DOM coordinates",
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

    def close(self) -> None:
        # A fragment made only of inline tags (`<b>hi</b>`) never crosses a block boundary, so
        # its text would otherwise be dropped and the document would project as empty.
        super().close()
        if self._skip_depth == 0:
            self._flush_block()

    def _flush_block(self) -> None:
        raw = "".join(self._text_parts)
        text = re.sub(r"[ \t]+", " ", raw).strip()
        if text:
            self.blocks.append(text)
        self._text_parts = []


def _format_execution_receipt(raw: bytes, path: str, blocks: list[str], anchors: list[dict], original_format="html") -> dict:
    """Bind this HTML execution to the retained bytes and its actual projection.

    The unified worker protocol still stores the receipt as a loss-report parameter,
    so this nested object does not add a fourth Core output.  It is a real execution
    receipt: the source digest, engine identity, derived document id, block/anchor
    counts and the limitations observed by this static snapshot worker are all
    derived from this invocation.  The source path is reduced to its display name.
    """
    source_sha256 = hashlib.sha256(raw).hexdigest()
    block_count = len(blocks)
    partial_note = (
        "static snapshot only: scripts, styles, templates and SVG are skipped; "
        "URL fetching, dynamic rendering and semantic fidelity are not measured"
    )
    return {
        "schema": "archeaxis.format-execution-receipt/v1",
        "receipt_id": f"{original_format}-execution-{source_sha256}",
        "status": "partial" if block_count else "unsupported",
        "original": {
            "sha256": source_sha256,
            "name": Path(path).name or "snapshot.html",
            "format": original_format,
            "retained": True,
        },
        "transform": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "derived_document_id": f"{original_format}-document-{source_sha256}",
        },
        "loss": {
            "status": "partial" if block_count else "unknown",
            "notes": [partial_note],
        },
        "structure": {"block_count": block_count, "block_kinds": ["block"] if block_count else []},
        "anchors": [
            {"block_id": f"block-{index}", "kind": anchor["kind"], "locator": anchor}
            for index, anchor in enumerate(anchors, start=1)
        ],
        "quality_facts": [
            {"name": "block_count", "status": "measured", "value": block_count, "unit": "blocks"},
            {"name": "anchor_count", "status": "measured", "value": len(anchors), "unit": "anchors"},
            {"name": "link_count", "status": "measured", "value": 0, "unit": "links"},
            {
                "name": "semantic_fidelity",
                "status": "unsupported",
                "note": "static HTML extraction does not measure semantic fidelity",
            },
        ],
        "fallback": {"used": False, "attempted_engines": [], "selected_engine": None, "reason": None},
    }


def _failed_execution_receipt(raw: bytes, path: str, error: BaseException) -> dict:
    """Record a path-free receipt when a retained snapshot cannot be projected.

    A malformed or non-HTML snapshot is still an execution attempt.  Returning
    only ``error`` made that attempt invisible to the format receipt contract,
    and including the exception text could accidentally echo a local path.  The
    failure receipt keeps the source digest and display name, records the error
    type, and deliberately leaves the projection empty.
    """
    source_sha256 = hashlib.sha256(raw).hexdigest()
    original_format = "mhtml" if Path(path).suffix.lower() in {".mht", ".mhtml"} else "html"
    error_type = type(error).__name__ or "ExecutionError"
    return {
        "schema": "archeaxis.format-execution-receipt/v1",
        "receipt_id": f"{original_format}-execution-{source_sha256}",
        "status": "failed",
        "original": {
            "sha256": source_sha256,
            "name": Path(path).name or "snapshot.html",
            "format": original_format,
            "retained": True,
        },
        "transform": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "derived_document_id": f"{original_format}-document-{source_sha256}",
        },
        "loss": {
            "status": "unknown",
            "notes": [f"execution failed before projection ({error_type})"],
        },
        "structure": {"block_count": 0, "block_kinds": []},
        "anchors": [],
        "quality_facts": [
            {"name": "source_bytes", "status": "measured", "value": len(raw), "unit": "bytes"},
            {
                "name": "semantic_fidelity",
                "status": "unsupported",
                "note": "execution failed before semantic projection",
            },
        ],
        "fallback": {"used": False, "attempted_engines": [], "selected_engine": None, "reason": None},
    }


def _article_text(html: str) -> tuple[str | None, str]:
    """Reuse the locked donor on saved bytes only; never call its URL fetcher."""
    from trafilatura import extract as extract_article

    # Preserve arbitrary fragments verbatim. Article cleanup is appropriate only
    # when the saved page itself marks a main/article region; short fragments and
    # generic notes must not acquire whitespace normalization or boilerplate loss.
    if not re.search(r"<(?:article|main)\b", html, re.I):
        return None, version("trafilatura")
    return extract_article(
        html, output_format="txt", include_comments=False,
        include_tables=True, include_links=False, deduplicate=False,
    ), version("trafilatura")


def extract(path: str) -> dict:
    is_mhtml = Path(path).suffix.lower() in {".mht", ".mhtml"}
    if is_mhtml:
        with Path(path).open("rb") as source:
            raw = source.read(MHTML_MAX_BYTES + 1)
        html_text, encoding, mhtml = _mhtml_root(raw)
    else:
        raw = Path(path).read_bytes()
        mhtml = None
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
    # R15/F02: a file that carries no HTML at all must fail rather than succeed with an
    # empty body. A page that is genuinely blank is different: it is marked up, so it is
    # reported as carrying no text instead of being refused. The test is markup presence
    # alone, not "no blocks": text is now flushed at close, so any text file would
    # otherwise be accepted as a page.
    if not _TAG_MARKER.search(html_text):
        raise ValueError("not an HTML document: no tags found in the snapshot")
    attempts = []
    selected = "stdlib-html-parser"
    donor_version = None
    try:
        article, donor_version = _article_text(html_text)
        if article and article.strip():
            blocks = [line.strip() for line in article.splitlines() if line.strip()]
            selected = "trafilatura"
            attempts.append({"engine": selected, "status": "succeeded", "version": donor_version})
        else:
            attempts.append({"engine": "trafilatura", "status": "empty", "version": donor_version})
    except ImportError:
        attempts.append({"engine": "trafilatura", "status": "missing_dependency"})
    except Exception as error:
        # Do not put parser messages or local paths in receipts.
        attempts.append({"engine": "trafilatura", "status": "failed", "error_type": type(error).__name__})
    fallback_used = selected != "trafilatura"
    if fallback_used:
        attempts.append({"engine": selected, "status": "succeeded" if blocks else "empty"})
    extraction = {"selected_engine": selected, "version": donor_version if not fallback_used else ENGINE_VERSION,
                  "fallback_used": fallback_used, "attempts": attempts,
                  "anchor_scope": "offsets in derived text, not original DOM coordinates"}
    projection = "\n\n".join(blocks)
    anchors: list[dict] = []
    offset = 0
    for index, block in enumerate(blocks, start=1):
        start = projection.find(block, offset)
        if start < 0:
            start = offset
        anchors.append({"kind": "mhtml_block" if mhtml else "block",
                        "path": (mhtml["root"]["path"] if mhtml else []) + [f"block-{index}"],
                        "char_start": start, "char_end": start + len(block)})
        offset = start + len(block)

    execution_receipt = _format_execution_receipt(raw, path, blocks, anchors, "mhtml" if mhtml else "html")
    mhtml_loss = ("MHTML only projects the selected decoded HTML root; MIME resources and Content-Location "
                  "remain declarations in retained original bytes; no scripts, resource resolution or "
                  "browser layout; positions address derived text, never archive byte offsets")
    if mhtml:
        execution_receipt["loss"]["notes"].append(mhtml_loss)
    execution_receipt["quality_facts"][2]["value"] = len(parser.links)
    execution_receipt["fallback"] = {
        "used": fallback_used, "attempted_engines": [item["engine"] for item in attempts],
        "selected_engine": selected,
        "reason": attempts[0]["status"] if fallback_used else None,
    }

    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": projection,
        "title": parser.title.strip(),
        "links": parser.links,
        "structure": anchors,
        "format_execution_receipt": execution_receipt,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"encoding": encoding, "skip_tags": sorted(_SKIP_TAGS),
                       "extraction": extraction, "source_sha256": hashlib.sha256(raw).hexdigest(),
                       **({"mhtml": mhtml} if mhtml else {})},
            "losses": [mhtml_loss] if mhtml else [],
            "loss_note": (
                "saved snapshot only; no fetching or script execution; article extraction is "
                "a heuristic, not semantic-fidelity evidence; anchors address the derived text; "
                "original link inventory retained separately"
                + ("; the marked-up page carries no text blocks at all" if not blocks else "")
                + ("; " + mhtml_loss if mhtml else "")
            ),
        },
    }


def main() -> int:
    # R15/F02: the same stdio job loop every route uses, with this worker's own identity
    # and capability, so a saved HTML snapshot reaches the Core through the normal
    # job/attempt/error machinery instead of a private CLI path.
    if "--staging-root" in sys.argv:
        import argparse
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
        spec = importlib.util.spec_from_file_location("html_transport", _transport)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        sidecar = argparse.ArgumentParser(description=__doc__)
        sidecar.add_argument("--staging-root", type=Path, required=True)
        sidecar.add_argument("--artifact-root", type=Path, default=None)
        args = sidecar.parse_args()
        return transport.serve_stdio(
            WORKER_IDENTITY, ["html.structure"], args.staging_root, args.artifact_root
        )

    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_html.py <snapshot.html>"}))
        return 2
    try:
        out = extract(sys.argv[1])
    except Exception as exc:  # noqa: BLE001
        failure = {"error": str(exc)}
        source = Path(sys.argv[1])
        try:
            # A present source, including a zero-byte source, has enough retained
            # bytes to produce a path-free failed execution receipt.  Missing or
            # unreadable inputs retain the existing structured error behavior.
            if source.is_file() and (source.suffix.lower() not in {".mht", ".mhtml"}
                                     or source.stat().st_size <= MHTML_MAX_BYTES):
                raw = source.read_bytes()
                failure["format_execution_receipt"] = _failed_execution_receipt(raw, str(source), exc)
        except OSError:
            pass
        print(json.dumps(failure, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
