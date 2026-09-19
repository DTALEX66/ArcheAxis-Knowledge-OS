use archeaxis_domain::{backup, source};
use archeaxis_store_sqlite::{init_workspace, raw_objects};

#[test]
fn missing_original_never_replaces_an_existing_backup_or_publishes_a_partial_one() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    source::import_source(&mut conn, b"original", "original.bin", None).unwrap();
    let old = dir.path().join("old.sqlite");
    backup::backup(&conn, old.to_str().unwrap()).unwrap();
    let original_snapshot = std::fs::read(&old).unwrap();
    source::import_source(&mut conn, b"new source", "new.bin", None).unwrap();
    let digest: String = conn.query_row("SELECT sha256 FROM sources WHERE original_name='new.bin'", [], |r| r.get(0)).unwrap();
    std::fs::remove_file(raw_objects::root(&conn).unwrap().join(digest)).unwrap();
    assert!(backup::backup(&conn, old.to_str().unwrap()).is_err());
    assert!(std::fs::read(&old).unwrap() == original_snapshot, "failed backup overwrote old snapshot");
    let fresh = dir.path().join("fresh.sqlite");
    assert!(backup::backup(&conn, fresh.to_str().unwrap()).is_err());
    assert!(!fresh.exists(), "failed backup published a partial snapshot");
    assert!(!dir.path().join("fresh.sqlite.objects").exists());
}

#[test]
fn online_backup_restores_original_bytes_and_rejects_tampering_without_changing_destination() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    source::import_source(&mut conn, b"\x00\xfforiginal\r\n", "original.bin", None).unwrap();
    let digest: String = conn.query_row("SELECT sha256 FROM sources", [], |r| r.get(0)).unwrap();
    let snapshot = dir.path().join("snapshot.sqlite");
    backup::backup(&conn, snapshot.to_str().unwrap()).unwrap();
    let mut dst = init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    backup::restore(snapshot.to_str().unwrap(), &mut dst).unwrap();
    assert_eq!(raw_objects::read(&dst, &digest).unwrap(), b"\x00\xfforiginal\r\n");
    source::import_source(&mut dst, b"keep me", "keep.bin", None).unwrap();
    std::fs::write(dir.path().join("snapshot.sqlite.objects").join(&digest), b"corrupt").unwrap();
    assert!(backup::restore(snapshot.to_str().unwrap(), &mut dst).is_err());
    assert_eq!(dst.query_row("SELECT count(*) FROM sources", [], |r| r.get::<_, i64>(0)).unwrap(), 2);
}

#[test]
fn verify_counts_rejects_a_tampered_persisted_source_object() {
    let dir = tempfile::tempdir().unwrap();
    let mut source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    source::import_source(&mut source_db, b"original", "original.bin", None).unwrap();
    let snapshot = dir.path().join("snapshot.sqlite");
    backup::backup(&source_db, snapshot.to_str().unwrap()).unwrap();

    let mut restored = init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    backup::restore(snapshot.to_str().unwrap(), &mut restored).unwrap();
    assert!(backup::verify_counts(&source_db, &restored).unwrap());

    let digest: String = restored
        .query_row("SELECT sha256 FROM sources", [], |row| row.get(0))
        .unwrap();
    std::fs::write(raw_objects::root(&restored).unwrap().join(digest), b"tampered").unwrap();

    assert!(backup::verify_counts(&source_db, &restored).is_err());
}

#[test]
fn verify_counts_rejects_schema_version_drift() {
    let dir = tempfile::tempdir().unwrap();
    let source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    let mut other_db = init_workspace(dir.path().join("other.sqlite").to_str().unwrap()).unwrap();
    other_db
        .execute(
            "UPDATE workspace_meta SET value='4' WHERE key='schema_version'",
            [],
        )
        .unwrap();

    assert!(backup::verify_counts(&source_db, &other_db).is_err());
}

#[test]
fn verify_counts_rejects_foreign_key_damage_even_when_counts_match() {
    let dir = tempfile::tempdir().unwrap();
    let mut source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    let mut other_db = init_workspace(dir.path().join("other.sqlite").to_str().unwrap()).unwrap();
    source::import_source(&mut source_db, b"same", "same.bin", None).unwrap();
    source::import_source(&mut other_db, b"same", "same.bin", None).unwrap();

    other_db.execute_batch("PRAGMA foreign_keys=OFF").unwrap();
    other_db
        .execute(
            "INSERT INTO review_events(knowledge_id, action, reviewer) VALUES('missing', 'review', 'tester')",
            [],
        )
        .unwrap();

    assert!(backup::verify_counts(&source_db, &other_db).is_err());
}
