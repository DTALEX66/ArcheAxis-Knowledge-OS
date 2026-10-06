//! Selected product document scope: no Agent-memory or credential row export.
use archeaxis_migration::export_typed_document_content_jsonl;
use rusqlite::Connection;
use sha2::{Digest, Sha256};
#[test]
fn exact_content_scope_keeps_raw_types_and_unknown_virtual_schema_without_secret_rows() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("legacy.sqlite");
    let conn = Connection::open(&db).unwrap();
    conn.execute_batch("CREATE TABLE kb_documents(id INTEGER PRIMARY KEY,title TEXT,content TEXT,source TEXT,tags_json TEXT,created_at TEXT); CREATE TABLE kb_cards(id INTEGER PRIMARY KEY,title TEXT,content BLOB,source_ids_json TEXT,tags_json TEXT,review_status TEXT,created_at TEXT); CREATE TABLE memory_records(id INTEGER,content TEXT); CREATE TABLE jobs(lease_token TEXT); CREATE VIRTUAL TABLE unknown_view USING fts5(content); INSERT INTO kb_documents VALUES(37,'title',CAST(x'80ff' AS TEXT),'legacy-source','[]','old'); INSERT INTO kb_cards VALUES(8,'card',x'00ff','[]','[]','legacy-accepted','old'); INSERT INTO memory_records VALUES(1,'PRIVATE_MEMORY_MARKER'); INSERT INTO jobs VALUES('PRIVATE_LEASE_MARKER'); INSERT INTO unknown_view VALUES('UNSELECTED_VIRTUAL_MARKER');").unwrap();
    drop(conn);
    let before = Sha256::digest(std::fs::read(&db).unwrap());
    let output = dir.path().join("export");
    let manifest =
        export_typed_document_content_jsonl(db.to_str().unwrap(), output.to_str().unwrap())
            .unwrap();
    assert_eq!(manifest.tables.len(), 2);
    assert_eq!(manifest.tables["kb_documents"].rows, 1);
    assert_eq!(manifest.tables["kb_cards"].rows, 1);
    assert!(manifest.unqueried_tables.contains_key("memory_records"));
    assert!(manifest.unqueried_tables.contains_key("jobs"));
    assert!(manifest.unqueried_tables.contains_key("unknown_view"));
    assert_eq!(
        manifest.disposition,
        "SELECTED_CONTENT_PRESERVED_ORIGINAL_RETAINED_NOT_SEMANTICALLY_MIGRATED"
    );
    let document =
        std::fs::read_to_string(output.join(&manifest.tables["kb_documents"].file)).unwrap();
    assert!(document.contains("80ff"));
    let card = std::fs::read_to_string(output.join(&manifest.tables["kb_cards"].file)).unwrap();
    assert!(card.contains("00ff"));
    for file in std::fs::read_dir(&output).unwrap() {
        let bytes = std::fs::read(file.unwrap().path()).unwrap();
        let text = String::from_utf8_lossy(&bytes);
        for marker in [
            "PRIVATE_MEMORY_MARKER",
            "PRIVATE_LEASE_MARKER",
            "UNSELECTED_VIRTUAL_MARKER",
        ] {
            assert!(!text.contains(marker));
            assert!(!text.contains(&hex::encode(marker.as_bytes())));
        }
    }
    assert_eq!(
        before.as_slice(),
        Sha256::digest(std::fs::read(&db).unwrap()).as_slice()
    );
}
#[test]
fn content_table_with_protected_column_fails_before_any_row_export() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("legacy.sqlite");
    let conn = Connection::open(&db).unwrap();
    conn.execute_batch("CREATE TABLE kb_cards(id INTEGER,content TEXT); CREATE TABLE kb_documents(id INTEGER,content TEXT,lease_token TEXT); INSERT INTO kb_documents VALUES(1,'ordinary','PRIVATE_LEASE_MARKER')").unwrap();
    drop(conn);
    let output = dir.path().join("export");
    assert!(
        export_typed_document_content_jsonl(db.to_str().unwrap(), output.to_str().unwrap())
            .is_err()
    );
    assert!(!output.join("typed-export-manifest.json").exists());
    for file in std::fs::read_dir(output).unwrap() {
        let text = std::fs::read_to_string(file.unwrap().path()).unwrap();
        assert!(!text.contains("PRIVATE_LEASE_MARKER"));
        assert!(!text.contains(&hex::encode(b"PRIVATE_LEASE_MARKER")));
    }
}

#[test]
fn selected_scope_requires_both_tables_before_creating_export_directory() {
    for schema in [
        "CREATE TABLE kb_documents(id INTEGER, content TEXT)",
        "CREATE TABLE unrelated(id INTEGER)",
    ] {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("legacy.sqlite");
        let conn = Connection::open(&db).unwrap();
        conn.execute_batch(schema).unwrap();
        drop(conn);
        let output = dir.path().join("export");
        assert!(
            export_typed_document_content_jsonl(db.to_str().unwrap(), output.to_str().unwrap())
                .is_err()
        );
        assert!(!output.exists());
    }
}

#[test]
fn exact_intake_scope_preserves_safe_fields_without_leasing_or_memory_rows() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("legacy.sqlite");
    let conn = Connection::open(&db).unwrap();
    conn.execute_batch("CREATE TABLE ir_intake_cards(id INTEGER,title TEXT,why TEXT,what_to_absorb_json TEXT,what_not_to_absorb_json TEXT,source_ids_json TEXT,risk_level TEXT,target_repo TEXT,created_at TEXT); INSERT INTO ir_intake_cards VALUES(1,'title','known why','[]','[]','[]','unknown','project','old'); CREATE TABLE memory_records(content TEXT); INSERT INTO memory_records VALUES('PRIVATE_MEMORY_MARKER')").unwrap();
    drop(conn);
    let output = dir.path().join("export");
    let manifest = archeaxis_migration::export_typed_intake_content_jsonl(
        db.to_str().unwrap(),
        output.to_str().unwrap(),
    )
    .unwrap();
    assert_eq!(manifest.tables.len(), 1);
    assert_eq!(manifest.tables["ir_intake_cards"].rows, 1);
    assert!(manifest.unqueried_tables.contains_key("memory_records"));
    let row =
        std::fs::read_to_string(output.join(&manifest.tables["ir_intake_cards"].file)).unwrap();
    assert!(row.contains(&hex::encode(b"known why")));
    assert!(!row.contains(&hex::encode(b"PRIVATE_MEMORY_MARKER")));
}
#[test]
fn intake_scope_rejects_missing_table_and_protected_column() {
    for schema in [
        "CREATE TABLE other(content TEXT)",
        "CREATE TABLE ir_intake_cards(title TEXT,why TEXT,lease_token TEXT)",
    ] {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("legacy.sqlite");
        let conn = Connection::open(&db).unwrap();
        conn.execute_batch(schema).unwrap();
        drop(conn);
        assert!(
            archeaxis_migration::export_typed_intake_content_jsonl(
                db.to_str().unwrap(),
                dir.path().join("export").to_str().unwrap()
            )
            .is_err()
        );
    }
}
