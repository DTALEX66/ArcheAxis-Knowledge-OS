#!/usr/bin/env python3
"""Preserve the tables a `legacy_dryrun` export could not read, using the product's own reader.

`archeaxis-migration`'s export names tables it cannot open in `unqueried_tables` — the real legacy
store has a `sqlite-vec` `vec0` table and that reader has no such module. The product does: its own
reader loads `sqlite_vec` best-effort (`app/workspace/migrate.py`), so the table is readable, and
the gap belongs to one reader rather than to the data. This fills the named gaps so the preserved
set is the whole database instead of "everything except one table".

It composes with the Rust export rather than replacing it: the Rust tool owns the per-table sha256
manifest, this writes the missing tables' JSONL and appends them to that manifest so one manifest
still describes the whole export.

Read-only against the source database. Refuses to invent rows: a named table that still cannot be
read is reported as still unqueried, and the exit code says so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = {".codex", ".dsh", ".hermes", ".openhuman", ".claude", ".agents", ".env"}


def reject_private(path: Path) -> Path:
    text = os.fspath(path).replace("\\", "/")
    if text.lower().startswith(("e:", "//")):
        raise ValueError("protected drive or UNC path is not permitted")
    absolute = Path(os.path.abspath(path))
    if any(part.casefold() in PRIVATE for part in absolute.parts):
        raise ValueError("private agent paths are not permitted")
    return absolute


def export_filename(name: str) -> str:
    """The file name the Rust export uses for a table.

    Mirrored rather than guessed: it keeps the plain name for `[A-Za-z0-9_-]` and hex-encodes
    anything else, so the files this tool writes appear in the manifest under the names the
    Rust verifier expects to find on disk.
    """
    plain = name and not name.startswith("__table_") and all(
        char.isascii() and (char.isalnum() or char in "_-") for char in name)
    return f"{name}.jsonl" if plain else f"__table_{name.encode('utf-8').hex()}.jsonl"


def value_json(value: object) -> object:
    """JSON for one cell, matching the Rust export's own mapping.

    BLOBs become lowercase hex strings there, so they do here too: one manifest describing one
    export must not hold two spellings of the same bytes.
    """
    if value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return str(value)


def export_tables(database: Path, out_dir: Path, names: list[str]) -> dict[str, dict]:
    try:
        import sqlite_vec
    except ImportError as error:  # the reason this gap cannot be closed, named
        raise SystemExit(
            f"sqlite_vec is not installed, so a vec0 table still cannot be read: {error}") from error
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    written: dict[str, dict] = {}
    try:
        connection.enable_load_extension(True)
        sqlite_vec.load(connection)
        connection.enable_load_extension(False)
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            try:
                rows = connection.execute(f"SELECT * FROM {quoted}").fetchall()
            except sqlite3.OperationalError as error:
                written[name] = {"error": str(error)}
                continue
            columns = [description[0] for description in connection.execute(
                f"SELECT * FROM {quoted} LIMIT 1").description]
            target = out_dir / export_filename(name)
            with target.open("w", encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    record = {column: value_json(value) for column, value in zip(columns, row, strict=True)}
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n")
            payload = target.read_bytes()
            written[name] = {
                "rows": len(rows),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
    finally:
        connection.close()
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", help="the legacy database whose gaps are being filled")
    parser.add_argument("export_dir", help="the directory the Rust export wrote into")
    args = parser.parse_args()

    database = reject_private(Path(args.database))
    out_dir = reject_private(Path(args.export_dir))
    manifest_path = out_dir / "export-manifest.json"
    if not database.is_file() or not manifest_path.is_file():
        print(f"need both the database and its manifest: {database} / {manifest_path}", file=sys.stderr)
        return 2
    if not database.is_relative_to(ROOT) and not out_dir.is_relative_to(ROOT):
        print("both paths must be inside this project", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pending = sorted((manifest.get("unqueried_tables") or {}).keys())
    if not pending:
        print("nothing unqueried: the export already covers every readable table")
        return 0

    written = export_tables(database, out_dir, pending)
    still_missing = {name: entry["error"] for name, entry in written.items() if "error" in entry}
    filled = {name: entry for name, entry in written.items() if "error" not in entry}

    manifest["tables"].update(filled)
    manifest["unqueried_tables"] = still_missing
    # The digest covers the gap, so it must be recomputed when the gap changes; leaving the old one
    # would make the manifest fail its own verification. The field order and the ordering of the
    # entries mirror the Rust `manifest_digest` exactly, including sorting by UTF-8 bytes rather
    # than by code point, so the Rust verifier recomputes the same value.
    def by_bytes(item: tuple[str, object]) -> bytes:
        return item[0].encode("utf-8")

    hasher = hashlib.sha256()
    for name, table in sorted(manifest["tables"].items(), key=by_bytes):
        hasher.update(name.encode("utf-8"))
        hasher.update(int(table["rows"]).to_bytes(8, "little"))
        hasher.update(str(table["sha256"]).encode("utf-8"))
    for name, reason in sorted(manifest["unqueried_tables"].items(), key=by_bytes):
        hasher.update(b"unqueried:")
        hasher.update(name.encode("utf-8"))
        hasher.update(str(reason).encode("utf-8"))
    manifest["manifest_sha256"] = hasher.hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for name, entry in sorted(filled.items()):
        print(f"filled {name}: {entry['rows']} rows sha256={entry['sha256'][:12]}")
    for name, reason in sorted(still_missing.items()):
        print(f"STILL UNQUERIED {name}: {reason}")
    print(f"tables in manifest: {len(manifest['tables'])} manifest_sha256={manifest['manifest_sha256']}")
    # 0 whole, 3 preserved with a named gap, 1 failed — the same three outcomes the Rust tool uses.
    return 3 if still_missing else 0


if __name__ == "__main__":
    sys.exit(main())
