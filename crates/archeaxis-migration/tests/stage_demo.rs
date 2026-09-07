//! C04: demo migration uses a legal type, verifies exported bytes/rows before
//! writing, stages atomically with honest inserted/reused counts, keeps
//! legacy row ids distinct (equal bodies do not collapse), and re-runs insert
//! zero new rows.

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
    conn.execute("INSERT INTO notes(body, created_at) VALUES('星环 legacy note one', '2026-08-29')", []).unwrap();
    conn.execute("INSERT INTO notes(body, created_at) VALUES('duplicate text body', '2026-08-30')", []).unwrap();
    conn.execute("INSERT INTO notes(body, created_at) VALUES('duplicate text body', '2026-08-31')", []).unwrap();
    conn.execute("INSERT INTO notes(body, created_at) VALUES('', '2026-09-01')", []).unwrap();
    conn.execute("INSERT INTO docs(title, sha256) VALUES('doc a', 'aaa')", []).unwrap();
    conn.execute("INSERT INTO legacy_extra(blob_data) VALUES(x'0102')", []).unwrap();
    drop(conn);
    db.to_str().unwrap().to_string()
}

fn knowledge_count(db: &str) -> i64 {
    let conn = Connection::open(db).unwrap();
    conn.query_row("SELECT count(*) FROM knowledge", [], |r| r.get(0)).unwrap()
}

#[test]
fn demo_stage_is_legal_verified_atomic_idempotent_and_preserves_row_ids() {
    let dir = tempfile::tempdir().unwrap();
    let db = make_legacy(dir.path());
    let out = dir.path().join("export").to_str().unwrap().to_string();
    export_jsonl(&db, &out).unwrap();
    let staging = dir.path().join("staging.sqlite");

    let first = stage_demo_semantic_import(&out, staging.to_str().unwrap()).unwrap();
    assert_eq!(first.notes_seen, 4);
    assert_eq!(first.notes_inserted, 3, "3 non-empty rows inserted");
    assert_eq!(first.notes_row_errors, 1, "empty-body row recorded as error");
    // identical bodies from different legacy ids stay distinct
    assert_eq!(first.notes_inserted + first.notes_reused, 3);
    assert_eq!(first.docs_loss_rows, 1);
    assert!(first.losses.iter().any(|l| l.starts_with("legacy_extra")));
    assert_eq!(knowledge_count(staging.to_str().unwrap()), 3);

    // second run inserts zero new rows and reports all as reused
    let second = stage_demo_semantic_import(&out, staging.to_str().unwrap()).unwrap();
    assert_eq!(second.notes_inserted, 0);
    assert_eq!(second.notes_reused, 3);
    assert_eq!(knowledge_count(staging.to_str().unwrap()), 3);
}

#[test]
fn tampered_jsonl_is_rejected_before_any_write() {
    let dir = tempfile::tempdir().unwrap();
    let db = make_legacy(dir.path());
    let out = dir.path().join("export").to_str().unwrap().to_string();
    export_jsonl(&db, &out).unwrap();
    // tamper with notes.jsonl content
    let notes = std::path::Path::new(&out).join("notes.jsonl");
    let mut data = std::fs::read(&notes).unwrap();
    data[0] ^= 0xFF;
    std::fs::write(&notes, data).unwrap();
    let staging = dir.path().join("staging.sqlite");
    let err = stage_demo_semantic_import(&out, staging.to_str().unwrap());
    assert!(err.is_err(), "hash mismatch must be rejected");
    assert!(!staging.exists(), "no staging db created on rejected import");
}
