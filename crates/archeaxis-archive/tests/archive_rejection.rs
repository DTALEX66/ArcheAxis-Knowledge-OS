use archeaxis_archive::{export_workspace, restore_workspace};
use archeaxis_store_sqlite::init_workspace;

fn fixture() -> (tempfile::TempDir, String, String) {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("source.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    archeaxis_domain::source::import_source(&mut conn, b"original", "input", None).unwrap();
    drop(conn);
    let archive = dir.path().join("archive").to_str().unwrap().to_owned();
    export_workspace(db.to_str().unwrap(), &archive).unwrap();
    let target = dir.path().join("target.sqlite").to_str().unwrap().to_owned();
    (dir, archive, target)
}

#[test]
fn corrupted_table_rejected_without_creating_target() {
    let (_dir, archive, target) = fixture();
    let path = std::path::Path::new(&archive).join("sources.jsonl");
    let text = std::fs::read_to_string(&path).unwrap().replace("input", "tampered");
    std::fs::write(path, text).unwrap();
    assert!(restore_workspace(&archive, &target).is_err());
    assert!(!std::path::Path::new(&target).exists());
}

#[test]
fn corrupt_manifest_and_false_zero_rows_are_rejected() {
    let (_dir, archive, target) = fixture();
    let path = std::path::Path::new(&archive).join("manifest.json");
    let mut value: serde_json::Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    value["tables"]["sources"]["rows"] = 0.into();
    std::fs::write(path, value.to_string()).unwrap();
    assert!(restore_workspace(&archive, &target).is_err());
    assert!(!std::path::Path::new(&target).exists());
}

#[test]
fn constraint_failure_does_not_publish_partial_database() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("invalid.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    archeaxis_domain::source::import_source(&mut conn, b"original", "input", None).unwrap();
    conn.execute_batch("PRAGMA foreign_keys=OFF;
        INSERT INTO transforms(source_id,engine,text) VALUES('absent','test','derived');").unwrap();
    drop(conn);
    let archive = dir.path().join("archive");
    export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    let target = dir.path().join("target.sqlite");
    assert!(restore_workspace(archive.to_str().unwrap(), target.to_str().unwrap()).is_err());
    assert!(!target.exists());
}

#[test]
fn existing_target_is_preserved_byte_for_byte() {
    let (_dir, archive, target) = fixture();
    std::fs::write(&target, b"existing user content").unwrap();
    let before = std::fs::read(&target).unwrap();
    assert!(restore_workspace(&archive, &target).is_err());
    assert_eq!(std::fs::read(&target).unwrap(), before);
}
