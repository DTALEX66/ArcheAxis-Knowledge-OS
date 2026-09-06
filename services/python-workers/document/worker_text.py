#!/usr/bin/env python3
"""ArcheAxis vNext document worker: plain text family (F01).

Formats: TXT / MD / CSV / TSV / JSON / XML (textual sources).

Isolation boundary: this worker NEVER opens the vNext database and never
executes file content. It decodes bytes faithfully (encoding/line endings
preserved and reported), projects text + line anchors, and prints a single
JSON envelope on stdout. Failure contract: non-zero exit + {"error": ...},
never a fake success envelope.

Provenance: pure-parser behaviour distilled from the legacy ingestion
adapters (app/ingestion/multi_format.py `_via_read`/`_decode_text_bytes`
semantics) without importing the legacy package.

Usage:
    python worker_text.py <input-file>
Output: {"engine","engine_version","text","structure","loss_receipt"}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ENGINE = "python-worker-text"
ENGINE_VERSION = "0.1.0"


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


def extract(path: str) -> dict:
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
    loss_receipt = {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "params": {"decode": decode_note["encoding"], "cap_lines": 5000,
                   "coverage_unit": "line anchors", "line_splitting": "str.splitlines(keepends=True)"},
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
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_text.py <input-file>"}))
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
