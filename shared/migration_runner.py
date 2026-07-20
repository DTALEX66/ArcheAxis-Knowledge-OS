"""Unified registry and operator boundary for database and shadow-index migrations."""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import sqlite3
from contextlib import closing, contextmanager, suppress
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from shared import core_schema, migration

_OPERATOR_TABLE = "migration_operator_runs"
_OPERATOR_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_OPERATOR_TABLE} (
    run_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    version INTEGER NOT NULL,
    target TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('applied', 'failed', 'rolled_back')),
    operation TEXT NOT NULL CHECK(operation IN ('apply', 'rollback')),
    provenance_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL
)
"""


_LOCK_TABLE = "migration_operator_locks"
_LOCK_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_LOCK_TABLE} (
    owner TEXT PRIMARY KEY,
    token TEXT NOT NULL,
    acquired_at TEXT NOT NULL
)
"""

_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHADOW_SUFFIX_RE = re.compile(r"^[0-9a-f]{32}$")
_VECTOR_DIM = 384


@dataclass(frozen=True)
class MigrationOwner:
    """Stable identity for one code-owned migration lifecycle."""

    owner: str
    version: int
    target: str
    kind: str

    @property
    def identity(self) -> tuple[str, int, str]:
        return (self.owner, self.version, self.target)


class MigrationRegistry:
    """Deterministic, fail-closed collection of migration owners."""

    def __init__(self, owners: list[MigrationOwner] | tuple[MigrationOwner, ...]) -> None:
        ordered = sorted(owners, key=lambda item: item.identity)
        identities: set[tuple[str, int, str]] = set()
        names: set[str] = set()
        targets: set[str] = set()
        for owner in ordered:
            if owner.identity in identities:
                raise ValueError(f"duplicate migration owner identity: {owner.identity!r}")
            if owner.owner in names:
                raise ValueError(f"duplicate migration owner name: {owner.owner!r}")
            if owner.target in targets:
                raise ValueError(f"duplicate migration target ownership: {owner.target!r}")
            if owner.version < 1 or not owner.owner or not owner.target:
                raise ValueError("migration owner identity must be non-empty and versioned")
            identities.add(owner.identity)
            names.add(owner.owner)
            targets.add(owner.target)
        self._owners = tuple(ordered)
        self._by_name = {owner.owner: owner for owner in ordered}

    @property
    def owners(self) -> tuple[MigrationOwner, ...]:
        return self._owners

    def get(self, name: str) -> MigrationOwner:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise ValueError(f"unknown migration owner: {name}") from exc


def default_registry(_db_path: str | Path = migration.DB_PATH) -> MigrationRegistry:
    """Return the production owner registry in deterministic identity order."""

    return MigrationRegistry(
        [
            MigrationOwner(
                core_schema.BASELINE_OWNER,
                core_schema.BASELINE_VERSION,
                core_schema.BASELINE_TARGET,
                "sqlite_core",
            ),
            MigrationOwner("taskpack.sqlite", 3, "kb_taskpacks", "sqlite"),
            MigrationOwner("vector.documents", 1, "vec_kb_documents", "vector"),
            MigrationOwner("vector.cards", 1, "vec_kb_cards", "vector"),
            MigrationOwner("fts.documents", 1, "kb_documents_fts", "fts"),
            MigrationOwner("fts.cards", 1, "kb_cards_fts", "fts"),
            MigrationOwner("research.sqlite", 1, "research_packages_v1", "sqlite_research"),
            MigrationOwner(
                "knowledge-governance.sqlite",
                1,
                "knowledge_candidate_promotions_v1",
                "sqlite_knowledge",
            ),
        ]
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _canonical_sql_value(value: Any) -> tuple[str, Any]:
    if value is None:
        return ("null", None)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return ("blob", bytes(value).hex())
    if isinstance(value, float):
        return ("float", repr(value))
    if isinstance(value, int):
        return ("integer", value)
    return ("text", str(value))


def require_sqlite_owners_applied(
    connection: sqlite3.Connection,
    registry: MigrationRegistry | None = None,
) -> None:
    """Require current applied provenance for every SQLite schema owner, read-only."""
    owners = tuple(
        owner for owner in (registry or default_registry()).owners if owner.kind.startswith("sqlite")
    )
    if not migration._table_exists(connection, _OPERATOR_TABLE):
        raise RuntimeError("SQLite operator provenance is missing")
    missing: list[str] = []
    for owner in owners:
        row = connection.execute(
            f"SELECT state FROM {_OPERATOR_TABLE} "
            "WHERE owner=? AND version=? AND target=? "
            "ORDER BY rowid DESC LIMIT 1",
            owner.identity,
        ).fetchone()
        if row is None or str(row[0]) != "applied":
            missing.append(owner.owner)
    if missing:
        raise RuntimeError(
            "SQLite operator provenance is not applied for: " + ", ".join(sorted(missing))
        )


class MigrationOperator:
    """Apply, inspect and roll back registered owners against one explicit database."""

    def __init__(
        self,
        *,
        db_path: str | Path = migration.DB_PATH,
        backup_dir: str | Path = migration.BACKUP_DIR,
        registry: MigrationRegistry | None = None,
    ) -> None:
        self.db_path = Path(db_path).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.registry = registry or default_registry(self.db_path)
        self._lock_database = self._lock_database_for_target(self.db_path)
        if not self.db_path.is_file():
            raise FileNotFoundError(f"SQLite database not found: {self.db_path}")
        with closing(self._connect_readonly()) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise RuntimeError(f"SQLite integrity check failed for {self.db_path}: {result}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path), timeout=30.0)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.row_factory = sqlite3.Row
        return connection

    def _connect_readonly(self) -> sqlite3.Connection:
        sidecars = [Path(f"{self.db_path}{suffix}") for suffix in ("-wal", "-shm")]
        present = [sidecar.name for sidecar in sidecars if sidecar.exists()]
        if present:
            raise RuntimeError(
                "read-only migration status requires a checkpointed database without "
                f"SQLite sidecars: {', '.join(present)}"
            )
        uri = f"{self.db_path.as_uri()}?mode=ro&immutable=1"
        connection = sqlite3.connect(uri, uri=True, timeout=30.0)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA query_only=ON")
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _lock_database_for_target(database: Path) -> Path:
        resolved = database.resolve()
        identity = str(resolved).casefold()
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        return resolved.with_name(f".{resolved.name}.{digest}.migration_operator_locks.lockdb")

    def _lock_connect(self) -> sqlite3.Connection:
        self._lock_database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self._lock_database), timeout=30.0)
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    @staticmethod
    def _database_fingerprint(connection: sqlite3.Connection) -> str:
        """Hash all non-operator schema and rows independent of SQLite page layout."""
        excluded = {_OPERATOR_TABLE, _LOCK_TABLE}
        objects = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        payload: list[Any] = []
        for item in objects:
            name = str(item["name"])
            if name in excluded:
                continue
            payload.append([str(item["type"]), name, str(item["tbl_name"]), str(item["sql"] or "")])
            if str(item["type"]) != "table":
                continue
            quoted_name = name.replace('"', '""')
            rows = connection.execute(f'SELECT * FROM "{quoted_name}"').fetchall()
            canonical_rows = sorted(
                json.dumps(
                    [_canonical_sql_value(value) for value in tuple(row)],
                    ensure_ascii=True,
                    separators=(",", ":"),
                )
                for row in rows
            )
            payload.append([name, canonical_rows])
        encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _failure_provenance(exc: Exception, operation: str) -> dict[str, str]:
        return {
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "operation": operation,
        }

    @staticmethod
    def _fts_source(owner: MigrationOwner) -> str:
        if owner.owner.endswith("documents"):
            return "kb_documents"
        if owner.owner.endswith("cards"):
            return "kb_cards"
        raise RuntimeError(f"unknown FTS owner source: {owner.owner}")

    def _fts_spec(self, owner: MigrationOwner) -> tuple[str, str, tuple[str, ...]]:
        from shared.fts_index import fts_source_spec

        active_table, create_sql, columns, _source_columns = fts_source_spec(
            self._fts_source(owner)
        )
        if active_table != owner.target:
            raise RuntimeError(f"FTS owner target mismatch: {owner.owner}")
        return active_table, create_sql, columns

    @staticmethod
    def _validate_shadow_name(name: object, prefix: str) -> str:
        value = str(name)
        suffix = value[len(prefix) :] if value.startswith(prefix) else ""
        if (
            not _SQL_IDENTIFIER_RE.fullmatch(value)
            or not value.startswith(prefix)
            or not _SHADOW_SUFFIX_RE.fullmatch(suffix)
        ):
            raise RuntimeError("rollback provenance does not match migration owner")
        return value

    def _active_index_fingerprint(
        self, owner: MigrationOwner, connection: sqlite3.Connection
    ) -> dict[str, object]:
        if owner.kind == "fts":
            from shared.fts_index import fts_index_fingerprint

            _active_table, _create_sql, columns = self._fts_spec(owner)
            return fts_index_fingerprint(connection, owner.target, columns)
        if owner.kind == "vector":
            from app.memory.vector_db import VectorDB

            return VectorDB(
                table_name=owner.target,
                dim=_VECTOR_DIM,
                db_path=self.db_path,
            ).fingerprint(connection=connection)
        raise RuntimeError(f"owner has no active index fingerprint: {owner.owner}")

    def _snapshot_operator_runs(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (_OPERATOR_TABLE,),
            ).fetchone()
            if exists is None:
                return []
            return [
                {"rowid": int(row["sequence"]), **dict(row)}
                for row in connection.execute(
                    f"SELECT rowid AS sequence, * FROM {_OPERATOR_TABLE} ORDER BY rowid"
                ).fetchall()
            ]

    @staticmethod
    def _restore_operator_runs_in_connection(
        connection: sqlite3.Connection, runs: list[dict[str, Any]]
    ) -> None:
        connection.execute(_OPERATOR_TABLE_SQL)
        connection.execute(f"DELETE FROM {_OPERATOR_TABLE}")
        for run in runs:
            connection.execute(
                f"INSERT INTO {_OPERATOR_TABLE}("
                "rowid, run_id, owner, version, target, state, operation, "
                "provenance_json, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run["rowid"],
                    run["run_id"],
                    run["owner"],
                    run["version"],
                    run["target"],
                    run["state"],
                    run["operation"],
                    run["provenance_json"],
                    run["recorded_at"],
                ),
            )

    @staticmethod
    def _restore_operator_runs(database: Path, runs: list[dict[str, Any]]) -> None:
        with closing(sqlite3.connect(str(database))) as connection:
            connection.execute("BEGIN IMMEDIATE")
            MigrationOperator._restore_operator_runs_in_connection(connection, runs)
            connection.commit()

    def _latest(self, owner: MigrationOwner) -> dict[str, Any] | None:
        return self._latest_with_state(owner)

    def _latest_with_state(
        self,
        owner: MigrationOwner,
        state: str | None = None,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any] | None:
        if connection is None:
            connection_context = closing(self._connect_readonly())
        else:
            connection_context = contextlib.nullcontext(connection)
        with connection_context as connection:
            if not migration._table_exists(connection, _OPERATOR_TABLE):
                return None
            state_clause = " AND state=?" if state is not None else ""
            parameters: tuple[Any, ...] = owner.identity + ((state,) if state is not None else ())
            row = connection.execute(
                f"SELECT run_id, state, operation, provenance_json, recorded_at "
                f"FROM {_OPERATOR_TABLE} "
                f"WHERE owner=? AND version=? AND target=?{state_clause} "
                "ORDER BY recorded_at DESC, run_id DESC LIMIT 1",
                parameters,
            ).fetchone()
        if row is None:
            return None
        return {
            "run_id": str(row["run_id"]),
            "state": str(row["state"]),
            "operation": str(row["operation"]),
            "provenance": json.loads(str(row["provenance_json"])),
            "recorded_at": str(row["recorded_at"]),
        }

    def _insert_record(
        self,
        connection: sqlite3.Connection,
        owner: MigrationOwner,
        *,
        state: str,
        operation: str,
        provenance: dict[str, Any],
        run_id: str | None = None,
    ) -> dict[str, Any]:
        recorded_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "database": str(self.db_path),
            "owner": owner.owner,
            "version": owner.version,
            "target": owner.target,
            **provenance,
        }
        connection.execute(_OPERATOR_TABLE_SQL)
        connection.execute(
            f"INSERT INTO {_OPERATOR_TABLE}("
            "run_id, owner, version, target, state, operation, provenance_json, recorded_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id or uuid4().hex,
                owner.owner,
                owner.version,
                owner.target,
                state,
                operation,
                json.dumps(_json_safe(payload), ensure_ascii=True, sort_keys=True),
                recorded_at,
            ),
        )
        return self._item(owner, state, payload, operation=operation, recorded_at=recorded_at)

    def _record(
        self,
        owner: MigrationOwner,
        *,
        state: str,
        operation: str,
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            item = self._insert_record(
                connection,
                owner,
                state=state,
                operation=operation,
                provenance=provenance,
            )
            connection.commit()
        return item

    @contextmanager
    def _owner_guard(self, owner: MigrationOwner):
        """Acquire a cross-process owner lease before inspecting or switching state."""
        token = uuid4().hex
        with closing(self._lock_connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(_LOCK_TABLE_SQL)
                connection.execute(
                    f"INSERT INTO {_LOCK_TABLE}(owner, token, acquired_at) VALUES (?, ?, ?)",
                    (owner.owner, token, datetime.now(timezone.utc).isoformat()),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise RuntimeError(f"migration owner is busy: {owner.owner}") from exc
        try:
            yield
        finally:
            with closing(self._lock_connect()) as connection:
                connection.execute(
                    f"DELETE FROM {_LOCK_TABLE} WHERE owner=? AND token=?",
                    (owner.owner, token),
                )
                connection.commit()

    @staticmethod
    def _item(
        owner: MigrationOwner,
        state: str,
        provenance: dict[str, Any],
        *,
        operation: str | None = None,
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "owner": owner.owner,
            "version": owner.version,
            "target": owner.target,
            "kind": owner.kind,
            "state": state,
            "provenance": provenance,
        }
        if operation is not None:
            item["operation"] = operation
        if recorded_at is not None:
            item["recorded_at"] = recorded_at
        return item

    def status(self) -> list[dict[str, Any]]:
        """Return all owner states without creating tables or changing the database."""

        result: list[dict[str, Any]] = []
        with closing(self._connect_readonly()) as conn:
            for owner in self.registry.owners:
                latest = self._latest_with_state(owner, connection=conn)
                if latest is not None:
                    if latest["state"] == "applied" and owner.kind in {
                        "sqlite",
                        "sqlite_research",
                        "sqlite_core",
                    }:
                        try:
                            if owner.kind == "sqlite_core":
                                with closing(self._connect_readonly()) as connection:
                                    core_schema.validate(connection)
                                live = {"pending": []}
                            else:
                                live = (
                                    migration.status(db_path=self.db_path)
                                    if owner.kind == "sqlite"
                                    else self._research_status()
                                )
                            if live["pending"] or (owner.kind == "sqlite" and not live["total"]):
                                raise RuntimeError("live schema does not match applied owner")
                        except Exception as exc:
                            result.append(
                                self._item(
                                    owner,
                                    "failed",
                                    {
                                        **latest["provenance"],
                                        "reason": "live_schema_drift",
                                        "error_type": type(exc).__name__,
                                    },
                                    operation="status",
                                    recorded_at=latest["recorded_at"],
                                )
                            )
                            continue
                    result.append(
                        self._item(
                            owner,
                            latest["state"],
                            latest["provenance"],
                            operation=latest["operation"],
                            recorded_at=latest["recorded_at"],
                        )
                    )
                    continue
                provenance: dict[str, Any] = {"database": str(self.db_path)}
                state = "pending"
                if owner.kind == "sqlite":
                    try:
                        taskpack = migration.status(db_path=self.db_path)
                        if not taskpack["total"]:
                            state = "failed"
                            provenance["reason"] = "target_missing"
                        else:
                            state = "applied" if not taskpack["pending"] else "pending"
                        provenance["schema_migrations"] = taskpack
                    except Exception as exc:
                        state = "failed"
                        provenance.update(error_type=type(exc).__name__, operation="status")
                elif owner.kind == "sqlite_research":
                    try:
                        research = self._research_status()
                        state = "applied" if not research["pending"] else "pending"
                        provenance["schema_migrations"] = research
                    except Exception as exc:
                        state = "failed"
                        provenance.update(error_type=type(exc).__name__, operation="status")
                result.append(self._item(owner, state, provenance))
        return result

    def _research_status(self) -> dict[str, object]:
        from shared import research_migration

        return research_migration.status(db_path=self.db_path)

    def _build_candidate(self, owner: MigrationOwner) -> Any:
        if owner.kind == "fts":
            from shared.fts_index import build_fts_candidate

            return build_fts_candidate(self._fts_source(owner), db_path=self.db_path)
        if owner.kind == "vector":
            from app.memory.vector_db import VectorDB

            records = self._canonical_vector_records(owner)
            active = VectorDB(
                table_name=owner.target,
                dim=_VECTOR_DIM,
                db_path=self.db_path,
            )
            return active.build_candidate(records)
        raise RuntimeError(f"owner does not use a shadow candidate: {owner.owner}")

    def _canonical_vector_records(
        self,
        owner: MigrationOwner,
        connection: sqlite3.Connection | None = None,
    ) -> tuple[tuple[str, Any], ...]:
        from app.memory.vector_db import SimpleTextEmbedder

        source = "kb_documents" if owner.owner.endswith("documents") else "kb_cards"
        if connection is None:
            with closing(self._connect()) as owned_connection:
                return self._canonical_vector_records(owner, connection=owned_connection)
        if not migration._table_exists(connection, source):
            raise RuntimeError(f"vector source table is missing: {source}")
        rows = connection.execute(
            f'SELECT id, title, content FROM "{source}" ORDER BY rowid'
        ).fetchall()
        embedder = SimpleTextEmbedder(dim=_VECTOR_DIM)
        return tuple(
            (str(row["id"]), embedder.embed(f"{row['title']}\n{row['content']}")) for row in rows
        )

    def _validate_candidate(
        self,
        owner: MigrationOwner,
        candidate: Any,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        candidate_database = Path(str(candidate.db_path)).resolve()
        if candidate_database != self.db_path or str(candidate.active_table) != owner.target:
            raise ValueError("candidate identity does not match migration owner")
        if owner.kind == "vector":
            from app.memory.vector_db import vector_fingerprint

            if connection is None:
                return
            expected = tuple(
                sorted(
                    (object_id, vector_fingerprint(vector))
                    for object_id, vector in self._canonical_vector_records(
                        owner, connection=connection
                    )
                )
            )
            if candidate.vector_fingerprints != expected:
                raise RuntimeError("canonical vector source changed")

    def apply(self, owner_name: str, *, candidate: Any | None = None) -> dict[str, Any]:
        """Apply one owner; shadow owners verify before activation."""
        owner = self.registry.get(owner_name)
        with self._owner_guard(owner):
            return self._apply_locked(owner, candidate=candidate)

    def _apply_locked(
        self, owner: MigrationOwner, *, candidate: Any | None = None
    ) -> dict[str, Any]:
        if owner.kind == "sqlite":
            try:
                current = migration.status(db_path=self.db_path)
            except Exception as exc:
                self._record(
                    owner,
                    state="failed",
                    operation="apply",
                    provenance=self._failure_provenance(exc, "apply"),
                )
                raise
            if not current["total"]:
                error = RuntimeError("TaskPack migration target is missing")
                self._record(
                    owner,
                    state="failed",
                    operation="apply",
                    provenance={
                        "error_type": type(error).__name__,
                        "operation": "apply",
                        "reason": "target_missing",
                    },
                )
                raise error
        current_research: dict[str, object] | None = None
        if owner.kind == "sqlite_research":
            try:
                current_research = self._research_status()
            except Exception as exc:
                self._record(
                    owner,
                    state="failed",
                    operation="apply",
                    provenance=self._failure_provenance(exc, "apply"),
                )
                raise
        with closing(self._connect()) as conn:
            latest = self._latest_with_state(owner, connection=conn)
        if (
            owner.kind == "sqlite_research"
            and latest is None
            and current_research is not None
            and not current_research["pending"]
        ):
            error = RuntimeError("research schema was applied outside MigrationOperator")
            self._record(
                owner,
                state="failed",
                operation="apply",
                provenance={
                    "error_type": type(error).__name__,
                    "operation": "apply",
                    "reason": "externally_applied",
                },
            )
            raise error
        if latest is not None and latest["state"] == "applied":
            if owner.kind == "sqlite":
                try:
                    current = migration.status(db_path=self.db_path)
                    if current["pending"]:
                        raise RuntimeError("applied migration owner has pending schema migrations")
                except Exception as exc:
                    self._record(
                        owner,
                        state="failed",
                        operation="apply",
                        provenance=self._failure_provenance(exc, "apply"),
                    )
                    raise
            elif owner.kind == "sqlite_research":
                try:
                    current = self._research_status()
                    if current["pending"]:
                        raise RuntimeError("applied research owner has pending schema migrations")
                except Exception as exc:
                    self._record(
                        owner,
                        state="failed",
                        operation="apply",
                        provenance=self._failure_provenance(exc, "apply"),
                    )
                    raise
            elif owner.kind == "sqlite_core":
                try:
                    with closing(self._connect()) as connection:
                        core_schema.validate(connection)
                except Exception as exc:
                    self._record(
                        owner,
                        state="failed",
                        operation="apply",
                        provenance=self._failure_provenance(exc, "apply"),
                    )
                    raise
            return self._item(
                owner,
                "applied",
                latest["provenance"],
                operation=latest["operation"],
                recorded_at=latest["recorded_at"],
            )
        if latest is not None and latest["state"] == "failed" and latest["operation"] == "rollback":
            raise RuntimeError(f"rollback must be retried before apply for owner: {owner.owner}")
        built_here = False
        rollback_handle: Any | None = None
        try:
            if owner.kind == "sqlite_core":
                operator_run_id = uuid4().hex
                with closing(self._connect()) as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    backup = migration._create_backup(
                        self.db_path,
                        self.backup_dir,
                        core_schema.BASELINE_MIGRATION_NAME,
                        operator_run_id=operator_run_id,
                    )
                    core_schema.apply(connection)
                    core_schema.validate(connection)
                    provenance = {
                        "applied_migrations": [core_schema.BASELINE_MIGRATION_NAME],
                        "backup_path": str(backup),
                        "backup_sha256": _sha256(backup),
                        "database_fingerprint_after_apply": self._database_fingerprint(
                            connection
                        ),
                        "schema_contract_objects": len(core_schema.expected_contract()),
                    }
                    applied_item = self._insert_record(
                        connection,
                        owner,
                        state="applied",
                        operation="apply",
                        provenance=provenance,
                        run_id=operator_run_id,
                    )
                    connection.commit()
                return applied_item
            if owner.kind == "sqlite":
                applied_item: dict[str, Any] | None = None
                operator_run_id = uuid4().hex

                def record_before_commit(
                    connection: sqlite3.Connection, run: migration.MigrationRun
                ) -> None:
                    nonlocal applied_item
                    backup = run.backup_path
                    if backup is None:
                        raise RuntimeError(
                            "SQLite schema is applied without operator rollback provenance"
                        )
                    provenance = {
                        "applied_migrations": list(run.applied),
                        "backup_path": str(backup),
                        "backup_sha256": _sha256(backup),
                        "database_fingerprint_after_apply": self._database_fingerprint(connection),
                    }
                    applied_item = self._insert_record(
                        connection,
                        owner,
                        state="applied",
                        operation="apply",
                        provenance=provenance,
                        run_id=operator_run_id,
                    )

                migration.migrate(
                    db_path=self.db_path,
                    backup_dir=self.backup_dir,
                    before_commit=record_before_commit,
                    backup_when_pending=True,
                    operator_run_id=operator_run_id,
                )
                if applied_item is None:
                    raise RuntimeError(
                        "SQLite schema is applied without operator rollback provenance"
                    )
                return applied_item
            if owner.kind == "sqlite_research":
                from shared import research_migration

                applied_item = None
                operator_run_id = uuid4().hex

                def record_research_before_commit(
                    connection: sqlite3.Connection, run: migration.MigrationRun
                ) -> None:
                    nonlocal applied_item
                    backup = run.backup_path
                    if backup is None:
                        raise RuntimeError(
                            "research SQLite schema is applied without operator rollback provenance"
                        )
                    provenance = {
                        "applied_migrations": list(run.applied),
                        "backup_path": str(backup),
                        "backup_sha256": _sha256(backup),
                        "database_fingerprint_after_apply": self._database_fingerprint(connection),
                    }
                    applied_item = self._insert_record(
                        connection,
                        owner,
                        state="applied",
                        operation="apply",
                        provenance=provenance,
                        run_id=operator_run_id,
                    )

                research_migration.migrate(
                    db_path=self.db_path,
                    backup_dir=self.backup_dir,
                    before_commit=record_research_before_commit,
                    backup_when_pending=True,
                    operator_run_id=operator_run_id,
                    _operator_capability=research_migration._OPERATOR_CAPABILITY,
                )
                if applied_item is None:
                    raise RuntimeError("research schema apply has no operator provenance")
                return applied_item
            if owner.kind == "sqlite_knowledge":
                from shared import knowledge_governance_migration

                applied_item = None
                operator_run_id = uuid4().hex

                def record_knowledge_before_commit(
                    connection: sqlite3.Connection, run: migration.MigrationRun
                ) -> None:
                    nonlocal applied_item
                    backup = run.backup_path
                    if backup is None:
                        raise RuntimeError(
                            "knowledge governance schema is applied without operator rollback provenance"
                        )
                    provenance = {
                        "applied_migrations": list(run.applied),
                        "backup_path": str(backup),
                        "backup_sha256": _sha256(backup),
                        "database_fingerprint_after_apply": self._database_fingerprint(connection),
                    }
                    applied_item = self._insert_record(
                        connection,
                        owner,
                        state="applied",
                        operation="apply",
                        provenance=provenance,
                        run_id=operator_run_id,
                    )

                knowledge_governance_migration.migrate(
                    db_path=self.db_path,
                    backup_dir=self.backup_dir,
                    before_commit=record_knowledge_before_commit,
                    backup_when_pending=True,
                    operator_run_id=operator_run_id,
                    _operator_capability=knowledge_governance_migration._OPERATOR_CAPABILITY,
                )
                if applied_item is None:
                    raise RuntimeError("knowledge governance schema apply has no operator provenance")
                return applied_item
            if candidate is None:
                candidate = self._build_candidate(owner)
                built_here = True
            self._validate_candidate(owner, candidate)
            applied_item = None

            def validate_shadow_before_switch(connection: sqlite3.Connection) -> None:
                self._validate_candidate(owner, candidate, connection=connection)

            def record_shadow_before_commit(connection: sqlite3.Connection, handle: Any) -> None:
                nonlocal applied_item
                provenance = {
                    "candidate_verified": True,
                    "candidate_target": str(candidate.table_name),
                    "active_fingerprint": self._active_index_fingerprint(owner, connection),
                    "rollback": {
                        "kind": owner.kind,
                        "data": _json_safe(asdict(handle)),
                    },
                }
                applied_item = self._insert_record(
                    connection,
                    owner,
                    state="applied",
                    operation="apply",
                    provenance=provenance,
                )

            rollback_handle = candidate.activate(
                before_switch=validate_shadow_before_switch,
                before_commit=record_shadow_before_commit,
            )
            if applied_item is None:
                raise RuntimeError("shadow activation has no operator provenance")
            return applied_item
        except Exception as exc:
            if built_here and candidate is not None and rollback_handle is None:
                with suppress(Exception):
                    candidate.discard()
            self._record(
                owner,
                state="failed",
                operation="apply",
                provenance=self._failure_provenance(exc, "apply"),
            )
            raise

    def _rollback_handle(self, owner: MigrationOwner, payload: dict[str, Any]) -> Any:
        rollback = payload.get("rollback")
        if not isinstance(rollback, dict) or rollback.get("kind") != owner.kind:
            raise RuntimeError("rollback provenance does not match migration owner")
        raw_data = rollback.get("data")
        if not isinstance(raw_data, dict):
            raise RuntimeError("rollback provenance does not match migration owner")
        data = dict(raw_data)
        if Path(str(data.get("db_path", ""))).resolve() != self.db_path:
            raise RuntimeError("rollback provenance does not match migration owner")
        if str(data.get("active_table", "")) != owner.target:
            raise RuntimeError("rollback provenance does not match migration owner")
        candidate_table = self._validate_shadow_name(
            data.get("candidate_table"), f"{owner.target}__candidate_"
        )
        backup_table = self._validate_shadow_name(
            data.get("backup_table"), f"{owner.target}__rollback_"
        )
        if len({owner.target, candidate_table, backup_table}) != 3:
            raise RuntimeError("rollback provenance does not match migration owner")
        data["candidate_table"] = candidate_table
        data["backup_table"] = backup_table
        active_fingerprint = payload.get("active_fingerprint")
        if not isinstance(active_fingerprint, dict):
            raise RuntimeError("rollback provenance does not include active fingerprint")
        if owner.kind == "fts":
            from shared.fts_index import FtsIndexRollback

            _active_table, create_sql, columns = self._fts_spec(owner)
            data["columns"] = tuple(data.get("columns", ()))
            if data["columns"] != columns or str(data.get("create_sql", "")) != create_sql:
                raise RuntimeError("rollback provenance does not match migration owner")
            return FtsIndexRollback(**data)
        if owner.kind == "vector":
            from app.memory.vector_db import VectorIndexRollback

            try:
                dim = int(data.get("dim", -1))
            except (TypeError, ValueError) as exc:
                raise RuntimeError("rollback provenance does not match migration owner") from exc
            if dim != _VECTOR_DIM:
                raise RuntimeError("rollback provenance does not match migration owner")
            data["dim"] = dim
            return VectorIndexRollback(**data)
        raise RuntimeError(f"owner has no shadow rollback handle: {owner.owner}")

    def rollback(self, owner_name: str) -> dict[str, Any]:
        """Roll back the latest applied run and retain attributable provenance."""
        owner = self.registry.get(owner_name)
        with self._owner_guard(owner):
            return self._rollback_locked(owner)

    def _rollback_locked(self, owner: MigrationOwner) -> dict[str, Any]:
        latest = self._latest(owner)
        if latest is not None and latest["state"] == "failed" and latest["operation"] == "rollback":
            latest = self._latest_with_state(owner, "applied")
        if latest is None or latest["state"] != "applied":
            raise RuntimeError(f"no applied migration to roll back for owner: {owner.owner}")
        try:
            if owner.kind in {"sqlite", "sqlite_research", "sqlite_knowledge", "sqlite_core"}:
                backup_value = latest["provenance"].get("backup_path")
                if not backup_value:
                    raise RuntimeError("applied SQLite migration has no rollback backup")
                backup = Path(str(backup_value))
                backup_hash = _sha256(backup)
                if latest["provenance"].get("backup_sha256") != backup_hash:
                    raise RuntimeError("rollback backup hash does not match operator provenance")
                raw_migrations = latest["provenance"].get("applied_migrations")
                if not isinstance(raw_migrations, list) or not raw_migrations:
                    raise RuntimeError("rollback provenance has no applied migrations")
                expected_migrations = {str(item) for item in raw_migrations}
                if owner.kind == "sqlite":
                    if not expected_migrations <= set(migration.TASKPACK_MIGRATIONS.values()):
                        raise RuntimeError("rollback provenance does not match migration owner")
                elif owner.kind == "sqlite_research":
                    if expected_migrations != {migration.RESEARCH_SCHEMA_MIGRATION_NAME}:
                        raise RuntimeError("rollback provenance does not match migration owner")
                elif owner.kind == "sqlite_knowledge":
                    allowed_migrations = {
                        migration.KNOWLEDGE_GOVERNANCE_MIGRATION_NAME,
                        migration.KNOWLEDGE_GOVERNANCE_EVENT_MIGRATION_NAME,
                        migration.KNOWLEDGE_VERSIONING_MIGRATION_NAME,
                    }
                    if not expected_migrations <= allowed_migrations:
                        raise RuntimeError("rollback provenance does not match migration owner")
                elif expected_migrations != {core_schema.BASELINE_MIGRATION_NAME}:
                    raise RuntimeError("rollback provenance does not match migration owner")
                expected_fingerprint = latest["provenance"].get("database_fingerprint_after_apply")
                if not expected_fingerprint:
                    raise RuntimeError("applied SQLite migration has no state fingerprint")
                with closing(self._connect()) as connection:
                    current_fingerprint = self._database_fingerprint(connection)
                if current_fingerprint != expected_fingerprint:
                    label = "TaskPack" if owner.kind == "sqlite" else owner.owner
                    raise RuntimeError(f"database changed since {label} apply")
                operator_runs = self._snapshot_operator_runs()
                rolled_back_item: dict[str, Any] | None = None
                provenance = {
                    "restored_backup_path": str(backup),
                    "restored_backup_sha256": backup_hash,
                    "validated_database_fingerprint": current_fingerprint,
                }

                def prepare_replacement(database: Path) -> None:
                    nonlocal rolled_back_item
                    with closing(sqlite3.connect(str(database))) as connection:
                        connection.row_factory = sqlite3.Row
                        connection.execute("BEGIN IMMEDIATE")
                        self._restore_operator_runs_in_connection(connection, operator_runs)
                        rolled_back_item = self._insert_record(
                            connection,
                            owner,
                            state="rolled_back",
                            operation="rollback",
                            provenance=provenance,
                        )
                        record = connection.execute(
                            f"SELECT 1 FROM {_OPERATOR_TABLE} "
                            "WHERE owner=? AND version=? AND target=? "
                            "AND state='rolled_back' AND operation='rollback' "
                            "AND recorded_at=?",
                            (*owner.identity, rolled_back_item["recorded_at"]),
                        ).fetchone()
                        if record is None:
                            raise RuntimeError("replacement database lacks rollback provenance")
                        connection.commit()

                migration.rollback(
                    backup_path=backup,
                    db_path=self.db_path,
                    prepare_replacement=prepare_replacement,
                    expected_migrations=expected_migrations,
                    expected_operator_run_id=latest["run_id"],
                )
                if rolled_back_item is None:
                    raise RuntimeError("SQLite rollback has no operator provenance")
                return rolled_back_item
            else:
                handle = self._rollback_handle(owner, latest["provenance"])
                expected_active_fingerprint = latest["provenance"]["active_fingerprint"]
                rolled_back_item = None
                provenance = {
                    "candidate_verified": True,
                    "rolled_back_from": latest["provenance"].get("candidate_target"),
                }

                def record_shadow_rollback_before_commit(
                    connection: sqlite3.Connection,
                ) -> None:
                    nonlocal rolled_back_item
                    rolled_back_item = self._insert_record(
                        connection,
                        owner,
                        state="rolled_back",
                        operation="rollback",
                        provenance=provenance,
                    )

                handle.rollback(
                    expected_active_fingerprint=expected_active_fingerprint,
                    before_commit=record_shadow_rollback_before_commit,
                )
                if rolled_back_item is None:
                    raise RuntimeError("shadow rollback has no operator provenance")
                return rolled_back_item
        except Exception as exc:
            self._record(
                owner,
                state="failed",
                operation="rollback",
                provenance=self._failure_provenance(exc, "rollback"),
            )
            raise
