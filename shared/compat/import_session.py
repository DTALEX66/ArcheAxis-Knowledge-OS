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

from shared.approved_paths import ApprovedRoots, ApprovedRootsError
from shared.compat.models import VaultFile
from shared.paths import native_path, ordinary_path

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
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as container:
            if "collection.anki2" not in set(container.namelist()):
                raise ValueError("package carries no collection.anki2")
            raw = container.read("collection.anki2")
    except zipfile.BadZipFile as error:
        raise ValueError(f"unreadable package: {error}") from error

    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(raw)
        note_types = _anki_note_type_names(connection)
        cards: dict[object, list[dict[str, object]]] = {}
        for row in connection.execute(
            "SELECT id, nid, ord, type, queue, due, ivl, factor, reps, lapses FROM cards"
        ):
            card_id, note_id, ordinal, type_, queue, due, ivl, factor, reps, lapses = row
            answered = reps > 0
            cards.setdefault(note_id, []).append({
                "card_id": card_id,
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
        for note_id, mid, flds, tags in connection.execute(
            "SELECT id, mid, flds, tags FROM notes"
        ):
            units.append({
                "note_id": note_id,
                "note_type": note_types.get(mid, f"unknown({mid})"),
                "fields": flds.split(ANKI_FIELD_SEPARATOR),
                "tags": [tag for tag in str(tags).split() if tag],
                "cards": cards.get(note_id, []),
                "scheduling_origin": "imported_from_source",
                "authority_effect": "candidate_or_measurement_only",
                # What the collection holds that this reader does not carry, declared so an
                # imported unit cannot be read as the whole of what the source knew.
                "not_carried": [
                    "deck_options: the learning steps, intervals and ease the collection scheduled with",
                    "deck_names: the deck an item belonged to",
                ],
            })
        return units
    finally:
        connection.close()


def _anki_note_type_names(connection: sqlite3.Connection) -> dict[int, str]:
    """Anki keeps its note types as JSON in col.models, keyed by a stringified id."""
    try:
        row = connection.execute("SELECT models FROM col").fetchone()
        models = json.loads(row[0]) if row else {}
    except (sqlite3.Error, ValueError, TypeError):
        return {}
    names: dict[int, str] = {}
    for key, model in models.items():
        try:
            names[int(key)] = str(model.get("name", key))
        except (TypeError, ValueError):
            continue
    return names


class ImportSession:
    """Scan and import a vault under an approved root into a compat ledger."""

    def __init__(self, store: Path, vault_root: Path) -> None:
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
