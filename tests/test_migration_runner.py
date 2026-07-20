from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Event

import pytest


def _create_legacy_taskpack_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            CREATE TABLE kb_taskpacks (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                steps_json TEXT NOT NULL DEFAULT '[]',
                allowed_tools_json TEXT NOT NULL DEFAULT '[]',
                blocked_tools_json TEXT NOT NULL DEFAULT '[]',
                constraints_json TEXT NOT NULL DEFAULT '[]',
                success_criteria_json TEXT NOT NULL DEFAULT '[]',
                risk_level TEXT NOT NULL DEFAULT 'low',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute("INSERT INTO kb_taskpacks(id, goal) VALUES ('legacy', 'preserve')")
        connection.commit()


def _create_current_taskpack_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            CREATE TABLE kb_taskpacks (
                id TEXT PRIMARY KEY,
                context_id TEXT NOT NULL DEFAULT '',
                goal TEXT NOT NULL,
                steps_json TEXT NOT NULL DEFAULT '[]',
                allowed_tools_json TEXT NOT NULL DEFAULT '[]',
                blocked_tools_json TEXT NOT NULL DEFAULT '[]',
                constraints_json TEXT NOT NULL DEFAULT '[]',
                success_criteria_json TEXT NOT NULL DEFAULT '[]',
                risk_level TEXT NOT NULL DEFAULT 'low',
                requires_review INTEGER NOT NULL DEFAULT 1 CHECK(requires_review IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute("INSERT INTO kb_taskpacks(id, goal) VALUES ('fresh', 'current schema')")
        connection.commit()


def _create_search_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(
            """
            CREATE TABLE kb_documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'unknown'
            );
            CREATE TABLE kb_cards (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE VIRTUAL TABLE kb_documents_fts USING fts5(
                id UNINDEXED, title, content, source, tokenize='porter unicode61'
            );
            CREATE VIRTUAL TABLE kb_cards_fts USING fts5(
                id UNINDEXED, title, content, tags, tokenize='porter unicode61'
            );
            INSERT INTO kb_documents(id, title, content, source)
            VALUES ('doc-new', 'New', 'verified candidate content', 'test');
            INSERT INTO kb_documents_fts(id, title, content, source)
            VALUES ('doc-old', 'Old', 'previous active content', 'test');
            """
        )
        connection.commit()


def _state(items: list[dict[str, object]], owner: str) -> dict[str, object]:
    return next(item for item in items if item["owner"] == owner)


def _sqlite_locked(exc: sqlite3.OperationalError) -> bool:
    return "locked" in str(exc).lower()


def _ordinary_vector_insert(
    database: Path,
    table_name: str,
    object_id: str,
    vector,
    *,
    connect=sqlite3.connect,
    timeout: float = 0,
) -> None:
    import numpy as np
    import sqlite_vec as sv

    from app.memory.vector_db import VectorDB

    vector_db = VectorDB(table_name=table_name, dim=len(vector), db_path=database)
    rowid = vector_db._to_rowid(object_id)
    blob = np.asarray(vector, dtype=np.float32).tobytes()
    with closing(connect(str(database), timeout=timeout)) as connection:
        connection.enable_load_extension(True)
        sv.load(connection)
        connection.enable_load_extension(False)
        connection.execute(
            f"INSERT OR REPLACE INTO {vector_db._map_table}(object_id, rowid) VALUES (?, ?)",
            (object_id, rowid),
        )
        connection.execute(
            f"INSERT OR REPLACE INTO {table_name}(rowid, embedding) VALUES (?, ?)",
            (rowid, blob),
        )
        connection.commit()


def _rewrite_latest_applied_provenance(
    database: Path, owner: str, update: dict[str, object]
) -> dict[str, object]:
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT rowid, provenance_json FROM migration_operator_runs "
            "WHERE owner=? AND state='applied' "
            "ORDER BY recorded_at DESC, run_id DESC LIMIT 1",
            (owner,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row[1])
        payload["rollback"]["data"].update(update)
        connection.execute(
            "UPDATE migration_operator_runs SET provenance_json=? WHERE rowid=?",
            (json.dumps(payload, ensure_ascii=True, sort_keys=True), row[0]),
        )
        connection.commit()
        return payload


def _sqlite_table_names(database: Path, *names: str) -> set[str]:
    placeholders = ", ".join("?" for _ in names)
    with closing(sqlite3.connect(database)) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                f"SELECT name FROM sqlite_master WHERE name IN ({placeholders})",
                names,
            )
        }


def test_registry_is_deterministic_and_rejects_duplicate_identity(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOwner, MigrationRegistry, default_registry

    registry = default_registry(tmp_path / "runtime.sqlite")
    identities = [owner.identity for owner in registry.owners]

    assert identities == sorted(identities)
    assert identities == [
        ("core.sqlite", 1, "core_schema_v1"),
        ("fts.cards", 1, "kb_cards_fts"),
        ("fts.documents", 1, "kb_documents_fts"),
        ("knowledge-governance.sqlite", 1, "knowledge_candidate_promotions_v1"),
        ("research.sqlite", 1, "research_packages_v1"),
        ("taskpack.sqlite", 3, "kb_taskpacks"),
        ("vector.cards", 1, "vec_kb_cards"),
        ("vector.documents", 1, "vec_kb_documents"),
    ]

    duplicate = MigrationOwner(
        owner="taskpack.sqlite",
        version=3,
        target="kb_taskpacks",
        kind="sqlite",
    )
    with pytest.raises(ValueError, match="duplicate migration owner identity"):
        MigrationRegistry([*registry.owners, duplicate])

    target_collision = MigrationOwner(
        owner="taskpack.alternate",
        version=1,
        target="kb_taskpacks",
        kind="sqlite",
    )
    with pytest.raises(ValueError, match="duplicate migration target ownership"):
        MigrationRegistry([*registry.owners, target_collision])


def test_core_baseline_owner_apply_status_and_rollback_are_provenanced(tmp_path: Path) -> None:
    from shared import core_schema
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    with closing(sqlite3.connect(database)):
        pass
    operator = MigrationOperator(db_path=database, backup_dir=backups)

    assert _state(operator.status(), "core.sqlite")["state"] == "pending"
    applied = operator.apply("core.sqlite")
    assert applied["state"] == "applied"
    assert applied["provenance"]["backup_sha256"]
    assert applied["provenance"]["schema_contract_objects"] == len(
        core_schema.expected_contract()
    )
    assert _state(operator.status(), "core.sqlite")["state"] == "applied"
    with closing(sqlite3.connect(database)) as connection:
        core_schema.validate(connection)

    rolled_back = operator.rollback("core.sqlite")
    assert rolled_back["state"] == "rolled_back"
    assert _state(operator.status(), "core.sqlite")["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='core_objects'"
        ).fetchone() is None


def test_taskpack_operator_status_apply_duplicate_run_and_rollback_provenance(
    tmp_path: Path,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    backups = tmp_path / "backups"
    _create_legacy_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=backups)

    pending = _state(operator.status(), "taskpack.sqlite")
    assert pending["state"] == "pending"
    assert pending["provenance"]["database"] == str(database.resolve())

    applied = operator.apply("taskpack.sqlite")
    assert applied["state"] == "applied"
    assert applied["provenance"]["backup_sha256"]
    assert operator.apply("taskpack.sqlite")["state"] == "applied"
    assert _state(operator.status(), "taskpack.sqlite")["state"] == "applied"

    rolled_back = operator.rollback("taskpack.sqlite")
    assert rolled_back["state"] == "rolled_back"
    assert rolled_back["provenance"]["restored_backup_sha256"]
    assert _state(operator.status(), "taskpack.sqlite")["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(kb_taskpacks)")}
    assert "context_id" not in columns


def test_fts_owner_applies_verified_candidate_and_rolls_back_previous_index(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")

    applied = operator.apply("fts.documents")
    assert applied["state"] == "applied"
    assert applied["provenance"]["candidate_verified"] is True
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'verified'"
            ).fetchone()[0]
            == "doc-new"
        )

    rolled_back = operator.rollback("fts.documents")
    assert rolled_back["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'previous'"
            ).fetchone()[0]
            == "doc-old"
        )


def test_applied_taskpack_owner_fails_closed_when_schema_ledger_drifts(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("taskpack.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE schema_migrations SET name='tampered_owner' WHERE version=3")
        connection.commit()

    with pytest.raises(RuntimeError, match="migration version 3 name collision"):
        operator.apply("taskpack.sqlite")

    failed = _state(operator.status(), "taskpack.sqlite")
    assert failed["state"] == "failed"
    assert failed["provenance"]["operation"] == "apply"


def test_fts_failed_verification_preserves_active_index_and_records_failure(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    candidate = operator._build_candidate(operator.registry.get("fts.documents"))
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE kb_documents SET content='source drift' WHERE id='doc-new'")
        connection.commit()

    with pytest.raises(RuntimeError, match="FTS candidate verification failed"):
        operator.apply("fts.documents", candidate=candidate)

    failed = _state(operator.status(), "fts.documents")
    assert failed["state"] == "failed"
    assert failed["provenance"]["error_type"] == "RuntimeError"
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'previous'"
            ).fetchone()[0]
            == "doc-old"
        )
    candidate.discard()


def test_vector_owner_rebuilds_from_canonical_rows_and_rolls_back(tmp_path: Path) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    active = VectorDB(table_name="vec_kb_documents", dim=384, db_path=database)
    embedder = SimpleTextEmbedder(dim=384)
    active.init()
    active.insert("doc-old", embedder.embed("previous vector"))
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")

    applied = operator.apply("vector.documents")
    assert applied["state"] == "applied"
    assert active.list_ids() == ["doc-new"]

    rolled_back = operator.rollback("vector.documents")
    assert rolled_back["state"] == "rolled_back"
    assert active.list_ids() == ["doc-old"]


def test_operator_rollback_replace_failure_preserves_active_database_and_records_failure(
    monkeypatch, tmp_path: Path
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("taskpack.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        migrated_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
        ).fetchone()[0]

    def fail_replace(_source: Path, _target: Path) -> Path:
        raise OSError("simulated Windows replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated Windows replace failure"):
        operator.rollback("taskpack.sqlite")

    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='kb_taskpacks'"
            ).fetchone()[0]
            == migrated_sql
        )
        assert (
            connection.execute("SELECT goal FROM kb_taskpacks WHERE id='legacy'").fetchone()[0]
            == "preserve"
        )
    failed = _state(operator.status(), "taskpack.sqlite")
    assert failed["state"] == "failed"
    assert failed["provenance"]["operation"] == "rollback"

    monkeypatch.undo()
    retried = operator.rollback("taskpack.sqlite")
    assert retried["state"] == "rolled_back"


def test_non_interactive_cli_reports_json_status_for_explicit_database(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli",
            "migrate",
            "status",
            "--db",
            str(database),
            "--backup-dir",
            str(tmp_path / "backups"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert _state(payload, "taskpack.sqlite")["state"] == "pending"


def test_taskpack_schema_and_applied_provenance_are_atomic(monkeypatch, tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    original_insert = operator._insert_record

    def fail_applied_record(connection, owner, *, state, operation, provenance, run_id=None):
        if state == "applied":
            raise RuntimeError("injected atomic provenance failure")
        return original_insert(
            connection,
            owner,
            state=state,
            operation=operation,
            provenance=provenance,
        )

    monkeypatch.setattr(operator, "_insert_record", fail_applied_record)
    with pytest.raises(RuntimeError, match="injected atomic provenance failure"):
        operator.apply("taskpack.sqlite")

    with closing(sqlite3.connect(database)) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(kb_taskpacks)")}
        assert "context_id" not in columns
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name='schema_migrations'"
            ).fetchone()[0]
            == 0
        )
    assert _state(operator.status(), "taskpack.sqlite")["state"] == "failed"

    monkeypatch.undo()
    applied = operator.apply("taskpack.sqlite")
    assert applied["provenance"]["backup_path"]
    assert operator.rollback("taskpack.sqlite")["state"] == "rolled_back"
    assert operator.apply("taskpack.sqlite")["state"] == "applied"


def test_fresh_current_taskpack_schema_gets_verified_backup_and_rollback(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_current_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")

    applied = operator.apply("taskpack.sqlite")

    assert applied["state"] == "applied"
    assert applied["provenance"]["backup_path"]
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM schema_migrations WHERE version IN (2, 3)"
            ).fetchone()[0]
            == 2
        )

    assert operator.rollback("taskpack.sqlite")["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name='schema_migrations'"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute("SELECT goal FROM kb_taskpacks WHERE id='fresh'").fetchone()[0]
            == "current schema"
        )


def test_empty_database_fails_closed_as_missing_taskpack_target(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    database.touch()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")

    status = _state(operator.status(), "taskpack.sqlite")
    assert status["state"] == "failed"
    assert status["provenance"]["reason"] == "target_missing"
    with pytest.raises(RuntimeError, match="TaskPack migration target is missing"):
        operator.apply("taskpack.sqlite")
    assert not list((tmp_path / "backups").glob("pre_migration_*.sqlite"))


def test_programmatic_fts_operator_never_initializes_configured_database(tmp_path: Path) -> None:
    configured = tmp_path / "configured.sqlite"
    isolated = tmp_path / "isolated.sqlite"
    with closing(sqlite3.connect(configured)) as connection:
        connection.execute("CREATE TABLE sentinel(value TEXT NOT NULL)")
        connection.execute("INSERT INTO sentinel VALUES ('untouched')")
        connection.commit()
    _create_search_database(isolated)
    before = configured.read_bytes()
    script = (
        "from shared.migration_runner import MigrationOperator; "
        f"op=MigrationOperator(db_path={str(isolated)!r}, backup_dir={str(tmp_path / 'backups')!r}); "
        "op.apply('fts.documents')"
    )
    environment = os.environ.copy()
    environment["COGNITIVE_DB_PATH"] = str(configured)

    subprocess.run([sys.executable, "-c", script], check=True, env=environment)

    assert configured.read_bytes() == before
    with closing(sqlite3.connect(configured)) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert tables == {"sentinel"}


def test_vector_candidate_rejects_changed_embedding_with_same_id(tmp_path: Path) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB

    database = tmp_path / "runtime.sqlite"
    database.touch()
    embedder = SimpleTextEmbedder(dim=128)
    active = VectorDB(table_name="vec_active", dim=128, db_path=database)
    active.init()
    candidate = active.build_candidate([("same-id", embedder.embed("canonical"))])
    candidate_db = VectorDB(candidate.table_name, dim=128, db_path=database)
    candidate_db.insert("same-id", embedder.embed("corrupted"))

    with pytest.raises(RuntimeError, match="candidate verification failed"):
        candidate.verify()
    candidate.discard()


def test_vector_operator_rejects_candidate_after_canonical_source_drift(tmp_path: Path) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    active = VectorDB(table_name="vec_kb_documents", dim=384, db_path=database)
    active.init()
    active.insert("doc-old", SimpleTextEmbedder(384).embed("previous"))
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    candidate = operator._build_candidate(operator.registry.get("vector.documents"))
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE kb_documents SET content='source drift' WHERE id='doc-new'")
        connection.commit()

    with pytest.raises(RuntimeError, match="canonical vector source changed"):
        operator.apply("vector.documents", candidate=candidate)

    assert active.list_ids() == ["doc-old"]
    candidate.discard()


def test_failed_vector_rollback_cleanup_preserves_active_candidate(
    monkeypatch, tmp_path: Path
) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    active = VectorDB(table_name="vec_kb_documents", dim=384, db_path=database)
    active.init()
    active.insert("doc-old", SimpleTextEmbedder(384).embed("previous"))
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("vector.documents")
    original_drop = VectorDB._drop_index

    def fail_cleanup(connection, table_name, map_table):
        if "__rollback_" in table_name:
            raise RuntimeError("injected vector cleanup failure")
        return original_drop(connection, table_name, map_table)

    monkeypatch.setattr(VectorDB, "_drop_index", staticmethod(fail_cleanup))
    with pytest.raises(RuntimeError, match="injected vector cleanup failure"):
        operator.rollback("vector.documents")

    assert active.list_ids() == ["doc-new"]
    failed = _state(operator.status(), "vector.documents")
    assert failed["state"] == "failed"
    assert failed["provenance"]["operation"] == "rollback"

    monkeypatch.undo()
    assert operator.rollback("vector.documents")["state"] == "rolled_back"
    assert active.list_ids() == ["doc-old"]


def test_taskpack_rollback_rejects_runtime_data_drift(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("taskpack.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE kb_taskpacks SET goal='new runtime work' WHERE id='legacy'")
        connection.commit()

    with pytest.raises(RuntimeError, match="database changed since TaskPack apply"):
        operator.rollback("taskpack.sqlite")

    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute("SELECT goal FROM kb_taskpacks WHERE id='legacy'").fetchone()[0]
            == "new runtime work"
        )


def test_taskpack_rollback_preserves_later_operator_provenance(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("taskpack.sqlite")
    with pytest.raises(RuntimeError, match="vector source table is missing"):
        operator.apply("vector.documents")
    assert _state(operator.status(), "vector.documents")["state"] == "failed"

    assert operator.rollback("taskpack.sqlite")["state"] == "rolled_back"
    vector_status = _state(operator.status(), "vector.documents")
    assert vector_status["state"] == "failed"
    assert vector_status["provenance"]["operation"] == "apply"


def test_taskpack_provenance_prepare_failure_does_not_replace_database(
    monkeypatch, tmp_path: Path
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("taskpack.sqlite")

    def fail_prepare(_connection, _runs):
        raise RuntimeError("injected provenance preparation failure")

    monkeypatch.setattr(operator, "_restore_operator_runs_in_connection", fail_prepare)
    with pytest.raises(RuntimeError, match="injected provenance preparation failure"):
        operator.rollback("taskpack.sqlite")
    with closing(sqlite3.connect(database)) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(kb_taskpacks)")}
    assert "requires_review" in columns

    monkeypatch.undo()
    assert operator.rollback("taskpack.sqlite")["state"] == "rolled_back"


def test_taskpack_rollback_lease_survives_database_replacement(monkeypatch, tmp_path: Path) -> None:
    from shared import migration
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    first = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    second = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    first.apply("taskpack.sqlite")
    replaced = Event()
    release = Event()
    original_rollback = migration.rollback

    def held_after_replace(**kwargs):
        result = original_rollback(**kwargs)
        replaced.set()
        assert release.wait(timeout=5)
        return result

    monkeypatch.setattr(migration, "rollback", held_after_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first.rollback, "taskpack.sqlite")
        assert replaced.wait(timeout=5)
        second_future = pool.submit(second.apply, "taskpack.sqlite")
        try:
            with pytest.raises(RuntimeError, match="migration owner is busy"):
                second_future.result(timeout=5)
        finally:
            release.set()
        assert first_future.result(timeout=5)["state"] == "rolled_back"


def test_owner_guard_release_cannot_delete_a_replaced_lease(tmp_path: Path) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    owner = operator.registry.get("taskpack.sqlite")
    lock_database = operator._lock_database

    with operator._owner_guard(owner), closing(sqlite3.connect(lock_database)) as connection:
        connection.execute(
            "UPDATE migration_operator_locks SET token='replacement' WHERE owner=?",
            (owner.owner,),
        )
        connection.commit()

    with closing(sqlite3.connect(lock_database)) as connection:
        assert (
            connection.execute(
                "SELECT token FROM migration_operator_locks WHERE owner=?", (owner.owner,)
            ).fetchone()[0]
            == "replacement"
        )


def test_fts_provenance_failure_is_atomic_even_if_handle_rollback_fails(
    monkeypatch, tmp_path: Path
) -> None:
    from shared.fts_index import FtsIndexRollback
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    original_insert = operator._insert_record

    def fail_applied_record(connection, owner, *, state, operation, provenance, run_id=None):
        if state == "applied":
            raise RuntimeError("injected FTS provenance failure")
        return original_insert(
            connection, owner, state=state, operation=operation, provenance=provenance
        )

    def fail_handle_rollback(_self):
        raise RuntimeError("injected unusable FTS handle")

    monkeypatch.setattr(operator, "_insert_record", fail_applied_record)
    monkeypatch.setattr(FtsIndexRollback, "rollback", fail_handle_rollback)
    with pytest.raises(RuntimeError, match="injected FTS provenance failure"):
        operator.apply("fts.documents")

    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'previous'"
            ).fetchone()[0]
            == "doc-old"
        )
    assert _state(operator.status(), "fts.documents")["state"] == "failed"


def test_vector_provenance_failure_is_atomic_even_if_handle_rollback_fails(
    monkeypatch, tmp_path: Path
) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB, VectorIndexRollback
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    active = VectorDB(table_name="vec_kb_documents", dim=384, db_path=database)
    active.init()
    active.insert("doc-old", SimpleTextEmbedder(384).embed("previous"))
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    original_insert = operator._insert_record

    def fail_applied_record(connection, owner, *, state, operation, provenance, run_id=None):
        if state == "applied":
            raise RuntimeError("injected vector provenance failure")
        return original_insert(
            connection, owner, state=state, operation=operation, provenance=provenance
        )

    def fail_handle_rollback(_self):
        raise RuntimeError("injected unusable vector handle")

    monkeypatch.setattr(operator, "_insert_record", fail_applied_record)
    monkeypatch.setattr(VectorIndexRollback, "rollback", fail_handle_rollback)
    with pytest.raises(RuntimeError, match="injected vector provenance failure"):
        operator.apply("vector.documents")

    assert active.list_ids() == ["doc-old"]
    assert _state(operator.status(), "vector.documents")["state"] == "failed"


def test_concurrent_fts_apply_has_one_owner_and_preserves_original_rollback(
    monkeypatch, tmp_path: Path
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    first = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    second = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    entered = Event()
    release = Event()
    original_build = first._build_candidate

    def held_build(owner):
        entered.set()
        assert release.wait(timeout=5)
        return original_build(owner)

    monkeypatch.setattr(first, "_build_candidate", held_build)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first.apply, "fts.documents")
        assert entered.wait(timeout=5)
        second_future = pool.submit(second.apply, "fts.documents")
        with pytest.raises(RuntimeError, match="migration owner is busy"):
            second_future.result(timeout=5)
        release.set()
        assert first_future.result(timeout=5)["state"] == "applied"

    assert first.rollback("fts.documents")["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'previous'"
            ).fetchone()[0]
            == "doc-old"
        )


def test_concurrent_fts_apply_with_different_backup_dirs_uses_one_owner_lease(
    monkeypatch, tmp_path: Path
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    first = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups-a")
    second = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups-b")
    entered = Event()
    release = Event()
    original_build = first._build_candidate

    def held_build(owner):
        entered.set()
        assert release.wait(timeout=5)
        return original_build(owner)

    monkeypatch.setattr(first, "_build_candidate", held_build)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first.apply, "fts.documents")
        assert entered.wait(timeout=5)
        second_future = pool.submit(second.apply, "fts.documents")
        try:
            with pytest.raises(RuntimeError, match="migration owner is busy"):
                second_future.result(timeout=5)
        finally:
            release.set()
        assert first_future.result(timeout=5)["state"] == "applied"

    assert first.rollback("fts.documents")["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'previous'"
            ).fetchone()[0]
            == "doc-old"
        )


def test_cli_apply_with_alternate_backup_dir_respects_active_owner_lease(
    tmp_path: Path,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups-a")
    owner = operator.registry.get("fts.documents")

    with operator._owner_guard(owner):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.cli",
                "migrate",
                "apply",
                "--owner",
                "fts.documents",
                "--db",
                str(database),
                "--backup-dir",
                str(tmp_path / "backups-b"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    assert completed.returncode != 0
    assert "migration owner is busy: fts.documents" in completed.stderr
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'previous'"
            ).fetchone()[0]
            == "doc-old"
        )


def test_fts_rollback_rejects_corrupted_provenance_before_foreign_database_touch(
    tmp_path: Path,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    foreign = tmp_path / "foreign.sqlite"
    _create_search_database(database)
    with closing(sqlite3.connect(foreign)) as connection:
        connection.executescript(
            """
            CREATE VIRTUAL TABLE foreign_fts USING fts5(
                id UNINDEXED, title, content, source, tokenize='porter unicode61'
            );
            CREATE VIRTUAL TABLE foreign_fts__rollback_attack USING fts5(
                id UNINDEXED, title, content, source, tokenize='porter unicode61'
            );
            CREATE VIRTUAL TABLE foreign_fts__candidate_attack USING fts5(
                id UNINDEXED, title, content, source, tokenize='porter unicode61'
            );
            INSERT INTO foreign_fts(id, title, content, source)
            VALUES ('foreign-active', 'Active', 'foreign active marker', 'test');
            INSERT INTO foreign_fts__rollback_attack(id, title, content, source)
            VALUES ('foreign-backup', 'Backup', 'foreign backup marker', 'test');
            INSERT INTO foreign_fts__candidate_attack(id, title, content, source)
            VALUES ('foreign-candidate', 'Candidate', 'foreign candidate marker', 'test');
            """
        )
        connection.commit()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("fts.documents")
    _rewrite_latest_applied_provenance(
        database,
        "fts.documents",
        {
            "active_table": "foreign_fts",
            "backup_table": "foreign_fts__rollback_attack",
            "candidate_table": "foreign_fts__candidate_attack",
            "db_path": str(foreign),
        },
    )

    with pytest.raises(RuntimeError, match="rollback provenance"):
        operator.rollback("fts.documents")

    with closing(sqlite3.connect(foreign)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM foreign_fts WHERE foreign_fts MATCH 'active'"
            ).fetchone()[0]
            == "foreign-active"
        )
    assert _sqlite_table_names(
        foreign,
        "foreign_fts",
        "foreign_fts__rollback_attack",
        "foreign_fts__candidate_attack",
    ) == {
        "foreign_fts",
        "foreign_fts__rollback_attack",
        "foreign_fts__candidate_attack",
    }


def test_vector_rollback_rejects_corrupted_provenance_before_unrelated_tables_touch(
    tmp_path: Path,
) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    embedder = SimpleTextEmbedder(384)
    active = VectorDB(table_name="vec_kb_documents", dim=384, db_path=database)
    active.init()
    active.insert("doc-old", embedder.embed("previous vector"))
    unrelated = VectorDB(table_name="vec_unrelated", dim=384, db_path=database)
    unrelated_backup = VectorDB(
        table_name="vec_unrelated__rollback_attack", dim=384, db_path=database
    )
    unrelated_candidate = VectorDB(
        table_name="vec_unrelated__candidate_attack", dim=384, db_path=database
    )
    for index, object_id, text in (
        (unrelated, "foreign-active", "foreign active marker"),
        (unrelated_backup, "foreign-backup", "foreign backup marker"),
        (unrelated_candidate, "foreign-candidate", "foreign candidate marker"),
    ):
        index.init()
        index.insert(object_id, embedder.embed(text))
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("vector.documents")
    _rewrite_latest_applied_provenance(
        database,
        "vector.documents",
        {
            "active_table": "vec_unrelated",
            "backup_table": "vec_unrelated__rollback_attack",
            "candidate_table": "vec_unrelated__candidate_attack",
            "db_path": str(database),
        },
    )

    with pytest.raises(RuntimeError, match="rollback provenance"):
        operator.rollback("vector.documents")

    assert unrelated.list_ids() == ["foreign-active"]
    assert unrelated_backup._index_exists()
    assert unrelated_candidate._index_exists()
    assert active.list_ids() == ["doc-new"]


def test_fts_rollback_rejects_post_apply_active_drift_and_allows_retry(
    tmp_path: Path,
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    applied = operator.apply("fts.documents")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO kb_documents_fts(rowid, id, title, content, source) "
            "VALUES (?, ?, ?, ?, ?)",
            (99, "runtime-drift", "Runtime", "runtime drift marker", "test"),
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="active FTS index changed since apply"):
        operator.rollback("fts.documents")

    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'drift'"
            ).fetchone()[0]
            == "runtime-drift"
        )
        retained = connection.execute(
            "SELECT provenance_json FROM migration_operator_runs "
            "WHERE owner='fts.documents' AND state='applied'"
        ).fetchone()[0]
        retained_payload = json.loads(retained)
        assert retained_payload["rollback"] == applied["provenance"]["rollback"]
        connection.execute("DELETE FROM kb_documents_fts WHERE rowid=99")
        connection.commit()
    failed = _state(operator.status(), "fts.documents")
    assert failed["state"] == "failed"
    assert failed["provenance"]["operation"] == "rollback"
    assert "active FTS index changed since apply" in failed["provenance"]["error_message"]
    assert "active_fingerprint" in applied["provenance"]

    assert operator.rollback("fts.documents")["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'previous'"
            ).fetchone()[0]
            == "doc-old"
        )


def test_vector_rollback_rejects_post_apply_active_drift_and_allows_retry(
    tmp_path: Path,
) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    embedder = SimpleTextEmbedder(384)
    active = VectorDB(table_name="vec_kb_documents", dim=384, db_path=database)
    active.init()
    active.insert("doc-old", embedder.embed("previous vector"))
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    applied = operator.apply("vector.documents")
    _ordinary_vector_insert(
        database,
        active.table_name,
        "runtime-drift",
        embedder.embed("runtime drift marker"),
    )

    with pytest.raises(RuntimeError, match="active vector index changed since apply"):
        operator.rollback("vector.documents")

    assert set(active.list_ids()) == {"doc-new", "runtime-drift"}
    with closing(sqlite3.connect(database)) as connection:
        retained = connection.execute(
            "SELECT provenance_json FROM migration_operator_runs "
            "WHERE owner='vector.documents' AND state='applied'"
        ).fetchone()[0]
    retained_payload = json.loads(retained)
    assert retained_payload["rollback"] == applied["provenance"]["rollback"]
    failed = _state(operator.status(), "vector.documents")
    assert failed["state"] == "failed"
    assert failed["provenance"]["operation"] == "rollback"
    assert "active vector index changed since apply" in failed["provenance"]["error_message"]
    assert "active_fingerprint" in applied["provenance"]

    active.delete("runtime-drift")
    assert operator.rollback("vector.documents")["state"] == "rolled_back"
    assert active.list_ids() == ["doc-old"]


def test_taskpack_rollback_rolled_back_provenance_failure_keeps_applied_state(
    monkeypatch, tmp_path: Path
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_legacy_taskpack_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("taskpack.sqlite")
    original_insert = operator._insert_record

    def fail_rolled_back_record(connection, owner, *, state, operation, provenance):
        if state == "rolled_back":
            raise RuntimeError("injected rolled_back provenance failure")
        return original_insert(
            connection,
            owner,
            state=state,
            operation=operation,
            provenance=provenance,
        )

    monkeypatch.setattr(operator, "_insert_record", fail_rolled_back_record)
    with pytest.raises(RuntimeError, match="injected rolled_back provenance failure"):
        operator.rollback("taskpack.sqlite")

    with closing(sqlite3.connect(database)) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(kb_taskpacks)")}
        assert "requires_review" in columns
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM schema_migrations WHERE version IN (2, 3)"
            ).fetchone()[0]
            == 2
        )
    failed = _state(operator.status(), "taskpack.sqlite")
    assert failed["state"] == "failed"
    assert failed["provenance"]["operation"] == "rollback"

    monkeypatch.undo()
    assert operator.rollback("taskpack.sqlite")["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(kb_taskpacks)")}
    assert "context_id" not in columns


def test_vector_rollback_rolled_back_provenance_failure_keeps_applied_state(
    monkeypatch, tmp_path: Path
) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    active = VectorDB(table_name="vec_kb_documents", dim=384, db_path=database)
    active.init()
    active.insert("doc-old", SimpleTextEmbedder(384).embed("previous"))
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("vector.documents")
    original_insert = operator._insert_record

    def fail_rolled_back_record(connection, owner, *, state, operation, provenance):
        if state == "rolled_back":
            raise RuntimeError("injected vector rolled_back provenance failure")
        return original_insert(
            connection,
            owner,
            state=state,
            operation=operation,
            provenance=provenance,
        )

    monkeypatch.setattr(operator, "_insert_record", fail_rolled_back_record)
    with pytest.raises(RuntimeError, match="injected vector rolled_back provenance failure"):
        operator.rollback("vector.documents")

    assert active.list_ids() == ["doc-new"]
    failed = _state(operator.status(), "vector.documents")
    assert failed["state"] == "failed"
    assert failed["provenance"]["operation"] == "rollback"

    monkeypatch.undo()
    assert operator.rollback("vector.documents")["state"] == "rolled_back"
    assert active.list_ids() == ["doc-old"]


def test_fts_rollback_rolled_back_provenance_failure_keeps_applied_state(
    monkeypatch, tmp_path: Path
) -> None:
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("fts.documents")
    original_insert = operator._insert_record

    def fail_rolled_back_record(connection, owner, *, state, operation, provenance):
        if state == "rolled_back":
            raise RuntimeError("injected FTS rolled_back provenance failure")
        return original_insert(
            connection,
            owner,
            state=state,
            operation=operation,
            provenance=provenance,
        )

    monkeypatch.setattr(operator, "_insert_record", fail_rolled_back_record)
    with pytest.raises(RuntimeError, match="injected FTS rolled_back provenance failure"):
        operator.rollback("fts.documents")

    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'verified'"
            ).fetchone()[0]
            == "doc-new"
        )
    failed = _state(operator.status(), "fts.documents")
    assert failed["state"] == "failed"
    assert failed["provenance"]["operation"] == "rollback"

    monkeypatch.undo()
    assert operator.rollback("fts.documents")["state"] == "rolled_back"
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'previous'"
            ).fetchone()[0]
            == "doc-old"
        )


def test_fts_apply_blocks_ordinary_source_writer_during_activation(
    monkeypatch, tmp_path: Path
) -> None:
    from shared.fts_index import FtsIndexCandidate
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    candidate = operator._build_candidate(operator.registry.get("fts.documents"))
    original_verify = FtsIndexCandidate.verify
    attempted = Event()
    writer_blocked = Event()
    writer_succeeded = Event()

    def verify_and_try_ordinary_writer(self, *args, **kwargs):
        result = original_verify(self, *args, **kwargs)
        if self.table_name != candidate.table_name or attempted.is_set():
            return result
        attempted.set()
        with closing(sqlite3.connect(database, timeout=0)) as connection:
            try:
                connection.execute(
                    "UPDATE kb_documents SET content='ordinary source writer' WHERE id='doc-new'"
                )
                connection.commit()
                writer_succeeded.set()
            except sqlite3.OperationalError as exc:
                connection.rollback()
                if not _sqlite_locked(exc):
                    raise
                writer_blocked.set()
        return result

    monkeypatch.setattr(FtsIndexCandidate, "verify", verify_and_try_ordinary_writer)

    assert operator.apply("fts.documents", candidate=candidate)["state"] == "applied"
    assert attempted.is_set()
    assert writer_blocked.is_set()
    assert not writer_succeeded.is_set()
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute("SELECT content FROM kb_documents WHERE id='doc-new'").fetchone()[0]
            == "verified candidate content"
        )


def test_vector_apply_blocks_ordinary_active_writer_during_activation(
    monkeypatch, tmp_path: Path
) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB, VectorIndexCandidate
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    embedder = SimpleTextEmbedder(384)
    active = VectorDB(table_name="vec_kb_documents", dim=384, db_path=database)
    active.init()
    active.insert("doc-old", embedder.embed("previous vector"))
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    candidate = operator._build_candidate(operator.registry.get("vector.documents"))
    original_verify = VectorIndexCandidate.verify
    attempted = Event()
    writer_blocked = Event()
    writer_succeeded = Event()

    def verify_and_try_ordinary_writer(self, *args, **kwargs):
        result = original_verify(self, *args, **kwargs)
        if self.table_name != candidate.table_name or attempted.is_set():
            return result
        attempted.set()
        try:
            _ordinary_vector_insert(
                database,
                active.table_name,
                "runtime-drift",
                embedder.embed("ordinary active writer"),
            )
            writer_succeeded.set()
        except sqlite3.OperationalError as exc:
            if not _sqlite_locked(exc):
                raise
            writer_blocked.set()
        return result

    monkeypatch.setattr(VectorIndexCandidate, "verify", verify_and_try_ordinary_writer)

    assert operator.apply("vector.documents", candidate=candidate)["state"] == "applied"
    assert attempted.is_set()
    assert writer_blocked.is_set()
    assert not writer_succeeded.is_set()
    assert active.list_ids() == ["doc-new"]
    assert operator.rollback("vector.documents")["state"] == "rolled_back"
    assert active.list_ids() == ["doc-old"]


def test_fts_rollback_blocks_ordinary_active_writer_during_snapshot(
    monkeypatch, tmp_path: Path
) -> None:
    from shared import fts_index
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("fts.documents")
    applied = _state(operator.status(), "fts.documents")
    backup_table = applied["provenance"]["rollback"]["data"]["backup_table"]
    real_connect = sqlite3.connect
    attempted = Event()
    writer_blocked = Event()
    writer_succeeded = Event()

    def try_ordinary_writer() -> None:
        attempted.set()
        with closing(real_connect(str(database), timeout=0)) as connection:
            try:
                connection.execute(
                    "INSERT INTO kb_documents_fts(rowid, id, title, content, source) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (99, "runtime", "Runtime", "ordinary rollback writer", "test"),
                )
                connection.commit()
                writer_succeeded.set()
            except sqlite3.OperationalError as exc:
                connection.rollback()
                if not _sqlite_locked(exc):
                    raise
                writer_blocked.set()

    class HookedConnection:
        def __init__(self, inner):
            object.__setattr__(self, "_inner", inner)

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def __setattr__(self, name, value):
            setattr(self._inner, name, value)

        def execute(self, sql, parameters=()):
            if f'FROM "{backup_table}"' in str(sql) and not attempted.is_set():
                try_ordinary_writer()
            return self._inner.execute(sql, parameters)

    def hooked_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        if Path(str(args[0])).resolve() == database.resolve():
            return HookedConnection(connection)
        return connection

    monkeypatch.setattr(fts_index.sqlite3, "connect", hooked_connect)

    assert operator.rollback("fts.documents")["state"] == "rolled_back"
    assert attempted.is_set()
    assert writer_blocked.is_set()
    assert not writer_succeeded.is_set()
    with closing(real_connect(str(database))) as connection:
        assert (
            connection.execute(
                "SELECT id FROM kb_documents_fts WHERE kb_documents_fts MATCH 'previous'"
            ).fetchone()[0]
            == "doc-old"
        )


def test_vector_rollback_blocks_ordinary_active_writer_during_validation(
    monkeypatch, tmp_path: Path
) -> None:
    from app.memory.vector_db import SimpleTextEmbedder, VectorDB
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "runtime.sqlite"
    _create_search_database(database)
    embedder = SimpleTextEmbedder(384)
    active = VectorDB(table_name="vec_kb_documents", dim=384, db_path=database)
    active.init()
    active.insert("doc-old", embedder.embed("previous vector"))
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("vector.documents")
    real_connect = sqlite3.connect
    real_get_conn = VectorDB._get_conn
    attempted = Event()
    writer_blocked = Event()
    writer_succeeded = Event()

    def try_ordinary_writer() -> None:
        attempted.set()
        try:
            _ordinary_vector_insert(
                database,
                active.table_name,
                "runtime-rollback",
                embedder.embed("ordinary rollback writer"),
                connect=real_connect,
            )
            writer_succeeded.set()
        except sqlite3.OperationalError as exc:
            if not _sqlite_locked(exc):
                raise
            writer_blocked.set()

    class HookedConnection:
        def __init__(self, inner):
            object.__setattr__(self, "_inner", inner)

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def __setattr__(self, name, value):
            setattr(self._inner, name, value)

        def execute(self, sql, parameters=()):
            if (
                "SELECT name FROM sqlite_master WHERE name IN" in str(sql)
                and active.table_name in parameters
                and not attempted.is_set()
            ):
                try_ordinary_writer()
            return self._inner.execute(sql, parameters)

    def hooked_get_conn(self):
        connection = real_get_conn(self)
        if Path(str(self.db_path)).resolve() == database.resolve():
            return HookedConnection(connection)
        return connection

    monkeypatch.setattr(VectorDB, "_get_conn", hooked_get_conn)

    assert operator.rollback("vector.documents")["state"] == "rolled_back"
    assert attempted.is_set()
    assert writer_blocked.is_set()
    assert not writer_succeeded.is_set()
    assert active.list_ids() == ["doc-old"]
