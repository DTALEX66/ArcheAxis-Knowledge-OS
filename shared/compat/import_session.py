"""Compatibility Kernel — import session with path safety and idempotency (K2).

The import session scans an approved vault root, parses each file into a
canonical ``VaultFile``, persists a governed compatibility ledger (not the
governed knowledge/machine-knowledge tables), and reports any content that
could not be expressed without loss. Re-importing the same source is
idempotent.
"""

from __future__ import annotations

import json
import os
import sqlite3
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from . import anki_package

if TYPE_CHECKING:
    from shared.compat.models import VaultFile

_SCHEMA = """
CREATE TABLE IF NOT EXISTS compat_files (
    relative_path TEXT PRIMARY KEY,
    source_hash TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    frontmatter_json TEXT NOT NULL,
    body_hash TEXT NOT NULL,
    is_canvas INTEGER NOT NULL DEFAULT 0,
    is_binary INTEGER NOT NULL DEFAULT 0,
    mime_type TEXT,
    imported_at TEXT NOT NULL,
    source_context TEXT NOT NULL DEFAULT 'acl,comments,history:not_recorded'
);
"""


# Anki joins a note's fields with the unit separator and stores scheduling as integers in its own
# vocabulary. Both are read as the source collection's facts and are never re-authored here.
ANKI_FIELD_SEPARATOR = "\x1f"
ANKI_CARD_TYPES = {0: "new", 1: "learning", 2: "review", 3: "relearning"}
ANKI_CARD_QUEUES = {0: "new", 1: "learning", 2: "review", 3: "day_learning", 4: "preview", -1: "suspended", -2: "buried", -3: "user_buried"}


def read_anki_package(path: str | Path) -> list[dict[str, object]]:
    """Read an Anki collection out of a package, on behalf of the compatibility kernel.

    This belongs here rather than in an adapter because it opens SQLite, and the set of modules
    permitted to do that is inventoried deliberately so it cannot grow quietly. What it opens is a
    foreign collection, deserialised in memory and never the workspace, so it cannot write; and the
    scheduling it returns is the source's own record, labelled as imported, because this function
    graded nothing. A card nobody has answered carries no interval rather than an interval of zero.
    """
    try:
        with zipfile.ZipFile(path) as container:
            _, _, raw = anki_package.collection_bytes(container)
    except zipfile.BadZipFile as error:
        raise ValueError(f"unreadable package: {error}") from error
    units = read_anki_collection(raw)["notes"]
    for unit in units:
        unit["not_carried"] = ["deck_options: source scheduler configuration",
                               "deck_names: only the standalone archive projection resolves deck IDs"]
    return units


def read_anki_collection(raw: bytes, *, review_limit: int = 0) -> dict:
    """Read the foreign database in memory. Only Rust Core persists AAOS objects."""

    connection = sqlite3.connect(":memory:")
    try:
        # SQLite's deserialize API needs rollback-mode header bytes for a
        # standalone database image. Anki's modern export can retain WAL mode.
        if raw.startswith(b"SQLite format 3\0") and raw[18:20] == b"\x02\x02":
            raw = raw[:18] + b"\x01\x01" + raw[20:]
        connection.deserialize(raw)
        # The catalog uses Anki's Unicode collation even on WITHOUT ROWID
        # tables. The projection keys by numeric IDs, never by name equality.
        connection.create_collation("unicase", _compare_anki_names)
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA query_only=ON")
        note_types, decks = _anki_catalog(connection)
        cards: dict[object, list[dict[str, object]]] = {}
        for row in connection.execute(
            "SELECT id, nid, did, ord, type, queue, due, ivl, factor, reps, lapses FROM cards ORDER BY id"
        ):
            card_id, note_id, deck_id, ordinal, type_, queue, due, ivl, factor, reps, lapses = row
            answered = reps > 0
            cards.setdefault(note_id, []).append({
                "card_id": card_id,
                "deck_id": deck_id,
                "template_ordinal": ordinal,
                "state": ANKI_CARD_TYPES.get(type_, f"unknown({type_})"),
                "queue": ANKI_CARD_QUEUES.get(queue, f"unknown({queue})"),
                "interval_days": ivl if answered else None,
                "due": due,
                "ease_per_mille": factor if answered else None,
                "reviews": reps,
                "lapses": lapses,
            })
        units: list[dict[str, object]] = []
        for note_id, guid, mid, flds, tags in connection.execute(
            "SELECT id, guid, mid, flds, tags FROM notes ORDER BY id"
        ):
            units.append({
                "note_id": note_id,
                "guid": guid,
                "note_type_id": mid,
                "note_type": note_types.get(mid, {}).get("name", f"unknown({mid})"),
                "fields": flds.split(ANKI_FIELD_SEPARATOR),
                "tags": [tag for tag in str(tags).split() if tag],
                "cards": cards.get(note_id, []),
                "scheduling_origin": "imported_from_source",
                "authority_effect": "candidate_or_measurement_only",
            })
        graph = {"notes": units, "decks": decks, "note_types": note_types}
        if review_limit:
            graph["source_review_history"] = _anki_review_history(connection, review_limit)
        return graph
    finally:
        connection.close()


def _compare_anki_names(left, right):
    a, b = left.casefold(), right.casefold()
    return (a > b) - (a < b)


def _anki_review_history(connection, limit):
    """Project native revlog values without creating AAOS reviews or changing their units."""
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='revlog'").fetchone():
        return {"origin": "imported_from_source", "available": False, "total": None, "events": []}
    source = " FROM revlog r JOIN cards c ON c.id=r.cid"
    total = connection.execute("SELECT count(*)" + source).fetchone()[0]
    columns = ("id", "cid", "ease", "ivl", "lastIvl", "factor", "time", "type")
    rows = connection.execute("SELECT r.id,r.cid,r.ease,r.ivl,r.lastIvl,r.factor,r.time,r.type" +
                              source + " ORDER BY r.id DESC LIMIT ?", (limit,))
    return {"origin": "imported_from_source", "available": True, "total": total,
            "events": [dict(zip(columns, row, strict=True)) for row in rows]}


def _anki_catalog(connection):
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='notetypes'").fetchone():
        models = {mid: {"name": name, "fields": {}, "templates": {}}
                  for mid, name in connection.execute("SELECT id, name FROM notetypes")}
        for table in ("fields", "templates"):
            # Native deck exports may retain field/template rows of types excluded
            # from the selected deck. Only resolve metadata for included types.
            for mid, ordinal, name in connection.execute(
                f"SELECT t.ntid, t.ord, t.name FROM {table} t JOIN notetypes n ON n.id=t.ntid"
            ):
                models[mid][table][ordinal] = name
        decks = {did: name.replace(ANKI_FIELD_SEPARATOR, "::")
                 for did, name in connection.execute("SELECT id, name FROM decks")}
        return models, decks
    model_json, deck_json = connection.execute("SELECT models, decks FROM col").fetchone()
    models = {}
    for mid, model in json.loads(model_json or "{}").items():
        models[int(mid)] = {"name": model["name"],
                            "fields": {row["ord"]: row["name"] for row in model.get("flds", [])},
                            "templates": {row["ord"]: row["name"] for row in model.get("tmpls", [])}}
    decks = {int(did): deck["name"] for did, deck in json.loads(deck_json or "{}").items()}
    return models, decks


class ImportSession:
    """Scan and import a vault under an approved root into a compat ledger."""

    def __init__(self, store: Path, vault_root: Path) -> None:
        from shared.approved_paths import ApprovedRoots
        from shared.paths import native_path

        self.store = store
        self.vault_root = vault_root.resolve()
        if not Path(native_path(self.vault_root)).is_dir():
            raise ValueError(f"vault root is not a directory: {vault_root}")
        self.approved = ApprovedRoots(source_roots=[self.vault_root])
        self._conn = sqlite3.connect(native_path(store))
        self._conn.execute(_SCHEMA)
        columns = {
            row[1] for row in self._conn.execute("PRAGMA table_info(compat_files)")
        }
        if "is_binary" not in columns:
            self._conn.execute(
                "ALTER TABLE compat_files ADD COLUMN is_binary INTEGER NOT NULL DEFAULT 0"
            )
        if "mime_type" not in columns:
            self._conn.execute("ALTER TABLE compat_files ADD COLUMN mime_type TEXT")
        # The kernel reads a source's files and nothing about who could see them, what comments
        # they carried, or what revision history came with them. That boundary is written down as
        # declared absence rather than left blank, so an unrecorded exposure cannot later be read
        # as a clean one. A column default carries it, so no insert has to remember to say so.
        if "source_context" not in columns:
            self._conn.execute(
                "ALTER TABLE compat_files ADD COLUMN source_context TEXT NOT NULL "
                "DEFAULT 'acl,comments,history:not_recorded'"
            )
        self._conn.commit()
        self._losses: list[dict[str, object]] = []

    def _scan_paths(self) -> list[Path]:
        """Enumerate files under the vault, rejecting symlink escapes."""
        from shared.approved_paths import ApprovedRootsError
        from shared.paths import native_path, ordinary_path

        results: list[Path] = []
        for root_name, dirs, files in os.walk(native_path(self.vault_root), topdown=True, followlinks=False):
            # The walk is prefixed so deep directories yield at all; containment and the
            # returned records keep the plain path.
            root = ordinary_path(root_name)
            # drop symlink dirs that escape the approved root
            kept: list[str] = []
            for d in dirs:
                candidate = (root / d).resolve()
                try:
                    self.approved.resolve_source(candidate)
                    kept.append(d)
                except ApprovedRootsError:
                    raise ApprovedRootsError(
                        f"vault traversal escaped approved root: {(root / d).as_posix()}"
                    ) from None
            dirs[:] = kept
            for f in files:
                results.append(root / f)
        return results

    def import_path(self, path: Path) -> VaultFile:
        """Import a single path, rejecting escapes."""
        from shared.compat.models import VaultFile

        resolved = self.approved.resolve_source(path)
        return VaultFile.from_path(resolved, vault=self.vault_root)

    def scan(self) -> list[VaultFile]:
        """Scan the vault, importing every file idempotently."""
        return [self.import_path(p) for p in self._scan_paths()]

    def run(self) -> int:
        """Run a full import, persisting the compatibility ledger."""
        files = self.scan()
        now = _now()
        for vf in files:
            # idempotent upsert keyed on relative path
            self._conn.execute(
                "INSERT INTO compat_files (relative_path, source_hash, file_size,"
                " frontmatter_json, body_hash, is_canvas, is_binary, mime_type, imported_at) VALUES (?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(relative_path) DO UPDATE SET source_hash=excluded.source_hash,"
                " file_size=excluded.file_size, frontmatter_json=excluded.frontmatter_json,"
                " body_hash=excluded.body_hash, is_canvas=excluded.is_canvas,"
                " is_binary=excluded.is_binary, mime_type=excluded.mime_type,"
                " imported_at=excluded.imported_at",
                (
                    vf.relative_path,
                    vf.source_hash,
                    vf.file_size,
                    _json(vf.frontmatter),
                    _sha256(vf.body),
                    1 if vf.is_canvas else 0,
                    1 if vf.is_binary else 0,
                    vf.mime_type,
                    now,
                ),
            )
        self._conn.commit()
        return len(files)

    def file_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM compat_files").fetchone()[0]

    def loss_report(self) -> list[dict[str, object]]:
        return list(self._losses)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _json(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)
