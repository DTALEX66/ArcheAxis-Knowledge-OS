#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ArcheAxis vNext capability worker: plain-text extraction example.

Isolation boundary (DIRECTORY_AUTHORITY): this worker NEVER opens the vNext
database and never writes to it. It reads an input file, produces
`text` + a loss receipt (packages/contracts/v1/worker-protocol.schema.json),
and prints a JSON envelope on stdout. The Rust Core (archeaxis-api jobs
endpoint) persists the receipt.

Usage:
    python worker_extract.py <input-file>

Output (stdout, single JSON line):
    {"engine": "python-worker-extract", "engine_version": "0.1.0",
     "text": "...", "loss_receipt": {"engine": ..., "params": {...},
     "loss_note": "..."}}

Failure contract: on any error the worker exits non-zero and prints
    {"error": "<message>"}  — never a fake success envelope.
"""

import json
import sys


def extract(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as fh:  # utf-8-sig strips BOM
        raw = fh.read()
    return {
        "engine": "python-worker-extract",
        "engine_version": "0.1.0",
        "text": raw,
        "loss_receipt": {
            "engine": "python-worker-extract",
            "engine_version": "0.1.0",
            "params": {"encoding": "utf-8-sig"},
            "loss_note": "BOM stripped; no other transform applied",
        },
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_extract.py <input-file>"}))
        return 2
    try:
        out = extract(sys.argv[1])
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
