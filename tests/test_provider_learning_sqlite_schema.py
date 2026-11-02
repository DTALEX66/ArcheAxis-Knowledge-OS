"""Synthetic SQLite checks of the exact Rust provider-learning DDL.

This does not execute Rust, rusqlite, the migration function, or backup and
restore. It creates only temporary databases through Python's sqlite3 module.
"""

import re
import sqlite3
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "crates" / "archeaxis-store-sqlite" / "src" / "lib.rs"


def provider_schema():
    source = SOURCE.read_text(encoding="utf-8")
    matches = re.findall(r'^const PROVIDER_LEARNING_SCHEMA_SQL: &str = r#"(.*?)"#;', source,
                         flags=re.MULTILINE | re.DOTALL)
    assert len(matches) == 1, "the unique Rust DDL constant must be extractable"
    return matches[0]


def schema_statements():
    """Split original SQLite statements without changing their bytes/text."""
    pending = ""
    statements = []
    for line in provider_schema().splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statements.append(pending)
            pending = ""
    assert not pending.strip() and len(statements) == 2
    return statements


def apply_original_schema(conn):
    for statement in schema_statements():
        conn.execute(statement)


@pytest.fixture
def db(tmp_path):
    connection = sqlite3.connect(tmp_path / "provider-learning.sqlite", isolation_level=None)
    connection.execute("PRAGMA foreign_keys=ON")
    assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
    apply_original_schema(connection)
    try:
        yield connection
    finally:
        connection.close()


def activity(conn, identity):
    conn.execute("INSERT INTO learning_provider_activities(activity_id,request_json,request_sha256) VALUES(?,?,?)",
                 (identity, "{}", "synthetic-digest"))


def attempt(conn, activity_id, attempt_id, state="pending", event=None, result=None,
            digest=None, cancel=None, completed=None):
    conn.execute("""INSERT INTO learning_provider_attempts
        (activity_id,attempt_id,origin_restore_epoch,state,client_event_id,result_json,
         result_sha256,client_cancel_id,completed_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                 (activity_id, attempt_id, "initial", state, event, result, digest, cancel, completed))


def test_exact_schema_creates_two_tables_with_foreign_key(db):
    names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert names == {"learning_provider_activities", "learning_provider_attempts"}
    foreign_keys = db.execute("PRAGMA foreign_key_list(learning_provider_attempts)").fetchall()
    assert len(foreign_keys) == 1 and foreign_keys[0][2:5] == (
        "learning_provider_activities", "activity_id", "activity_id"
    )
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_foreign_key_and_terminal_shapes_reject_invalid_rows(db):
    with pytest.raises(sqlite3.IntegrityError):
        attempt(db, "absent", "orphan")
    activity(db, "activity")
    attempt(db, "activity", "pending")
    attempt(db, "activity", "submitted", "submitted", "event", "{}", "digest", completed="now")
    attempt(db, "activity", "cancelled", "cancelled", cancel="cancel", completed="now")
    bad = [
        {"state": "unrecognized"},
        {"state": None},
        {"state": "pending", "event": "event-pending"},
        {"state": "pending", "result": "{}"},
        {"state": "pending", "digest": "digest"},
        {"state": "pending", "cancel": "cancel-pending"},
        {"state": "pending", "completed": "now"},
        {"state": "submitted", "result": "{}", "digest": "digest", "completed": "now"},
        {"state": "submitted", "event": "e", "digest": "digest", "completed": "now"},
        {"state": "submitted", "event": "e", "result": "{}", "completed": "now"},
        {"state": "submitted", "event": "e", "result": "{}", "digest": "digest"},
        {"state": "submitted", "event": "e", "result": "{}", "digest": "digest", "cancel": "c", "completed": "now"},
        {"state": "cancelled", "completed": "now"},
        {"state": "cancelled", "cancel": "c"},
        {"state": "cancelled", "event": "e", "cancel": "c", "completed": "now"},
        {"state": "cancelled", "result": "{}", "cancel": "c", "completed": "now"},
        {"state": "cancelled", "digest": "digest", "cancel": "c", "completed": "now"},
    ]
    for index, invalid in enumerate(bad):
        with pytest.raises(sqlite3.IntegrityError):
            attempt(db, "activity", f"bad_{index}", **invalid)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM learning_provider_activities WHERE activity_id=?", ("activity",))
    assert db.execute("SELECT count(*) FROM learning_provider_attempts").fetchone() == (3,)
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_event_and_cancel_ids_are_unique_across_activities(db):
    for name in ("first", "second"):
        activity(db, name)
    attempt(db, "first", "same_attempt", "submitted", "shared-event", "{}", "digest", completed="now")
    attempt(db, "first", "cancelled", "cancelled", cancel="shared-cancel", completed="now")
    with pytest.raises(sqlite3.IntegrityError):
        attempt(db, "second", "other", "submitted", "shared-event", "{}", "digest", completed="now")
    with pytest.raises(sqlite3.IntegrityError):
        attempt(db, "second", "other", "cancelled", cancel="shared-cancel", completed="now")
    with pytest.raises(sqlite3.IntegrityError):
        attempt(db, "first", "same_attempt")
    # Attempt identity is scoped to activity, while several pending rows can
    # have NULL event/cancel IDs. These do not demonstrate domain admission.
    attempt(db, "second", "same_attempt")
    attempt(db, "second", "another")
    assert db.execute("SELECT count(*) FROM learning_provider_attempts").fetchone() == (4,)


def test_ddl_failure_rolls_back_first_table_and_preserves_existing_data(tmp_path):
    conn = sqlite3.connect(tmp_path / "rollback.sqlite", isolation_level=None)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("CREATE TABLE synthetic_existing(value TEXT)")
        conn.execute("INSERT INTO synthetic_existing(value) VALUES('preserve')")
        # This deliberately conflicting stand-in forces the second original
        # CREATE TABLE to fail; it is not a copy of the Rust table schema.
        conn.execute("CREATE TABLE learning_provider_attempts(marker TEXT)")
        statements = schema_statements()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(statements[0])
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(statements[1])
        conn.execute("ROLLBACK")
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert names == {"synthetic_existing", "learning_provider_attempts"}
        assert conn.execute("SELECT value FROM synthetic_existing").fetchall() == [("preserve",)]
        assert [row[1] for row in conn.execute("PRAGMA table_info(learning_provider_attempts)")] == ["marker"]
    finally:
        conn.close()


def test_observe_sqlite_limits_not_domain_validation(db):
    # SQLite rowid tables permit NULL in a non-INTEGER PRIMARY KEY unless
    # NOT NULL/STRICT/WITHOUT ROWID closes that gap. This is a limitation of
    # the current DDL, not an assertion that NULL is a valid domain identity.
    activity(db, None)
    activity(db, None)
    assert db.execute("SELECT count(*) FROM learning_provider_activities WHERE activity_id IS NULL").fetchone() == (2,)
    # The DDL also does not parse JSON or validate SHA-256; Rust domain checks
    # must be evaluated separately.
    db.execute("INSERT INTO learning_provider_activities(activity_id,request_json,request_sha256) VALUES(?,?,?)",
               ("unchecked", "not-json", "not-a-sha256"))
    attempt(db, "unchecked", "synthetic", "submitted", "e", "not-json", "not-a-sha256", completed="now")
    assert db.execute("SELECT request_json FROM learning_provider_activities WHERE activity_id='unchecked'").fetchone() == ("not-json",)
