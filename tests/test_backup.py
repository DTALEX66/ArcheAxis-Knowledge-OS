from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest

from shared import backup as backup_module


def test_restore_backup_stages_and_activates_explicit_backup_path(
    monkeypatch, tmp_path, capsys
):
    from app import runtime_entrypoint

    backup_path = tmp_path / "offline-backup.sqlite"
    candidate_path = tmp_path / "restore-candidate.sqlite"
    database_path = tmp_path / "runtime.sqlite"
    events: list[tuple[str, str]] = []

    def restore(source: str) -> str:
        events.append(("restore", source))
        return str(candidate_path)

    def activate_restore(candidate: str) -> str:
        events.append(("activate_restore", candidate))
        return str(database_path)

    monkeypatch.setattr(backup_module, "restore", restore)
    monkeypatch.setattr(backup_module, "activate_restore", activate_restore)
    monkeypatch.setenv("ARCHEAXIS_RESTORE_BACKUP", "legacy-env-backup.sqlite")
    monkeypatch.setenv("COGNITIVE_RESTORE_BACKUP", "legacy-cognitive-backup.sqlite")

    assert runtime_entrypoint.main(["restore-backup", str(backup_path)]) == 0

    assert events == [
        ("restore", str(backup_path)),
        ("activate_restore", str(candidate_path)),
    ]
    assert capsys.readouterr().out == '{"status":"restored"}\n'


def _create_migrated_database(monkeypatch, path: Path, backup_dir: Path, title: str) -> None:
    from app.memory import database as memory_database
    from shared import migration, storage

    monkeypatch.setattr(memory_database, "DB_PATH", path)
    monkeypatch.setattr(storage, "DB_PATH", path)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)
    storage.init()
    memory_database.init_db()
    migration.migrate(db_path=path, backup_dir=backup_dir)
    storage.insert(
        "kb_documents",
        {
            "id": "doc-1",
            "title": title,
            "content": "content before restore",
            "source": "test",
        },
    )


def test_backup_candidate_and_offline_activation_restore_expected_snapshot(
    monkeypatch, tmp_path
):
    database = tmp_path / "runtime" / "cognitive.sqlite"
    database.parent.mkdir()
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(backup_module, "DB_PATH", database)
    monkeypatch.setattr(backup_module, "BACKUP_DIR", backup_dir)
    _create_migrated_database(monkeypatch, database, backup_dir, "before")

    snapshot = Path(backup_module.backup())
    assert snapshot.with_suffix(".sqlite.manifest.json").is_file()
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("UPDATE kb_documents SET title='after' WHERE id='doc-1'")
        conn.commit()

    candidate = Path(backup_module.restore(str(snapshot)))
    assert candidate.with_suffix(".sqlite.manifest.json").is_file()
    with closing(sqlite3.connect(database)) as conn:
        assert conn.execute("SELECT title FROM kb_documents WHERE id='doc-1'").fetchone()[0] == "after"
    with closing(sqlite3.connect(candidate)) as conn:
        assert conn.execute("SELECT title FROM kb_documents WHERE id='doc-1'").fetchone()[0] == "before"
    assert candidate.parent == backup_dir / "restore-candidates"

    identity_path = backup_module._volume_identity_path(database)
    original_identity = identity_path.read_text(encoding="ascii")
    identity_path.write_text(str(uuid4()), encoding="ascii")
    with pytest.raises(RuntimeError, match="different database volume"):
        backup_module.activate_restore(str(candidate))
    identity_path.write_text(original_identity, encoding="ascii")

    other_database = tmp_path / "runtime" / "other.sqlite"
    monkeypatch.setattr(backup_module, "DB_PATH", other_database)
    with pytest.raises(RuntimeError, match="different target database"):
        backup_module.activate_restore(str(candidate))
    monkeypatch.setattr(backup_module, "DB_PATH", database)

    backup_module.acquire_runtime_lock()
    try:
        with pytest.raises(RuntimeError, match="requires the app to be offline"):
            backup_module.activate_restore(str(candidate))
    finally:
        backup_module.release_runtime_lock()

    activate_locked = backup_module._activate_restore_locked

    def assert_lease_is_held(candidate_path, candidate_hash, target_database):
        with pytest.raises(
            RuntimeError, match="requires the app to be offline"
        ), backup_module.runtime_lease(target_database):
            pass
        return activate_locked(candidate_path, candidate_hash, target_database)

    monkeypatch.setattr(backup_module, "_activate_restore_locked", assert_lease_is_held)
    activated = Path(backup_module.activate_restore(str(candidate)))

    assert activated == database
    with closing(sqlite3.connect(database)) as conn:
        assert conn.execute("SELECT title FROM kb_documents WHERE id='doc-1'").fetchone()[0] == "before"


def test_restore_candidate_rejects_tampered_backup_bytes(monkeypatch, tmp_path):
    database = tmp_path / "runtime" / "cognitive.sqlite"
    database.parent.mkdir()
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(backup_module, "DB_PATH", database)
    monkeypatch.setattr(backup_module, "BACKUP_DIR", backup_dir)
    _create_migrated_database(monkeypatch, database, backup_dir, "before")
    snapshot = Path(backup_module.backup())
    snapshot.write_bytes(snapshot.read_bytes() + b"tamper")

    with pytest.raises(RuntimeError, match="manifest does not match"):
        backup_module.restore(str(snapshot))


def test_failed_compensation_preserves_verified_recovery_copy(monkeypatch, tmp_path):
    database = tmp_path / "runtime" / "cognitive.sqlite"
    database.parent.mkdir()
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(backup_module, "DB_PATH", database)
    monkeypatch.setattr(backup_module, "BACKUP_DIR", backup_dir)
    _create_migrated_database(monkeypatch, database, backup_dir, "before")
    snapshot = Path(backup_module.backup())
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("UPDATE kb_documents SET title='last-known-good' WHERE id='doc-1'")
        conn.commit()
    candidate = Path(backup_module.restore(str(snapshot)))

    real_validate = backup_module._validate_sqlite_database
    database_validations = 0

    def fail_post_replace_validation(path):
        nonlocal database_validations
        result = real_validate(path)
        if Path(path) == database:
            database_validations += 1
            if database_validations == 2:
                raise RuntimeError("forced post-replacement validation failure")
        return result

    real_replace = Path.replace

    def fail_compensation_replace(path, target):
        if ".compensation_" in path.name:
            raise OSError("forced compensation replace failure")
        return real_replace(path, target)

    monkeypatch.setattr(backup_module, "_validate_sqlite_database", fail_post_replace_validation)
    monkeypatch.setattr(Path, "replace", fail_compensation_replace)

    with pytest.raises(RuntimeError, match="recovery copy was preserved") as error:
        backup_module.activate_restore(str(candidate))

    preserved = list(database.parent.glob(".cognitive.sqlite.pre_restore_*.sqlite"))
    assert len(preserved) == 1
    assert str(preserved[0]) in str(error.value)
    with closing(sqlite3.connect(preserved[0])) as conn:
        title = conn.execute("SELECT title FROM kb_documents WHERE id='doc-1'").fetchone()[0]
    assert title == "last-known-good"


def test_failed_compensation_validation_preserves_verified_recovery_copy(
    monkeypatch, tmp_path
):
    database = tmp_path / "runtime" / "cognitive.sqlite"
    database.parent.mkdir()
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(backup_module, "DB_PATH", database)
    monkeypatch.setattr(backup_module, "BACKUP_DIR", backup_dir)
    _create_migrated_database(monkeypatch, database, backup_dir, "before")
    snapshot = Path(backup_module.backup())
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("UPDATE kb_documents SET title='last-known-good' WHERE id='doc-1'")
        conn.commit()
    candidate = Path(backup_module.restore(str(snapshot)))

    real_validate = backup_module._validate_sqlite_database
    database_validations = 0

    def fail_live_validations(path):
        nonlocal database_validations
        result = real_validate(path)
        if Path(path) == database:
            database_validations += 1
            if database_validations in {2, 3}:
                raise RuntimeError("forced live validation failure")
        return result

    monkeypatch.setattr(backup_module, "_validate_sqlite_database", fail_live_validations)

    with pytest.raises(RuntimeError, match="recovery copy was preserved") as error:
        backup_module.activate_restore(str(candidate))

    preserved = list(database.parent.glob(".cognitive.sqlite.pre_restore_*.sqlite"))
    assert len(preserved) == 1
    assert preserved[0].is_file()
    assert str(preserved[0]) in str(error.value)
    with closing(sqlite3.connect(preserved[0])) as conn:
        title = conn.execute("SELECT title FROM kb_documents WHERE id='doc-1'").fetchone()[0]
    assert title == "last-known-good"
