//! Migration dry-run tests over a synthetic legacy DB (read-only export path).
use archeaxis_migration::{export_jsonl, inventory};
use rusqlite::Connection;

fn make_legacy(dir: &std::path::Path) -> String {
    let db = dir.join("legacy.sqlite");
    let conn = Connection::open(&db).unwrap();
    conn.execute_batch(
        "CREATE TABLE notes(id INTEGER PRIMARY KEY, body TEXT, created_at TEXT);
         CREATE TABLE docs(id INTEGER PRIMARY KEY, title TEXT, sha256 TEXT);
         CREATE TABLE empty_table(id INTEGER PRIMARY KEY, value TEXT);",
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
    assert_eq!(m1.tables["empty_table"].rows, 0);
    assert_eq!(
        std::fs::read(std::path::Path::new(&out).join("empty_table.jsonl")).unwrap(),
        b""
    );
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

/// A table this build cannot read is named, not turned into "the database is unreadable".
///
/// The real legacy store carries a `sqlite-vec` `vec0` index table, which this build has no module
/// for. Without this, the whole inventory aborts with `no such module: vec0` and reads as a corrupt
/// file rather than as one table needing an extension.
#[test]
fn an_unreadable_table_is_named_beside_the_readable_ones() {
    use archeaxis_migration::inventory_reporting_unreadable;

    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("legacy.sqlite");
    {
        let conn = Connection::open(&db).unwrap();
        // A schema entry whose backing table cannot be opened stands in for a table whose module
        // is absent: both fail only when the table is read, which is the case being covered.
        conn.execute_batch(
            "CREATE TABLE readable(id INTEGER PRIMARY KEY, name TEXT);
             INSERT INTO readable(name) VALUES('a');
             PRAGMA writable_schema=ON;
             INSERT INTO sqlite_master(type,name,tbl_name,rootpage,sql)
             VALUES('table','ghost','ghost',0,'CREATE TABLE ghost(id INTEGER)');
             PRAGMA writable_schema=OFF;",
        )
        .unwrap();
        conn.cache_flush().unwrap();
    }
    let (readable, unreadable) =
        inventory_reporting_unreadable(db.to_str().unwrap()).unwrap();
    assert_eq!(
        readable.iter().find(|t| t.name == "readable").map(|t| t.row_count),
        Some(1)
    );
    assert!(unreadable.contains_key("ghost"), "{unreadable:?}");
    assert!(!unreadable.values().any(|reason| reason.is_empty()));

    // The strict form still refuses the whole inventory, and now says which table it refused over.
    let error = inventory(db.to_str().unwrap()).unwrap_err().to_string();
    assert!(error.contains("ghost"), "{error}");
}

/// A table this build cannot open is named in the manifest, and everything else is still exported.
///
/// The real legacy store hits exactly this: one `sqlite-vec` table and no such module here, which
/// used to abort the export and preserve nothing at all. A partial preservation that says which
/// part is missing is a real result; one that aborts is a total loss of the readable tables.
#[test]
fn an_unreadable_table_is_named_in_the_manifest_and_the_rest_is_still_exported() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("legacy.sqlite");
    {
        let conn = Connection::open(&db).unwrap();
        conn.execute_batch(
            "CREATE TABLE readable(id INTEGER PRIMARY KEY, name TEXT);
             INSERT INTO readable(name) VALUES('kept');
             PRAGMA writable_schema=ON;
             INSERT INTO sqlite_master(type,name,tbl_name,rootpage,sql)
             VALUES('table','ghost','ghost',0,'CREATE TABLE ghost(id INTEGER)');
             PRAGMA writable_schema=OFF;",
        )
        .unwrap();
        conn.cache_flush().unwrap();
    }
    let out = dir.path().join("export");
    let manifest = export_jsonl(db.to_str().unwrap(), out.to_str().unwrap()).unwrap();

    assert_eq!(manifest.tables.len(), 1, "{:?}", manifest.tables);
    assert_eq!(manifest.tables["readable"].rows, 1);
    assert!(out.join("readable.jsonl").is_file(), "the readable table must still be exported");
    assert!(!out.join("ghost.jsonl").exists(), "an unreadable table has no file");

    assert_eq!(manifest.unqueried_tables.len(), 1, "{:?}", manifest.unqueried_tables);
    assert!(manifest.unqueried_tables.contains_key("ghost"), "{:?}", manifest.unqueried_tables);
    assert!(!manifest.unqueried_tables["ghost"].is_empty());

    // The digest covers the gap: an export of the same readable table *without* the unreadable one
    // must not share this manifest's digest, or a reader comparing digests could not tell a partial
    // preservation from a whole one.
    let clean_db = dir.path().join("clean.sqlite");
    {
        let conn = Connection::open(&clean_db).unwrap();
        conn.execute_batch(
            "CREATE TABLE readable(id INTEGER PRIMARY KEY, name TEXT);
             INSERT INTO readable(name) VALUES('kept');",
        )
        .unwrap();
    }
    let clean = export_jsonl(
        clean_db.to_str().unwrap(),
        dir.path().join("export-clean").to_str().unwrap(),
    )
    .unwrap();
    assert!(clean.unqueried_tables.is_empty(), "{:?}", clean.unqueried_tables);
    assert_eq!(clean.tables["readable"].sha256, manifest.tables["readable"].sha256);
    assert_ne!(clean.manifest_sha256, manifest.manifest_sha256);
}
