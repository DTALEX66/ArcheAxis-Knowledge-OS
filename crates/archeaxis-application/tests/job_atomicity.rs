use archeaxis_application::{bootstrap, jobs};
use archeaxis_domain::source::{self, ImportOutcome};
use rusqlite::Connection;

fn fixture() -> (tempfile::TempDir, Connection, String) {
    let dir = tempfile::tempdir().unwrap();
    let (mut conn, _) = bootstrap(dir.path().join("jobs.sqlite").to_str().unwrap()).unwrap();
    let sid = match source::import_source(&mut conn, b"original", "file.txt", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } => source_id,
        _ => unreachable!(),
    };
    jobs::enqueue(&mut conn, "job", "text", &sid).unwrap();
    (dir, conn, sid)
}

#[test]
fn duplicate_completion_is_durable_and_conflicting_content_is_rejected() {
    let (dir, mut conn, _) = fixture();
    jobs::complete(&mut conn, "job", "engine", "derived", None).unwrap();
    drop(conn);
    let (mut conn, _) = bootstrap(dir.path().join("jobs.sqlite").to_str().unwrap()).unwrap();
    jobs::complete(&mut conn, "job", "engine", "derived", None).unwrap();
    assert!(jobs::complete(&mut conn, "job", "engine", "different", None).is_err());
    let count: i64 = conn.query_row("SELECT count(*) FROM transforms", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 1);
}

#[test]
fn insert_failure_never_marks_job_completed() {
    let (_dir, mut conn, _) = fixture();
    conn.execute_batch("CREATE TRIGGER reject_transform BEFORE INSERT ON transforms BEGIN SELECT RAISE(ABORT, 'injected failure'); END;").unwrap();
    assert!(jobs::complete(&mut conn, "job", "engine", "derived", None).is_err());
    assert_eq!(jobs::job_state(&conn, "job").unwrap().as_deref(), Some(jobs::STATE_QUEUED));
    let count: i64 = conn.query_row("SELECT count(*) FROM transforms", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 0);
}

#[test]
fn enqueue_conflict_and_missing_jobs_are_errors() {
    let (_dir, mut conn, sid) = fixture();
    jobs::enqueue(&mut conn, "job", "text", &sid).unwrap();
    assert!(jobs::enqueue(&mut conn, "job", "ocr", &sid).is_err());
    assert!(jobs::complete(&mut conn, "missing", "engine", "text", None).is_err());
    assert!(jobs::fail(&mut conn, "missing", "oops").is_err());
}

#[test]
fn terminal_results_cannot_be_overwritten() {
    let (_dir, mut conn, sid) = fixture();
    jobs::complete(&mut conn, "job", "engine", "derived", None).unwrap();
    assert!(jobs::fail(&mut conn, "job", "late failure").is_err());
    jobs::enqueue(&mut conn, "failed", "text", &sid).unwrap();
    jobs::fail(&mut conn, "failed", "failure \"quoted\"\nline").unwrap();
    let receipt: String = conn.query_row("SELECT loss_receipt FROM jobs WHERE job_id='failed'", [], |r| r.get(0)).unwrap();
    let value: serde_json::Value = serde_json::from_str(&receipt).unwrap();
    assert_eq!(value["error"], "failure \"quoted\"\nline");
    assert!(jobs::complete(&mut conn, "failed", "engine", "late", None).is_err());
}

#[test]
fn succeeded_state_matches_contract() {
    assert_eq!(jobs::STATE_COMPLETED, archeaxis_contracts::JOB_SUCCEEDED);
}

#[test]
fn job_update_failure_also_rolls_back_inserted_transform() {
    let (_dir, mut conn, _) = fixture();
    conn.execute_batch("CREATE TRIGGER reject_completion BEFORE UPDATE ON jobs BEGIN SELECT RAISE(ABORT, 'injected update failure'); END;").unwrap();
    assert!(jobs::complete(&mut conn, "job", "engine", "derived", None).is_err());
    let count: i64 = conn.query_row("SELECT count(*) FROM transforms", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 0);
    assert_eq!(jobs::job_state(&conn, "job").unwrap().as_deref(), Some(jobs::STATE_QUEUED));
}

#[test]
fn future_and_unrelated_databases_are_unchanged_on_rejection() {
    let (dir, conn, _) = fixture();
    conn.execute("UPDATE workspace_meta SET value='999' WHERE key='schema_version'", []).unwrap();
    drop(conn);
    let path = dir.path().join("jobs.sqlite");
    let before = std::fs::read(&path).unwrap();
    assert!(bootstrap(path.to_str().unwrap()).is_err());
    assert_eq!(std::fs::read(path).unwrap(), before);
    let legacy = dir.path().join("legacy.sqlite");
    let conn = Connection::open(&legacy).unwrap();
    conn.execute("CREATE TABLE legacy_user_data(body TEXT)", []).unwrap();
    drop(conn);
    let before = std::fs::read(&legacy).unwrap();
    assert!(bootstrap(legacy.to_str().unwrap()).is_err());
    assert_eq!(std::fs::read(legacy).unwrap(), before);
}

#[test]
fn concurrent_open_migrates_v1_once_and_preserves_existing_jobs() {
    let (dir, conn, _) = fixture();
    conn.execute_batch("ALTER TABLE jobs DROP COLUMN completion_digest;
        ALTER TABLE jobs DROP COLUMN transform_id;
        UPDATE workspace_meta SET value='1' WHERE key='schema_version';
        UPDATE jobs SET state='completed';").unwrap();
    drop(conn);
    let barrier = std::sync::Arc::new(std::sync::Barrier::new(4));
    let handles: Vec<_> = (0..4).map(|_| {
        let barrier = barrier.clone();
        let path = dir.path().join("jobs.sqlite");
        std::thread::spawn(move || {
            barrier.wait();
            bootstrap(path.to_str().unwrap()).map(|_| ())
        })
    }).collect();
    for handle in handles { handle.join().unwrap().unwrap(); }
    let (conn, _) = bootstrap(dir.path().join("jobs.sqlite").to_str().unwrap()).unwrap();
    assert_eq!(jobs::job_state(&conn, "job").unwrap().as_deref(), Some(jobs::STATE_COMPLETED));
    let version: String = conn.query_row("SELECT value FROM workspace_meta WHERE key='schema_version'", [], |r| r.get(0)).unwrap();
    assert_eq!(version, archeaxis_store_sqlite::SCHEMA_VERSION.to_string());
}
