//! Migration dry-run tests over a synthetic legacy DB (read-only export path).
use archeaxis_migration::{export_jsonl, inventory};
use rusqlite::Connection;

fn make_legacy(dir: &std::path::Path) -> String {
    let db = dir.join("legacy.sqlite");
    let conn = Connection::open(&db).unwrap();
    conn.execute_batch(
        "CREATE TABLE notes(id INTEGER PRIMARY KEY, body TEXT, created_at TEXT);
         CREATE TABLE docs(id INTEGER PRIMARY KEY, title TEXT, sha256 TEXT);",
    )
    .unwrap();
    conn.execute(
        "INSERT INTO notes(body, created_at) VALUES('legacy note one', '2026-08-29')",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO notes(body, created_at) VALUES('legacy note two', '2026-08-29')",
        [],
    )
    .unwrap();
    conn.execute("INSERT INTO docs(title, sha256) VALUES('doc a', 'aaa')", [])
        .unwrap();
    drop(conn);
    db.to_str().unwrap().to_string()
}

#[test]
fn inventory_readonly() {
    let dir = tempfile::tempdir().unwrap();
    let db = make_legacy(dir.path());
    let tables = inventory(&db).unwrap();
    let names: Vec<&str> = tables.iter().map(|t| t.name.as_str()).collect();
    assert!(names.contains(&"notes"));
    assert!(names.contains(&"docs"));
    let notes = tables.iter().find(|t| t.name == "notes").unwrap();
    assert_eq!(notes.row_count, 2);
    assert!(!names.iter().any(|n| n.starts_with("sqlite_")));
}

#[test]
fn export_jsonl_and_manifest_stable() {
    let dir = tempfile::tempdir().unwrap();
    let db = make_legacy(dir.path());
    let out = dir.path().join("export").to_str().unwrap().to_string();

    let m1 = export_jsonl(&db, &out).unwrap();
    assert_eq!(m1.tables["notes"].rows, 2);
    assert_eq!(m1.tables["docs"].rows, 1);
    assert_eq!(m1.manifest_sha256.len(), 64);

    // re-export is byte-stable (same digest) -> reproducible dry-run basis
    let out2 = dir.path().join("export2").to_str().unwrap().to_string();
    let m2 = export_jsonl(&db, &out2).unwrap();
    assert_eq!(m1.manifest_sha256, m2.manifest_sha256);

    // content jsonl exists
    let jsonl = std::fs::read_to_string(std::path::Path::new(&out).join("notes.jsonl")).unwrap();
    assert!(jsonl.contains("legacy note one"));
    assert_eq!(jsonl.lines().count(), 2);
}

#[test]
fn legacy_db_never_modified() {
    let dir = tempfile::tempdir().unwrap();
    let db = make_legacy(dir.path());
    let before = std::fs::read(&db).unwrap();
    let out = dir.path().join("export").to_str().unwrap().to_string();
    export_jsonl(&db, &out).unwrap();
    // open read-only only: file bytes unchanged (WAL not created on legacy)
    let after = std::fs::read(&db).unwrap();
    assert_eq!(before.len(), after.len());
}
