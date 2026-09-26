use archeaxis_domain::{
    backup, knowledge,
    machine::{self, MachineTask},
    source,
};
use archeaxis_store_sqlite::{init_workspace, raw_objects};
use rusqlite::Connection;

#[test]
fn backup_restore_preserves_machine_failure_retest_and_knowledge_binding() {
    let dir = tempfile::tempdir().unwrap();
    let mut source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    let accepted = knowledge::create_knowledge(
        &mut source_db,
        "FACTUAL_CLAIM",
        "synthetic accepted fact for backup continuity",
        "accepted",
        None,
        None,
        "owner",
    )
    .unwrap();
    machine::record_machine_task(
        &mut source_db,
        &MachineTask {
            task_id: "synthetic-failed-task",
            principal: "machine",
            conditions: "offline; synthetic fixed sample",
            knowledge_version: Some(&accepted),
            method_version: Some("method-synthetic-1"),
            tool_version: Some("tool-synthetic-1"),
            model_version: "synthetic-model-1",
            scope: "one synthetic extraction",
            outcome: "failed",
            failure: Some("synthetic missing extraction"),
            retest_of: None,
        },
    )
    .unwrap();
    machine::record_machine_task(
        &mut source_db,
        &MachineTask {
            task_id: "synthetic-retest-task",
            principal: "machine",
            conditions: "offline; same synthetic fixed sample after human correction",
            knowledge_version: Some(&accepted),
            method_version: Some("method-synthetic-1"),
            tool_version: Some("tool-synthetic-1"),
            model_version: "synthetic-model-1",
            scope: "one synthetic corrected extraction",
            outcome: "succeeded",
            failure: None,
            retest_of: Some("synthetic-failed-task"),
        },
    )
    .unwrap();

    let snapshot = dir.path().join("snapshot.sqlite");
    backup::backup(&source_db, snapshot.to_str().unwrap()).unwrap();
    let snapshot_db = Connection::open(snapshot.to_str().unwrap()).unwrap();
    assert!(backup::verify_counts(&source_db, &snapshot_db).unwrap());

    let mut restored_db =
        init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    backup::restore(snapshot.to_str().unwrap(), &mut restored_db).unwrap();
    assert!(backup::verify_counts(&restored_db, &snapshot_db).unwrap());

    let failed = machine::machine_task(&restored_db, "synthetic-failed-task")
        .unwrap()
        .expect("failed machine receipt restored");
    assert_eq!(failed.knowledge_version.as_deref(), Some(accepted.as_str()));
    assert_eq!(failed.outcome, "failed");
    assert_eq!(
        failed.failure.as_deref(),
        Some("synthetic missing extraction")
    );

    let retest = machine::machine_task(&restored_db, "synthetic-retest-task")
        .unwrap()
        .expect("retest machine receipt restored");
    assert_eq!(
        retest.conditions,
        "offline; same synthetic fixed sample after human correction"
    );
    assert_eq!(retest.knowledge_version.as_deref(), Some(accepted.as_str()));
    assert_eq!(retest.method_version.as_deref(), Some("method-synthetic-1"));
    assert_eq!(retest.tool_version.as_deref(), Some("tool-synthetic-1"));
    assert_eq!(retest.model_version, "synthetic-model-1");
    assert_eq!(retest.scope, "one synthetic corrected extraction");
    assert_eq!(retest.outcome, "succeeded");
    assert_eq!(retest.retest_of.as_deref(), Some("synthetic-failed-task"));
}

#[test]
fn missing_original_never_replaces_an_existing_backup_or_publishes_a_partial_one() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    source::import_source(&mut conn, b"original", "original.bin", None).unwrap();
    let old = dir.path().join("old.sqlite");
    backup::backup(&conn, old.to_str().unwrap()).unwrap();
    let original_snapshot = std::fs::read(&old).unwrap();
    source::import_source(&mut conn, b"new source", "new.bin", None).unwrap();
    let digest: String = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE original_name='new.bin'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    std::fs::remove_file(raw_objects::root(&conn).unwrap().join(digest)).unwrap();
    assert!(backup::backup(&conn, old.to_str().unwrap()).is_err());
    assert!(
        std::fs::read(&old).unwrap() == original_snapshot,
        "failed backup overwrote old snapshot"
    );
    let fresh = dir.path().join("fresh.sqlite");
    assert!(backup::backup(&conn, fresh.to_str().unwrap()).is_err());
    assert!(
        !fresh.exists(),
        "failed backup published a partial snapshot"
    );
    assert!(!dir.path().join("fresh.sqlite.objects").exists());
}

#[test]
fn online_backup_restores_original_bytes_and_rejects_tampering_without_changing_destination() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    source::import_source(&mut conn, b"\x00\xfforiginal\r\n", "original.bin", None).unwrap();
    let digest: String = conn
        .query_row("SELECT sha256 FROM sources", [], |r| r.get(0))
        .unwrap();
    let snapshot = dir.path().join("snapshot.sqlite");
    backup::backup(&conn, snapshot.to_str().unwrap()).unwrap();
    let mut dst = init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    backup::restore(snapshot.to_str().unwrap(), &mut dst).unwrap();
    assert_eq!(
        raw_objects::read(&dst, &digest).unwrap(),
        b"\x00\xfforiginal\r\n"
    );
    source::import_source(&mut dst, b"keep me", "keep.bin", None).unwrap();
    std::fs::write(
        dir.path().join("snapshot.sqlite.objects").join(&digest),
        b"corrupt",
    )
    .unwrap();
    assert!(backup::restore(snapshot.to_str().unwrap(), &mut dst).is_err());
    assert_eq!(
        dst.query_row("SELECT count(*) FROM sources", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        2
    );
}

#[test]
fn verify_counts_rejects_a_tampered_persisted_source_object() {
    let dir = tempfile::tempdir().unwrap();
    let mut source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    source::import_source(&mut source_db, b"original", "original.bin", None).unwrap();
    let snapshot = dir.path().join("snapshot.sqlite");
    backup::backup(&source_db, snapshot.to_str().unwrap()).unwrap();

    let mut restored =
        init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    backup::restore(snapshot.to_str().unwrap(), &mut restored).unwrap();
    assert!(backup::verify_counts(&source_db, &restored).unwrap());

    let digest: String = restored
        .query_row("SELECT sha256 FROM sources", [], |row| row.get(0))
        .unwrap();
    std::fs::write(
        raw_objects::root(&restored).unwrap().join(digest),
        b"tampered",
    )
    .unwrap();

    assert!(backup::verify_counts(&source_db, &restored).is_err());
}

#[test]
fn verify_counts_rejects_schema_version_drift() {
    let dir = tempfile::tempdir().unwrap();
    let source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    let other_db = init_workspace(dir.path().join("other.sqlite").to_str().unwrap()).unwrap();
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

#[test]
fn verify_counts_rejects_schema_catalog_change_even_when_counts_match() {
    let dir = tempfile::tempdir().unwrap();
    let mut source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    let other_path = dir.path().join("other.sqlite");
    let mut other_db = init_workspace(other_path.to_str().unwrap()).unwrap();
    source::import_source(&mut source_db, b"same", "same.bin", None).unwrap();
    source::import_source(&mut other_db, b"same", "same.bin", None).unwrap();

    let index_name: String = other_db
        .query_row(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='sources' LIMIT 1",
            [],
            |row| row.get(0),
        )
        .unwrap();
    other_db.execute_batch("PRAGMA writable_schema=ON").unwrap();
    other_db
        .execute(
            "DELETE FROM sqlite_master WHERE type='index' AND name=?1",
            [index_name],
        )
        .unwrap();
    other_db
        .execute_batch("PRAGMA writable_schema=OFF")
        .unwrap();
    drop(other_db);
    let other_db = Connection::open(other_path).unwrap();

    assert!(backup::verify_counts(&source_db, &other_db).is_err());
}

#[test]
fn verify_counts_covers_workspace_metadata_and_schema_drift() {
    let dir = tempfile::tempdir().unwrap();
    let source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    let extra_row_db =
        init_workspace(dir.path().join("extra-row.sqlite").to_str().unwrap()).unwrap();
    extra_row_db
        .execute(
            "INSERT INTO workspace_meta(key, value) VALUES('extra', 'untracked')",
            [],
        )
        .unwrap();
    assert!(!backup::verify_counts(&source_db, &extra_row_db).unwrap());

    let extra_table_db =
        init_workspace(dir.path().join("extra-table.sqlite").to_str().unwrap()).unwrap();
    extra_table_db
        .execute_batch("CREATE TABLE migration_extra(id INTEGER PRIMARY KEY, value TEXT);")
        .unwrap();
    assert!(!backup::verify_counts(&source_db, &extra_table_db).unwrap());
}

#[test]
fn verify_counts_rejects_same_count_different_row_content() {
    let dir = tempfile::tempdir().unwrap();
    let mut source_db = init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    let mut restored =
        init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    knowledge::create_knowledge(
        &mut source_db,
        "FACTUAL_CLAIM",
        "original row",
        "candidate",
        None,
        None,
        "test",
    )
    .unwrap();
    knowledge::create_knowledge(
        &mut restored,
        "FACTUAL_CLAIM",
        "different row",
        "candidate",
        None,
        None,
        "test",
    )
    .unwrap();

    assert!(!backup::verify_counts(&source_db, &restored).unwrap());
}

#[test]
fn verify_counts_uses_a_stable_read_snapshot_during_concurrent_source_writes() {
    use std::sync::{
        atomic::{AtomicBool, Ordering},
        mpsc,
    };
    use std::time::Duration;

    let dir = tempfile::tempdir().unwrap();
    let source_path = dir.path().join("source.sqlite");
    let source_db = init_workspace(source_path.to_str().unwrap()).unwrap();
    let restored = init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    source_db.execute_batch("PRAGMA journal_mode=WAL;").unwrap();
    restored.execute_batch("PRAGMA journal_mode=WAL;").unwrap();

    let (entered_tx, entered_rx) = mpsc::channel();
    let (release_tx, release_rx) = mpsc::channel();
    let first_compare = AtomicBool::new(false);
    source_db
        .create_collation("verification_gate", move |left, right| {
            if !first_compare.swap(true, Ordering::SeqCst) {
                entered_tx.send(()).unwrap();
                release_rx.recv().unwrap();
            }
            left.cmp(right)
        })
        .unwrap();
    restored
        .create_collation("verification_gate", |left, right| left.cmp(right))
        .unwrap();

    for conn in [&source_db, &restored] {
        conn.execute_batch(
            "CREATE TABLE a_blocker(value TEXT COLLATE verification_gate);
             INSERT INTO a_blocker(value) VALUES('a'),('b');
             CREATE TABLE z_mutated(value TEXT NOT NULL);
             INSERT INTO z_mutated(value) VALUES('before');",
        )
        .unwrap();
    }

    let verify = std::thread::spawn(move || backup::verify_counts(&source_db, &restored));
    entered_rx
        .recv_timeout(Duration::from_secs(5))
        .expect("verification did not reach the deterministic pause point");

    let writer = Connection::open(source_path).unwrap();
    writer
        .execute(
            "INSERT INTO z_mutated(value) VALUES('during verification')",
            [],
        )
        .unwrap();
    release_tx.send(()).unwrap();

    assert!(verify.join().unwrap().unwrap());
}
