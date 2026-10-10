use archeaxis_store_sqlite::{SCHEMA_VERSION, init_workspace};
use rusqlite::Connection;

// Bounded synthetic old-v11 DB; legacy tables originate from the current shared schema.
// Dedicated archive tests separately validate true historical table/column wire contracts.
#[test]
fn eleven_to_twelve_adds_teaching_tables_without_changing_document_bytes() {
    let d = tempfile::tempdir().unwrap();
    let db = d.path().join("legacy.sqlite");
    let c = init_workspace(db.to_str().unwrap()).unwrap();
    c.execute(
        "INSERT INTO documents(document_id,title,current_version) VALUES('legacy','Original',1)",
        [],
    )
    .unwrap();
    c.execute("INSERT INTO document_versions(document_id,version,editor_json,text_projection,content_sha256,revision_basis) VALUES('legacy',1,'{\"text\":\"原文😀\"}','原文😀','test-hash','saved-original')",[]).unwrap();
    c.execute("INSERT INTO document_checks(check_id,document_id,version,dimension,receipt_json) VALUES('receipt','legacy',1,'recognition_fidelity','{\"status\":\"pending\"}')",[]).unwrap();
    c.execute_batch("DROP TABLE teaching_withdrawals;DROP TABLE teaching_records;UPDATE workspace_meta SET value='11' WHERE key='schema_version';").unwrap();
    drop(c);
    let c = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(SCHEMA_VERSION, 12);
    let row:(String,String,String)=c.query_row("SELECT editor_json,text_projection,revision_basis FROM document_versions WHERE document_id='legacy'",[],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).unwrap();
    assert_eq!(
        row,
        (
            "{\"text\":\"原文😀\"}".into(),
            "原文😀".into(),
            "saved-original".into()
        )
    );
    assert_eq!(
        c.query_row("SELECT receipt_json FROM document_checks", [], |r| r
            .get::<_, String>(0))
            .unwrap(),
        "{\"status\":\"pending\"}"
    );
    for table in ["teaching_records", "teaching_withdrawals"] {
        assert_eq!(
            c.query_row(&format!("SELECT count(*) FROM {table}"), [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            0
        );
    }
    assert_eq!(
        c.query_row(
            "SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'teaching_%'",
            [],
            |r| r.get::<_, i64>(0)
        )
        .unwrap(),
        4
    );
    drop(c);
    let c = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        c.query_row("SELECT count(*) FROM document_versions", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        1
    );
    assert_eq!(
        c.query_row(
            "SELECT value FROM workspace_meta WHERE key='schema_version'",
            [],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        "12"
    );
}
#[test]
fn failed_legacy_migration_leaves_version_and_legacy_rows_unchanged() {
    let d = tempfile::tempdir().unwrap();
    let db = d.path().join("invalid-eleven.sqlite");
    let c = init_workspace(db.to_str().unwrap()).unwrap();
    c.execute_batch("DROP TABLE teaching_withdrawals;DROP TABLE teaching_records;UPDATE workspace_meta SET value='11' WHERE key='schema_version';PRAGMA foreign_keys=OFF;INSERT INTO transforms(source_id,engine,text) VALUES('missing-source','test','retained-invalid-row');").unwrap();
    drop(c);
    assert!(init_workspace(db.to_str().unwrap()).is_err());
    let c = Connection::open_with_flags(db, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
    assert_eq!(
        c.query_row(
            "SELECT value FROM workspace_meta WHERE key='schema_version'",
            [],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        "11"
    );
    assert_eq!(
        c.query_row("SELECT text FROM transforms", [], |r| r.get::<_, String>(0))
            .unwrap(),
        "retained-invalid-row"
    );
    assert_eq!(c.query_row("SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('teaching_records','teaching_withdrawals')",[],|r|r.get::<_,i64>(0)).unwrap(),0);
}
