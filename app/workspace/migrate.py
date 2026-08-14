"""AXW-DATA-403 — legacy single-database migration.

Moves data out of the legacy monolithic ``cognitive_os.sqlite`` into the
four-asset-domain workspace layout defined by the workspace manifest
(AXW-DATA-401), without ever deleting the legacy database — it is kept
as a historical asset (task-pack rule).

Pipeline (fail-safe order, per docs/design/AXW-DATA-403-migration.md):

1. ``backup`` — consistent snapshot via ``VACUUM INTO`` into ``backups/``
   with a timestamped name. A missing source is skipped (ok); a backup
   that already exists for the same source hash is not re-created.
2. ``dry_run`` — read-only migration plan: table list, row counts, target
   paths. Never writes.
3. ``migrate`` — executes the plan: relational tables are copied into the
   evidence-ledger ``ledger.sqlite``, BLOB rows become hash-named files in
   the source archive, text rows become Markdown files in the learning
   vault, AI-asset rows become JSON files in the AI vault. A migration
   manifest records every disposition. Idempotent: a second call for the
   same source hash returns the recorded result without re-backing-up.
4. ``rollback_readback`` — opens a backup, verifies integrity and the
   source hash, and returns the backup file itself as the restore
   candidate. Current state is never overwritten.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from shared.workspace_manifest import create_workspace
from shared.workspace_manifest import load as load_manifest

LEDGER_DB_NAME = "ledger.sqlite"
MIGRATION_MANIFEST_NAME = "migration-manifest.json"
MIGRATION_MANIFEST_VERSION = "1.0"
BACKUP_PREFIX = "cognitive_os.pre-"
BACKUP_SUFFIX = ".sqlite"

# Table-name prefixes routed to each asset domain.
_VAULT_PREFIXES = (
    "note",
    "markdown",
    "canvas",
    "lesson",
    "daily",
    "vault",
    "kb_doc",
    "doc",
)
_AI_PREFIXES = ("memory", "rule", "skill", "agent", "tool")
_FILE_TABLE_NAMES = ("attachments", "raw_assets", "media", "blobs", "files")


# ── low-level helpers ───────────────────────────────────────────────────


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def content_hash(path: str | Path) -> str:
    """Logical content hash of a SQLite database.

    ``VACUUM INTO`` snapshots have different raw bytes than the source
    file, so byte-level hashes cannot verify a backup. This hash covers
    the logical content instead: every table (sorted) and every row in
    rowid order, with bytes and text tagged distinctly — it is stable
    across VACUUM and detects any data change.
    """
    hasher = hashlib.sha256()
    database = Path(path)
    with _connect(database, readonly=True) as connection:
        for name in _list_tables(connection):
            hasher.update(b"table\0")
            hasher.update(name.encode("utf-8"))
            quoted = _quote_ident(name)
            for row in connection.execute(f"SELECT * FROM {quoted} ORDER BY rowid"):
                for value in row:
                    if isinstance(value, bytes):
                        hasher.update(b"b")
                        hasher.update(value)
                    else:
                        hasher.update(b"s")
                        hasher.update(repr(value).encode("utf-8"))
    return hasher.hexdigest()


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    raw = str(path)
    # SQLite's file: URI parser cannot express the \\?\ extended-path prefix
    # (invalid uri authority). Extended paths connect natively on Windows;
    # keep the URI readonly mode for plain paths only.
    is_extended = raw.startswith("\\\\?\\")
    if readonly and not is_extended:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=30.0)
    else:
        connection = sqlite3.connect(raw, timeout=30.0)
    connection.execute("PRAGMA busy_timeout=30000")
    return connection


def _list_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(row[0]) for row in rows]


def _row_counts(connection: sqlite3.Connection, tables: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in tables:
        row = connection.execute(f"SELECT COUNT(*) FROM {_quote_ident(name)}").fetchone()
        counts[name] = int(row[0]) if row else 0
    return counts


def _table_columns(connection: sqlite3.Connection, name: str) -> list[tuple[str, str]]:
    rows = connection.execute(f"PRAGMA table_info({_quote_ident(name)})").fetchall()
    return [(str(row[1]), str(row[2])) for row in rows]


def _classify_table(name: str, column_types: list[str]) -> str:
    """Map a legacy table to one of ``files | vault | ai | ledger``."""
    lowered = name.casefold()
    if lowered in _FILE_TABLE_NAMES or lowered.startswith(
        ("attachment", "raw_asset", "blob")
    ):
        return "files"
    if any("blob" in ctype.casefold() for ctype in column_types):
        return "files"
    if lowered.startswith(_VAULT_PREFIXES):
        return "vault"
    if lowered.startswith(_AI_PREFIXES):
        return "ai"
    return "ledger"


def _workspace_manifest(workspace_root: str | Path):
    """Load the workspace manifest, creating the workspace when absent."""
    root = Path(workspace_root)
    marker = root / "manifest.json"
    if marker.is_file():
        return load_manifest(marker)
    return create_workspace(root.parent, root.name)


def _find_backup_for_hash(backup_dir: Path, digest: str) -> Path | None:
    if not backup_dir.is_dir():
        return None
    for candidate in sorted(backup_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}")):
        if f"-{digest[:8]}{BACKUP_SUFFIX}" in candidate.name:
            return candidate
    return None


# ── step 1: backup ──────────────────────────────────────────────────────


def backup(
    db_path: str | Path,
    backup_dir: str | Path,
    *,
    source_hash_value: str | None = None,
) -> dict[str, object]:
    """Consistent snapshot of the legacy database via ``VACUUM INTO``.

    A missing source is skipped (ok). Backing up the same source twice
    never creates a second file — the existing backup is returned.
    """
    source = Path(db_path)
    target_dir = Path(backup_dir)
    if not source.is_file():
        return {
            "status": "ok",
            "skipped": True,
            "reason": "legacy database not present",
            "backup_path": None,
            "source_hash": None,
        }
    digest = source_hash_value or content_hash(source)
    target_dir.mkdir(parents=True, exist_ok=True)
    existing = _find_backup_for_hash(target_dir, digest)
    if existing is not None:
        return {
            "status": "ok",
            "skipped": True,
            "reason": "backup already exists for this source",
            "backup_path": str(existing),
            "source_hash": digest,
            "created": False,
        }
    target = target_dir / f"{BACKUP_PREFIX}{_utc_stamp()}-{digest[:8]}{BACKUP_SUFFIX}"
    escaped = str(target).replace("'", "''")
    with _connect(source) as connection:
        connection.execute(f"VACUUM INTO '{escaped}'")
    return {
        "status": "ok",
        "skipped": False,
        "reason": "",
        "backup_path": str(target),
        "source_hash": digest,
        "created": True,
    }


# ── step 2: dry-run ─────────────────────────────────────────────────────


def _target_dir(manifest, domain_key: str) -> Path:
    domain = manifest.domains[domain_key]
    return Path(domain.path)


def _plan(db_path: Path, manifest) -> dict[str, object]:
    with _connect(db_path, readonly=True) as connection:
        tables = _list_tables(connection)
        counts = _row_counts(connection, tables)
        table_plan: list[dict[str, object]] = []
        for name in tables:
            column_types = [ctype for _, ctype in _table_columns(connection, name)]
            kind = _classify_table(name, column_types)
            domain_key = {
                "files": "source_archive",
                "vault": "human_learning_vault",
                "ai": "ai_asset_vault",
                "ledger": "evidence_ledger",
            }[kind]
            table_plan.append(
                {
                    "name": name,
                    "rows": counts[name],
                    "kind": kind,
                    "domain": domain_key,
                    "target": str(_target_dir(manifest, domain_key)),
                }
            )
    return {
        "source": str(db_path),
        "source_hash": content_hash(db_path),
        "tables": table_plan,
        "targets": {
            domain_key: str(_target_dir(manifest, domain_key))
            for domain_key in ("source_archive", "evidence_ledger", "human_learning_vault", "ai_asset_vault")
        },
    }


def dry_run(db_path: str | Path, workspace_root: str | Path) -> dict[str, object]:
    """Read-only migration plan (table list / row counts / target paths)."""
    source = Path(db_path)
    if not source.is_file():
        return {
            "status": "ok",
            "skipped": True,
            "reason": "legacy database not present",
            "plan": None,
        }
    manifest = _workspace_manifest(workspace_root)
    return {"status": "ok", "skipped": False, "plan": _plan(source, manifest)}


# ── step 3: migrate ─────────────────────────────────────────────────────


def _copy_table_to_ledger(
    source: sqlite3.Connection,
    ledger: sqlite3.Connection,
    name: str,
) -> dict[str, object]:
    row = source.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    schema_sql = str(row[0]) if row and row[0] else ""
    if not schema_sql or schema_sql.lstrip().upper().startswith("CREATE VIRTUAL TABLE"):
        return {"name": name, "disposition": "skipped", "reason": "virtual table or missing schema"}
    ledger.execute(schema_sql)
    columns = [column for column, _ in _table_columns(source, name)]
    column_list = ", ".join(_quote_ident(column) for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    rows = source.execute(f"SELECT {column_list} FROM {_quote_ident(name)}").fetchall()
    ledger.executemany(
        f"INSERT INTO {_quote_ident(name)} ({column_list}) VALUES ({placeholders})",
        rows,
    )
    return {"name": name, "disposition": "copied", "rows": len(rows)}


def _extract_blob_rows(
    source: sqlite3.Connection,
    domain_dir: Path,
    name: str,
    column_types: list[tuple[str, str]],
) -> list[dict[str, object]]:
    blob_index = next(
        (index for index, (_, ctype) in enumerate(column_types) if "blob" in ctype.casefold()),
        None,
    )
    entries: list[dict[str, object]] = []
    if blob_index is None:
        return entries
    quoted = _quote_ident(name)
    for row in source.execute(f"SELECT * FROM {quoted}").fetchall():
        payload = row[blob_index]
        if payload is None:
            continue
        digest = hashlib.sha256(payload).hexdigest()
        relative = f"{name}/{digest}.bin"
        target = domain_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        entries.append(
            {
                "table": name,
                "row_id": str(row[0]),
                "file": relative,
                "sha256": digest,
                "size": len(payload),
            }
        )
    return entries


def _write_text_rows(
    source: sqlite3.Connection,
    domain_dir: Path,
    name: str,
    column_types: list[tuple[str, str]],
    suffix: str,
) -> list[dict[str, object]]:
    text_columns = [
        (index, ctype)
        for index, (column, ctype) in enumerate(column_types)
        if index > 0 and ctype.upper() in ("TEXT", "VARCHAR", "CLOB")
    ]
    # Prefer a body-ish column (content/body/text/markdown/payload) over
    # metadata columns such as title/name; fall back to the last TEXT
    # column so the file still carries the row's primary payload.
    preferred = [
        index
        for index, (column, _) in enumerate(column_types)
        if index > 0 and column.casefold() in {"content", "body", "text", "markdown", "payload"}
    ]
    text_index = next(
        (index for index in preferred if any(index == tindex for tindex, _ in text_columns)),
        None,
    )
    if text_index is None and text_columns:
        text_index = text_columns[-1][0]
    entries: list[dict[str, object]] = []
    quoted = _quote_ident(name)
    for row in source.execute(f"SELECT * FROM {quoted}").fetchall():
        rid = str(row[0])
        content = str(row[text_index]) if text_index is not None else json.dumps(list(row))
        relative = f"{name}/{rid}{suffix}"
        target = domain_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        entries.append({"table": name, "row_id": rid, "file": relative, "chars": len(content)})
    return entries


def _write_json_rows(
    source: sqlite3.Connection,
    domain_dir: Path,
    name: str,
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    quoted = _quote_ident(name)
    columns = [column for column, _ in _table_columns(source, name)]
    for row in source.execute(f"SELECT * FROM {quoted}").fetchall():
        rid = str(row[0])
        payload = {
            column: (value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value)
            for column, value in zip(columns, row, strict=True)
        }
        relative = f"{name}/{rid}.json"
        target = domain_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        entries.append({"table": name, "row_id": rid, "file": relative})
    return entries


def migrate(
    db_path: str | Path,
    workspace_root: str | Path,
    *,
    backup_dir: str | Path | None = None,
) -> dict[str, object]:
    """Backup → plan → move data into the four-asset-domain layout.

    The legacy database is never deleted. Idempotent: a migration whose
    manifest already records the current source hash returns the recorded
    result without creating another backup.
    """
    source = Path(db_path)
    if not source.is_file():
        return {
            "status": "ok",
            "skipped": True,
            "reason": "legacy database not present",
        }
    root = Path(workspace_root)
    manifest = _workspace_manifest(root)
    digest = content_hash(source)

    marker_path = root / MIGRATION_MANIFEST_NAME
    if marker_path.is_file():
        try:
            previous = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
        if previous.get("source_hash") == digest:
            return {
                "status": "ok",
                "already_migrated": True,
                "source_hash": digest,
                "backup_path": previous.get("backup_path"),
                "migration_manifest": str(marker_path),
            }

    backups = Path(backup_dir) if backup_dir is not None else Path(str(manifest.backup.location))
    backup_result = backup(source, backups, source_hash_value=digest)
    plan = _plan(source, manifest)

    ledger_path = _target_dir(manifest, "evidence_ledger") / LEDGER_DB_NAME
    source_archive = _target_dir(manifest, "source_archive")
    learning_vault = _target_dir(manifest, "human_learning_vault")
    ai_vault = _target_dir(manifest, "ai_asset_vault")

    copied: list[dict[str, object]] = []
    files: list[dict[str, object]] = []
    with _connect(source) as src, _connect(ledger_path) as ledger:
        for entry in plan["tables"]:
            name = str(entry["name"])
            kind = str(entry["kind"])
            if kind == "ledger":
                copied.append(_copy_table_to_ledger(src, ledger, name))
            elif kind == "files":
                files.extend(
                    _extract_blob_rows(src, source_archive, name, _table_columns(src, name))
                )
            elif kind == "vault":
                files.extend(
                    _write_text_rows(
                        src, learning_vault, name, _table_columns(src, name), ".md"
                    )
                )
            elif kind == "ai":
                files.extend(_write_json_rows(src, ai_vault, name))
        ledger.commit()

    result: dict[str, object] = {
        "schema_version": MIGRATION_MANIFEST_VERSION,
        "migrated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(source),
        "source_hash": digest,
        "backup_path": backup_result.get("backup_path"),
        "tables": plan["tables"],
        "copied": copied,
        "files": files,
        "targets": plan["targets"],
        "legacy_db_kept": source.is_file(),
    }
    marker_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    result["migration_manifest"] = str(marker_path)
    return {"status": "ok", "already_migrated": False, **result}


# ── step 4: rollback readback ───────────────────────────────────────────


def rollback_readback(
    backup_path: str | Path,
    expected_source_hash: str | None = None,
) -> dict[str, object]:
    """Verify a backup produced by ``backup()`` and expose the restore
    candidate. The restore target is the backup file itself; the current
    workspace state is never overwritten."""
    backup_file = Path(backup_path)
    if not backup_file.is_file():
        return {
            "status": "error",
            "reason": f"backup file not found: {backup_file}",
        }
    actual_hash = content_hash(backup_file)
    try:
        with _connect(backup_file, readonly=True) as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    except sqlite3.Error as exc:
        return {"status": "error", "reason": f"backup is not a readable SQLite file: {exc}"}
    hash_matches = expected_source_hash is None or actual_hash == expected_source_hash
    return {
        "status": "ok",
        "backup_path": str(backup_file),
        "integrity": integrity,
        "source_hash": actual_hash,
        "file_sha256": _sha256_file(backup_file),
        "expected_source_hash": expected_source_hash,
        "hash_matches": hash_matches,
        "restore_candidate": str(backup_file),
        "restore_note": (
            "restore by copying the backup file over the legacy path; "
            "current workspace state is never overwritten"
        ),
    }


def list_backups(backup_dir: str | Path) -> list[str]:
    """Timestamped backup files, newest first (read-only helper)."""
    directory = Path(backup_dir)
    if not directory.is_dir():
        return []
    return sorted(
        (str(path) for path in directory.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}")),
        reverse=True,
    )


__all__ = [
    "BACKUP_PREFIX",
    "BACKUP_SUFFIX",
    "LEDGER_DB_NAME",
    "MIGRATION_MANIFEST_NAME",
    "MIGRATION_MANIFEST_VERSION",
    "backup",
    "dry_run",
    "list_backups",
    "migrate",
    "rollback_readback",
]
