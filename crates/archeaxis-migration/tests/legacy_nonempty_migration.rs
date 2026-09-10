//! R07: first non-empty legacy migration path, proven end to end on a synthetic
//! legacy library (notes + docs + attachments + links + learning history):
//! read-only snapshot, hash/count-verified export, staged import with the legacy
//! schedule preserved where it exists, unscheduled where it does not, idempotent
//! re-runs, and a byte-identical legacy database afterwards (no dual-write).
//!
//! The owner's real private library was not provided, so this proves the software
//! path on synthetic data only - the real-library qualification stays open.

use archeaxis_migration::{export_jsonl, inventory, stage_demo_semantic_import, stage_legacy_learning_history};
use rusqlite::Connection;
use sha2::{Digest, Sha256};

fn bytes_sha256(path: &std::path::Path) -> String {
    hex::encode(Sha256::digest(std::fs::read(path).unwrap()))
}

/// Build a NON-EMPTY legacy database with the tables the migration understands.
fn build_legacy_db(path: &std::path::Path) {
    let conn = Connection::open(path).unwrap();
    conn.execute_batch(
        "CREATE TABLE notes(id INTEGER PRIMARY KEY, body TEXT, created_at TEXT);
         CREATE TABLE docs(id INTEGER PRIMARY KEY, title TEXT, sha256 TEXT);
         CREATE TABLE attachments(id INTEGER PRIMARY KEY, name TEXT, bytes BLOB);
         CREATE TABLE links(id INTEGER PRIMARY KEY, from_id INTEGER, to_id INTEGER);
         CREATE TABLE learning_history(id INTEGER PRIMARY KEY, item TEXT, kind TEXT,
                                       outcome TEXT, next_review_days INTEGER, created_at TEXT);
         INSERT INTO notes(body, created_at) VALUES
            ('legacy note alpha', '2026-08-01T00:00:00Z'),
            ('legacy note beta',  '2026-08-02T00:00:00Z'),
            ('legacy note gamma', '2026-08-03T00:00:00Z');
         INSERT INTO docs(title, sha256) VALUES ('legacy doc', 'deadbeef');
         INSERT INTO attachments(name, bytes) VALUES ('a.png', X'89504E47');
         INSERT INTO links(from_id, to_id) VALUES (1, 2), (2, 3);
         INSERT INTO learning_history(item, kind, outcome, next_review_days, created_at) VALUES
            ('legacy-card-1', 'review', 'correct',   7, '2026-08-04T00:00:00Z'),
            ('legacy-card-2', 'review', 'incorrect', 0, '2026-08-05T00:00:00Z'),
            ('legacy-card-3', 'review', 'correct', NULL, '2026-08-06T00:00:00Z');",
    )
    .unwrap();
}

#[test]
fn non_empty_legacy_library_stages_notes_and_learning_history_without_touching_the_source() {
    let dir = tempfile::tempdir().unwrap();
    let legacy = dir.path().join("legacy.sqlite");
    build_legacy_db(&legacy);
    let before = bytes_sha256(&legacy);

    // Read-only inventory sees the real non-empty tables.
    let tables = inventory(legacy.to_str().unwrap()).unwrap();
    let names: Vec<String> = tables.iter().map(|t| t.name.clone()).collect();
    for expected in ["notes", "docs", "attachments", "links", "learning_history"] {
        assert!(names.iter().any(|n| n == expected), "missing {expected} in {names:?}");
    }

    // Consistent read-only export, then verify + stage.
    let export = dir.path().join("export");
    std::fs::create_dir_all(&export).unwrap();
    let manifest = export_jsonl(legacy.to_str().unwrap(), export.to_str().unwrap()).unwrap();
    assert_eq!(manifest.tables.get("notes").unwrap().rows, 3);
    assert_eq!(manifest.tables.get("learning_history").unwrap().rows, 3);

    let staging = dir.path().join("staging.sqlite");
    let staged = stage_demo_semantic_import(export.to_str().unwrap(), staging.to_str().unwrap()).unwrap();
    assert_eq!(staged.notes_seen, 3);
    assert_eq!(staged.notes_inserted, 3, "all three notes must migrate on a first run");
    assert_eq!(staged.notes_reused, 0);
    assert!(staged.attachments_loss_rows >= 1, "attachments are explicit losses today");
    assert!(staged.links_loss_rows >= 2, "links are explicit losses today");

    let learning = stage_legacy_learning_history(
        export.to_str().unwrap(),
        staging.to_str().unwrap(),
        "learning_history",
    )
    .unwrap();
    assert_eq!(learning.rows_seen, 3);
    assert_eq!(
        learning.staged_scheduled, 1,
        "the legacy 7-day interval is preserved"
    );
    assert_eq!(
        learning.staged_unscheduled, 2,
        "a row with no schedule, and a legacy 0 (due immediately, which vNext history cannot represent), are both recorded as unscheduled and never invented"
    );
    assert_eq!(learning.row_errors, 0);

    // The migrated history is real, and its schedules mean what they claim.
    let conn = Connection::open(&staging).unwrap();
    let with_due: i64 = conn
        .query_row(
            "SELECT count(*) FROM learning_events WHERE next_review IS NOT NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let without_due: i64 = conn
        .query_row("SELECT count(*) FROM learning_events WHERE next_review IS NULL", [], |r| r.get(0))
        .unwrap();
    assert_eq!(with_due, 1, "only the legacy 7-day interval is stored as a due date");
    assert_eq!(
        without_due, 2,
        "no-schedule and legacy-due-immediately rows are stored without a due date"
    );

    // Re-running the migration replays receipts instead of duplicating history.
    let again = stage_legacy_learning_history(
        export.to_str().unwrap(),
        staging.to_str().unwrap(),
        "learning_history",
    )
    .unwrap();
    assert_eq!(again.replayed, 3);
    assert_eq!(again.staged_scheduled + again.staged_unscheduled, 0);
    let total: i64 =
        conn.query_row("SELECT count(*) FROM learning_events", [], |r| r.get(0)).unwrap();
    assert_eq!(total, 3, "history must not accumulate on re-runs");

    // No dual-write: the legacy database is byte-identical afterwards.
    assert_eq!(bytes_sha256(&legacy), before, "the legacy database must never be modified");
}
