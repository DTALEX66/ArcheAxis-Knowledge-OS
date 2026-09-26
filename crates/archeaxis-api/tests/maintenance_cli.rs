use archeaxis_domain::source;
use archeaxis_store_sqlite::writer::Store;
use serde_json::Value;
use std::{path::Path, process::Command};

fn core() -> &'static str {
    env!("CARGO_BIN_EXE_archeaxis-api")
}

fn invoke(action: &str, database: &Path, artifact: &Path) -> (i32, Value) {
    let output = Command::new(core())
        .args([
            format!("--maintenance-{action}"),
            database.to_string_lossy().into_owned(),
            artifact.to_string_lossy().into_owned(),
        ])
        .output()
        .expect("maintenance Core executable starts");
    let value: Value = serde_json::from_slice(&output.stdout).expect("Core emits JSON receipt");
    (output.status.code().unwrap_or(-1), value)
}

async fn add_source(database: &Path, bytes: &'static [u8], name: &'static str) {
    let store = Store::open(database).unwrap();
    store
        .submit(move |connection| source::import_source(connection, bytes, name, None))
        .await
        .unwrap()
        .unwrap();
}

fn source_count(database: &Path) -> i64 {
    rusqlite::Connection::open(database)
        .unwrap()
        .query_row("SELECT count(*) FROM sources", [], |row| row.get(0))
        .unwrap()
}

#[tokio::test]
async fn rust_core_backup_restore_preserves_canonical_database_and_raw_objects() {
    let directory = tempfile::tempdir().unwrap();
    let database = directory.path().join("workspace.sqlite");
    let snapshot = directory.path().join("snapshot.sqlite");

    add_source(&database, b"original source bytes", "original.txt").await;
    let (code, receipt) = invoke("backup", &database, &snapshot);
    assert_eq!(code, 0, "{receipt}");
    assert_eq!(receipt["ok"], true);
    assert!(snapshot.is_file());
    assert!(Path::new(&format!("{}.objects", snapshot.display())).is_dir());
    assert_eq!(source_count(&database), 1);

    add_source(&database, b"later source bytes", "later.txt").await;
    assert_eq!(source_count(&database), 2);

    let (code, receipt) = invoke("restore", &database, &snapshot);
    assert_eq!(code, 0, "{receipt}");
    assert_eq!(receipt["ok"], true);
    assert_eq!(receipt["verified"], true);
    assert_eq!(source_count(&database), 1);
    let preserved = Path::new(receipt["preserved_previous"].as_str().unwrap());
    assert!(preserved.is_file());
    assert!(Path::new(&format!("{}.objects", preserved.display())).is_dir());
}

#[tokio::test]
async fn maintenance_cli_refuses_to_run_while_another_core_owns_the_writer_lock() {
    let directory = tempfile::tempdir().unwrap();
    let database = directory.path().join("workspace.sqlite");
    let snapshot = directory.path().join("snapshot.sqlite");
    add_source(&database, b"owner-held source", "owner.txt").await;
    let owner = Store::open(&database).unwrap();

    let (code, receipt) = invoke("backup", &database, &snapshot);
    assert_ne!(code, 0, "{receipt}");
    assert_eq!(receipt["ok"], false);
    assert!(!snapshot.exists());

    drop(owner);
}

#[tokio::test]
async fn maintenance_backup_refuses_to_overwrite_an_existing_artifact() {
    let directory = tempfile::tempdir().unwrap();
    let database = directory.path().join("workspace.sqlite");
    let snapshot = directory.path().join("snapshot.sqlite");
    add_source(&database, b"source bytes", "source.txt").await;
    std::fs::write(&snapshot, b"owner artifact").unwrap();

    let (code, receipt) = invoke("backup", &database, &snapshot);
    assert_ne!(code, 0, "{receipt}");
    assert_eq!(receipt["ok"], false);
    assert_eq!(std::fs::read(&snapshot).unwrap(), b"owner artifact");
}
