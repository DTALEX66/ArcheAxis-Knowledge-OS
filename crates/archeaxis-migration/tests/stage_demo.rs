//! X10 slice: synthetic non-empty legacy -> vNext staging demo mapping with a
//! loss ledger and idempotent re-run.

use archeaxis_migration::{export_jsonl, stage_demo_semantic_import};
use rusqlite::Connection;

fn make_legacy(dir: &std::path::Path) -> String {
    let db = dir.join("legacy.sqlite");
    let conn = Connection::open(&db).unwrap();
    conn.execute_batch(
        "CREATE TABLE notes(id INTEGER PRIMARY KEY, body TEXT, created_at TEXT);
         CREATE TABLE docs(id INTEGER PRIMARY KEY, title TEXT, sha256 TEXT);
         CREATE TABLE legacy_extra(id INTEGER PRIMARY KEY, blob_data BLOB);",
    )
    .unwrap();
    conn.execute(
        "INSERT INTO notes(body, created_at) VALUES('星环 legacy note one', '2026-08-29')",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO notes(body, created_at) VALUES('second note with plain text', '2026-08-30')",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO notes(body, created_at) VALUES('', '2026-08-31')",
        [], // empty body must become a row error in the ledger
    )
    .unwrap();
    conn.execute("INSERT INTO docs(title, sha256) VALUES('doc a', 'aaa')", [])
        .unwrap();
    conn.execute("INSERT INTO legacy_extra(blob_data) VALUES(x'0102')", [])
        .unwrap();
    drop(conn);
    db.to_str().unwrap().to_string()
}

fn knowledge_count(db: &str) -> i64 {
    let conn = Connection::open(db).unwrap();
    conn.query_row("SELECT count(*) FROM knowledge", [], |r| r.get(0))
        .unwrap()
}

#[test]
fn demo_stage_maps_notes_and_ledgers_the_rest_idempotently() {
    let dir = tempfile::tempdir().unwrap();
    let db = make_legacy(dir.path());
    let out = dir.path().join("export").to_str().unwrap().to_string();
    export_jsonl(&db, &out).unwrap();

    let staging = dir.path().join("staging.sqlite");
    let first = stage_demo_semantic_import(&out, staging.to_str().unwrap()).unwrap();
    assert_eq!(first.notes_imported, 2, "two non-empty notes staged");
    assert_eq!(first.notes_row_errors, 1, "empty-body note recorded as row error");
    assert_eq!(first.docs_loss_rows, 1, "metadata-only docs row recorded as loss");
    assert!(
        first.losses.iter().any(|l| l.starts_with("legacy_extra")),
        "unmapped table in loss ledger"
    );
    assert_eq!(first.other_unmapped_tables, vec!["legacy_extra".to_string()]);

    // Re-run on the SAME staging db: ids are deterministic, so no duplicates.
    let second = stage_demo_semantic_import(&out, staging.to_str().unwrap()).unwrap();
    assert_eq!(second.notes_imported, first.notes_imported);
    assert_eq!(knowledge_count(staging.to_str().unwrap()), 2);
}
